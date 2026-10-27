#!/usr/bin/env python3
"""Phase 09 Plan 03 — test suite for scripts/backfill_alerts.py.

Isolation strategy: tests use tempfile DB + monkey-patched `run_pipeline`
stub (returns canned AlertState dict). No real pipeline invocations in
unit tests — full-grid execution happens in Task 3 against live DB.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

SCRIPT = REPO_ROOT / "scripts" / "backfill_alerts.py"
PYTHON = sys.executable


def _make_fake_state(alert_triggered: bool = True) -> dict:
    """Build a minimal AlertState dict that adapter + persist path accepts."""
    return {
        "alert_triggered": alert_triggered,
        "severity": "P2",
        "channel_group": "GOOGLE_ADEX",
        "alert_rule": "A1",
        "triage_label": "TEST",
        "alert_payload": {
            "revenue": {"current": 100.0, "baseline": 200.0, "delta_pct": -50.0},
            "contributors": [],
            "geo_breakdown": [],
            "environment_split": {},
            "insights": {},
        },
        "execution_errors": [],
        "execution_time_sec": 0.01,
        "config_version": "1.0.0",
    }


class TestBackfillAlertsCLI(unittest.TestCase):
    """Subprocess-level CLI tests (tests 1, 2)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="backfill_test_")
        self.db_path = Path(self.tmpdir) / "test.db"
        self.checkpoint_path = Path(self.tmpdir) / "ckpt.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_cli_parses_required_flags(self):
        """Test 1: CLI accepts --start/--end/--dry-run/--db-path and reports tuple count."""
        result = subprocess.run(
            [
                PYTHON, str(SCRIPT),
                "--start", "2026-01-23",
                "--end", "2026-01-24",
                "--dry-run",
                "--db-path", str(self.db_path),
                "--checkpoint-path", str(self.checkpoint_path),
            ],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, f"exit={result.returncode} stderr={result.stderr}")
        # 2 days × 8 channels × 3 triggers = 48
        self.assertIn("48 tuples", result.stdout, f"stdout={result.stdout!r}")

    def test_dry_run_does_not_invoke_pipeline(self):
        """Test 2: --dry-run prints tuple count but does NOT call the pipeline."""
        import backend.db.database as db_mod
        db_mod._DB_PATH = None
        from scripts import backfill_alerts as bf

        call_counter = {"n": 0}

        def _stub(*a, **kw):
            call_counter["n"] += 1
            return _make_fake_state()

        argv = [
            "backfill_alerts",
            "--start", "2026-01-23", "--end", "2026-01-24",
            "--dry-run",
            "--db-path", str(self.db_path),
            "--checkpoint-path", str(self.checkpoint_path),
        ]
        with mock.patch("scripts.backfill_alerts.run_pipeline", side_effect=_stub), \
             mock.patch("sys.argv", argv), \
             self.assertRaises(SystemExit) as ctx:
            bf.main()
        self.assertEqual(ctx.exception.code, 0)
        self.assertEqual(call_counter["n"], 0, "Dry run must not invoke pipeline")


class TestBackfillAlertsInProcess(unittest.TestCase):
    """In-process tests (tests 3-11) via mock.patch — no subprocess overhead."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="backfill_test_")
        self.db_path = Path(self.tmpdir) / "test.db"
        self.checkpoint_path = Path(self.tmpdir) / "ckpt.json"
        os.environ["VNA_DB_PATH"] = str(self.db_path)
        # Reset db_path state and init test DB
        import backend.db.database as db_mod
        db_mod._DB_PATH = None
        if hasattr(db_mod._local, "connection"):
            try:
                db_mod._local.connection.close()
            except Exception:
                pass
            db_mod._local.connection = None
        from backend.db.database import init_db
        init_db(str(self.db_path))

    def tearDown(self):
        import shutil
        import backend.db.database as db_mod
        if hasattr(db_mod._local, "connection") and db_mod._local.connection is not None:
            try:
                db_mod._local.connection.close()
            except Exception:
                pass
            db_mod._local.connection = None
        db_mod._DB_PATH = None
        os.environ.pop("VNA_DB_PATH", None)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_main(self, argv: list) -> int:
        """Invoke backfill_alerts.main() with argv; return exit code."""
        from scripts import backfill_alerts as bf
        with mock.patch("sys.argv", ["backfill_alerts"] + argv):
            try:
                bf.main()
                return 0
            except SystemExit as se:
                return se.code if isinstance(se.code, int) else 0

    def test_checkpoint_persists_completed_tuples(self):
        """Test 3: 1-day range with stub → 24 completed tuples in checkpoint."""
        calls = []

        def _stub(**kw):
            calls.append(kw)
            return _make_fake_state()

        with mock.patch("scripts.backfill_alerts.run_pipeline", side_effect=_stub):
            code = self._run_main([
                "--start", "2026-01-23", "--end", "2026-01-23",
                "--db-path", str(self.db_path),
                "--checkpoint-path", str(self.checkpoint_path),
            ])
        self.assertEqual(code, 0)
        ckpt = json.loads(self.checkpoint_path.read_text())
        self.assertEqual(len(ckpt["completed"]), 24, f"expected 24, got {len(ckpt['completed'])}")
        self.assertEqual(len(ckpt["failed_tuples"]), 0)
        self.assertEqual(len(calls), 24)

    def test_resume_skips_completed_tuples(self):
        """Test 4: pre-seed checkpoint with 12 completed → stub invoked only 12 times."""
        from scripts.backfill_alerts import CHANNELS, TRIGGERS, _tuple_key
        d = date(2026, 1, 23)
        seeded = []
        for c in CHANNELS[:4]:
            for t in TRIGGERS:
                seeded.append(_tuple_key(d, c, t))
        # 4 channels × 3 triggers = 12 pre-seeded
        self.checkpoint_path.write_text(json.dumps({
            "completed": seeded,
            "failed_tuples": [],
            "start_ts": "2026-04-23T12:00:00+00:00",
        }))

        calls = []

        def _stub(**kw):
            calls.append(kw)
            return _make_fake_state()

        with mock.patch("scripts.backfill_alerts.run_pipeline", side_effect=_stub):
            code = self._run_main([
                "--start", "2026-01-23", "--end", "2026-01-23",
                "--db-path", str(self.db_path),
                "--checkpoint-path", str(self.checkpoint_path),
            ])
        self.assertEqual(code, 0)
        # 24 total - 12 seeded = 12 remaining
        self.assertEqual(len(calls), 12, f"expected 12, got {len(calls)}")

    def test_force_flag_ignores_checkpoint(self):
        """Test 5: --force ignores checkpoint → all 24 tuples invoked."""
        self.checkpoint_path.write_text(json.dumps({
            "completed": ["some|pre-existing|key"],
            "failed_tuples": [],
            "start_ts": "2026-04-23T12:00:00+00:00",
        }))

        calls = []

        def _stub(**kw):
            calls.append(kw)
            return _make_fake_state()

        with mock.patch("scripts.backfill_alerts.run_pipeline", side_effect=_stub):
            code = self._run_main([
                "--start", "2026-01-23", "--end", "2026-01-23",
                "--force",
                "--db-path", str(self.db_path),
                "--checkpoint-path", str(self.checkpoint_path),
            ])
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 24)

    def test_fail_soft_continues_on_exception(self):
        """Test 6: stub raises once → execution continues; failed_tuples length 1; exit 1."""
        counter = {"n": 0}

        def _stub(**kw):
            counter["n"] += 1
            if counter["n"] == 3:
                raise RuntimeError("pipeline exploded")
            return _make_fake_state()

        with mock.patch("scripts.backfill_alerts.run_pipeline", side_effect=_stub):
            code = self._run_main([
                "--start", "2026-01-23", "--end", "2026-01-23",
                "--db-path", str(self.db_path),
                "--checkpoint-path", str(self.checkpoint_path),
            ])
        self.assertEqual(code, 1, "exit must be 1 when any tuple failed (D-06)")
        ckpt = json.loads(self.checkpoint_path.read_text())
        self.assertEqual(len(ckpt["failed_tuples"]), 1)
        # Check 24 stub invocations attempted (23 succeeded + 1 raised)
        self.assertEqual(counter["n"], 24)

    def test_channel_list_is_8_values_from_models(self):
        """Test 7: script imports CHANNEL_GROUP_CHECK_VALUES from backend.db.models."""
        from scripts.backfill_alerts import CHANNELS
        from backend.db.models import CHANNEL_GROUP_CHECK_VALUES
        self.assertEqual(tuple(CHANNELS), CHANNEL_GROUP_CHECK_VALUES)
        self.assertEqual(len(CHANNELS), 8)

    def test_trigger_list_is_A1_A2_A3(self):
        """Test 8: TRIGGERS literal is ['A1','A2','A3'] per D-18."""
        from scripts.backfill_alerts import TRIGGERS
        self.assertEqual(TRIGGERS, ["A1", "A2", "A3"])

    def test_invocation_uses_mode_backtest(self):
        """Test 9: every stub invocation receives mode="BACKTEST"."""
        calls = []

        def _stub(**kw):
            calls.append(kw)
            return _make_fake_state()

        with mock.patch("scripts.backfill_alerts.run_pipeline", side_effect=_stub):
            self._run_main([
                "--start", "2026-01-23", "--end", "2026-01-23",
                "--channel", "GOOGLE_ADEX",
                "--rule", "A1",
                "--db-path", str(self.db_path),
                "--checkpoint-path", str(self.checkpoint_path),
            ])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["mode"], "BACKTEST")

    def test_invocation_uses_iso_timestamp(self):
        """Test 10: timestamp kwarg matches ISO-8601 YYYY-MM-DDTHH:MM:SS."""
        import re
        calls = []

        def _stub(**kw):
            calls.append(kw)
            return _make_fake_state()

        with mock.patch("scripts.backfill_alerts.run_pipeline", side_effect=_stub):
            self._run_main([
                "--start", "2026-01-23", "--end", "2026-01-23",
                "--channel", "GOOGLE_ADEX",
                "--rule", "A1",
                "--db-path", str(self.db_path),
                "--checkpoint-path", str(self.checkpoint_path),
            ])
        self.assertEqual(len(calls), 1)
        ts = calls[0]["timestamp"]
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_checkpoint_records_start_ts(self):
        """Test 11: checkpoint JSON has start_ts (used by rollback)."""
        def _stub(**kw):
            return _make_fake_state()

        with mock.patch("scripts.backfill_alerts.run_pipeline", side_effect=_stub):
            self._run_main([
                "--start", "2026-01-23", "--end", "2026-01-23",
                "--channel", "GOOGLE_ADEX",
                "--rule", "A1",
                "--db-path", str(self.db_path),
                "--checkpoint-path", str(self.checkpoint_path),
            ])
        ckpt = json.loads(self.checkpoint_path.read_text())
        self.assertIn("start_ts", ckpt)
        self.assertIsNotNone(ckpt["start_ts"])
        # Must be ISO-like
        self.assertRegex(ckpt["start_ts"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_auto_detect_end_date_from_parquet(self):
        """Test 12: if --end omitted, reads parquet max_date = 2026-03-23 on live env."""
        parquet_path = REPO_ROOT / "data" / "baseline" / "daily_aggregated.parquet"
        if not parquet_path.exists():
            self.skipTest("parquet not present — integration-style test")
        from scripts.backfill_alerts import _auto_detect_end_date
        d = _auto_detect_end_date()
        self.assertEqual(d, date(2026, 3, 23))

    def test_persists_alert_when_run_pipeline_triggers(self):
        """Test 13 (B-1 fix): orchestrator actually calls create_alert when pipeline triggers."""
        def _stub(**kw):
            # Customize alert_id deterministically via severity+timestamp
            st = _make_fake_state(alert_triggered=True)
            st["channel_group"] = kw.get("channel_group", "GOOGLE_ADEX")
            st["alert_rule"] = kw.get("trigger_type", "A1")
            return st

        with mock.patch("scripts.backfill_alerts.run_pipeline", side_effect=_stub):
            code = self._run_main([
                "--start", "2026-01-23", "--end", "2026-01-23",
                "--channel", "GOOGLE_ADEX",
                "--rule", "A1",
                "--db-path", str(self.db_path),
                "--checkpoint-path", str(self.checkpoint_path),
            ])
        self.assertEqual(code, 0)
        with sqlite3.connect(str(self.db_path)) as c:
            n = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        self.assertEqual(n, 1, "B-1 fix: create_alert must have been invoked by orchestrator")
        with sqlite3.connect(str(self.db_path)) as c:
            pr = c.execute("SELECT COUNT(*) FROM pipeline_runs WHERE mode='BACKTEST'").fetchone()[0]
        self.assertGreaterEqual(pr, 1, "pipeline_runs must record the invocation")


if __name__ == "__main__":
    unittest.main()
