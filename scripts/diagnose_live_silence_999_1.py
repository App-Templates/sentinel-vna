#!/usr/bin/env python3
"""
Phase 999.1 Plan 01 — read-only LIVE-silence diagnostic (REQ MONITOR-09).

Purpose
-------
Produce evidence for the Phase 999.1 root-cause analysis of
`pipeline_runs_last_24h=1 AND alerts_last_24h=0` at the Phase 10.1-08
watchdog re-enable (Case C). The Phase 10.1-08 smoke returned:

    last_alert_at        = 2026-03-23 13:00:00.000000
    alerts_last_24h      = 0
    pipeline_runs_last_24h = 1   (the 2026-04-23 smoke itself)

This script answers seven questions against the live DB + parquet without
mutating anything:

  1. What is MAX/MIN/COUNT of non-deprecated alerts? (mirrors
     `get_alerts_pipeline_health` query shape)
  2. What is the MIN / MAX / second-MAX of LIVE pipeline_runs.timestamp,
     and the channel_group at each extremum? (distinguishes smoke-test
     terminus from real-scheduler terminus)
  3. Which channel_group values are present in LIVE pipeline_runs, and
     do any violate the `ChannelGroup` enum? (no SQL-level CHECK on
     pipeline_runs.channel_group — only app-level enforcement)
  4. What is the status distribution for LIVE pipeline_runs?
     ('no_alert' vs 'ok' / 'success' / 'failed')
  5. What is the `data_source` histogram for non-deprecated alerts?
     (all 'backfill' → H1 weight high; any 'real_parquet' / 'live' →
     H1 weakens)
  6. What is the parquet `daily_aggregated.parquet` max/min date?
     (max == 2026-03-23 pins H1 to exact cutoff)
  7. Are there any running uvicorn/scheduler processes?
     (explains zero fresh LIVE runs in last 24h)

Read-only contract
------------------
* `sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)` — URI read-only.
* `pyarrow.parquet.read_table(..., columns=['date'])` — single-column scan.
* No INSERT/UPDATE/DELETE/DROP/ALTER/REPLACE/TRUNCATE anywhere.
* No `run_pipeline`, `start_scheduler`, `run_watch_cycle` import.
* No network calls, no config mutation, no file writes outside the
  explicit `--emit-markdown PATH` flag.

Reference
---------
- REQ MONITOR-09 (Phase 999.1 investigate-live-pipeline-silent-since-2026-03-23)
- .planning/phases/10.1-pipeline-monitoring-hotfix-and-hardening/10.1-VERIFICATION.md
  frontmatter `overrides[0]` (operator-accepted Case C)
- .planning/phases/09-alert-backfill-legacy-migration/COVERAGE-GAP.md
  (Option A/B parquet-refresh plant-seed — remediation owner for H1)
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Hardcoded paths — no env-var injection (T-999.1.01-05 mitigation).
DB_PATH = REPO_ROOT / "data" / "vna_alerts.db"
DAILY_PARQUET = REPO_ROOT / "data" / "baseline" / "daily_aggregated.parquet"
DIAGNOSIS_PATH = (
    REPO_ROOT
    / ".planning"
    / "phases"
    / "999.1-investigate-live-pipeline-silent-since-2026-03-23"
    / "999.1-DIAGNOSIS.md"
)

EVIDENCE_BEGIN = "<!-- BEGIN EVIDENCE 999.1-01 -->"
EVIDENCE_END = "<!-- END EVIDENCE 999.1-01 -->"


# ---------------------------------------------------------------------------
# Section 1: last-alert summary (non-deprecated)
# ---------------------------------------------------------------------------
def _check_last_alert(conn: sqlite3.Connection) -> dict[str, Any]:
    """MAX/MIN/COUNT(*) of non-deprecated alerts (mirrors MONITOR-01 query shape)."""
    row = conn.execute(
        "SELECT MAX(created_at), MIN(created_at), COUNT(*) FROM alerts WHERE deprecated = 0"
    ).fetchone()
    max_ca, min_ca, count = row[0], row[1], int(row[2] or 0)

    # Total row count including deprecated, for context.
    total_row = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()
    total = int(total_row[0] or 0)

    deprecated_row = conn.execute(
        "SELECT COUNT(*) FROM alerts WHERE deprecated = 1"
    ).fetchone()
    deprecated_count = int(deprecated_row[0] or 0)

    return {
        "max_created_at": max_ca,
        "min_created_at": min_ca,
        "count_non_deprecated": count,
        "count_deprecated": deprecated_count,
        "count_total": total,
    }


# ---------------------------------------------------------------------------
# Section 2: LIVE pipeline_runs — extremes + smoke-vs-scheduler differentiation
# ---------------------------------------------------------------------------
def _check_live_runs(conn: sqlite3.Connection) -> dict[str, Any]:
    """MIN/MAX/2nd-MAX timestamp for mode='LIVE' (smoke vs real-scheduler terminus)."""
    total_row = conn.execute(
        "SELECT COUNT(*) FROM pipeline_runs WHERE mode = 'LIVE'"
    ).fetchone()
    total = int(total_row[0] or 0)

    min_row = conn.execute(
        "SELECT MIN(timestamp) FROM pipeline_runs WHERE mode = 'LIVE'"
    ).fetchone()
    min_ts = min_row[0]

    # Top-2 descending — derives both max and second-max in one query.
    top2 = conn.execute(
        """SELECT timestamp, channel_group
           FROM pipeline_runs
           WHERE mode = 'LIVE'
           ORDER BY timestamp DESC
           LIMIT 2"""
    ).fetchall()
    max_ts = top2[0][0] if len(top2) >= 1 else None
    max_ch = top2[0][1] if len(top2) >= 1 else None
    second_max_ts = top2[1][0] if len(top2) >= 2 else None
    second_max_ch = top2[1][1] if len(top2) >= 2 else None

    # Daily histogram for last 45 days.
    rows_per_day = conn.execute(
        """SELECT substr(timestamp, 1, 10) AS day, COUNT(*) AS c
           FROM pipeline_runs
           WHERE mode = 'LIVE'
             AND timestamp >= date('now', '-45 days')
           GROUP BY day
           ORDER BY day DESC"""
    ).fetchall()
    per_day = [{"day": r[0], "count": int(r[1])} for r in rows_per_day]

    return {
        "total_live_runs": total,
        "min_timestamp": min_ts,
        "max_timestamp": max_ts,
        "max_timestamp_channel_group": max_ch,
        "second_max_timestamp": second_max_ts,
        "second_max_timestamp_channel_group": second_max_ch,
        "per_day_last_45d": per_day,
    }


# ---------------------------------------------------------------------------
# Section 3: LIVE channel_group coverage vs enum vs config
# ---------------------------------------------------------------------------
def _check_live_channels(conn: sqlite3.Connection) -> dict[str, Any]:
    """DISTINCT channel_group in LIVE runs, vs ChannelGroup enum, vs config.scheduling.channels.

    Also returns the live DDL of pipeline_runs so DIAGNOSIS.md can cite the
    absence of a SQL-level CHECK constraint on channel_group.
    """
    # Step A: observed distinct values.
    observed_rows = conn.execute(
        """SELECT DISTINCT channel_group
           FROM pipeline_runs
           WHERE mode = 'LIVE'
           ORDER BY channel_group"""
    ).fetchall()
    observed = [r[0] for r in observed_rows]

    # Step B: DDL text.
    ddl_row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='pipeline_runs'"
    ).fetchone()
    table_ddl = ddl_row[0] if ddl_row and ddl_row[0] else ""

    # Step C: app-level allowed set (read import — respects read-only contract).
    from backend.db.models import ChannelGroup  # noqa: E402  (read-only import)

    app_allowed_set = [cg.value for cg in ChannelGroup]

    # Step E: config-level allowed set.
    try:
        from backend.utils.config_loader import get_config  # noqa: E402
        cfg = get_config()
        configured = list(cfg.scheduling.channels)
    except Exception as exc:  # fail-soft; diagnosis should never crash
        configured = []
        configured_error = repr(exc)
    else:
        configured_error = None

    # Step D: per-value flags.
    per_value_flags = []
    for val in observed:
        per_value_flags.append(
            {
                "value": val,
                "in_enum": val in app_allowed_set,
                "in_config": val in configured,
                "constraint_violation": val not in app_allowed_set,
            }
        )

    missing_in_live = [c for c in configured if c not in observed]
    unexpected_values = [
        v for v in observed if v not in app_allowed_set
    ]

    return {
        "configured": configured,
        "configured_error": configured_error,
        "observed": observed,
        "missing_in_live": missing_in_live,
        "unexpected_values": unexpected_values,
        "app_allowed_set": app_allowed_set,
        "table_ddl": table_ddl,
        "per_value_flags": per_value_flags,
    }


# ---------------------------------------------------------------------------
# Section 4: LIVE status distribution
# ---------------------------------------------------------------------------
def _check_live_statuses(conn: sqlite3.Connection) -> dict[str, Any]:
    """GROUP BY status for LIVE runs."""
    rows = conn.execute(
        """SELECT status, COUNT(*)
           FROM pipeline_runs
           WHERE mode = 'LIVE'
           GROUP BY status
           ORDER BY COUNT(*) DESC"""
    ).fetchall()
    distribution = [{"status": r[0], "count": int(r[1])} for r in rows]
    total = sum(d["count"] for d in distribution)
    return {
        "total_live_runs": total,
        "distribution": distribution,
    }


# ---------------------------------------------------------------------------
# Section 5: alert.data_source histogram (non-deprecated)
# ---------------------------------------------------------------------------
def _check_alert_data_sources(conn: sqlite3.Connection) -> dict[str, Any]:
    """data_source histogram for non-deprecated alerts."""
    rows = conn.execute(
        """SELECT COALESCE(data_source, '(null)') AS ds, COUNT(*)
           FROM alerts
           WHERE deprecated = 0
           GROUP BY ds
           ORDER BY COUNT(*) DESC"""
    ).fetchall()
    histogram = [{"data_source": r[0], "count": int(r[1])} for r in rows]
    return {
        "histogram": histogram,
        "total": sum(h["count"] for h in histogram),
    }


# ---------------------------------------------------------------------------
# Section 6: parquet max date
# ---------------------------------------------------------------------------
def _check_parquet_max_date() -> dict[str, Any]:
    """MAX/MIN of the `date` column in data/baseline/daily_aggregated.parquet.

    Uses single-column projection (pyarrow read_table columns=['date']) to
    avoid loading revenue / publisher data into the diagnostic process.
    """
    try:
        import pyarrow.parquet as pq  # noqa: E402

        table = pq.read_table(DAILY_PARQUET, columns=["date"])
        dates = table.column("date").to_pylist()
    except Exception as exc:
        return {
            "path": str(DAILY_PARQUET),
            "error": repr(exc),
            "min_date": None,
            "max_date": None,
            "days_since_max": None,
            "today": datetime.now(timezone.utc).date().isoformat(),
            "row_count": 0,
            "unique_dates": 0,
        }

    def _to_iso(v: Any) -> str | None:
        if v is None:
            return None
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)

    iso_dates = [_to_iso(d) for d in dates if d is not None]
    if not iso_dates:
        min_iso = max_iso = None
    else:
        min_iso = min(iso_dates)
        max_iso = max(iso_dates)

    today = datetime.now(timezone.utc).date()
    days_since_max: int | None
    if max_iso:
        try:
            max_parsed = datetime.fromisoformat(max_iso).date()
            days_since_max = (today - max_parsed).days
        except Exception:
            days_since_max = None
    else:
        days_since_max = None

    return {
        "path": str(DAILY_PARQUET),
        "min_date": min_iso,
        "max_date": max_iso,
        "days_since_max": days_since_max,
        "today": today.isoformat(),
        "row_count": len(dates),
        "unique_dates": len(set(iso_dates)),
    }


# ---------------------------------------------------------------------------
# Section 7: scheduler process enumeration
# ---------------------------------------------------------------------------
def _check_scheduler_processes() -> dict[str, Any]:
    """pgrep -af for uvicorn / scheduler — informational only."""
    try:
        result = subprocess.run(
            ["pgrep", "-af", "uvicorn|backend.*scheduler"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        pids: list[int] = []
        cmdlines: list[str] = []
        for ln in lines:
            parts = ln.split(None, 1)
            if not parts:
                continue
            try:
                pids.append(int(parts[0]))
            except ValueError:
                continue
            cmdlines.append(parts[1] if len(parts) > 1 else "")
        return {
            "running": len(pids) > 0,
            "pids": pids,
            "cmdlines": cmdlines,
            "pgrep_rc": result.returncode,
        }
    except Exception as exc:
        return {
            "running": False,
            "pids": [],
            "cmdlines": [],
            "error": repr(exc),
        }


# ---------------------------------------------------------------------------
# Markdown formatter (splices evidence between idempotent delimiters)
# ---------------------------------------------------------------------------
def _format_last_alert(d: dict[str, Any]) -> str:
    lines = [
        "### §1. Last alert (non-deprecated)",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| `MAX(created_at) WHERE deprecated=0` | `{d['max_created_at']}` |",
        f"| `MIN(created_at) WHERE deprecated=0` | `{d['min_created_at']}` |",
        f"| `COUNT(*) WHERE deprecated=0` | {d['count_non_deprecated']} |",
        f"| `COUNT(*) WHERE deprecated=1` | {d['count_deprecated']} |",
        f"| `COUNT(*) total`                 | {d['count_total']} |",
    ]
    return "\n".join(lines)


def _format_live_runs(d: dict[str, Any]) -> str:
    lines = [
        "### §2. LIVE pipeline_runs — extremes",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| `COUNT(*) WHERE mode='LIVE'` | {d['total_live_runs']} |",
        f"| `MIN(timestamp)` | `{d['min_timestamp']}` |",
        f"| `MAX(timestamp)` | `{d['max_timestamp']}` |",
        f"| `MAX(timestamp).channel_group` | `{d['max_timestamp_channel_group']}` |",
        f"| `2nd-MAX(timestamp)` | `{d['second_max_timestamp']}` |",
        f"| `2nd-MAX(timestamp).channel_group` | `{d['second_max_timestamp_channel_group']}` |",
        "",
        "**Per-day counts (last 45 days, LIVE only):**",
        "",
    ]
    if d["per_day_last_45d"]:
        lines.append("| Day | Count |")
        lines.append("|---|---|")
        for row in d["per_day_last_45d"]:
            lines.append(f"| {row['day']} | {row['count']} |")
    else:
        lines.append("_(no LIVE runs in the last 45 days)_")
    return "\n".join(lines)


def _format_live_channels(d: dict[str, Any]) -> str:
    lines = [
        "### §3. LIVE channel_group coverage",
        "",
        f"**Observed (DISTINCT):** `{d['observed']}`",
        "",
        f"**Configured (`config.scheduling.channels`):** `{d['configured']}`",
    ]
    if d.get("configured_error"):
        lines.append(f"  _(config load error: `{d['configured_error']}`)_")
    lines.extend(
        [
            "",
            f"**App-level allowed set (`ChannelGroup` enum):** `{d['app_allowed_set']}`",
            "",
            f"**Missing in LIVE (configured but never run):** `{d['missing_in_live']}`",
            "",
            f"**Unexpected values (observed but not in enum):** `{d['unexpected_values']}`",
            "",
            "**Per-value flags:**",
            "",
            "| Value | In Enum | In Config | Constraint Violation |",
            "|---|---|---|---|",
        ]
    )
    for pv in d["per_value_flags"]:
        lines.append(
            f"| `{pv['value']}` | {pv['in_enum']} | {pv['in_config']} | {pv['constraint_violation']} |"
        )
    lines.extend(
        [
            "",
            "**Live pipeline_runs DDL (confirms NO SQL-level CHECK on `channel_group`):**",
            "",
            "```sql",
            d["table_ddl"] or "(DDL not found)",
            "```",
        ]
    )
    return "\n".join(lines)


def _format_live_statuses(d: dict[str, Any]) -> str:
    lines = [
        "### §4. LIVE status distribution",
        "",
        f"**Total LIVE runs:** {d['total_live_runs']}",
        "",
        "| Status | Count |",
        "|---|---|",
    ]
    for row in d["distribution"]:
        lines.append(f"| `{row['status']}` | {row['count']} |")
    return "\n".join(lines)


def _format_alert_data_sources(d: dict[str, Any]) -> str:
    lines = [
        "### §5. Non-deprecated alert `data_source` histogram",
        "",
        f"**Total non-deprecated alerts:** {d['total']}",
        "",
        "| data_source | Count |",
        "|---|---|",
    ]
    for row in d["histogram"]:
        lines.append(f"| `{row['data_source']}` | {row['count']} |")
    return "\n".join(lines)


def _format_parquet(d: dict[str, Any]) -> str:
    lines = [
        "### §6. Parquet freshness (`data/baseline/daily_aggregated.parquet`)",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| path | `{d['path']}` |",
        f"| `MIN(date)` | `{d['min_date']}` |",
        f"| `MAX(date)` | `{d['max_date']}` |",
        f"| `today` (UTC) | `{d['today']}` |",
        f"| `days_since_max` | {d['days_since_max']} |",
        f"| `row_count` | {d['row_count']} |",
        f"| `unique_dates` | {d['unique_dates']} |",
    ]
    if d.get("error"):
        lines.append(f"| error | `{d['error']}` |")
    return "\n".join(lines)


def _format_scheduler_processes(d: dict[str, Any]) -> str:
    lines = [
        "### §7. Scheduler process enumeration (`pgrep -af uvicorn|backend.*scheduler`)",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| `running` | {d['running']} |",
        f"| `pids` | `{d['pids']}` |",
    ]
    if d.get("error"):
        lines.append(f"| `error` | `{d['error']}` |")
    lines.extend(["", "**Cmdlines:**", ""])
    if d["cmdlines"]:
        for cl in d["cmdlines"]:
            lines.append(f"- `{cl}`")
    else:
        lines.append("_(no matching processes)_")
    return "\n".join(lines)


def _emit_markdown(results: dict[str, Any], out_path: Path | None) -> str:
    """Format seven sections into a Markdown evidence block.

    If `out_path` is provided:
      * If file missing, create with a minimal scaffold + inject the block.
      * If file exists and contains `EVIDENCE_BEGIN` + `EVIDENCE_END` markers,
        replace the block between them (idempotent).
      * If file exists without markers, append the block after the existing
        content.
    Returns the formatted block as a string in all cases.
    """
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body_sections = [
        "## Evidence",
        "",
        f"_Machine-generated at {generated_at} by `scripts/diagnose_live_silence_999_1.py --emit-markdown`. "
        "Re-run the script to refresh this block in place; content between the BEGIN/END markers is "
        "overwritten deterministically._",
        "",
        _format_last_alert(results["last_alert"]),
        "",
        _format_live_runs(results["live_runs"]),
        "",
        _format_live_channels(results["live_channels"]),
        "",
        _format_live_statuses(results["live_statuses"]),
        "",
        _format_alert_data_sources(results["alert_data_sources"]),
        "",
        _format_parquet(results["parquet"]),
        "",
        _format_scheduler_processes(results["scheduler_processes"]),
    ]
    body = "\n".join(body_sections)
    block = f"{EVIDENCE_BEGIN}\n{body}\n{EVIDENCE_END}"

    if out_path is None:
        return block

    out_path = Path(out_path)

    if not out_path.exists():
        scaffold = (
            "# Phase 999.1 — LIVE Pipeline Silence Diagnosis\n"
            "\n"
            "**Investigation date:** "
            + datetime.now(timezone.utc).strftime("%Y-%m-%d")
            + "\n"
            "**Scope:** Root-cause analysis for Case C `triggered=True` at Phase 10.1-08 re-enable\n"
            "**Method:** read-only queries against live DB + parquet (no mutation)\n"
            "\n"
            + block
            + "\n"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(scaffold, encoding="utf-8")
        return block

    existing = out_path.read_text(encoding="utf-8")
    if EVIDENCE_BEGIN in existing and EVIDENCE_END in existing:
        pattern = re.compile(
            re.escape(EVIDENCE_BEGIN) + r".*?" + re.escape(EVIDENCE_END),
            re.DOTALL,
        )
        new_text = pattern.sub(block, existing, count=1)
    else:
        sep = "" if existing.endswith("\n") else "\n"
        new_text = existing + sep + "\n" + block + "\n"
    out_path.write_text(new_text, encoding="utf-8")
    return block


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def _run_all_checks() -> dict[str, Any]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Live DB not found at {DB_PATH}")

    # Read-only URI — T-999.1.01-01 mitigation.
    uri = f"file:{DB_PATH}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        return {
            "last_alert": _check_last_alert(conn),
            "live_runs": _check_live_runs(conn),
            "live_channels": _check_live_channels(conn),
            "live_statuses": _check_live_statuses(conn),
            "alert_data_sources": _check_alert_data_sources(conn),
            "parquet": _check_parquet_max_date(),
            "scheduler_processes": _check_scheduler_processes(),
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 999.1 read-only LIVE-silence diagnostic (MONITOR-09).",
    )
    parser.add_argument(
        "--emit-markdown",
        metavar="PATH",
        type=Path,
        default=None,
        help=(
            "Splice the evidence block into the given Markdown file between "
            "the BEGIN/END EVIDENCE 999.1-01 markers (idempotent). If the "
            "file does not exist, a scaffold is created."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit raw results as JSON to stdout instead of Markdown.",
    )
    args = parser.parse_args()

    try:
        results = _run_all_checks()
    except Exception as exc:
        print(f"DIAGNOSTIC_ERROR: {exc!r}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(results, indent=2, default=str))
        return 0

    block = _emit_markdown(results, args.emit_markdown)
    if args.emit_markdown:
        print(
            f"Evidence block written to {args.emit_markdown} "
            f"(between {EVIDENCE_BEGIN} / {EVIDENCE_END})."
        )
    else:
        print(block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
