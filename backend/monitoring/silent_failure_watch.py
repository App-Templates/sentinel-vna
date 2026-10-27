"""Phase 10 MONITOR-02: silent-failure watchdog.

Detects the 2-month silent-failure incident pattern of 2026-01-22 ->
2026-04-22 and emits a Slack P0 meta-alert within one cycle.

Detection rule (from REQ MONITOR-02):
    pipeline_runs_last_24h > 0 AND alerts_last_24h == 0 => TRIGGERED (P0)

Edge cases:
    * pipeline_runs=0 AND alerts=0 => zero-state (app just started or
      scheduler off) => NOT triggered.
    * pipeline_runs=0 AND alerts>0  => impossible in practice (alerts come
      from runs) => treat as NOT triggered (data anomaly, log WARNING).
    * pipeline_runs>0 AND alerts>0  => healthy => NOT triggered.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
from datetime import datetime, timezone
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.db.operations import get_alerts_pipeline_health
from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger

logger = get_logger(__name__)

META_ALERT_EMOJI = ":rotating_light:"
META_ALERT_HEADER = "PIPELINE SILENT FAILURE"
PHASE_REF = "Phase 10 MONITOR-02"


def _resolve_webhook_url() -> Optional[str]:
    """env SLACK_WEBHOOK_URL first; then config.silent_failure_monitor.slack_channel_override;
    then config.slack_notifications.webhook_url (YAML fallback, same pattern as notifier.send_daily_digest)."""
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if url:
        return url

    # Override from silent_failure_monitor section takes precedence over generic slack_notifications
    try:
        cfg = get_config()
        override = cfg.silent_failure_monitor.slack_channel_override
        if override:
            return override
    except Exception as e:
        logger.warning("silent_failure_monitor config access failed: %s", e)

    # Final fallback: generic slack_notifications.webhook_url from YAML
    try:
        import yaml
        from pathlib import Path
        config_path = Path(__file__).resolve().parent.parent.parent / "config" / "alerting_rules.yaml"
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
        return data.get("slack_notifications", {}).get("webhook_url")
    except Exception as e:
        logger.warning("Failed to load webhook from slack_notifications config: %s", e)
        return None


def _build_meta_alert_blocks(metrics: dict) -> list:
    """Build Block Kit payload for a P0 meta-alert.

    Distinct from notifier._build_slack_blocks_p0 (which is alert-shaped with
    contributors/geo/env). Meta-alert body cites run/alert counts + last alert
    timestamp + phase reference.
    """
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    last_alert_text = metrics.get("last_alert_at") or "(never)"
    body_text = (
        f"*{META_ALERT_EMOJI} P0 {META_ALERT_HEADER}*\n\n"
        f"*Pattern:* `pipeline_runs_last_24h > 0 AND alerts_last_24h == 0`\n"
        f"*Pipeline runs (24h):* {metrics['pipeline_runs_last_24h']}\n"
        f"*Alerts written (24h):* {metrics['alerts_last_24h']}\n"
        f"*Last alert at:* {last_alert_text}\n\n"
        f"_This is the same divergence pattern that caused the 2026-01-22 -> "
        f"2026-04-22 silent-failure incident. Investigate immediately._\n\n"
        f"Watchdog: {PHASE_REF} | Now: {now_utc}"
    )
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{META_ALERT_EMOJI} {META_ALERT_HEADER} (P0)"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": body_text},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Source: {PHASE_REF} watchdog | Endpoint: /api/health/alerts-pipeline"},
            ],
        },
    ]


def send_meta_alert(metrics: dict, _webhook_override: Optional[str] = None) -> bool:
    """POST a P0 meta-alert Block Kit payload to Slack.

    Returns True on successful 200 response; False if webhook unconfigured,
    auth failed, or all retries exhausted. Does NOT raise -- silent-failure
    watchdog must never crash the scheduler.

    `_webhook_override` is for testing only (bypasses config resolution).
    """
    webhook_url = _webhook_override or _resolve_webhook_url()
    if not webhook_url:
        logger.warning(
            "send_meta_alert: webhook unconfigured (env SLACK_WEBHOOK_URL missing, "
            "config.silent_failure_monitor.slack_channel_override null, "
            "config.slack_notifications.webhook_url missing). Skipping Slack send."
        )
        return False

    blocks = _build_meta_alert_blocks(metrics)
    payload_json = json.dumps({"blocks": blocks}).encode("utf-8")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            req = Request(
                webhook_url,
                data=payload_json,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    logger.info(
                        "send_meta_alert: Slack POST succeeded (attempt %d/%d) metrics=%s",
                        attempt + 1, max_retries, metrics,
                    )
                    return True
                # Defensive path: urlopen() raises HTTPError for non-2xx on standard
                # implementations, so this branch is only reached on rare non-raising
                # implementations that return non-exception non-2xx.
                logger.warning(
                    "send_meta_alert: Slack returned %d (non-raising)", resp.status
                )
                return False
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = e.headers.get("Retry-After", "")
                try:
                    backoff = int(retry_after) if retry_after.isdigit() else (2 ** attempt)
                except Exception:
                    backoff = 2 ** attempt
                if attempt < max_retries - 1:
                    logger.warning(
                        "send_meta_alert: Slack 429 rate-limit (attempt %d/%d), sleeping %ds",
                        attempt + 1, max_retries, backoff,
                    )
                    time.sleep(backoff)
                    continue
                else:
                    logger.error("send_meta_alert: 429 after %d retries", max_retries)
                    return False
            elif e.code >= 500:
                if attempt < max_retries - 1:
                    delay = 2 ** attempt
                    logger.warning(
                        "send_meta_alert: Slack %d (attempt %d/%d), retrying in %ds",
                        e.code, attempt + 1, max_retries, delay,
                    )
                    time.sleep(delay)
                    continue
                else:
                    logger.error("send_meta_alert: 5xx after %d retries", max_retries)
                    return False
            else:
                logger.error(
                    "send_meta_alert: Slack %d %s non-retriable", e.code, e.reason,
                )
                return False
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                delay = 2 ** attempt
                logger.warning(
                    "send_meta_alert: network error (attempt %d/%d), retrying in %ds: %r",
                    attempt + 1, max_retries, delay, e,
                )
                time.sleep(delay)
                continue
            else:
                logger.error("send_meta_alert: URLError after %d retries: %r", max_retries, e)
                return False
    return False


def check_silent_failure() -> dict:
    """Query 24h metrics and classify as triggered/healthy/zero-state.

    Returns {
        triggered: bool,
        reason: str,        # 'silent_failure' | 'healthy' | 'zero_state' | 'data_anomaly'
        metrics: dict,      # forwarded from get_alerts_pipeline_health()
    }
    """
    metrics = get_alerts_pipeline_health()
    prl = metrics["pipeline_runs_last_24h"]
    al = metrics["alerts_last_24h"]

    if prl == 0 and al == 0:
        reason = "zero_state"
        triggered = False
    elif prl > 0 and al == 0:
        reason = "silent_failure"
        triggered = True
    elif prl == 0 and al > 0:
        reason = "data_anomaly"  # alerts without runs -- investigate but don't panic
        triggered = False
        logger.warning(
            "check_silent_failure: data_anomaly -- alerts_last_24h=%d but pipeline_runs_last_24h=0",
            al,
        )
    else:
        reason = "healthy"
        triggered = False

    return {"triggered": triggered, "reason": reason, "metrics": metrics}


def run_watch_cycle() -> dict:
    """APScheduler entry point. Runs one watchdog cycle.

    Never raises -- logs and continues. Scheduler must keep running even
    if the watchdog itself errors (the whole point is to surface problems,
    not to become one).

    Returns result dict for test visibility / test assertions.
    """
    logger.info("silent_failure_watch: cycle start")
    try:
        result = check_silent_failure()
    except Exception as e:
        logger.exception("silent_failure_watch: check_silent_failure raised")
        return {"triggered": False, "reason": "watchdog_error", "metrics": {}, "error": str(e)}

    if result["triggered"]:
        try:
            sent = send_meta_alert(result["metrics"])
            result["slack_sent"] = sent
        except Exception as e:
            logger.exception("silent_failure_watch: send_meta_alert raised")
            result["slack_sent"] = False
            result["slack_error"] = str(e)
    else:
        result["slack_sent"] = False

    logger.info(
        "silent_failure_watch: cycle complete -- triggered=%s reason=%s metrics=%s",
        result["triggered"], result["reason"], result["metrics"],
    )
    return result
