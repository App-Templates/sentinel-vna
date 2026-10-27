#!/usr/bin/env python3
"""Phase 10 Plan 03 -- silent_failure_watch.py test suite.

Phase 18 HARD-03 extension — CSV-EOF boundary + post-cutoff synthetic-class
regression (TestPhase18HardeningRegression class, lines ~249-).

Mocks get_alerts_pipeline_health + urlopen to cover all trigger paths.
"""
import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.monitoring import silent_failure_watch as sfw


class TestCheckSilentFailure(unittest.TestCase):

    @patch("backend.monitoring.silent_failure_watch.get_alerts_pipeline_health")
    def test_healthy(self, mock_get):
        mock_get.return_value = {"last_alert_at": "2026-04-23T12:00:00", "alerts_last_24h": 5, "pipeline_runs_last_24h": 10}
        r = sfw.check_silent_failure()
        self.assertFalse(r["triggered"])
        self.assertEqual(r["reason"], "healthy")

    @patch("backend.monitoring.silent_failure_watch.get_alerts_pipeline_health")
    def test_silent_failure_triggers(self, mock_get):
        mock_get.return_value = {"last_alert_at": "2026-02-21T18:00:00", "alerts_last_24h": 0, "pipeline_runs_last_24h": 24}
        r = sfw.check_silent_failure()
        self.assertTrue(r["triggered"])
        self.assertEqual(r["reason"], "silent_failure")

    @patch("backend.monitoring.silent_failure_watch.get_alerts_pipeline_health")
    def test_zero_state(self, mock_get):
        mock_get.return_value = {"last_alert_at": None, "alerts_last_24h": 0, "pipeline_runs_last_24h": 0}
        r = sfw.check_silent_failure()
        self.assertFalse(r["triggered"])
        self.assertEqual(r["reason"], "zero_state")

    @patch("backend.monitoring.silent_failure_watch.get_alerts_pipeline_health")
    def test_data_anomaly(self, mock_get):
        mock_get.return_value = {"last_alert_at": "2026-04-23T12:00:00", "alerts_last_24h": 3, "pipeline_runs_last_24h": 0}
        r = sfw.check_silent_failure()
        self.assertFalse(r["triggered"])
        self.assertEqual(r["reason"], "data_anomaly")


class TestSendMetaAlert(unittest.TestCase):

    def setUp(self):
        self.metrics = {"last_alert_at": "2026-02-21T18:00:00", "alerts_last_24h": 0, "pipeline_runs_last_24h": 24}

    @patch("backend.monitoring.silent_failure_watch.urlopen")
    def test_send_success_200(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__ = lambda self: mock_resp
        mock_urlopen.return_value.__exit__ = lambda self, *a: None
        ok = sfw.send_meta_alert(self.metrics, _webhook_override="https://hooks.slack.com/test")
        self.assertTrue(ok)
        self.assertEqual(mock_urlopen.call_count, 1)
        # Inspect payload
        call_req = mock_urlopen.call_args[0][0]
        payload = json.loads(call_req.data.decode("utf-8"))
        self.assertIn("blocks", payload)
        body = json.dumps(payload)
        self.assertIn("PIPELINE SILENT FAILURE", body)
        # body text references the actual counts
        body_text = next(
            (b["text"]["text"] for b in payload["blocks"] if b.get("type") == "section"),
            "",
        )
        self.assertIn("24", body_text)  # pipeline_runs_last_24h count

    @patch("backend.monitoring.silent_failure_watch.time.sleep", return_value=None)
    @patch("backend.monitoring.silent_failure_watch.urlopen")
    def test_send_retries_on_500(self, mock_urlopen, mock_sleep):
        """5xx triggers exponential backoff retry. Migrated from Phase 10 dead-path
        (resp.status=500) to raise-HTTPError semantics (MONITOR-07 fix)."""
        from urllib.error import HTTPError
        # HTTPError requires (url, code, msg, hdrs, fp) -- fp=None accepted.
        err_503 = HTTPError("https://hooks.slack.com/test", 503, "Service Unavailable", {}, None)
        resp_200 = MagicMock(); resp_200.status = 200
        ctx_200 = MagicMock()
        ctx_200.__enter__ = lambda self: resp_200
        ctx_200.__exit__ = lambda self, *a: None
        mock_urlopen.side_effect = [err_503, err_503, ctx_200]
        ok = sfw.send_meta_alert(self.metrics, _webhook_override="https://hooks.slack.com/test")
        self.assertTrue(ok)
        self.assertEqual(mock_urlopen.call_count, 3)

    @patch("backend.monitoring.silent_failure_watch.time.sleep", return_value=None)
    @patch("backend.monitoring.silent_failure_watch.urlopen")
    def test_send_honors_retry_after_on_429(self, mock_urlopen, mock_sleep):
        """429 rate-limit: read Retry-After header, honor its value, retry."""
        from urllib.error import HTTPError
        err_429 = HTTPError(
            "https://hooks.slack.com/test", 429, "Too Many Requests",
            {"Retry-After": "2"}, None,
        )
        resp_200 = MagicMock(); resp_200.status = 200
        ctx_200 = MagicMock(); ctx_200.__enter__ = lambda self: resp_200
        ctx_200.__exit__ = lambda self, *a: None
        mock_urlopen.side_effect = [err_429, ctx_200]
        ok = sfw.send_meta_alert(self.metrics, _webhook_override="https://hooks.slack.com/test")
        self.assertTrue(ok)
        self.assertEqual(mock_urlopen.call_count, 2)
        # Assert sleep was called with exactly the Retry-After value (2 seconds)
        sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
        self.assertIn(2, sleep_args, f"Retry-After=2 not honored; sleeps={sleep_args!r}")

    @patch("backend.monitoring.silent_failure_watch.time.sleep")
    @patch("backend.monitoring.silent_failure_watch.urlopen")
    def test_send_clamps_excessive_retry_after(self, mock_urlopen, mock_sleep):
        """MONITOR-13 (Phase 10.2 / WR-02): a malicious upstream returning
        Retry-After: 999999 must NOT block the watchdog for ~11.5 days. The
        parsed value is clamped to MAX_BACKOFF_SEC (60s).
        """
        from backend.monitoring import silent_failure_watch as sfw
        self.assertTrue(hasattr(sfw, "MAX_BACKOFF_SEC"),
                        "MAX_BACKOFF_SEC module constant required for MONITOR-13")
        self.assertEqual(sfw.MAX_BACKOFF_SEC, 60,
                         "MAX_BACKOFF_SEC must be 60s per Phase 10.2 Plan 02 contract")

        err = urllib.error.HTTPError(
            url="https://hooks.slack.com/services/x",
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "999999"},
            fp=None,
        )
        # First attempt raises 429 with malicious Retry-After; second succeeds.
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = Mock(return_value=mock_resp)
        mock_resp.__exit__ = Mock(return_value=False)
        mock_urlopen.side_effect = [err, mock_resp]

        result = sfw.send_meta_alert(
            {"pipeline_runs_last_24h": 100, "alerts_last_24h": 0, "last_alert_at": None},
            _webhook_override="https://hooks.slack.com/services/x",
        )

        self.assertTrue(result, "send_meta_alert should succeed on second attempt")
        mock_sleep.assert_called_once_with(60)
        # Crucially: NEVER 999999.
        for call in mock_sleep.call_args_list:
            self.assertNotEqual(call.args[0], 999999,
                                "WR-02 regression: Retry-After: 999999 leaked through clamp")

    @patch("backend.monitoring.silent_failure_watch.time.sleep", return_value=None)
    @patch("backend.monitoring.silent_failure_watch.urlopen")
    def test_send_retries_on_429_without_retry_after_uses_exponential(self, mock_urlopen, mock_sleep):
        """429 without Retry-After: fall back to exponential backoff."""
        from urllib.error import HTTPError
        err_429 = HTTPError(
            "https://hooks.slack.com/test", 429, "Too Many Requests", {}, None,
        )
        resp_200 = MagicMock(); resp_200.status = 200
        ctx_200 = MagicMock(); ctx_200.__enter__ = lambda self: resp_200
        ctx_200.__exit__ = lambda self, *a: None
        mock_urlopen.side_effect = [err_429, ctx_200]
        ok = sfw.send_meta_alert(self.metrics, _webhook_override="https://hooks.slack.com/test")
        self.assertTrue(ok)
        sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
        # attempt=0 → 2**0 = 1
        self.assertIn(1, sleep_args, f"Exponential fallback not applied; sleeps={sleep_args!r}")

    @patch("backend.monitoring.silent_failure_watch.time.sleep", return_value=None)
    @patch("backend.monitoring.silent_failure_watch.urlopen")
    def test_send_non_retriable_on_4xx(self, mock_urlopen, mock_sleep):
        """4xx non-429: non-retriable, return False immediately."""
        from urllib.error import HTTPError
        err_404 = HTTPError(
            "https://hooks.slack.com/test", 404, "Not Found", {}, None,
        )
        mock_urlopen.side_effect = [err_404]
        ok = sfw.send_meta_alert(self.metrics, _webhook_override="https://hooks.slack.com/test")
        self.assertFalse(ok)
        self.assertEqual(mock_urlopen.call_count, 1, "4xx must NOT retry")
        self.assertEqual(mock_sleep.call_count, 0, "4xx must NOT sleep")

    @patch("backend.monitoring.silent_failure_watch.time.sleep", return_value=None)
    @patch("backend.monitoring.silent_failure_watch.urlopen")
    def test_send_retries_on_urlerror(self, mock_urlopen, mock_sleep):
        """URLError (network layer): retry with exponential backoff."""
        from urllib.error import URLError
        err_net = URLError("dns lookup failed")
        resp_200 = MagicMock(); resp_200.status = 200
        ctx_200 = MagicMock(); ctx_200.__enter__ = lambda self: resp_200
        ctx_200.__exit__ = lambda self, *a: None
        mock_urlopen.side_effect = [err_net, err_net, ctx_200]
        ok = sfw.send_meta_alert(self.metrics, _webhook_override="https://hooks.slack.com/test")
        self.assertTrue(ok)
        self.assertEqual(mock_urlopen.call_count, 3)
        sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
        self.assertEqual(sleep_args[:2], [1, 2], f"Exponential sleeps wrong: {sleep_args!r}")

    @patch("backend.monitoring.silent_failure_watch.time.sleep", return_value=None)
    @patch("backend.monitoring.silent_failure_watch.urlopen")
    def test_send_returns_false_when_all_retries_exhausted_on_5xx(self, mock_urlopen, mock_sleep):
        """3 consecutive 5xx → return False after 3 attempts, no 4th retry."""
        from urllib.error import HTTPError
        err_503 = HTTPError("https://hooks.slack.com/test", 503, "Service Unavailable", {}, None)
        mock_urlopen.side_effect = [err_503, err_503, err_503]
        ok = sfw.send_meta_alert(self.metrics, _webhook_override="https://hooks.slack.com/test")
        self.assertFalse(ok)
        self.assertEqual(mock_urlopen.call_count, 3, "Must not exceed max_retries=3")

    @patch("backend.monitoring.silent_failure_watch._resolve_webhook_url", return_value=None)
    def test_send_skips_on_missing_webhook(self, mock_resolve):
        # Pass no override; stubbed resolver returns None
        ok = sfw.send_meta_alert(self.metrics)
        self.assertFalse(ok)


class TestRunWatchCycle(unittest.TestCase):

    @patch("backend.monitoring.silent_failure_watch.send_meta_alert", return_value=True)
    @patch("backend.monitoring.silent_failure_watch.get_alerts_pipeline_health")
    def test_cycle_triggers_slack_on_silent_failure(self, mock_get, mock_send):
        mock_get.return_value = {"last_alert_at": "2026-02-21T18:00:00", "alerts_last_24h": 0, "pipeline_runs_last_24h": 24}
        r = sfw.run_watch_cycle()
        self.assertTrue(r["triggered"])
        self.assertTrue(r["slack_sent"])
        mock_send.assert_called_once()

    @patch("backend.monitoring.silent_failure_watch.send_meta_alert")
    @patch("backend.monitoring.silent_failure_watch.get_alerts_pipeline_health")
    def test_cycle_skips_slack_when_healthy(self, mock_get, mock_send):
        mock_get.return_value = {"last_alert_at": "2026-04-23T12:00:00", "alerts_last_24h": 5, "pipeline_runs_last_24h": 10}
        r = sfw.run_watch_cycle()
        self.assertFalse(r["triggered"])
        self.assertFalse(r["slack_sent"])
        mock_send.assert_not_called()

    @patch("backend.monitoring.silent_failure_watch.get_alerts_pipeline_health", side_effect=RuntimeError("db down"))
    def test_cycle_never_raises_on_db_failure(self, mock_get):
        r = sfw.run_watch_cycle()
        self.assertFalse(r["triggered"])
        self.assertEqual(r["reason"], "watchdog_error")
        self.assertIn("db down", r.get("error", ""))


class TestPhase18HardeningRegression(unittest.TestCase):
    """Phase 18 HARD-03 extension — CSV-EOF boundary + post-cutoff synthetic-class regression.

    Defense-in-depth against H6 (tz-mismatch silent synthetic fallback, Phase 17.3 RC) and
    Phase 17.4 CSV-EOF edge case (ALT-20260323-010000-P1: 1h beyond hour_kpi.csv EOF at
    2026-03-23 00:00:00 UTC — deprecated=1 by Phase 17.4 rewrite script secondary path).
    Cross-checks Path A guard with test_alert_revenue_pbi_parity INV-6 — both must agree
    on the live state of backend/agents/data_fetcher_real.py.

    CONTEXT.md D-07 + D-08 implementation.
    """

    POST_CUTOFF_ISO = "2026-05-21 00:00:00.000000"
    SYNTHETIC_CLASS_SOURCES = ("backfill", "synthetic", "synthetic_no_athena")
    CSV_EOF_ALERT_ID = "ALT-20260323-010000-P1"

    def test_post_cutoff_google_adex_synthetic_class_triggers_signal(self):
        """Seed a synthetic-class GOOGLE_ADEX alert post-cutoff; canonical violator query must flag it.

        Uses an ephemeral sqlite3 DB (tempfile) — no write to live data/vna_alerts.db.
        Validates the SQL pattern from test_alert_revenue_pbi_parity INV-2 fires correctly.
        """
        import sqlite3
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE alerts ("
                " alert_id TEXT PRIMARY KEY,"
                " channel_group TEXT NOT NULL,"
                " created_at TEXT NOT NULL,"
                " data_source TEXT NOT NULL,"
                " deprecated INTEGER NOT NULL DEFAULT 0,"
                " revenue_current REAL"
                ")"
            )
            conn.execute(
                "INSERT INTO alerts VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "ALT-TEST-POST-CUTOFF-SYNTH",
                    "GOOGLE_ADEX",
                    "2026-05-21 01:00:00.000000",
                    "synthetic_no_athena",
                    0,
                    500.00,
                ),
            )
            conn.commit()
            violators = conn.execute(
                "SELECT alert_id, data_source FROM alerts "
                "WHERE channel_group='GOOGLE_ADEX' AND created_at >= ? "
                "AND data_source IN ('backfill', 'synthetic', 'synthetic_no_athena') "
                "AND deprecated=0",
                (self.POST_CUTOFF_ISO,),
            ).fetchall()
            self.assertGreaterEqual(
                len(violators), 1,
                "watchdog violator query must flag post-cutoff synthetic GOOGLE_ADEX alert; "
                f"got 0 violators (inserted: ALT-TEST-POST-CUTOFF-SYNTH synthetic_no_athena "
                f">= {self.POST_CUTOFF_ISO})",
            )
            conn.close()
        finally:
            os.unlink(db_path)

    def test_csv_eof_boundary_marked_deprecated_not_active(self):
        """ALT-20260323-010000-P1 (1h beyond hour_kpi.csv EOF) must be deprecated=1 after Phase 17.4.

        CSV terminates at 2026-03-23 00:00:00 UTC. The alert at 2026-03-23 01:00 is 1h beyond
        EOF — rewrite script secondary path: deprecated=1, reason 'synthetic-era pre-H6-fix,
        CSV hourly EOF boundary 2026-03-23'. Counted in INV-4 of test_alert_revenue_pbi_parity.
        skipTest gracefully when data/vna_alerts.db is absent (CI environment without seeded DB).
        """
        import sqlite3
        from pathlib import Path
        db_path = Path(__file__).resolve().parent.parent / "data" / "vna_alerts.db"
        if not db_path.exists():
            self.skipTest(f"live DB not present at {db_path} (CI environment without seeded DB)")
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT deprecated, data_source FROM alerts WHERE alert_id=?",
                (self.CSV_EOF_ALERT_ID,),
            ).fetchone()
            self.assertIsNotNone(
                row,
                f"CSV-EOF alert {self.CSV_EOF_ALERT_ID} missing from DB — "
                "Phase 17.4 rewrite should have deprecated it",
            )
            self.assertEqual(
                row[0], 1,
                f"{self.CSV_EOF_ALERT_ID} must be deprecated=1 (Phase 17.4 closed); "
                f"got deprecated={row[0]} (data_source={row[1]!r})",
            )
        finally:
            conn.close()

    def test_path_a_guard_grep_consistency(self):
        """Defense-in-depth: source-grep for GOOGLE_ADEX + BACKTEST in data_fetcher_real.py.

        Cross-check with INV-6 in test_alert_revenue_pbi_parity — both must agree on the
        live state of the Path A guard. If this fails, INV-6 will also fail; fixing one
        fixes both. CONTEXT.md D-08.
        """
        from pathlib import Path
        src_path = (
            Path(__file__).resolve().parent.parent
            / "backend" / "agents" / "data_fetcher_real.py"
        )
        self.assertTrue(
            src_path.exists(),
            f"data_fetcher_real.py missing at {src_path}",
        )
        src = src_path.read_text()
        self.assertIn(
            "GOOGLE_ADEX", src,
            "Path A guard literal 'GOOGLE_ADEX' must be present in data_fetcher_real.py "
            "(CONTEXT.md D-08 regression guard)",
        )
        self.assertIn(
            "BACKTEST", src,
            "Path A guard literal 'BACKTEST' must be present in data_fetcher_real.py "
            "(CONTEXT.md D-08 regression guard)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
