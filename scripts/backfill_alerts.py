#!/usr/bin/env python3
"""
Phase 09 Plan 03 — BACKFILL-01 orchestrator.

Invokes run_pipeline(mode="BACKTEST") per (date × channel × trigger in [A1,A2,A3])
for the range [--start, --end] (end defaults to parquet max_date). Resumable via
JSON checkpoint; fail-soft per tuple.

Run:
  .venv/bin/python scripts/backfill_alerts.py --start 2026-01-23 --end 2026-03-23
  .venv/bin/python scripts/backfill_alerts.py --dry-run
  .venv/bin/python scripts/backfill_alerts.py --force
  .venv/bin/python scripts/backfill_alerts.py --channel GOOGLE_ADEX --rule A1
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.db.models import CHANNEL_GROUP_CHECK_VALUES  # noqa: E402
from backend.workflow.graph import run_pipeline  # noqa: E402

DEFAULT_DB_PATH = REPO_ROOT / "data" / "vna_alerts.db"
DEFAULT_CHECKPOINT_PATH = REPO_ROOT / "data" / ".backfill_checkpoint.json"
DAILY_PARQUET = REPO_ROOT / "data" / "baseline" / "daily_aggregated.parquet"

# D-08: start is day after max legacy alert timestamp (2026-01-22 → 2026-01-23).
DEFAULT_START = date(2026, 1, 23)

# D-18: external triggers explicitly ['A1', 'A2', 'A3']. Emergent rules
# (data-gap/margin/coverage/pricing) fire internally via anomaly_detector.
# Deliberately-absent rule + cross-channel rule not wired in v1.3 (deferred).
TRIGGERS = ["A1", "A2", "A3"]

# Channels from models.py — single source of truth.
CHANNELS = list(CHANNEL_GROUP_CHECK_VALUES)  # 8 values

logger = logging.getLogger("backfill")


def _auto_detect_end_date() -> date:
    """Read max date from daily_aggregated.parquet (D-08 End auto-detection)."""
    try:
        import pyarrow.parquet as pq
        t = pq.read_table(str(DAILY_PARQUET), columns=["date"])
        max_d = t["date"].to_pandas().max()
        if hasattr(max_d, "date"):
            return max_d.date()
        if isinstance(max_d, str):
            return date.fromisoformat(max_d)
        return max_d
    except Exception as e:
        logger.error("Failed to auto-detect end date from parquet: %s", e)
        return (datetime.now(timezone.utc).date() - timedelta(days=1))


def _daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _tuple_key(d: date, channel: str, trigger: str) -> str:
    return f"{d.isoformat()}|{channel}|{trigger}"


def _load_checkpoint(path: Path) -> dict:
    if not path.exists():
        return {"completed": [], "failed_tuples": [], "start_ts": None}
    try:
        with open(path) as f:
            data = json.load(f)
        # Defensive: tolerate missing keys in legacy checkpoints
        data.setdefault("completed", [])
        data.setdefault("failed_tuples", [])
        data.setdefault("start_ts", None)
        return data
    except Exception as exc:
        logger.warning("Checkpoint parse failed (%s) — starting fresh", exc)
        return {"completed": [], "failed_tuples": [], "start_ts": None}


def _save_checkpoint(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    tmp.replace(path)  # atomic rename


def _build_alert_model_from_state(state: dict, ts_iso: str):
    """Adapter: AlertState (nested alert_payload per report_builder.py:23-61)
    → AlertModel (flat ORM fields per backend/db/models.py).

    B-1 fix (ERRATA): run_pipeline returns AlertState but does NOT persist.
    Orchestrator calls this adapter then create_alert() per tuple.
    Pattern reference: backend/backtest/runner_real.py:252-278.
    """
    from backend.db.models import (
        AlertModel, AlertRule, AlertStatus, ChannelGroup, Severity,
        generate_alert_id,
    )

    payload = state.get("alert_payload") or {}
    revenue = payload.get("revenue") or {}
    ts = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))

    sev_raw = state.get("severity") or payload.get("severity") or "P2"
    try:
        severity_enum = Severity[sev_raw] if isinstance(sev_raw, str) else sev_raw
    except KeyError:
        severity_enum = Severity.P2

    ch_raw = state.get("channel_group") or payload.get("channel_group") or "GOOGLE_ADEX"
    try:
        channel_enum = ChannelGroup(ch_raw) if isinstance(ch_raw, str) else ch_raw
    except ValueError:
        channel_enum = ChannelGroup.GOOGLE_ADEX

    rule_raw = state.get("alert_rule") or payload.get("alert_rule") or "A1"
    try:
        rule_enum = AlertRule(rule_raw) if isinstance(rule_raw, str) else rule_raw
    except ValueError:
        rule_enum = AlertRule.A1

    return AlertModel(
        alert_id=generate_alert_id(severity_enum, ts),
        timestamp=ts,
        severity=severity_enum,
        channel_group=channel_enum,
        status=AlertStatus.OPEN,
        alert_rule=rule_enum,
        revenue_current=round(float(revenue.get("current") or 0), 2),
        revenue_baseline=round(float(revenue.get("baseline") or 0), 2),
        revenue_delta_pct=round(float(revenue.get("delta_pct") or 0), 2),
        triage_label=state.get("triage_label") or payload.get("triage_label") or "UNKNOWN",
        contributors_json=json.dumps(payload.get("contributors") or []),
        geo_breakdown_json=json.dumps(payload.get("geo_breakdown") or []),
        environment_split_json=json.dumps(payload.get("environment_split") or {}),
        insights_json=json.dumps(payload.get("insights") or {}),
        execution_time_sec=round(float(state.get("execution_time_sec") or 0), 3),
        data_source="backfill",
        config_version=state.get("config_version") or "1.0.0",
        created_at=ts,
        updated_at=ts,
    )


def main():
    ap = argparse.ArgumentParser(description="Phase 09 BACKFILL-01 orchestrator")
    ap.add_argument("--start", type=lambda s: date.fromisoformat(s), default=DEFAULT_START)
    ap.add_argument("--end", type=lambda s: date.fromisoformat(s), default=None,
                    help="Inclusive end date. Default: parquet max_date (auto-detected).")
    ap.add_argument("--channel", choices=CHANNELS + ["ALL"], default="ALL")
    ap.add_argument("--rule", choices=TRIGGERS + ["ALL"], default="ALL")
    ap.add_argument("--force", action="store_true", help="Ignore checkpoint — re-run all tuples.")
    ap.add_argument("--dry-run", action="store_true", help="Print tuple count, do not invoke pipeline.")
    ap.add_argument("--checkpoint-path", type=Path, default=DEFAULT_CHECKPOINT_PATH)
    ap.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Point backend.db.database at the target DB so create_alert writes there.
    import backend.db.database as db_mod
    db_mod._DB_PATH = None
    # Close any pre-existing thread-local connection (test fixtures reuse module)
    if hasattr(db_mod._local, "connection") and db_mod._local.connection is not None:
        try:
            db_mod._local.connection.close()
        except Exception:
            pass
        db_mod._local.connection = None
    from backend.db.database import init_db
    init_db(str(args.db_path))

    end_date = args.end or _auto_detect_end_date()
    logger.info("Backfill range: %s → %s (inclusive)", args.start, end_date)

    active_channels = [args.channel] if args.channel != "ALL" else CHANNELS
    active_triggers = [args.rule] if args.rule != "ALL" else TRIGGERS

    all_tuples = [
        (d, c, t)
        for d in _daterange(args.start, end_date)
        for c in active_channels
        for t in active_triggers
    ]

    state = _load_checkpoint(args.checkpoint_path) if not args.force else \
            {"completed": [], "failed_tuples": [], "start_ts": None}
    if state["start_ts"] is None:
        state["start_ts"] = datetime.now(timezone.utc).isoformat()
        _save_checkpoint(args.checkpoint_path, state)

    completed_set = set(state["completed"])
    remaining = [t for t in all_tuples if _tuple_key(*t) not in completed_set]

    logger.info(
        "Tuples total=%d | completed=%d | failed=%d | remaining=%d",
        len(all_tuples), len(completed_set), len(state["failed_tuples"]), len(remaining),
    )

    if args.dry_run:
        print(f"DRY RUN: {len(remaining)} tuples would be invoked (of {len(all_tuples)} total). No changes.")
        sys.exit(0)

    if not remaining:
        print("IDEMPOTENT-NOOP: all tuples already completed in checkpoint.")
        sys.exit(0)

    # Deferred import (tests mock run_pipeline at scripts.backfill_alerts.run_pipeline level).
    from backend.db.operations import create_alert, record_pipeline_run

    succeeded, failed_now = 0, 0
    for i, (d, channel, trigger) in enumerate(remaining, 1):
        # D-07 (NEW-B-7): disambiguate alert_id per tuple. generate_alert_id
        # uses only (severity, ts); 24 same-day 00:00:00 tuples would collide.
        # HH = channel_idx * len(TRIGGERS) + trigger_idx ∈ [0, 23]; 8×3=24.
        hh = CHANNELS.index(channel) * len(TRIGGERS) + TRIGGERS.index(trigger)
        ts_dt = datetime(d.year, d.month, d.day, hh, 0, 0, tzinfo=timezone.utc)
        ts_iso = ts_dt.isoformat()
        key = _tuple_key(d, channel, trigger)
        run_id = f"bf-{uuid.uuid4().hex[:8]}"
        t0 = time.time()
        alert_written = False
        alert_id_for_log = None
        err_message = None
        try:
            logger.debug("[%d/%d] %s hh=%02d", i, len(remaining), key, hh)
            final_state = run_pipeline(
                trigger_type=trigger,
                channel_group=channel,
                mode="BACKTEST",
                timestamp=ts_iso,
            )
            duration = round(time.time() - t0, 3)

            # B-1: run_pipeline returns AlertState but does NOT persist.
            # Orchestrator is responsible for create_alert + record_pipeline_run.
            if final_state.get("alert_triggered"):
                alert_model = _build_alert_model_from_state(final_state, ts_iso)
                create_alert(alert_model)  # INSERT OR IGNORE (Task 1b guarantees idempotency).
                alert_written = True
                alert_id_for_log = alert_model.alert_id

            errs = final_state.get("execution_errors") or []
            if errs:
                err_message = "; ".join(str(e) for e in errs)[:500]

            status = (
                "failed" if errs else ("success" if alert_written else "no_alert")
            )
            # B-6: canonical record_pipeline_run signature per operations.py:250-262.
            record_pipeline_run(
                run_id, ts_iso, channel, trigger, "BACKTEST",
                status, duration,
                alert_id=alert_id_for_log,
                error_message=err_message,
                alerts_written_count=1 if alert_written else 0,
            )

            state["completed"].append(key)
            succeeded += 1
        except Exception as exc:
            logger.error("FAIL %s: %s", key, exc)
            state["failed_tuples"].append({"key": key, "error": str(exc)[:500]})
            # Best-effort pipeline_runs record on failure (observability).
            try:
                record_pipeline_run(
                    run_id, ts_iso, channel, trigger, "BACKTEST",
                    "failed", round(time.time() - t0, 3),
                    error_message=str(exc)[:500],
                    alerts_written_count=0,
                )
            except Exception:
                pass
            failed_now += 1

        # Checkpoint every 20 tuples to tolerate mid-run aborts.
        if i % 20 == 0 or i == len(remaining):
            _save_checkpoint(args.checkpoint_path, state)

    _save_checkpoint(args.checkpoint_path, state)
    logger.info("Backfill complete: succeeded=%d failed=%d", succeeded, failed_now)
    logger.info("Final checkpoint: %s", args.checkpoint_path)
    sys.exit(1 if state["failed_tuples"] else 0)  # D-06: non-zero on any failure


if __name__ == "__main__":
    main()
