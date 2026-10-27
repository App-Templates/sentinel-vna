#!/usr/bin/env python3
"""Phase 10 Plan 01 — Live-DB smoke tests for apply_migration_003.py.

Spawns a fresh temp DB seeded to post-002 state, exercises the driver,
and asserts all post-apply invariants. Uses VNA_SKIP_LSOF=1 escape
hatch (test-context reentry with parent handles — safe).
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DRIVER = REPO_ROOT / "scripts" / "apply_migration_003.py"
LIVE_DB = REPO_ROOT / "data" / "vna_alerts.db"
VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"


class TestMigration003Apply(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="mig003_"))
        self.tmp_db = self.tmpdir / "vna_alerts.db"
        # Copy current live DB (post-002 state) into temp; migration 003 will
        # mutate only this temp copy.
        shutil.copyfile(LIVE_DB, self.tmp_db)
        # Strip -wal/-shm if present (not meaningful after file-level copy).
        for suf in ("-wal", "-shm"):
            p = Path(str(LIVE_DB) + suf)
            tmp_p = Path(str(self.tmp_db) + suf)
            if p.exists():
                shutil.copyfile(p, tmp_p)

        self.env = os.environ.copy()
        self.env["VNA_SKIP_LSOF"] = "1"
        # Point driver at temp DB via monkey-patched DB_PATH module constant.
        # Driver uses REPO_ROOT-relative paths; we override DB_PATH via env.
        # Since apply_migration_003.py hardcodes DB_PATH, easiest: copy driver
        # to temp with patched constants — OR invoke via a wrapper script OR
        # use a symlink trick. Simpler: use a shim module.
        # Pragmatic approach: write a one-line shim that imports + patches.
        self.shim = self.tmpdir / "run_driver.py"
        driver_path = str(DRIVER)
        tmp_db_str = str(self.tmp_db)
        self.shim.write_text(
            "import sys; from pathlib import Path; import importlib.util\n"
            f"spec = importlib.util.spec_from_file_location('apply_migration_003', {driver_path!r})\n"
            "d = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(d)\n"
            f"d.DB_PATH = Path({tmp_db_str!r})\n"
            f"d.BAK_PATH = Path({tmp_db_str!r} + '.pre.bak')\n"
            "d.main()\n"
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_driver(self, extra_args=None):
        cmd = [str(VENV_PY), str(self.shim)]
        if extra_args:
            cmd.extend(extra_args)
        return subprocess.run(cmd, capture_output=True, text=True, env=self.env)

    def test_dry_run_no_mutation(self):
        result = self._run_driver(["--dry-run"])
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        conn = sqlite3.connect(str(self.tmp_db))
        cols = {r[1] for r in conn.execute("PRAGMA table_info(pipeline_runs)").fetchall()}
        conn.close()
        self.assertNotIn("alerts_written_count", cols, "dry-run must not mutate")

    def test_first_apply_success(self):
        result = self._run_driver()
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}\nstdout: {result.stdout}")
        conn = sqlite3.connect(str(self.tmp_db))
        cols = {r[1] for r in conn.execute("PRAGMA table_info(pipeline_runs)").fetchall()}
        self.assertIn("alerts_written_count", cols)
        ledger = conn.execute(
            "SELECT applied_at FROM vna_schema_migrations WHERE migration_id='003_add_alerts_written_count'"
        ).fetchone()
        self.assertIsNotNone(ledger)
        zero_count = conn.execute(
            "SELECT COUNT(*) FROM pipeline_runs WHERE alerts_written_count = 0"
        ).fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
        self.assertEqual(zero_count, total, "DEFAULT 0 must propagate to all existing rows")
        conn.close()

    def test_second_apply_idempotent_skip(self):
        self._run_driver()  # first apply
        result = self._run_driver()  # second apply
        self.assertEqual(result.returncode, 0)
        self.assertIn("SKIP", result.stdout, "Second run must emit SKIP message")

    def test_row_counts_preserved(self):
        conn = sqlite3.connect(str(self.tmp_db))
        pre_alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        pre_pr = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
        conn.close()
        self._run_driver()
        conn = sqlite3.connect(str(self.tmp_db))
        post_alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        post_pr = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
        conn.close()
        self.assertEqual(pre_alerts, post_alerts)
        self.assertEqual(pre_pr, post_pr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
