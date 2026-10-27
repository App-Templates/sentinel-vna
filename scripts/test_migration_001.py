#!/usr/bin/env python3
"""
Migration 001_expand_channel_groups Validation Tests
Validates the CHECK-expansion migration that closes the 2-month silent-failure
root cause on alerts.channel_group and alerts.alert_rule, plus tightens
pending_notifications CHECKs.

Phase 08 - Schema Migration + ETL Extensions (SCHEMA-01).

Run:  .venv/bin/python scripts/test_migration_001.py
Exit: 0 = all pass, 1 = failures detected.

Constraints:
- stdlib only (sqlite3, unittest, pathlib, tempfile, subprocess, re, os, datetime)
- does NOT touch data/vna_alerts.db (live DB must not be mutated in Plan 01)
- uses tempfile for ephemeral SQLite DBs
"""

import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_000 = REPO_ROOT / "scripts" / "migrations" / "000_wip_drift_baseline.sql"
MIGRATION_001 = REPO_ROOT / "scripts" / "migrations" / "001_expand_channel_groups.sql"
MODELS_PATH = REPO_ROOT / "backend" / "db" / "models.py"


# ---------------------------------------------------------------------------
# Domain constants (authoritative from models.py:182 and models.py:184)
# ---------------------------------------------------------------------------

EXPECTED_CHANNEL_GROUPS = (
    "'GOOGLE_ADEX'",
    "'OPEN_BIDDING'",
    "'HEADER_BIDDING_MAGNITE'",
    "'HEADER_BIDDING_PUBMATIC'",
    "'TAM'",
    "'DIRECT'",
    "'DEAL'",
    "'GOOGLE'",
)

EXPECTED_ALERT_RULES = (
    "'A0'",
    "'A1'",
    "'A2'",
    "'A3'",
    "'A5'",
    "'A6'",
    "'A7'",
    "'A8'",
)

# A4 is deliberately skipped — must NOT appear in alert_rule CHECK
FORBIDDEN_ALERT_RULES = ("'A4'",)

EXPECTED_SEVERITY_VALUES = ("'P0'", "'P1'", "'P2'")


# ---------------------------------------------------------------------------
# Stale DDL from wip-schema.sql lines 55-75 + 135-143
# These define the pre-migration state that 001.sql must expand.
# Defined as constants so the test suite does NOT depend on models.py
# (Plan 02 will change models.py; this test must survive that change).
# ---------------------------------------------------------------------------

STALE_ALERTS_DDL = """
CREATE TABLE alerts (
    alert_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('P0', 'P1', 'P2')),
    channel_group TEXT NOT NULL CHECK(channel_group IN ('GOOGLE', 'OPEN_BIDDING')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'ACK', 'RESOLVED', 'SNOOZED')),
    alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A0', 'A1', 'A2', 'A3')),
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
    updated_at TEXT NOT NULL
);
"""

STALE_ALERTS_INDEXES = """
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_severity ON alerts(severity);
"""

# pending_notifications from 000.sql — no CHECKs (what migration 001 tightens)
STALE_PENDING_NOTIFICATIONS_DDL = """
CREATE TABLE pending_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    channel_group TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);
"""

STALE_PENDING_NOTIFICATIONS_INDEX = """
CREATE INDEX idx_pending_notifications_created_at ON pending_notifications(created_at);
"""

# Sample rows to insert before migration (using values legal under stale CHECKs)
_SAMPLE_ALERT_ROWS = [
    ("ALT-20260101-120000-P0", "2026-01-01T12:00:00Z", "P0", "GOOGLE", "OPEN",
     "A0", 100.0, 200.0, -50.0, "TRAFFIC", "[]", "[]", "{}", "{}", 0.1,
     "athena", "1.0.0", "2026-01-01T12:00:00Z", "2026-01-01T12:00:00Z"),
    ("ALT-20260101-120001-P1", "2026-01-01T12:00:01Z", "P1", "GOOGLE", "OPEN",
     "A1", 80.0, 100.0, -20.0, "COVERAGE", "[]", "[]", "{}", "{}", 0.2,
     "athena", "1.0.0", "2026-01-01T12:00:01Z", "2026-01-01T12:00:01Z"),
    ("ALT-20260101-120002-P2", "2026-01-01T12:00:02Z", "P2", "OPEN_BIDDING", "OPEN",
     "A2", 60.0, 80.0, -25.0, "MIXED", "[]", "[]", "{}", "{}", 0.3,
     "athena", "1.0.0", "2026-01-01T12:00:02Z", "2026-01-01T12:00:02Z"),
    ("ALT-20260101-120003-P0", "2026-01-01T12:00:03Z", "P0", "GOOGLE", "OPEN",
     "A3", 50.0, 100.0, -50.0, "REVENUE_ONLY", "[]", "[]", "{}", "{}", 0.4,
     "athena", "1.0.0", "2026-01-01T12:00:03Z", "2026-01-01T12:00:03Z"),
    ("ALT-20260101-120004-P1", "2026-01-01T12:00:04Z", "P1", "OPEN_BIDDING", "ACK",
     "A0", 90.0, 100.0, -10.0, "TRAFFIC", "[]", "[]", "{}", "{}", 0.5,
     "athena", "1.0.0", "2026-01-01T12:00:04Z", "2026-01-01T12:00:04Z"),
]

_SAMPLE_PENDING_ROWS = [
    (1, "ALT-20260101-120000-P0", "P0", "GOOGLE", "2026-01-01T12:00:00Z", "2026-01-01T12:00:00Z"),
    (2, "ALT-20260101-120001-P1", "P1", "GOOGLE", "2026-01-01T12:00:01Z", "2026-01-01T12:00:01Z"),
    (3, "ALT-20260101-120002-P2", "P2", "OPEN_BIDDING", "2026-01-01T12:00:02Z", "2026-01-01T12:00:02Z"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def _load_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_models_source() -> str:
    return MODELS_PATH.read_text(encoding="utf-8")


def _extract_models_create_block(models_src: str, const_name: str) -> str:
    """Extract the SQL string assigned to SQL_CREATE_<TABLE> in models.py."""
    pattern = rf'{re.escape(const_name)}\s*=\s*"""(.*?)"""'
    m = re.search(pattern, models_src, re.DOTALL)
    if not m:
        raise AssertionError(f"{const_name} not found in backend/db/models.py")
    return m.group(1)


def _table_sql(conn: sqlite3.Connection, table: str) -> str:
    cur = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    row = cur.fetchone()
    return row[0] if row else ""


def _normalize_ws(s: str) -> str:
    """Collapse whitespace for lenient substring comparisons."""
    return re.sub(r"\s+", " ", s).strip()


def _apply_sql(conn: sqlite3.Connection, sql: str) -> None:
    """Apply a SQL script to the given connection."""
    conn.executescript(sql)


def _build_baseline_db() -> tuple:
    """
    Create a tempfile DB with the 11-table Phase 07 baseline.

    Steps:
      1. Apply STALE_ALERTS_DDL + STALE_ALERTS_INDEXES (the pre-migration alerts table)
      2. Apply the remaining WIP tables from 000_wip_drift_baseline.sql
         (alert_feedback, alert_assignments, manual_interventions,
          alert_intervention_links, pending_notifications)

    Returns (path, conn).  The DB is ready for 001.sql to be applied.
    """
    fd, path = tempfile.mkstemp(suffix=".db", prefix="mig001_test_")
    os.close(fd)
    conn = sqlite3.connect(path)

    # Step 1: create stale alerts table (2-value CHECKs)
    _apply_sql(conn, STALE_ALERTS_DDL)
    _apply_sql(conn, STALE_ALERTS_INDEXES)

    # Step 2: apply 000 to create the 5 WIP tables (alert_feedback,
    # alert_assignments, manual_interventions, alert_intervention_links,
    # pending_notifications). 000.sql uses CREATE IF NOT EXISTS so applying
    # to a DB that already has alerts is fine.
    migration_000 = _load_sql(MIGRATION_000)
    _apply_sql(conn, migration_000)

    return path, conn


def _build_baseline_db_with_rows() -> tuple:
    """
    Same as _build_baseline_db but also inserts sample rows into alerts and
    pending_notifications so row-preservation tests have data to verify.
    """
    path, conn = _build_baseline_db()

    # Disable FK checks so we can insert into pending_notifications after
    # the alerts inserts (FK references alerts).
    conn.execute("PRAGMA foreign_keys=ON;")

    conn.executemany(
        """
        INSERT INTO alerts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        _SAMPLE_ALERT_ROWS,
    )

    conn.executemany(
        """
        INSERT INTO pending_notifications(id, alert_id, severity, channel_group,
                                          timestamp, created_at)
        VALUES (?,?,?,?,?,?)
        """,
        _SAMPLE_PENDING_ROWS,
    )
    conn.commit()

    return path, conn


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestMigration001(unittest.TestCase):
    """Validation suite for scripts/migrations/001_expand_channel_groups.sql."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.migration_001_sql = _load_sql(MIGRATION_001)
        cls.models_src = _load_models_source()

    def _fresh_baseline_db(self) -> tuple:
        """Return (path, conn) with 11-table baseline (no rows)."""
        path, conn = _build_baseline_db()
        self.addCleanup(conn.close)
        self.addCleanup(lambda p=path: os.path.exists(p) and os.unlink(p))
        return path, conn

    def _fresh_baseline_db_with_rows(self) -> tuple:
        """Return (path, conn) with 11-table baseline + sample rows."""
        path, conn = _build_baseline_db_with_rows()
        self.addCleanup(conn.close)
        self.addCleanup(lambda p=path: os.path.exists(p) and os.unlink(p))
        return path, conn

    # --- 1 ------------------------------------------------------------------
    def test_migration_applies_on_baseline_db(self):
        """Migration 001 applies on 11-table Phase 07 baseline without error."""
        _, conn = self._fresh_baseline_db()
        try:
            _apply_sql(conn, self.migration_001_sql)
        except Exception as e:  # noqa: BLE001
            self.fail(f"Migration 001 raised on baseline DB: {e!r}")

    # --- 2 ------------------------------------------------------------------
    def test_channel_group_check_has_8_values(self):
        """
        After migration, alerts.channel_group CHECK contains all 8 expected
        values and does NOT contain the stale 2-value constraint signature.
        """
        _, conn = self._fresh_baseline_db()
        _apply_sql(conn, self.migration_001_sql)

        alerts_sql = _table_sql(conn, "alerts")
        self.assertTrue(alerts_sql, "alerts table not found in sqlite_master")

        for val in EXPECTED_CHANNEL_GROUPS:
            with self.subTest(channel_group=val):
                self.assertIn(
                    val,
                    alerts_sql,
                    f"Expected channel_group value {val} missing from alerts DDL",
                )

        # Stale signature must be gone (2-value only CHECK)
        stale_sig = "channel_group IN ('GOOGLE', 'OPEN_BIDDING')"
        self.assertNotIn(
            stale_sig,
            alerts_sql,
            "Stale 2-value channel_group CHECK still present after migration",
        )

    # --- 3 ------------------------------------------------------------------
    def test_alert_rule_check_has_8_values_skipping_a4(self):
        """
        After migration, alerts.alert_rule CHECK contains A0-A3, A5-A8
        and does NOT contain A4.
        """
        _, conn = self._fresh_baseline_db()
        _apply_sql(conn, self.migration_001_sql)

        alerts_sql = _table_sql(conn, "alerts")
        self.assertTrue(alerts_sql, "alerts table not found in sqlite_master")

        # Positive assertions: all expected rules present
        for rule in EXPECTED_ALERT_RULES:
            with self.subTest(alert_rule=rule):
                self.assertIn(
                    rule,
                    alerts_sql,
                    f"Expected alert_rule value {rule} missing from alerts DDL",
                )

        # Explicit negative: A4 MUST NOT appear in alert_rule CHECK
        for forbidden in FORBIDDEN_ALERT_RULES:
            with self.subTest(forbidden_alert_rule=forbidden):
                # We only check the alert_rule CHECK clause, not the whole file.
                # Extract the alert_rule CHECK substring to avoid false negatives
                # from other column names or comments containing 'A4'.
                alert_rule_match = re.search(
                    r"CHECK\(alert_rule IN \([^)]+\)\)",
                    alerts_sql,
                )
                self.assertIsNotNone(
                    alert_rule_match,
                    "Could not find CHECK(alert_rule IN ...) in alerts DDL",
                )
                self.assertNotIn(
                    forbidden,
                    alert_rule_match.group(0),
                    f"Forbidden alert_rule value {forbidden} found in alerts DDL CHECK — "
                    "A4 is deliberately skipped",
                )

    # --- 4 ------------------------------------------------------------------
    def test_pending_notifications_check_tightened(self):
        """
        After migration, pending_notifications has:
        - CHECK(severity IN ('P0', 'P1', 'P2'))
        - CHECK(channel_group IN (...)) with all 8 values
        """
        _, conn = self._fresh_baseline_db()
        _apply_sql(conn, self.migration_001_sql)

        pn_sql = _table_sql(conn, "pending_notifications")
        self.assertTrue(pn_sql, "pending_notifications not found in sqlite_master")

        # Severity tightened
        self.assertIn(
            "CHECK(severity IN ('P0', 'P1', 'P2'))",
            pn_sql,
            "pending_notifications.severity CHECK not tightened to 3 values",
        )

        # channel_group tightened to 8 values
        for val in EXPECTED_CHANNEL_GROUPS:
            with self.subTest(pending_channel_group=val):
                self.assertIn(
                    val,
                    pn_sql,
                    f"Expected channel_group value {val} missing from pending_notifications DDL",
                )

    # --- 5 ------------------------------------------------------------------
    def test_alerts_checks_byte_identical_to_models_py(self):
        """
        The channel_group and alert_rule CHECK clauses in the migrated alerts
        table are byte-for-byte identical (whitespace-normalized) to those in
        SQL_CREATE_ALERTS in backend/db/models.py.

        This is the primary drift-prevention assertion.
        """
        _, conn = self._fresh_baseline_db()
        _apply_sql(conn, self.migration_001_sql)

        alerts_sql = _table_sql(conn, "alerts")
        self.assertTrue(alerts_sql, "alerts table not found in sqlite_master")

        # Extract channel_group CHECK from models.py SQL_CREATE_ALERTS
        models_alerts_block = _extract_models_create_block(
            self.models_src, "SQL_CREATE_ALERTS"
        )

        # Extract CHECK(channel_group ...) from models block
        cg_pattern = re.compile(r"CHECK\(channel_group IN \([^)]+\)\)")
        models_cg_match = cg_pattern.search(models_alerts_block)
        self.assertIsNotNone(
            models_cg_match,
            "CHECK(channel_group ...) not found in SQL_CREATE_ALERTS in models.py",
        )
        models_cg_clause = _normalize_ws(models_cg_match.group(0))

        db_cg_match = cg_pattern.search(alerts_sql)
        self.assertIsNotNone(
            db_cg_match,
            "CHECK(channel_group ...) not found in migrated alerts table DDL",
        )
        db_cg_clause = _normalize_ws(db_cg_match.group(0))

        self.assertEqual(
            db_cg_clause,
            models_cg_clause,
            "channel_group CHECK clause differs between migrated DB and models.py — "
            "byte-identical requirement violated",
        )

        # Extract CHECK(alert_rule ...) from models block
        ar_pattern = re.compile(r"CHECK\(alert_rule IN \([^)]+\)\)")
        models_ar_match = ar_pattern.search(models_alerts_block)
        self.assertIsNotNone(
            models_ar_match,
            "CHECK(alert_rule ...) not found in SQL_CREATE_ALERTS in models.py",
        )
        models_ar_clause = _normalize_ws(models_ar_match.group(0))

        db_ar_match = ar_pattern.search(alerts_sql)
        self.assertIsNotNone(
            db_ar_match,
            "CHECK(alert_rule ...) not found in migrated alerts table DDL",
        )
        db_ar_clause = _normalize_ws(db_ar_match.group(0))

        self.assertEqual(
            db_ar_clause,
            models_ar_clause,
            "alert_rule CHECK clause differs between migrated DB and models.py — "
            "byte-identical requirement violated",
        )

    # --- 6 ------------------------------------------------------------------
    def test_row_preservation(self):
        """
        Rows existing before migration are preserved (row count unchanged).
        Inserts 5 alerts + 3 pending_notifications, applies 001, verifies counts.
        """
        _, conn = self._fresh_baseline_db_with_rows()

        pre_alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        pre_pending = conn.execute(
            "SELECT COUNT(*) FROM pending_notifications"
        ).fetchone()[0]

        self.assertEqual(pre_alerts, 5, "Expected 5 pre-migration alerts")
        self.assertEqual(pre_pending, 3, "Expected 3 pre-migration pending_notifications")

        _apply_sql(conn, self.migration_001_sql)

        post_alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        post_pending = conn.execute(
            "SELECT COUNT(*) FROM pending_notifications"
        ).fetchone()[0]

        self.assertEqual(
            post_alerts,
            pre_alerts,
            f"Row count changed for alerts: {pre_alerts} → {post_alerts}",
        )
        self.assertEqual(
            post_pending,
            pre_pending,
            f"Row count changed for pending_notifications: {pre_pending} → {post_pending}",
        )

    # --- 7 ------------------------------------------------------------------
    def test_migration_is_ddl_only_no_data_insert(self):
        """
        Migration source file contains no arbitrary data INSERTs.
        Only allowed INSERT forms:
          - INSERT INTO <t> SELECT * FROM _<t>_old_001   (row-copy)
          - INSERT OR REPLACE INTO vna_schema_migrations  (ledger)
        No INSERT INTO alerts VALUES or INSERT INTO pending_notifications VALUES.
        """
        migration_sql = self.migration_001_sql
        # Strip SQL comments to avoid false positives
        stripped = re.sub(r"--[^\n]*", "", migration_sql)
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL)

        # Must not contain bare data inserts into real tables
        forbidden_patterns = [
            r"(?i)\bINSERT\s+INTO\s+alerts\s+VALUES\b",
            r"(?i)\bINSERT\s+INTO\s+pending_notifications\s+VALUES\b",
        ]
        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(
                    re.search(pattern, stripped),
                    f"Migration 001 must not contain data INSERT matching {pattern!r}; "
                    "only row-copy (INSERT SELECT) and ledger insert are allowed",
                )

    # --- 8 ------------------------------------------------------------------
    def test_vna_schema_migrations_ledger_row(self):
        """
        After migration, vna_schema_migrations table contains exactly one row
        with migration_id='001_expand_channel_groups'.
        """
        _, conn = self._fresh_baseline_db()
        _apply_sql(conn, self.migration_001_sql)

        count = conn.execute(
            "SELECT COUNT(*) FROM vna_schema_migrations "
            "WHERE migration_id='001_expand_channel_groups'"
        ).fetchone()[0]

        self.assertEqual(
            count,
            1,
            "Expected exactly 1 ledger row for '001_expand_channel_groups' "
            f"in vna_schema_migrations; got {count}",
        )

    # --- 9 ------------------------------------------------------------------
    def test_second_apply_is_guarded(self):
        """
        A second naked apply (without driver pre-check) MUST raise an error.

        IDEMPOTENCY CONTRACT: The driver (Plan 03 apply script / test harness)
        must check sqlite_master for 'GOOGLE_ADEX' before invoking 001.sql.
        This test asserts that skipping the guard causes a clear failure
        (not silent corruption), enforcing the driver-guard invariant.

        Expected error: sqlite3.IntegrityError (UNIQUE constraint failed:
        vna_schema_migrations.migration_id) — the ledger INSERT at the top of
        the transaction fails before any DDL executes, and the whole transaction
        rolls back cleanly.
        """
        _, conn = self._fresh_baseline_db()
        # First apply — must succeed
        try:
            _apply_sql(conn, self.migration_001_sql)
        except Exception as e:  # noqa: BLE001
            self.fail(f"First apply raised unexpectedly: {e!r}")

        # Second apply — must raise a database error (IntegrityError for UNIQUE
        # constraint violation on vna_schema_migrations.migration_id)
        with self.assertRaises(
            sqlite3.DatabaseError,  # covers IntegrityError (subclass of DatabaseError)
            msg=(
                "Second naked apply of 001.sql must raise sqlite3.DatabaseError "
                "(typically IntegrityError: UNIQUE constraint failed on "
                "vna_schema_migrations.migration_id) to enforce the driver-guard "
                "invariant; silent double-apply would corrupt the DB"
            ),
        ):
            _apply_sql(conn, self.migration_001_sql)

    # --- 10 -----------------------------------------------------------------
    def test_migration_file_is_tracked_in_git(self):
        """Migration 001 file is tracked in git (not untracked)."""
        result = subprocess.run(
            [
                "git",
                "-C", str(REPO_ROOT),
                "ls-files", "--error-unmatch",
                "scripts/migrations/001_expand_channel_groups.sql",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"git ls-files --error-unmatch failed for 001_expand_channel_groups.sql: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}",
        )

    # --- 11 -----------------------------------------------------------------
    def test_file_has_header_documenting_rollback(self):
        """
        Migration header must contain:
        - 'data/vna_alerts.db.pre-phase08.bak' (rollback artifact reference)
        - 'IDEMPOTENCY CONTRACT' (driver-guard documentation)
        """
        migration_sql = self.migration_001_sql

        self.assertIn(
            "data/vna_alerts.db.pre-phase08.bak",
            migration_sql,
            "Migration header must reference the rollback backup artifact "
            "'data/vna_alerts.db.pre-phase08.bak'",
        )

        self.assertIn(
            "IDEMPOTENCY CONTRACT",
            migration_sql,
            "Migration must contain 'IDEMPOTENCY CONTRACT' documentation in header",
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    log("=" * 80)
    log("Migration 001_expand_channel_groups - Validation Suite")
    log("=" * 80)
    log(f"Migration 000: {MIGRATION_000}")
    log(f"Migration 001: {MIGRATION_001}")
    log(f"Models file:   {MODELS_PATH}")

    if not MIGRATION_000.exists():
        log(f"FATAL: migration 000 file not found: {MIGRATION_000}")
        return 1
    if not MIGRATION_001.exists():
        log(f"FATAL: migration 001 file not found: {MIGRATION_001}")
        return 1
    if not MODELS_PATH.exists():
        log(f"FATAL: models file not found: {MODELS_PATH}")
        return 1

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMigration001)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    log("=" * 80)
    log(
        f"Summary: ran={result.testsRun} "
        f"failures={len(result.failures)} "
        f"errors={len(result.errors)} "
        f"skipped={len(result.skipped)}"
    )
    log("=" * 80)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
