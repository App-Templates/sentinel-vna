#!/usr/bin/env python3
"""Phase 17.4 Plan 04 — Smoke tests for apply_migration_006.py (D2CLOSE-03).

Tests against a synthesized tmpdb (no live DB mutation). Uses the
importlib shim pattern from Phase 10.1 (scripts/ has no __init__.py).

5 test methods:
  test_migration_006_marks_exactly_199_rows  — count exactness
  test_migration_006_data_source_unchanged   — data_source field preserved (D-11)
  test_migration_006_google_adex_untouched   — 39 GOOGLE_ADEX rows stay deprecated=0
  test_migration_006_idempotent              — second apply exits 0 (skip); DB unchanged
  test_migration_006_rollback                — rollback SQL restores deprecated=0 + NULL reason

Seed shape mirrors live DB pre-Plan-04:
  39  GOOGLE_ADEX  data_source='backfill' deprecated=0   ← rewrite-script target
  199 other-channel data_source='backfill' deprecated=0  ← migration 006 target
  200 parquet       deprecated=1                          ← already deprecated (unchanged)
  Total: 438 alerts (mirrors live DB count comment in SQL header)
"""
import importlib.util
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DRIVER_PATH = REPO_ROOT / "scripts" / "apply_migration_006.py"
SQL_PATH = REPO_ROOT / "scripts" / "migrations" / "006_backfill_split_marking.sql"
ROLLBACK_SQL_PATH = REPO_ROOT / "scripts" / "migrations" / "006_rollback.sql"
VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"

# Expected counts matching plan invariants
EXPECTED_DEPRECATED_COUNT = 199
EXPECTED_GOOGLE_ADEX_BACKFILL = 39
EXPECTED_TOTAL_BACKFILL = 238  # 39 + 199 (data_source unchanged)
EXPECTED_PARQUET_DEPRECATED = 200  # already-deprecated rows (should be untouched)

# Canonical deprecation reason string used by migration 006
DEPRECATION_REASON = "synthetic-era pre-H6-fix, Phase 21 Athena dependency"

# Channel groups for other-channel seed rows (7 channels × 28-33 rows ≈ 199)
# Must match alerts table CHECK constraint values
OTHER_CHANNELS = [
    "DEAL",                   # 26 rows
    "DIRECT",                 # 33 rows
    "GOOGLE",                 # 24 rows
    "HEADER_BIDDING_MAGNITE", # 29 rows
    "HEADER_BIDDING_PUBMATIC",# 29 rows
    "OPEN_BIDDING",           # 30 rows
    "TAM",                    # 28 rows
]

# Row counts per channel (sum = 199)
OTHER_CHANNEL_COUNTS = {
    "DEAL": 26,
    "DIRECT": 33,
    "GOOGLE": 24,
    "HEADER_BIDDING_MAGNITE": 29,
    "HEADER_BIDDING_PUBMATIC": 29,
    "OPEN_BIDDING": 30,
    "TAM": 28,
}

# Minimal CREATE TABLE DDL matching live DB schema (deprecated + deprecation_reason added Phase 09)
ALERTS_DDL = """
CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('P0', 'P1', 'P2')),
    channel_group TEXT NOT NULL CHECK(channel_group IN (
        'GOOGLE_ADEX', 'OPEN_BIDDING', 'HEADER_BIDDING_MAGNITE',
        'HEADER_BIDDING_PUBMATIC', 'TAM', 'DIRECT', 'DEAL', 'GOOGLE'
    )),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'ACK', 'RESOLVED', 'SNOOZED')),
    alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A0', 'A1', 'A2', 'A3', 'A5', 'A6', 'A7', 'A8')),
    revenue_current REAL NOT NULL,
    revenue_baseline REAL NOT NULL,
    revenue_delta_pct REAL NOT NULL,
    triage_label TEXT NOT NULL,
    contributors_json TEXT DEFAULT '[]',
    geo_breakdown_json TEXT DEFAULT '[]',
    environment_split_json TEXT DEFAULT '{}',
    insights_json TEXT DEFAULT '{}',
    execution_time_sec REAL DEFAULT 0.0,
    data_source TEXT DEFAULT 'athena',
    config_version TEXT DEFAULT '1.0.0',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deprecated INTEGER NOT NULL DEFAULT 0 CHECK(deprecated IN (0, 1)),
    deprecation_reason TEXT
);
"""


def _tmpdb_with_schema(tmpdir: Path) -> Path:
    """Create a minimal tmpdb mirroring the live DB schema + seed data.

    Seed:
      39  rows: channel_group='GOOGLE_ADEX',   data_source='backfill', deprecated=0
      199 rows: channel_group != 'GOOGLE_ADEX', data_source='backfill', deprecated=0
      200 rows: channel_group='GOOGLE',          data_source='parquet',  deprecated=1
              (simulates the Phase 09 MIGRATE-01 already-deprecated parquet rows)

    Total: 438 rows — mirrors comment in 006_backfill_split_marking.sql header.
    """
    db = tmpdir / "vna_alerts.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS vna_schema_migrations (
            migration_id TEXT PRIMARY KEY,
            applied_at   TEXT NOT NULL
        );
        INSERT OR IGNORE INTO vna_schema_migrations(migration_id, applied_at)
            VALUES ('001_expand_channel_groups',    '2026-04-23 10:00:00');
        INSERT OR IGNORE INTO vna_schema_migrations(migration_id, applied_at)
            VALUES ('002_add_alert_deprecation',    '2026-04-23 10:01:00');
        INSERT OR IGNORE INTO vna_schema_migrations(migration_id, applied_at)
            VALUES ('003_add_alerts_written_count', '2026-04-23 10:02:00');
        INSERT OR IGNORE INTO vna_schema_migrations(migration_id, applied_at)
            VALUES ('004_canonicalize_alerts_created_at', '2026-04-24 09:00:00');
    """)
    conn.executescript(ALERTS_DDL)

    # Seed 39 GOOGLE_ADEX backfill rows (rewrite-script target — should be untouched by mig 006)
    for i in range(39):
        conn.execute(
            "INSERT INTO alerts(alert_id, timestamp, severity, channel_group, alert_rule, "
            "revenue_current, revenue_baseline, revenue_delta_pct, triage_label, "
            "data_source, created_at, updated_at, deprecated) "
            "VALUES (?, '2026-03-22 01:00:00', 'P2', 'GOOGLE_ADEX', 'A1', "
            "736.01, 800.0, -7.9, 'REVENUE_DROP', 'backfill', "
            "'2026-03-22 01:00:00.000000', '2026-03-22 01:00:00.000000', 0)",
            (f"GA-BACKFILL-{i:04d}",),
        )

    # Seed 199 non-GOOGLE_ADEX backfill rows (migration 006 target)
    row_idx = 0
    for channel, count in OTHER_CHANNEL_COUNTS.items():
        for j in range(count):
            conn.execute(
                "INSERT INTO alerts(alert_id, timestamp, severity, channel_group, alert_rule, "
                "revenue_current, revenue_baseline, revenue_delta_pct, triage_label, "
                "data_source, created_at, updated_at, deprecated) "
                "VALUES (?, '2026-03-20 07:00:00', 'P2', ?, 'A1', "
                "500.0, 600.0, -16.7, 'REVENUE_DROP', 'backfill', "
                "'2026-03-20 07:00:00.000000', '2026-03-20 07:00:00.000000', 0)",
                (f"CH-BACKFILL-{row_idx:04d}", channel),
            )
            row_idx += 1

    assert row_idx == EXPECTED_DEPRECATED_COUNT, (
        f"Seed loop produced {row_idx} other-channel rows, expected {EXPECTED_DEPRECATED_COUNT}"
    )

    # Seed 200 parquet deprecated=1 rows (Phase 09 MIGRATE-01 already-deprecated)
    for k in range(200):
        conn.execute(
            "INSERT INTO alerts(alert_id, timestamp, severity, channel_group, alert_rule, "
            "revenue_current, revenue_baseline, revenue_delta_pct, triage_label, "
            "data_source, created_at, updated_at, deprecated, deprecation_reason) "
            "VALUES (?, '2025-12-01 00:00:00', 'P2', 'GOOGLE', 'A1', "
            "100.0, 120.0, -16.7, 'REVENUE_DROP', 'parquet', "
            "'2025-12-01 00:00:00.000000', '2025-12-01 00:00:00.000000', 1, 'Phase 09 MIGRATE-01')",
            (f"PQ-DEPRECATED-{k:04d}",),
        )

    conn.commit()
    conn.close()
    return db


def _make_shim(tmpdir: Path, tmp_db: Path) -> Path:
    """Write a one-liner shim that loads the driver and patches DB_PATH."""
    shim = tmpdir / "run_driver_006.py"
    shim.write_text(
        "import sys; from pathlib import Path; import importlib.util\n"
        f"spec = importlib.util.spec_from_file_location('apply_migration_006', {str(DRIVER_PATH)!r})\n"
        "d = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(d)\n"
        f"d.DB_PATH = Path({str(tmp_db)!r})\n"
        f"d.BAK_PATH = Path({str(tmp_db)!r} + '.pre.bak')\n"
        "d.main()\n"
    )
    return shim


class TestMigration006Apply(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="mig006_"))
        self.tmp_db = _tmpdb_with_schema(self.tmpdir)
        self.shim = _make_shim(self.tmpdir, self.tmp_db)
        self.env = os.environ.copy()
        self.env["VNA_SKIP_LSOF"] = "1"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_driver(self, extra_args=None):
        cmd = [str(VENV_PY), str(self.shim)]
        if extra_args:
            cmd.extend(extra_args)
        return subprocess.run(cmd, capture_output=True, text=True, env=self.env)

    def _query(self, sql, params=()):
        conn = sqlite3.connect(str(self.tmp_db))
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def _count(self, sql, params=()):
        return self._query(sql, params)[0][0]

    # ------------------------------------------------------------------
    # Test 1: migration marks exactly 199 non-GOOGLE_ADEX backfill rows
    # ------------------------------------------------------------------

    def test_migration_006_marks_exactly_199_rows(self):
        """After first apply, exactly 199 non-GOOGLE_ADEX backfill rows must be deprecated=1."""
        result = self._run_driver()
        self.assertEqual(
            result.returncode, 0,
            f"Driver failed.\nstdout: {result.stdout}\nstderr: {result.stderr}",
        )
        count = self._count(
            "SELECT COUNT(*) FROM alerts "
            "WHERE channel_group != 'GOOGLE_ADEX' AND data_source = 'backfill' AND deprecated = 1"
        )
        self.assertEqual(
            count, EXPECTED_DEPRECATED_COUNT,
            f"Expected {EXPECTED_DEPRECATED_COUNT} rows deprecated=1, got {count}\n"
            f"stdout: {result.stdout}",
        )
        # Also verify deprecation_reason is set on all 199
        with_reason = self._count(
            "SELECT COUNT(*) FROM alerts WHERE deprecation_reason = ?",
            (DEPRECATION_REASON,),
        )
        self.assertEqual(
            with_reason, EXPECTED_DEPRECATED_COUNT,
            f"Expected {EXPECTED_DEPRECATED_COUNT} rows with canonical reason, got {with_reason}",
        )

    # ------------------------------------------------------------------
    # Test 2: data_source field UNCHANGED (D-11 audit trail preservation)
    # ------------------------------------------------------------------

    def test_migration_006_data_source_unchanged(self):
        """After apply, all 238 backfill rows still have data_source='backfill'. D-11."""
        result = self._run_driver()
        self.assertEqual(result.returncode, 0,
                         f"Driver failed: {result.stdout}\n{result.stderr}")
        total_backfill = self._count(
            "SELECT COUNT(*) FROM alerts WHERE data_source = 'backfill'"
        )
        self.assertEqual(
            total_backfill, EXPECTED_TOTAL_BACKFILL,
            f"Expected {EXPECTED_TOTAL_BACKFILL} rows with data_source='backfill' post-apply, "
            f"got {total_backfill}. Migration must NOT modify data_source (D-11).",
        )

    # ------------------------------------------------------------------
    # Test 3: GOOGLE_ADEX rows untouched (they are the rewrite-script target)
    # ------------------------------------------------------------------

    def test_migration_006_google_adex_untouched(self):
        """GOOGLE_ADEX backfill rows must stay deprecated=0 AND deprecated=0 post-apply."""
        result = self._run_driver()
        self.assertEqual(result.returncode, 0,
                         f"Driver failed: {result.stdout}\n{result.stderr}")
        google_adex_still_active = self._count(
            "SELECT COUNT(*) FROM alerts "
            "WHERE channel_group = 'GOOGLE_ADEX' AND data_source = 'backfill' AND deprecated = 0"
        )
        self.assertEqual(
            google_adex_still_active, EXPECTED_GOOGLE_ADEX_BACKFILL,
            f"Expected {EXPECTED_GOOGLE_ADEX_BACKFILL} GOOGLE_ADEX backfill rows with deprecated=0 "
            f"post-apply, got {google_adex_still_active}. "
            "Migration 006 must NOT touch GOOGLE_ADEX rows (they are the rewrite-script target).",
        )

    # ------------------------------------------------------------------
    # Test 4: idempotency — second apply exits 0 (skip), DB unchanged
    # ------------------------------------------------------------------

    def test_migration_006_idempotent(self):
        """Second invocation exits 0 with SKIP message; row counts unchanged."""
        # First apply
        result1 = self._run_driver()
        self.assertEqual(result1.returncode, 0,
                         f"First apply failed: {result1.stdout}\n{result1.stderr}")
        count_after_first = self._count(
            "SELECT COUNT(*) FROM alerts WHERE deprecation_reason = ?",
            (DEPRECATION_REASON,),
        )

        # Second apply
        result2 = self._run_driver()
        self.assertEqual(
            result2.returncode, 0,
            f"Second apply must exit 0 (idempotent skip).\n"
            f"stdout: {result2.stdout}\nstderr: {result2.stderr}",
        )
        self.assertIn(
            "SKIP", result2.stdout,
            f"Second apply must emit SKIP. stdout: {result2.stdout}",
        )
        count_after_second = self._count(
            "SELECT COUNT(*) FROM alerts WHERE deprecation_reason = ?",
            (DEPRECATION_REASON,),
        )
        self.assertEqual(
            count_after_first, count_after_second,
            "Row counts must be unchanged after second apply (idempotency violated)",
        )

    # ------------------------------------------------------------------
    # Test 5: rollback SQL restores deprecated=0 + NULL reason; ledger deleted
    # ------------------------------------------------------------------

    def test_migration_006_rollback(self):
        """Apply migration → run rollback SQL → all 199 rows back to deprecated=0 / NULL."""
        # Apply forward migration
        result = self._run_driver()
        self.assertEqual(result.returncode, 0,
                         f"Driver failed: {result.stdout}\n{result.stderr}")

        # Verify migration applied
        deprecated_pre_rollback = self._count(
            "SELECT COUNT(*) FROM alerts WHERE deprecation_reason = ?",
            (DEPRECATION_REASON,),
        )
        self.assertEqual(deprecated_pre_rollback, EXPECTED_DEPRECATED_COUNT,
                         "Pre-rollback: should have 199 marked rows")

        # Apply rollback SQL
        rollback_sql = ROLLBACK_SQL_PATH.read_text(encoding="utf-8")
        conn = sqlite3.connect(str(self.tmp_db))
        conn.executescript(rollback_sql)
        conn.close()

        # All 199 rows should be back to deprecated=0 / NULL reason
        still_deprecated = self._count(
            "SELECT COUNT(*) FROM alerts WHERE deprecation_reason = ?",
            (DEPRECATION_REASON,),
        )
        self.assertEqual(
            still_deprecated, 0,
            f"After rollback, no rows should have canonical deprecation_reason. Got {still_deprecated}.",
        )

        non_google_back_to_zero = self._count(
            "SELECT COUNT(*) FROM alerts "
            "WHERE channel_group != 'GOOGLE_ADEX' AND data_source = 'backfill' "
            "  AND deprecated = 0 AND deprecation_reason IS NULL"
        )
        self.assertEqual(
            non_google_back_to_zero, EXPECTED_DEPRECATED_COUNT,
            f"After rollback, {EXPECTED_DEPRECATED_COUNT} rows should be deprecated=0 / NULL. "
            f"Got {non_google_back_to_zero}.",
        )

        # Ledger row must be gone
        conn = sqlite3.connect(str(self.tmp_db))
        ledger = conn.execute(
            "SELECT 1 FROM vna_schema_migrations WHERE migration_id = '006_backfill_split_marking'"
        ).fetchone()
        conn.close()
        self.assertIsNone(ledger, "Ledger row should be deleted after rollback SQL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
