#!/usr/bin/env python3
"""Phase 10.1 Plan 01 — Smoke tests for apply_migration_004.py.

Tests against a synthesized tmpdb (no live DB mutation). Uses the
importlib shim pattern from Phase 10 (scripts/ has no __init__.py).

Test classes:
  TestMigration004Apply   — first-apply conversion, idempotency, MAX fix, dry-run
  TestMigration004SQL     — SQL file structure assertions (no DB)
"""
import importlib.util
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DRIVER_PATH = REPO_ROOT / "scripts" / "apply_migration_004.py"
SQL_PATH = REPO_ROOT / "scripts" / "migrations" / "004_canonicalize_alerts_created_at.sql"
ROLLBACK_SQL = REPO_ROOT / "scripts" / "migrations" / "004_rollback.sql"
VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"

# Canonical regex: 'YYYY-MM-DD HH:MM:SS.ffffff'
CANONICAL_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}$")

# Seed data — all 4 input format patterns + 2 already-canonical
# (alert_id, created_at_input, expected_canonical_output)
SEED_ROWS = [
    ("aw1", "2026-04-23T21:42:50+00:00",         "2026-04-23 21:42:50.000000"),
    ("aw2", "2026-04-23T21:42:50.142222+00:00",   "2026-04-23 21:42:50.142222"),
    ("nv1", "2026-04-23T21:42:51.042222",         "2026-04-23 21:42:51.042222"),
    ("nv2", "2026-04-23T21:42:52",                "2026-04-23 21:42:52.000000"),
    ("sp1", "2026-04-23 21:42:53",                "2026-04-23 21:42:53.000000"),
    ("sp2", "2026-04-23 21:42:54.999999",         "2026-04-23 21:42:54.999999"),
]


def _make_tmpdb(tmpdir: Path) -> Path:
    """Create a minimal post-003 schema tmpdb with SEED_ROWS in alerts."""
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

        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY,
            alert_id    TEXT UNIQUE NOT NULL,
            created_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id                   INTEGER PRIMARY KEY,
            run_id               TEXT UNIQUE NOT NULL,
            status               TEXT,
            alerts_written_count INTEGER NOT NULL DEFAULT 0
        );
    """)
    for alert_id, created_at, _ in SEED_ROWS:
        conn.execute(
            "INSERT OR IGNORE INTO alerts(alert_id, created_at) VALUES (?, ?)",
            (alert_id, created_at),
        )
    conn.commit()
    conn.close()
    return db


def _make_shim(tmpdir: Path, tmp_db: Path) -> Path:
    """Write a one-liner shim that loads the driver and patches DB_PATH."""
    shim = tmpdir / "run_driver_004.py"
    shim.write_text(
        "import sys; from pathlib import Path; import importlib.util\n"
        f"spec = importlib.util.spec_from_file_location('apply_migration_004', {str(DRIVER_PATH)!r})\n"
        "d = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(d)\n"
        f"d.DB_PATH = Path({str(tmp_db)!r})\n"
        f"d.BAK_PATH = Path({str(tmp_db)!r} + '.pre.bak')\n"
        "d.main()\n"
    )
    return shim


class TestMigration004Apply(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="mig004_"))
        self.tmp_db = _make_tmpdb(self.tmpdir)
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

    def _get_created_at(self):
        conn = sqlite3.connect(str(self.tmp_db))
        rows = {r[0]: r[1] for r in conn.execute(
            "SELECT alert_id, created_at FROM alerts"
        ).fetchall()}
        conn.close()
        return rows

    def test_first_apply_converts_all_formats(self):
        """After first apply, all 6 rows must match canonical regex and expected value."""
        result = self._run_driver()
        self.assertEqual(result.returncode, 0,
                         f"Driver failed.\nstdout: {result.stdout}\nstderr: {result.stderr}")
        rows = self._get_created_at()
        for alert_id, _, expected in SEED_ROWS:
            actual = rows[alert_id]
            self.assertRegex(actual, CANONICAL_RE,
                             f"{alert_id}: {actual!r} does not match canonical regex")
            self.assertEqual(actual, expected,
                             f"{alert_id}: expected {expected!r}, got {actual!r}")

    def test_second_apply_idempotent_skip(self):
        """Second invocation exits 0 with SKIP message; rows unchanged."""
        self._run_driver()  # first apply
        rows_after_first = self._get_created_at()
        result = self._run_driver()  # second apply
        self.assertEqual(result.returncode, 0,
                         f"Second apply failed.\nstdout: {result.stdout}\nstderr: {result.stderr}")
        self.assertIn("SKIP", result.stdout,
                      f"Second apply must emit SKIP. stdout: {result.stdout}")
        rows_after_second = self._get_created_at()
        self.assertEqual(rows_after_first, rows_after_second,
                         "Row values must be unchanged after second apply")

    def test_max_created_at_returns_true_latest_post_migration(self):
        """Pre-migration MAX(created_at) returns wrong row (aware T '+' sorts below digits);
        post-migration MAX returns the chronologically latest row."""
        conn = sqlite3.connect(str(self.tmp_db))
        # Remove all SEED_ROWS and insert our two targeted rows
        conn.execute("DELETE FROM alerts")
        # Row A: aware T format (chronologically earlier but '+' sorts below digits so MAX picks it)
        conn.execute("INSERT INTO alerts(alert_id, created_at) VALUES (?, ?)",
                     ("rowA", "2026-04-23T21:42:50+00:00"))
        # Row B: space-sep naive later by 1 microsecond
        conn.execute("INSERT INTO alerts(alert_id, created_at) VALUES (?, ?)",
                     ("rowB", "2026-04-23 21:42:51.000001"))
        conn.commit()
        # Pre-migration: MAX returns rowA because '+' (ASCII 43) < digits ('2' = ASCII 50)
        pre_max = conn.execute("SELECT alert_id FROM alerts ORDER BY created_at DESC LIMIT 1").fetchone()[0]
        conn.close()
        self.assertEqual(pre_max, "rowA",
                         "Pre-migration MAX should return rowA (aware T format bug)")
        # Post-migration
        result = self._run_driver()
        self.assertEqual(result.returncode, 0,
                         f"Driver failed.\nstdout: {result.stdout}\nstderr: {result.stderr}")
        conn = sqlite3.connect(str(self.tmp_db))
        post_max = conn.execute("SELECT alert_id FROM alerts ORDER BY created_at DESC LIMIT 1").fetchone()[0]
        conn.close()
        self.assertEqual(post_max, "rowB",
                         "Post-migration MAX should return rowB (later timestamp)")

    def test_dry_run_no_mutation(self):
        """--dry-run exits 0 without modifying any rows."""
        original_rows = self._get_created_at()
        result = self._run_driver(["--dry-run"])
        self.assertEqual(result.returncode, 0,
                         f"Dry-run failed.\nstdout: {result.stdout}\nstderr: {result.stderr}")
        after_rows = self._get_created_at()
        self.assertEqual(original_rows, after_rows,
                         "dry-run must not mutate any row")

    def test_rollback_sql_removes_ledger_only(self):
        """After apply + rollback.sql: ledger row gone, alert values remain canonical."""
        self._run_driver()  # apply
        # Verify canonical format post-apply
        rows = self._get_created_at()
        for alert_id, _, _ in SEED_ROWS:
            self.assertRegex(rows[alert_id], CANONICAL_RE)
        # Apply rollback SQL
        rollback_sql = ROLLBACK_SQL.read_text(encoding="utf-8")
        conn = sqlite3.connect(str(self.tmp_db))
        conn.executescript(rollback_sql)
        conn.close()
        # Ledger row must be gone
        conn = sqlite3.connect(str(self.tmp_db))
        ledger = conn.execute(
            "SELECT 1 FROM vna_schema_migrations WHERE migration_id='004_canonicalize_alerts_created_at'"
        ).fetchone()
        conn.close()
        self.assertIsNone(ledger, "Ledger row should be gone after rollback SQL")
        # Alert rows must remain canonical (one-way — format normalization is not reversed)
        rows_after = self._get_created_at()
        for alert_id, _, _ in SEED_ROWS:
            self.assertRegex(rows_after[alert_id], CANONICAL_RE,
                             f"{alert_id}: row should remain canonical after rollback SQL")

    def test_ledger_insert_without_or_replace(self):
        """SQL file must NOT contain OR REPLACE in the INSERT INTO vna_schema_migrations."""
        sql_text = SQL_PATH.read_text(encoding="utf-8")
        # Find the INSERT statement
        insert_lines = [line for line in sql_text.splitlines()
                        if "INSERT INTO VNA_SCHEMA_MIGRATIONS" in line.upper()]
        self.assertTrue(insert_lines, "No INSERT INTO vna_schema_migrations found in SQL file")
        for line in insert_lines:
            self.assertNotIn("OR REPLACE", line.upper(),
                             f"INSERT must not contain OR REPLACE: {line!r}")

    def test_pragma_foreign_keys_off_before_begin(self):
        """PRAGMA foreign_keys=OFF must appear BEFORE BEGIN TRANSACTION in SQL file."""
        sql_text = SQL_PATH.read_text(encoding="utf-8")
        lines = sql_text.splitlines()
        pragma_line = None
        begin_line = None
        for i, line in enumerate(lines):
            stripped = line.strip().upper()
            if "PRAGMA FOREIGN_KEYS=OFF" in stripped and pragma_line is None:
                pragma_line = i
            if stripped.startswith("BEGIN") and "TRANSACTION" in stripped and begin_line is None:
                begin_line = i
        self.assertIsNotNone(pragma_line, "PRAGMA foreign_keys=OFF not found in SQL file")
        self.assertIsNotNone(begin_line, "BEGIN TRANSACTION not found in SQL file")
        self.assertLess(pragma_line, begin_line,
                        f"PRAGMA (line {pragma_line}) must precede BEGIN (line {begin_line})")


if __name__ == "__main__":
    unittest.main(verbosity=2)
