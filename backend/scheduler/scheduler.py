from __future__ import annotations

import os
import time
import uuid
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.db.models import ChannelGroup, RecheckStatus
from backend.db.operations import (
    get_alert_by_id,
    get_pending_rechecks,
    record_pipeline_run,
    update_recheck_status,
)
from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger
from backend.workflow.graph import run_pipeline

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


async def _run_trigger_for_channels(trigger_type: str, channels: list) -> None:
    """Run a single trigger type across all channels, recording results."""
    for channel_name in channels:
        channel = ChannelGroup(channel_name)
        logger.info("Running %s check for %s", trigger_type, channel.value)
        run_id = str(uuid.uuid4())[:8]
        timestamp_now = datetime.utcnow().isoformat()
        start = time.time()
        try:
            result = run_pipeline(
                trigger_type=trigger_type,
                channel_group=channel.value,
                mode="LIVE",
            )
            duration = time.time() - start
            if result.get("alert_triggered"):
                logger.info(
                    "%s alert generated for %s: severity=%s",
                    trigger_type, channel.value, result.get("severity"),
                )
                status = "success"
                alert_id = result.get("alert_payload", {}).get("alert_id")
            else:
                logger.info("No %s anomaly detected for %s", trigger_type, channel.value)
                status = "no_alert"
                alert_id = None
            llm_fallback = any(
                "LLM" in str(e) and "failed" in str(e)
                for e in result.get("execution_errors", [])
            )
            llm_used = bool(os.environ.get("ANTHROPIC_API_KEY")) and not llm_fallback
            record_pipeline_run(
                run_id, timestamp_now, channel.value, trigger_type, "LIVE",
                status, duration, llm_used, llm_fallback, alert_id,
            )
        except Exception as exc:
            duration = time.time() - start
            record_pipeline_run(
                run_id, timestamp_now, channel.value, trigger_type, "LIVE",
                "failed", duration, error_message=str(exc),
            )
            logger.error(
                "%s pipeline failed for %s: %s", trigger_type, channel.value, exc,
                exc_info=True,
            )


async def run_alerting_cycle() -> None:
    """A1 + A3 cycle — runs every 2h (interval_hours from config)."""
    try:
        config = get_config()
        channels = config.scheduling.channels
        logger.info("Starting A1+A3 alerting cycle for channels: %s", channels)

        await _run_trigger_for_channels("A1", channels)
        await _run_trigger_for_channels("A3", channels)

        logger.info("A1+A3 alerting cycle finished")
    except Exception as exc:
        logger.error("Alerting cycle error: %s", exc, exc_info=True)


async def run_drift_cycle() -> None:
    """A2 drift cycle — runs every 6h."""
    try:
        config = get_config()
        channels = config.scheduling.channels
        logger.info("Starting A2 drift cycle for channels: %s", channels)

        await _run_trigger_for_channels("A2", channels)

        logger.info("A2 drift cycle finished")
    except Exception as exc:
        logger.error("A2 drift cycle error: %s", exc, exc_info=True)


async def check_recheck_queue() -> None:
    try:
        pending = get_pending_rechecks()
        if not pending:
            return

        logger.info("Processing %d pending rechecks", len(pending))
        for item in pending:
            queue_id = item["queue_id"]
            alert_id = item["alert_id"]
            try:
                logger.info("Rechecking alert %s (queue %d)", alert_id, queue_id)
                alert = get_alert_by_id(alert_id)
                if alert is None:
                    logger.warning("Alert %s not found, skipping recheck", alert_id)
                    update_recheck_status(queue_id, RecheckStatus.FAILED)
                    continue
                channel_group = alert.get("channel_group", "GOOGLE")
                run_pipeline(
                    trigger_type="A1",
                    channel_group=channel_group,
                    mode="LIVE",
                )
                update_recheck_status(queue_id, RecheckStatus.COMPLETED)
                logger.info("Recheck completed for alert %s", alert_id)
            except Exception as exc:
                logger.error(
                    "Recheck failed for alert %s: %s", alert_id, exc, exc_info=True
                )
                update_recheck_status(queue_id, RecheckStatus.FAILED)
    except Exception as exc:
        logger.error("Recheck queue error: %s", exc, exc_info=True)


def start_scheduler() -> None:
    scheduler = _get_scheduler()
    if scheduler.running:
        logger.warning("Scheduler already running")
        return

    config = get_config()

    # A1 + A3: run every interval_hours (default 2h)
    scheduler.add_job(
        run_alerting_cycle,
        trigger=IntervalTrigger(hours=config.scheduling.interval_hours),
        id="alerting_cycle",
        name="A1+A3 alerting cycle",
        replace_existing=True,
    )

    # A2 drift: run every 6h (3x the base interval)
    drift_interval_hours = config.scheduling.interval_hours * 3
    scheduler.add_job(
        run_drift_cycle,
        trigger=IntervalTrigger(hours=drift_interval_hours),
        id="drift_cycle",
        name="A2 drift detection cycle",
        replace_existing=True,
    )

    scheduler.add_job(
        check_recheck_queue,
        trigger=IntervalTrigger(minutes=config.scheduling.recheck_interval_minutes),
        id="recheck_queue",
        name="Recheck queue processor",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started: A1+A3 every %dh, A2 drift every %dh, rechecks every %dm",
        config.scheduling.interval_hours,
        drift_interval_hours,
        config.scheduling.recheck_interval_minutes,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped (waited for running jobs)")
    _scheduler = None


def is_scheduler_running() -> bool:
    return _scheduler is not None and _scheduler.running
