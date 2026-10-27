#!/usr/bin/env python3
"""Phase 10 Plan 03 -- silent_failure_watch.py test suite.

Mocks get_alerts_pipeline_health + urlopen to cover all trigger paths.
"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
