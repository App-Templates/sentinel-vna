"""
Notifier Agent (Node 9)
Sends alerts via Slack, email, and saves to SQLite.
Pure Python - no LLM needed.

Slack/Email delivery runs in a ThreadPoolExecutor so that time.sleep()
during retries does NOT block the main LangGraph worker thread.
"""

import json
import os
import smtplib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from urllib.error import URLError
from urllib.request import Request, urlopen

from backend.db.database import get_db
from backend.db.operations import find_open_alert
from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("agent.notifier")

# Shared thread pool for non-blocking notification delivery
_notification_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="notifier")


def _canonical_utc_now() -> str:
    """D-10.1-01 (MONITOR-04): canonical alerts.created_at format.
    Matches SQLite datetime('now') for correct string-comparison semantics.
    Format: 'YYYY-MM-DD HH:MM:SS.ffffff' (space-sep naive UTC microseconds).
    """
    return datetime.utcnow().isoformat(sep=' ', timespec='microseconds')


def _canonical_utc_cutoff(hours_ago: int) -> str:
    """D-10.2-01 (MONITOR-11): canonical cutoff for created_at WHERE-clause queries.
    Returns a byte-identical-format string to _canonical_utc_now() so SQLite's
    string compare on pending_notifications.created_at matches correctly across
    the day boundary. Closes CR-01 (Phase 10.1 review) — the same bug class as
    MAJOR-NEW-01 in a sibling callsite explicitly out-of-scope of D-10.1-01.
    Format: 'YYYY-MM-DD HH:MM:SS.ffffff' (space-sep naive UTC microseconds).
    """
    return (datetime.utcnow() - timedelta(hours=hours_ago)) \
        .isoformat(sep=' ', timespec='microseconds')


SEVERITY_EMOJI = {"P0": "\U0001f534", "P1": "\U0001f7e0", "P2": "\U0001f7e1"}


def _should_send_immediate(severity: str, config) -> bool:
    """Check if alert severity should trigger immediate Slack notification."""
    try:
        immediate_severities = config.slack_notifications.immediate_severities
    except (AttributeError, TypeError):
        # Default to P0 only if config missing
        immediate_severities = ["P0"]
    return severity in immediate_severities


def _save_to_pending_notifications(state: AlertState) -> bool:
    """Save alert to pending_notifications table for daily digest."""
    payload = state.get("alert_payload", {})
    if not payload:
        logger.warning("No alert payload to save to pending notifications")
        return False

    try:
        alert_id = payload.get("alert_id", "")
        severity = payload.get("severity", "P1")
        channel_group = payload.get("channel_group", "GOOGLE")
        timestamp = payload.get("timestamp", "")
        # D-10.1-01 (MONITOR-04): canonical space-sep naive UTC microseconds.
        created_at = _canonical_utc_now()

        with get_db() as conn:
            conn.execute(
                """INSERT INTO pending_notifications (
                    alert_id, severity, channel_group, timestamp, created_at
                ) VALUES (?, ?, ?, ?, ?)""",
                (alert_id, severity, channel_group, timestamp, created_at),
            )
        logger.info("Alert saved to pending notifications: %s", alert_id)
        return True
    except Exception as e:
        logger.error("Failed to save to pending_notifications: %s", e)
        return False


def _save_to_db(state: AlertState) -> tuple[bool, bool]:
    """Save alert to SQLite. In LIVE mode, dedup against existing open alerts.

    Returns (saved, is_new):
        saved: True if DB write succeeded (INSERT or UPDATE)
        is_new: True only if a new alerts row was INSERTed;
                False if dedup-UPDATE path taken.

    is_new is consumed by scheduler.py (Plan 10.1-07) for
    alerts_written_count semantics (D-10.1-07).
    """
    payload = state.get("alert_payload", {})
    if not payload:
        logger.warning("No alert payload to save")
        return (False, False)

    try:
        mode = state.get("mode", "LIVE")
        channel_group = payload.get("channel_group", "GOOGLE")
        alert_rule = payload.get("alert_rule", "A1")
        new_alert_id = payload.get("alert_id", "")

        # Dedup: in LIVE mode, check for an existing open alert for the same channel/rule
        if mode != "BACKTEST":
            existing = find_open_alert(channel_group, alert_rule)
            if existing:
                existing_id = existing.get("alert_id", "")
                logger.info(
                    "Dedup: updating existing alert %s instead of creating new %s",
                    existing_id, new_alert_id,
                )
                # D-10.1-01 (MONITOR-04): canonical space-sep naive UTC microseconds.
                now = _canonical_utc_now()
                with get_db() as conn:
                    conn.execute(
                        """UPDATE alerts
                           SET revenue_current = ?,
                               revenue_baseline = ?,
                               revenue_delta_pct = ?,
                               updated_at = ?
                           WHERE alert_id = ?""",
                        (
                            payload.get("revenue", {}).get("current", 0),
                            payload.get("revenue", {}).get("baseline", 0),
                            payload.get("revenue", {}).get("delta_pct", 0),
                            now,
                            existing_id,
                        ),
                    )
                return (True, False)  # UPDATE path → is_new=False

        # D-10.1-01 (MONITOR-04): canonical space-sep naive UTC microseconds.
        now = _canonical_utc_now()
        with get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO alerts (
                    alert_id, timestamp, severity, channel_group, status, alert_rule,
                    revenue_current, revenue_baseline, revenue_delta_pct,
                    triage_label, contributors_json, geo_breakdown_json,
                    environment_split_json, insights_json,
                    execution_time_sec, data_source, config_version,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    new_alert_id,
                    payload.get("timestamp", ""),
                    payload.get("severity", "P1"),
                    channel_group,
                    "OPEN",
                    alert_rule,
                    payload.get("revenue", {}).get("current", 0),
                    payload.get("revenue", {}).get("baseline", 0),
                    payload.get("revenue", {}).get("delta_pct", 0),
                    payload.get("triage_label", "UNKNOWN"),
                    json.dumps(payload.get("contributors", [])),
                    json.dumps(payload.get("geo_breakdown", [])),
                    json.dumps(payload.get("environment_split", {})),
                    json.dumps(payload.get("insights", {})),
                    0.0,
                    payload.get("data_source", "synthetic"),
                    "1.0.0",
                    now,
                    now,
                ),
            )
        logger.info("Alert saved to DB: %s", new_alert_id)
        return (True, True)  # INSERT path → is_new=True
    except Exception as e:
        logger.error("Failed to save alert to DB: %s", e)
        return (False, False)


def _build_slack_blocks_p0(state: AlertState) -> List[dict]:
    """Build full Slack Block Kit message for P0 alerts (critical urgency)."""
    payload = state.get("alert_payload", {})
    severity = payload.get("severity", "P0")
    emoji = SEVERITY_EMOJI.get(severity, "")
    delta = payload.get("revenue", {})
    triage = payload.get("triage_label", "UNKNOWN")
    alert_id = payload.get("alert_id", "N/A")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {severity} Alert: Revenue {delta.get('delta_pct', 0):+.1f}% | {payload.get('channel_group', 'GOOGLE')}",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Alert ID:*\n{alert_id}"},
                {"type": "mrkdwn", "text": f"*Rule:*\n{payload.get('alert_rule', 'A1')}"},
                {"type": "mrkdwn", "text": f"*Revenue:*\nEUR {delta.get('current', 0):,.0f} (baseline: {delta.get('baseline', 0):,.0f})"},
                {"type": "mrkdwn", "text": f"*Classification:*\n{triage}"},
            ],
        },
        {"type": "divider"},
    ]

    # Add top findings
    insights = payload.get("insights", {})
    findings = insights.get("top_findings", [])
    if findings:
        findings_text = "\n".join(
            f"*{f.get('rank', '-')}.* {f.get('title', 'N/A')}"
            for f in findings[:3]
        )
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Key Findings:*\n{findings_text}"},
        })

    # Add top contributors (top 5)
    contributors = payload.get("contributors", [])
    if contributors:
        contrib_text = "\n".join(
            f"- {c.get('display_name', c.get('publisher_id', '?'))}: {c.get('delta_pct', 0):+.1f}% (quota: {c.get('quota_of_drop', 0):.0f}%)"
            for c in contributors[:5]
        )
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Top Contributors:*\n{contrib_text}"},
        })

    # Add geo breakdown
    geo_breakdown = payload.get("geo_breakdown", [])
    if geo_breakdown:
        geo_text = "\n".join(
            f"- {g.get('cluster', '?')}: {g.get('delta_pct', 0):+.1f}% ({g.get('quota_of_drop', 0):.0f}% of drop)"
            for g in geo_breakdown
        )
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Geo Breakdown:*\n{geo_text}"},
        })

    # Add environment split
    env_split = payload.get("environment_split", {})
    if env_split:
        env_text = "\n".join(
            f"- {env}: {data.get('delta_pct', 0):+.1f}% ({data.get('quota_of_drop', 0):.0f}% of drop)"
            for env, data in env_split.items()
        )
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Environment Split:*\n{env_text}"},
        })

    # Add next steps (top 3)
    next_steps = insights.get("next_steps", [])
    if next_steps:
        steps_text = "\n".join(f"- {s}" for s in next_steps[:3])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Next Steps:*\n{steps_text}"},
        })

    # Context footer
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Confidence: {insights.get('diagnosis_confidence', 'medium')} | Source: {payload.get('data_source', 'synthetic')} | {payload.get('timestamp', '')}"},
        ],
    })

    # Action button
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View in Dashboard"},
                "url": f"https://sentinel.adkaora.com/alerts/{alert_id}",
            },
        ],
    })

    return blocks


def _build_slack_blocks_p1(state: AlertState) -> List[dict]:
    """Build medium Slack Block Kit message for P1 alerts."""
    payload = state.get("alert_payload", {})
    severity = payload.get("severity", "P1")
    emoji = SEVERITY_EMOJI.get(severity, "")
    delta = payload.get("revenue", {})
    triage = payload.get("triage_label", "UNKNOWN")
    alert_id = payload.get("alert_id", "N/A")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {severity} Alert: Revenue {delta.get('delta_pct', 0):+.1f}% | {payload.get('channel_group', 'GOOGLE')}",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Alert ID:*\n{alert_id}"},
                {"type": "mrkdwn", "text": f"*Rule:*\n{payload.get('alert_rule', 'A1')}"},
                {"type": "mrkdwn", "text": f"*Revenue:*\nEUR {delta.get('current', 0):,.0f} (baseline: {delta.get('baseline', 0):,.0f})"},
                {"type": "mrkdwn", "text": f"*Classification:*\n{triage}"},
            ],
        },
    ]

    # Add top contributors (top 3 only)
    contributors = payload.get("contributors", [])
    if contributors:
        contrib_text = "\n".join(
            f"- {c.get('display_name', c.get('publisher_id', '?'))}: {c.get('delta_pct', 0):+.1f}%"
            for c in contributors[:3]
        )
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Top Contributors:*\n{contrib_text}"},
        })

    # Add next steps (top 2)
    insights = payload.get("insights", {})
    next_steps = insights.get("next_steps", [])
    if next_steps:
        steps_text = "\n".join(f"- {s}" for s in next_steps[:2])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Next Steps:*\n{steps_text}"},
        })

    # Context footer
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Confidence: {insights.get('diagnosis_confidence', 'medium')} | Source: {payload.get('data_source', 'synthetic')} | {payload.get('timestamp', '')}"},
        ],
    })

    # Action button
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Details"},
                "url": f"https://sentinel.adkaora.com/alerts/{alert_id}",
            },
        ],
    })

    return blocks


def _build_slack_blocks_p2(state: AlertState) -> List[dict]:
    """Build compact single-line Slack Block Kit message for P2 alerts."""
    payload = state.get("alert_payload", {})
    severity = payload.get("severity", "P2")
    emoji = SEVERITY_EMOJI.get(severity, "")
    delta_pct = payload.get("revenue", {}).get("delta_pct", 0)
    channel = payload.get("channel_group", "GOOGLE")
    triage = payload.get("triage_label", "UNKNOWN")
    alert_id = payload.get("alert_id", "N/A")

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{severity}*: Revenue {delta_pct:+.1f}% | {channel} | {triage} | Alert: `{alert_id}`",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Details"},
                    "url": f"https://sentinel.adkaora.com/alerts/{alert_id}",
                },
            ],
        },
    ]

    return blocks


def _send_slack(state: AlertState) -> bool:
    """Send alert to Slack webhook with retry and exponential backoff.

    Selects appropriate Block Kit template based on severity:
    - P0: Full report with geo, env, findings, next steps
    - P1: Medium report with top 3 contributors, top 2 next steps
    - P2: Compact single-line format
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.info("Slack webhook not configured, skipping")
        return False

    # Select template based on severity
    payload = state.get("alert_payload", {})
    severity = payload.get("severity", "P1")

    if severity == "P0":
        blocks = _build_slack_blocks_p0(state)
    elif severity == "P1":
        blocks = _build_slack_blocks_p1(state)
    else:
        blocks = _build_slack_blocks_p2(state)

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
                    logger.info("Slack notification sent successfully")
                    return True
                elif resp.status >= 500:
                    delay = 2 ** attempt
                    logger.warning(
                        "Slack server error %d (attempt %d/%d), retrying in %ds",
                        resp.status, attempt + 1, max_retries, delay,
                    )
                    time.sleep(delay)
                else:
                    logger.warning("Slack returned status %d", resp.status)
                    return False
        except (URLError, OSError) as e:
            if attempt < max_retries - 1:
                delay = 2 ** attempt
                logger.warning(
                    "Slack send failed (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1, max_retries, delay, e,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Failed to send Slack notification after %d attempts: %s",
                    max_retries, e,
                )
                return False
    return False


def _send_email(state: AlertState) -> bool:
    """Send alert via SMTP email."""
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    email_to = os.environ.get("ALERT_EMAIL_TO")

    if not all([smtp_host, smtp_user, email_to]):
        logger.info("Email not configured, skipping")
        return False

    payload = state.get("alert_payload", {})
    severity = payload.get("severity", "P1")
    report = state.get("markdown_report", "No report available")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[{severity}] Revenue Alert: {payload.get('alert_id', 'N/A')}"
    msg["From"] = smtp_user
    msg["To"] = email_to

    # Plain text version
    msg.attach(MIMEText(report, "plain"))

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.ehlo()
                if smtp_port == 587:
                    server.starttls()
                if smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [email_to], msg.as_string())
            logger.info("Email notification sent to %s", email_to)
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error("Email auth failed (not retrying): %s", e)
            return False
        except (smtplib.SMTPServerDisconnected, ConnectionRefusedError, TimeoutError, OSError) as e:
            if attempt < max_retries - 1:
                delay = 2 ** attempt
                logger.warning(
                    "Email send failed (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1, max_retries, delay, e,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Failed to send email after %d attempts: %s",
                    max_retries, e,
                )
                return False
    return False


def _build_digest_blocks(rows: List[tuple]) -> List[dict]:
    """Build digest Block Kit message from pending_notifications rows.

    Args:
        rows: List of tuples (alert_id, severity, channel_group, timestamp)

    Returns:
        List of Slack Block Kit blocks
    """
    count = len(rows)
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":calendar: Daily Alert Digest — {count} alerts in last 24h",
            },
        },
        {"type": "divider"},
    ]

    # Add up to 20 alerts (Slack has block limits)
    for alert_id, severity, channel_group, timestamp in rows[:20]:
        emoji = SEVERITY_EMOJI.get(severity, "")
        alert_text = f"{emoji} *{severity}* | {channel_group} | {timestamp} | <https://sentinel.adkaora.com/alerts/{alert_id}|View>"
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": alert_text},
        })

    # Context footer with generation time
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Generated at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"},
        ],
    })

    return blocks


def send_daily_digest() -> dict:
    """
    Send daily digest of P1/P2 alerts accumulated in pending_notifications.
    Called by APScheduler CronTrigger job.
    Returns: { "sent": bool, "alert_count": int, "message": str }
    """
    logger.info("Starting daily digest job")

    # Try to get webhook URL from environment first, then config
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")

    if not webhook_url:
        # Read from alerting_rules.yaml directly (slack_notifications not in Pydantic model yet)
        try:
            import yaml
            from pathlib import Path
            config_path = Path(__file__).parent.parent.parent / "config" / "alerting_rules.yaml"
            with open(config_path, "r") as f:
                config_dict = yaml.safe_load(f)
            webhook_url = config_dict.get("slack_notifications", {}).get("webhook_url")
        except Exception as e:
            logger.warning("Failed to load webhook from config: %s", e)

    if not webhook_url:
        logger.warning("Slack webhook not configured, skipping digest")
        return {"sent": False, "alert_count": 0, "message": "Webhook not configured"}

    # 1. Query pending_notifications from last 24 hours
    cutoff = _canonical_utc_cutoff(24)  # D-10.2-01 / MONITOR-11: canonical space-sep, matches _canonical_utc_now writes

    with get_db() as conn:
        rows = conn.execute(
            """SELECT alert_id, severity, channel_group, timestamp
               FROM pending_notifications
               WHERE created_at >= ?
               ORDER BY created_at DESC""",
            (cutoff,)
        ).fetchall()

    if not rows:
        logger.info("No pending alerts for digest")
        return {"sent": False, "alert_count": 0, "message": "No pending alerts"}

    # 2. Build digest Block Kit message
    blocks = _build_digest_blocks(rows)

    # 3. Send to Slack
    payload_json = json.dumps({"blocks": blocks}).encode("utf-8")

    try:
        req = Request(
            webhook_url,
            data=payload_json,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                logger.info("Daily digest sent successfully (%d alerts)", len(rows))

                # 4. Clear pending_notifications after successful send
                with get_db() as conn:
                    conn.execute("DELETE FROM pending_notifications WHERE created_at >= ?", (cutoff,))

                return {"sent": True, "alert_count": len(rows), "message": "Digest sent"}
            else:
                logger.error("Slack digest failed with status %d", resp.status)
                return {"sent": False, "alert_count": len(rows), "message": f"HTTP {resp.status}"}
    except (URLError, OSError) as e:
        logger.error("Failed to send digest: %s", e)
        return {"sent": False, "alert_count": len(rows), "message": str(e)}


def notifier_agent(state: AlertState) -> AlertState:
    """
    Main entry point for notifications.
    - Saves to SQLite (synchronous -- critical path)
    - Routes Slack notifications based on severity: immediate (P0) vs digest (P1/P2)
    - Sends email in parallel via ThreadPoolExecutor
      so that time.sleep() retries do NOT block the main LangGraph thread.
    """
    logger.info("Notifier started | alert=%s", state.get("alert_payload", {}).get("alert_id", "N/A"))
    errors = list(state.get("execution_errors", []))
    payload = state.get("alert_payload", {})
    severity = payload.get("severity", "P1")

    delivery_status = {
        "db_saved": False,
        "db_new_row": False,   # D-10.1-07: True only on INSERT (new alert row), False on dedup UPDATE
        "slack_sent": False,
        "slack_queued": False,
        "email_sent": False,
    }

    # 1. Always save to DB synchronously (critical path)
    try:
        # D-10.1-07: unpack (saved, is_new) tuple — is_new consumed by Plan 10.1-07 counter fix
        saved, is_new = _save_to_db(state)
        delivery_status["db_saved"] = saved
        delivery_status["db_new_row"] = is_new
    except Exception as e:
        logger.error("DB save failed: %s", e)
        errors.append(f"DB save failed: {e}")

    # 2. Load config for notification routing
    try:
        config = get_config()
    except Exception:
        config = None

    futures = {}

    # 3. Route Slack based on severity
    if config and config.notifications.slack_enabled:
        if _should_send_immediate(severity, config):
            logger.info("Sending immediate notification for %s alert", severity)
            futures["slack"] = _notification_executor.submit(_send_slack, state)
        else:
            logger.info("Saved %s alert to pending notifications for daily digest", severity)
            try:
                delivery_status["slack_queued"] = _save_to_pending_notifications(state)
            except Exception as e:
                logger.error("Failed to queue notification: %s", e)
                errors.append(f"Notification queue failed: {e}")

    # 4. Dispatch Email to thread pool (non-blocking)
    if config and config.notifications.email_enabled:
        futures["email"] = _notification_executor.submit(_send_email, state)

    # 5. Collect results with a timeout (max 30s total for both)
    for name, future in futures.items():
        try:
            result = future.result(timeout=30)
            if name == "slack":
                delivery_status["slack_sent"] = result
            else:
                delivery_status["email_sent"] = result
        except TimeoutError:
            logger.error("%s notification timed out after 30s", name.capitalize())
            errors.append(f"{name.capitalize()} notification timed out")
            future.cancel()
        except Exception as e:
            logger.error("%s send failed: %s", name.capitalize(), e)
            errors.append(f"{name.capitalize()} notification failed: {e}")

    logger.info(
        "Notifier complete: db=%s, slack_sent=%s, slack_queued=%s, email=%s",
        delivery_status["db_saved"],
        delivery_status["slack_sent"],
        delivery_status["slack_queued"],
        delivery_status["email_sent"],
    )

    return {
        **state,
        "delivery_status": delivery_status,
        "execution_errors": errors,
    }
