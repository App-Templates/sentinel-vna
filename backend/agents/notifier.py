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
from datetime import datetime, timezone
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

SEVERITY_EMOJI = {"P0": "\U0001f534", "P1": "\U0001f7e0", "P2": "\U0001f7e1"}


def _save_to_db(state: AlertState) -> bool:
    """Save alert to SQLite database. In LIVE mode, dedup against existing open alerts."""
    payload = state.get("alert_payload", {})
    if not payload:
        logger.warning("No alert payload to save")
        return False

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
                now = datetime.now(timezone.utc).isoformat()
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
                return True

        with get_db() as conn:
            now = datetime.now(timezone.utc).isoformat()

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
        return True
    except Exception as e:
        logger.error("Failed to save alert to DB: %s", e)
        return False


def _build_slack_blocks(state: AlertState) -> List[dict]:
    """Build Slack Block Kit message."""
    payload = state.get("alert_payload", {})
    severity = payload.get("severity", "P1")
    emoji = SEVERITY_EMOJI.get(severity, "")
    delta = payload.get("revenue", {})
    triage = payload.get("triage_label", "UNKNOWN")

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
                {"type": "mrkdwn", "text": f"*Alert ID:*\n{payload.get('alert_id', 'N/A')}"},
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

    # Add top contributors
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

    # Add next steps
    next_steps = insights.get("next_steps", [])
    if next_steps:
        steps_text = "\n".join(f"- {s}" for s in next_steps[:3])
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Next Steps:*\n{steps_text}"},
        })

    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Confidence: {insights.get('diagnosis_confidence', 'medium')} | Source: {payload.get('data_source', 'synthetic')} | {payload.get('timestamp', '')}"},
        ],
    })

    return blocks


def _send_slack(state: AlertState) -> bool:
    """Send alert to Slack webhook with retry and exponential backoff."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.info("Slack webhook not configured, skipping")
        return False

    blocks = _build_slack_blocks(state)
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


def notifier_agent(state: AlertState) -> AlertState:
    """
    Main entry point for notifications.
    - Saves to SQLite (synchronous -- critical path)
    - Sends to Slack and Email in parallel via ThreadPoolExecutor
      so that time.sleep() retries do NOT block the main LangGraph thread.
    """
    logger.info("Notifier started | alert=%s", state.get("alert_payload", {}).get("alert_id", "N/A"))
    errors = list(state.get("execution_errors", []))

    delivery_status = {
        "db_saved": False,
        "slack_sent": False,
        "email_sent": False,
    }

    # 1. Always save to DB synchronously (critical path)
    try:
        delivery_status["db_saved"] = _save_to_db(state)
    except Exception as e:
        logger.error("DB save failed: %s", e)
        errors.append(f"DB save failed: {e}")

    # 2. Dispatch Slack & Email to thread pool (non-blocking)
    try:
        config = get_config()
    except Exception:
        config = None

    futures = {}

    if config and config.notifications.slack_enabled:
        futures["slack"] = _notification_executor.submit(_send_slack, state)

    if config and config.notifications.email_enabled:
        futures["email"] = _notification_executor.submit(_send_email, state)

    # 3. Collect results with a timeout (max 30s total for both)
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
        "Notifier complete: db=%s, slack=%s, email=%s",
        delivery_status["db_saved"],
        delivery_status["slack_sent"],
        delivery_status["email_sent"],
    )

    return {
        **state,
        "delivery_status": delivery_status,
        "execution_errors": errors,
    }
