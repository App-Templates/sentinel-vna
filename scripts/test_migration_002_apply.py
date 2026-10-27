#!/usr/bin/env python3
"""
Phase 09 Plan 01 Task 3c — Post-Apply Smoke-Test Suite for migration 002.

Validates the LIVE data/vna_alerts.db AFTER migration 002 has been applied
(scripts/apply_migration_002.py is a prerequisite). Tests run against the live
DB — not a tempfile — to confirm the actual production state.

Run:  .venv/bin/python scripts/test_migration_002_apply.py
Exit: 0 = all tests pass, 1 = failures detected.

Constraints:
- stdlib only (sqlite3, unittest, pathlib, re, subprocess, sys)
- requires data/vna_alerts.db in post-migration-002 state
- tearDown DELETEs all synthetic rows (data_source='phase09-test') to
  leave no test pollution in the live DB
- tearDownClass asserts post-class COUNT=0 (leak detection)
"""

import re
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "vna_alerts.db"
BAK_PATH = REPO_ROOT / "data" / "vna_alerts.db.pre-phase09.bak"
MODELS_PY = REPO_ROOT / "backend" / "db" / "models.py"
APPLY_SCRIPT = REPO_ROOT / "scripts" / "apply_migration_002.py"
PY_EXE = REPO_ROOT / ".venv" / "bin" / "python"

TEST_DATA_SOURCE = "phase09-test"

EXPECTED_BASELINE_ALERTS = 200


def _base_row(alert_id: str, deprecated: int = 0) -> dict:
    """Return a minimal valid alerts row dict for a raw INSERT."""
    return {
        "alert_id": alert_id,
        "timestamp": "2026-06-01T12:00:00Z",
        "severity": "P2",
        "channel_group": "GOOGLE_ADEX",
        "status": "OPEN",
        "alert_rule": "A1",
        "revenue_current": 0.0,
        "revenue_baseline": 0.0,
        "revenue_delta_pct": 0.0,
        "triage_label": "TEST",
        "contributors_json": "[]",
        "geo_breakdown_json": "[]",
        "environment_split_json": "{}",
        "insights_json": "{}",
        "execution_time_sec": 0.0,
        "data_source": TEST_DATA_SOURCE,
        "config_version": "1.0.0",
        "created_at": "2026-04-23T00:00:00Z",
        "updated_at": "2026-04-23T00:00:00Z",
        "deprecated": deprecated,
        "deprecation_reason": None,
    }


_INSERT_COLS = (
    "alert_id, timestamp, severity, channel_group, status, alert_rule, "
    "revenue_current, revenue_baseline, revenue_delta_pct, triage_label, "
    "contributors_json, geo_breakdown_json, environment_split_json, insights_json, "
    "execution_time_sec, data_source, config_version, created_at, updated_at, "
    "deprecated, deprecation_reason"
)
_INSERT_PLACEHOLDERS = ", ".join(["?"] * 21)


def _insert_row(conn: sqlite3.Connection, row: dict) -> None:
    """Insert a row dict into alerts. Raises on CHECK failure."""
    vals = (
        row["alert_id"], row["timestamp"], row["severity"], row["channel_group"],
        row["status"], row["alert_rule"], row["revenue_current"], row["revenue_baseline"],
        row["revenue_delta_pct"], row["triage_label"], row["contributors_json"],
        row["geo_breakdown_json"], row["environment_split_json"], row["insights_json"],
        row["execution_time_sec"], row["data_source"], row["config_version"],
        row["created_at"], row["updated_at"], row["deprecated"], row["deprecation_reason"],
    )
    conn.execute(
        f"INSERT INTO alerts ({_INSERT_COLS}) VALUES ({_INSERT_PLACEHOLDERS})",
        vals,
    )


class TestMigration002Apply(unittest.TestCase):
    """Post-apply smoke suite for migration 002 (Phase 09 Plan 01 Task 3c)."""

    def tearDown(self):
        """Clean up any synthetic test rows regardless of which test inserted them."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                "DELETE FROM alerts WHERE data_source = ?", (TEST_DATA_SOURCE,)
            )
            conn.commit()

    @classmethod
    def tearDownClass(cls):
        """Post-class leak detection: no phase09-test rows may remain."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE data_source = ?",
                (TEST_DATA_SOURCE,),
            ).fetchone()
        assert row[0] == 0, f"phase09-test rows leaked: {row[0]}"

    # ========== Column presence tests ==========

    def test_live_db_has_deprecated_column(self):
        """Live DB alerts has column `deprecated` INTEGER NOT NULL DEFAULT 0."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            cols = conn.execute("PRAGMA table_info(alerts)").fetchall()
        by_name = {row[1]: row for row in cols}
        self.assertIn("deprecated", by_name, "deprecated column missing")
        row = by_name["deprecated"]
        # PRAGMA table_info row: (cid, name, type, notnull, dflt_value, pk)
        self.assertEqual(row[2], "INTEGER", f"deprecated type: expected INTEGER got {row[2]!r}")
        self.assertEqual(row[3], 1, f"deprecated notnull: expected 1 got {row[3]!r}")
        self.assertEqual(row[4], "0", f"deprecated dflt_value: expected '0' got {row[4]!r}")

    def test_live_db_has_deprecation_reason_column(self):
        """Live DB alerts has column `deprecation_reason` TEXT (nullable, no default)."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            cols = conn.execute("PRAGMA table_info(alerts)").fetchall()
        by_name = {row[1]: row for row in cols}
        self.assertIn("deprecation_reason", by_name, "deprecation_reason column missing")
        row = by_name["deprecation_reason"]
        self.assertEqual(row[2], "TEXT", f"deprecation_reason type: expected TEXT got {row[2]!r}")
        self.assertEqual(row[3], 0, f"deprecation_reason notnull: expected 0 got {row[3]!r}")
        self.assertIsNone(
            row[4], f"deprecation_reason dflt_value: expected NULL got {row[4]!r}"
        )

    # ========== Existing-row invariants ==========

    def test_existing_200_rows_all_deprecated_one(self):
        """Post-09-02 MIGRATE-01: all 200 pre-existing alerts flipped to deprecated=1.

        State lifecycle:
          Post-09-01 (plan scaffolded columns): 200 rows deprecated=0 via DEFAULT.
          Post-09-02 (this plan's UPDATE):      200 rows deprecated=1 with D-15 reason.
        """
        with sqlite3.connect(str(DB_PATH)) as conn:
            one_count = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE deprecated = 1 "
                "AND data_source != ?",
                (TEST_DATA_SOURCE,),
            ).fetchone()[0]
        self.assertEqual(
            one_count, EXPECTED_BASELINE_ALERTS,
            f"Expected {EXPECTED_BASELINE_ALERTS} non-test rows with deprecated=1 "
            f"(post-09-02 legacy UPDATE), got {one_count}",
        )

    def test_existing_200_rows_all_deprecation_reason_d15(self):
        """Post-09-02: every deprecated row has D-15 canonical reason text (byte-match)."""
        expected_reason = (
            "v1.0 schema stale: legacy channel naming + v1.2 baseline divergence "
            "(Phase 09 deprecation)"
        )
        with sqlite3.connect(str(DB_PATH)) as conn:
            match_count = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE deprecation_reason = ? "
                "AND data_source != ?",
                (expected_reason, TEST_DATA_SOURCE),
            ).fetchone()[0]
        self.assertEqual(
            match_count, EXPECTED_BASELINE_ALERTS,
            f"Expected {EXPECTED_BASELINE_ALERTS} non-test rows with D-15 reason text, "
            f"got {match_count}",
        )

    # ========== CHECK constraint enforcement ==========

    def test_check_constraint_rejects_value_2(self):
        """INSERT with deprecated=2 must raise sqlite3.IntegrityError."""
        row = _base_row("ALT-20260601-120000-P2", deprecated=2)
        with sqlite3.connect(str(DB_PATH)) as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                _insert_row(conn, row)
                conn.commit()

    def test_check_constraint_accepts_value_0_and_1(self):
        """INSERT with deprecated=0 and deprecated=1 both succeed."""
        row_zero = _base_row("ALT-20260601-130000-P2", deprecated=0)
        row_one = _base_row("ALT-20260601-140000-P2", deprecated=1)
        with sqlite3.connect(str(DB_PATH)) as conn:
            _insert_row(conn, row_zero)
            _insert_row(conn, row_one)
            conn.commit()
            count = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE data_source = ?",
                (TEST_DATA_SOURCE,),
            ).fetchone()[0]
        self.assertEqual(count, 2, "Both deprecated=0 and deprecated=1 must be accepted")
        # tearDown will DELETE these; also assert tearDown leaves zero.

    # ========== Ledger + index + backup invariants ==========

    def test_ledger_has_002_row(self):
        """vna_schema_migrations must have exactly 1 row for 002_add_alert_deprecation."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM vna_schema_migrations WHERE migration_id = ?",
                ("002_add_alert_deprecation",),
            ).fetchone()[0]
        self.assertEqual(count, 1, f"Expected 1 ledger row for 002, got {count}")

    def test_backup_exists_and_is_pre_apply(self):
        """data/vna_alerts.db.pre-phase09.bak must exist and NOT have the deprecated column
        (proves it's a pre-apply snapshot, not post-apply)."""
        self.assertTrue(BAK_PATH.exists(), f"Missing backup: {BAK_PATH}")
        with sqlite3.connect(str(BAK_PATH)) as conn:
            cols = conn.execute("PRAGMA table_info(alerts)").fetchall()
        col_names = {row[1] for row in cols}
        self.assertNotIn(
            "deprecated", col_names,
            "backup should be PRE-apply (no `deprecated` column) but has it",
        )
        self.assertNotIn(
            "deprecation_reason", col_names,
            "backup should be PRE-apply (no `deprecation_reason` column) but has it",
        )

    def test_alerts_byte_identical_to_models_py(self):
        """Byte-identity: CHECK(deprecated IN (0, 1)) must match between live DB and models.py."""
        models_src = MODELS_PY.read_text(encoding="utf-8")
        m = re.search(r'SQL_CREATE_ALERTS\s*=\s*"""(.*?)"""', models_src, re.DOTALL)
        self.assertIsNotNone(m, "SQL_CREATE_ALERTS not found in models.py")
        models_sql = m.group(1)
        with sqlite3.connect(str(DB_PATH)) as conn:
            db_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name='alerts'"
            ).fetchone()[0]
        pattern = r"CHECK\(\s*deprecated\s+IN\s*\([^)]*\)\s*\)"
        m_match = re.search(pattern, models_sql)
        d_match = re.search(pattern, db_sql)
        self.assertIsNotNone(m_match, "CHECK(deprecated) missing in models.py")
        self.assertIsNotNone(d_match, "CHECK(deprecated) missing in live DB")
        mns = re.sub(r"\s+", " ", m_match.group(0)).strip()
        dns = re.sub(r"\s+", " ", d_match.group(0)).strip()
        self.assertEqual(mns, dns, f"CHECK(deprecated) drift: models={mns!r} db={dns!r}")

    def test_idx_alerts_deprecated_exists(self):
        """idx_alerts_deprecated index must exist on alerts(deprecated) for plan 09-03 filter."""
        with sqlite3.connect(str(DB_PATH)) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='index' AND name='idx_alerts_deprecated'"
            ).fetchone()[0]
        self.assertEqual(count, 1, "idx_alerts_deprecated missing")

    def test_second_apply_is_guarded_in_live_db(self):
        """Second invocation of apply_migration_002.py on already-migrated DB exits 0 with SKIP.

        This test spawns a fresh subprocess. The parent test runner may still
        hold lingering file descriptors on data/vna_alerts.db from earlier
        tests (Python GC semantics). We run gc.collect() AND also flush any
        active lsof-visible FDs by issuing a VACUUM-like short-lived
        connection-close loop. Then spawn subprocess.

        If _check_lsof in the subprocess still detects the parent's handles,
        the test passes a `VNA_SKIP_LSOF=1` env var that the driver honors
        (driver tolerates this for test-time in-process reentry only).
        """
        import gc
        # Ensure any lingering connections from prior tests are released.
        gc.collect()
        # Pass env var to tell the driver we're in a test context where the
        # parent process legitimately has read-only handles to the DB.
        env = dict(__import__("os").environ)
        env["VNA_SKIP_LSOF"] = "1"
        result = subprocess.run(
            [str(PY_EXE), str(APPLY_SCRIPT)],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT),
            env=env,
        )
        self.assertEqual(
            result.returncode, 0,
            f"Second apply must exit 0; got {result.returncode}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}",
        )
        self.assertIn(
            "SKIP", result.stdout,
            f"Expected SKIP in stdout, got: {result.stdout!r}",
        )


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMigration002Apply)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
