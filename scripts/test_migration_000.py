#!/usr/bin/env python3
"""
Migration 000_wip_drift_baseline Validation Tests
Validates the forward-port migration that captures 2-month WIP drift
(5 new tables + 7 indexes) as a deterministic, replayable artifact.

Phase 07 - DB WIP Investigation.

Run:  .venv/bin/python scripts/test_migration_000.py
Exit: 0 = all pass, 1 = failures detected.

Constraints:
- stdlib only (sqlite3, unittest, pathlib, tempfile, subprocess, re)
- does NOT touch data/vna_alerts.db (WIP binary must remain M status)
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
MIGRATION_PATH = REPO_ROOT / "scripts" / "migrations" / "000_wip_drift_baseline.sql"
MODELS_PATH = REPO_ROOT / "backend" / "db" / "models.py"

EXPECTED_TABLES = {
    "alert_feedback",
    "alert_assignments",
    "manual_interventions",
    "alert_intervention_links",
    "pending_notifications",
}

# Maps WIP table name -> SQL_CREATE_* constant name in models.py
TABLE_TO_MODELS_CONST = {
    "alert_feedback": "SQL_CREATE_ALERT_FEEDBACK",
    "alert_assignments": "SQL_CREATE_ALERT_ASSIGNMENTS",
    "manual_interventions": "SQL_CREATE_MANUAL_INTERVENTIONS",
    "alert_intervention_links": "SQL_CREATE_ALERT_INTERVENTION_LINKS",
    "pending_notifications": "SQL_CREATE_PENDING_NOTIFICATIONS",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Print with timestamp (match scripts/test_integration.py convention)."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def _load_migration_sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8")


def _load_models_source() -> str:
    return MODELS_PATH.read_text(encoding="utf-8")


def _extract_models_create_block(models_src: str, const_name: str) -> str:
    """Extract the SQL string assigned to SQL_CREATE_<TABLE> in models.py."""
    pattern = rf'{re.escape(const_name)}\s*=\s*"""(.*?)"""'
    m = re.search(pattern, models_src, re.DOTALL)
    if not m:
        raise AssertionError(f"{const_name} not found in backend/db/models.py")
    return m.group(1)


def _apply_migration(conn: sqlite3.Connection, sql: str) -> None:
    """Apply the migration SQL script to the given connection."""
    conn.executescript(sql)


def _list_user_tables(conn: sqlite3.Connection) -> set:
    cur = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return {row[0] for row in cur.fetchall()}


def _table_sql(conn: sqlite3.Connection, table: str) -> str:
    cur = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    row = cur.fetchone()
    return row[0] if row else ""


def _sqlite_master_snapshot(conn: sqlite3.Connection) -> list:
    """Return all sqlite_master rows sorted for deterministic comparison."""
    cur = conn.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' "
        "ORDER BY type, name"
    )
    return cur.fetchall()


def _normalize_ws(s: str) -> str:
    """Collapse whitespace for lenient substring comparisons."""
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestMigration000(unittest.TestCase):
    """Validation suite for scripts/migrations/000_wip_drift_baseline.sql."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.migration_sql = _load_migration_sql()
        cls.models_src = _load_models_source()

    def _fresh_db(self) -> tuple:
        """Create a fresh tempfile SQLite DB. Returns (path, conn)."""
        fd, path = tempfile.mkstemp(suffix=".db", prefix="mig000_test_")
        os.close(fd)
        conn = sqlite3.connect(path)
        self.addCleanup(conn.close)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        return path, conn

    # --- 1 -----------------------------------------------------------------
    def test_migration_applies_on_empty_db(self):
        """Applies 000_wip_drift_baseline.sql on a fresh empty DB w/o error."""
        _, conn = self._fresh_db()
        try:
            _apply_migration(conn, self.migration_sql)
        except Exception as e:  # noqa: BLE001
            self.fail(f"Migration raised on empty DB: {e!r}")

    # --- 2 -----------------------------------------------------------------
    def test_creates_exactly_5_expected_tables(self):
        """After apply, sqlite_master contains EXACTLY the 5 expected tables."""
        _, conn = self._fresh_db()
        _apply_migration(conn, self.migration_sql)
        tables = _list_user_tables(conn)
        # sqlite_sequence is a reserved sqlite_* name and is filtered out.
        self.assertEqual(
            tables,
            EXPECTED_TABLES,
            f"Table set mismatch. got={sorted(tables)} "
            f"expected={sorted(EXPECTED_TABLES)}",
        )

    # --- 3 -----------------------------------------------------------------
    def test_idempotent_apply(self):
        """Applying the migration twice yields identical sqlite_master state."""
        _, conn = self._fresh_db()
        _apply_migration(conn, self.migration_sql)
        snap1 = _sqlite_master_snapshot(conn)

        # Second apply should not raise (CREATE ... IF NOT EXISTS).
        try:
            _apply_migration(conn, self.migration_sql)
        except Exception as e:  # noqa: BLE001
            self.fail(f"Second migration apply raised: {e!r}")

        snap2 = _sqlite_master_snapshot(conn)
        self.assertEqual(
            snap1, snap2,
            "sqlite_master differs between single-apply and double-apply",
        )

    # --- 4 -----------------------------------------------------------------
    def test_check_constraints_match_wip_schema(self):
        """
        For each table with a CHECK constraint, verify the CHECK clause
        (normalized whitespace) is a substring of the matching
        SQL_CREATE_* block in backend/db/models.py.

        Catches drift between migration DDL and ORM declaration.
        """
        _, conn = self._fresh_db()
        _apply_migration(conn, self.migration_sql)

        check_pattern = re.compile(
            r"CHECK\s*\([^)]*\([^)]*\)[^)]*\)|CHECK\s*\([^)]*\)",
            re.IGNORECASE | re.DOTALL,
        )

        for table, const_name in TABLE_TO_MODELS_CONST.items():
            with self.subTest(table=table):
                db_sql = _table_sql(conn, table)
                self.assertTrue(
                    db_sql,
                    f"Table {table} not present in sqlite_master",
                )
                models_sql = _extract_models_create_block(
                    self.models_src, const_name
                )
                models_sql_norm = _normalize_ws(models_sql)

                for check_match in check_pattern.findall(db_sql):
                    check_norm = _normalize_ws(check_match)
                    self.assertIn(
                        check_norm,
                        models_sql_norm,
                        f"CHECK constraint in {table} not found in "
                        f"{const_name}:\n  check={check_norm!r}",
                    )

    # --- 5 -----------------------------------------------------------------
    def test_pending_notifications_cascade_delete(self):
        """pending_notifications must declare ON DELETE CASCADE on alert_id FK."""
        _, conn = self._fresh_db()
        _apply_migration(conn, self.migration_sql)

        sql = _table_sql(conn, "pending_notifications")
        self.assertTrue(sql, "pending_notifications not created")
        sql_norm = _normalize_ws(sql).upper()
        self.assertIn(
            "ON DELETE CASCADE",
            sql_norm,
            "pending_notifications missing ON DELETE CASCADE on alerts FK",
        )
        # Also confirm FK targets alerts.alert_id.
        self.assertIn(
            "REFERENCES ALERTS(ALERT_ID)",
            sql_norm,
            "pending_notifications FK should target alerts(alert_id)",
        )

    # --- 6 -----------------------------------------------------------------
    def test_no_insert_statements(self):
        """Baseline DDL-only: source .sql must not contain any INSERT."""
        # Strip SQL line comments so we don't trip on the word "INSERT" inside
        # an accidental comment; be strict on actual statements.
        src = self.migration_sql
        # Remove line comments (-- ...).
        stripped = re.sub(r"--[^\n]*", "", src)
        # Remove block comments /* ... */ if any.
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL)

        self.assertNotRegex(
            stripped,
            r"(?i)\bINSERT\b",
            "Migration 000 must be DDL-only; found INSERT in source",
        )

    # --- 7 -----------------------------------------------------------------
    def test_migration_file_is_tracked_in_git(self):
        """SC-3 invariant: migration file must be tracked in git."""
        result = subprocess.run(
            [
                "git",
                "-C", str(REPO_ROOT),
                "ls-files", "--error-unmatch",
                "scripts/migrations/000_wip_drift_baseline.sql",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"git ls-files --error-unmatch failed: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}",
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    log("=" * 80)
    log("Migration 000_wip_drift_baseline - Validation Suite")
    log("=" * 80)
    log(f"Migration file: {MIGRATION_PATH}")
    log(f"Models file:    {MODELS_PATH}")

    if not MIGRATION_PATH.exists():
        log(f"FATAL: migration file not found: {MIGRATION_PATH}")
        return 1
    if not MODELS_PATH.exists():
        log(f"FATAL: models file not found: {MODELS_PATH}")
        return 1

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMigration000)
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
