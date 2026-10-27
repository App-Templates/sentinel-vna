#!/usr/bin/env python3
"""
Phase 17.4 D2CLOSE-03 (D-07, D-09) — In-place rewrite of 39 GOOGLE_ADEX
backfill alerts. Uses Plan 02 Path A (hour_kpi.csv direct read) via
`backend.agents.data_fetcher_real.data_fetcher_agent` in BACKTEST mode.

Replaces the synthetic-era revenue_current/baseline/delta_pct with PBI-parity
numbers; flips data_source='backfill' → 'real_csv'.

Idempotent: second run completes 0-UPDATE because all 39 alerts already carry
data_source='real_csv' after first execution.

Dry-run: --dry-run prints per-alert before/after WITHOUT writing.

Run:
    .venv/bin/python scripts/rewrite_backfill_google_adex_post_17_4.py [--dry-run] [--db <path>]

Pre-requisites (enforced by BLOCKING gate Task 2):
    - Migration 006 applied (199 non-GOOGLE_ADEX rows deprecated=1)
    - Snapshot data/vna_alerts.db.pre-17.4-backfill-rewrite exists (WAL-safe backup)
    - Git tag pre-17.4-backfill-rewrite set on current HEAD
    - Operator R-05 OK obtained

Exit codes:
    0 = success (39 UPDATEd) OR idempotent-noop (already rewritten)
    1 = fatal precondition failure
    2 = per-alert data_fetcher_real call failure (aborts on first failure)
    3 = post-rewrite count mismatch (expected 39 real_csv, got something else)
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_DB = REPO_ROOT / "data" / "vna_alerts.db"
REPORT_PATH = (
    REPO_ROOT
    / ".planning"
    / "phases"
    / "17.4-d2-closure-tecnica-post-phase-17-3-downgrade"
    / "17.4-BACKFILL-REWRITE-REPORT.md"
)

# Query to identify the 39 GOOGLE_ADEX backfill alerts to rewrite.
# Idempotency: skips rows already flipped to data_source != 'backfill'.
SELECT_TARGETS_SQL = """
    SELECT alert_id, timestamp, channel_group, alert_rule, severity,
           revenue_current, revenue_baseline, revenue_delta_pct, data_source
      FROM alerts
     WHERE channel_group = 'GOOGLE_ADEX'
       AND data_source = 'backfill'
       AND deprecated = 0
     ORDER BY timestamp
"""

# UPDATE SQL — sets new revenue values + flips provenance tag.
UPDATE_SQL = """
    UPDATE alerts
       SET revenue_current = ?,
           revenue_baseline = ?,
           revenue_delta_pct = ?,
           data_source = 'real_csv',
           updated_at = ?
     WHERE alert_id = ?
"""

# Edge case: GOOGLE_ADEX alerts whose timestamp falls outside hour_kpi.csv coverage
# (verified 2026-05-21: CSV terminates at 2026-03-23 00:00:00 UTC; the only Phase 09
# backfill alert at 2026-03-23 01:00:00 has no CSV row to read). Plan 02 Path A
# cannot supply real values for these — we mark them deprecated with a reason that
# parallels Migration 006 (the 199 non-GOOGLE_ADEX deprecations) so they share a
# canonical "synthetic-era pre-H6-fix" provenance flag in audit queries.
DEPRECATE_EOF_SQL = """
    UPDATE alerts
       SET deprecated = 1,
           deprecation_reason = 'synthetic-era pre-H6-fix, CSV hourly EOF boundary 2026-03-23',
           updated_at = ?
     WHERE alert_id = ?
"""

EXPECTED_COUNT = 39  # total D-07 targets (rewrite + EOF-deprecate combined)


def _now_canonical() -> str:
    """Migration 004 canonical: space-separator naive UTC microseconds."""
    return (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
        .strftime("%Y-%m-%d %H:%M:%S.%f")
    )


def _normalize_timestamp(ts: str) -> str:
    """Normalize DB-stored timestamp to ISO 8601 with UTC offset for data_fetcher_agent.

    The alerts table stores timestamps in 'YYYY-MM-DD HH:MM:SS' or
    'YYYY-MM-DD HH:MM:SS.ffffff' format (canonical per Migration 004).
    data_fetcher_agent expects ISO format (with or without offset); the agent
    handles tz-aware inputs by stripping tzinfo internally (Phase 17.3 fix).
    """
    if not ts:
        return ts
    # Replace space separator with T for ISO 8601 compatibility
    normalized = ts.replace(" ", "T") if " " in ts and "T" not in ts else ts
    # Append UTC offset if missing (live data is UTC-only per Phase 07/09 audit)
    if "+" not in normalized and "Z" not in normalized:
        normalized = normalized + "+00:00"
    return normalized


def _build_state(row: sqlite3.Row) -> dict:
    """Build AlertState dict for data_fetcher_agent BACKTEST invocation."""
    ts = _normalize_timestamp(row["timestamp"])
    return {
        "trigger_type": row["alert_rule"],
        "channel_group": "GOOGLE_ADEX",
        "mode": "BACKTEST",
        "timestamp": ts,
        "execution_errors": [],
    }


def _compute_new_metrics(row: sqlite3.Row) -> tuple[float, float, float] | None:
    """Invoke data_fetcher_real in BACKTEST mode and extract new revenue values.

    Plan 02 Path A activates for GOOGLE_ADEX + BACKTEST mode:
        - _compute_hourly_totals_for_channel reads hour_kpi.csv (459k rows)
        - matches by timestamp prefix ts[:13] ("YYYY-MM-DD HH")
        - returns hourly aggregate in PBI-parity range
        - sets data_source_used='real_csv' in returned state

    Returns None (signal: edge case → deprecate via DEPRECATE_EOF_SQL) when Path A
    did not activate (e.g. the alert timestamp falls outside hour_kpi.csv coverage
    — verified Phase 09 boundary: CSV terminates 2026-03-23 00:00:00 so the alert
    at 2026-03-23 01:00:00 is 1h beyond EOF). Callers MUST handle None as the
    "deprecate this alert" path rather than UPDATE-with-synthetic-values.
    """
    from backend.agents.data_fetcher_real import data_fetcher_agent

    state = _build_state(row)
    result = data_fetcher_agent(state)

    ds = result.get("data_source", "?")
    if ds != "real_csv":
        # CSV coverage miss — let main loop deprecate this row instead of rewriting.
        return None

    cur = float((result.get("current_metrics") or {}).get("revenue", 0.0))
    base = float((result.get("baseline_metrics") or {}).get("revenue", 0.0))

    if base > 0:
        delta_pct = ((cur - base) / base) * 100.0
    else:
        delta_pct = 0.0

    return round(cur, 2), round(base, 2), round(delta_pct, 2)


def _emit_report(records: list[dict], db_path: Path, eof_deprecated: list[dict] | None = None) -> None:
    """Write per-alert before/after report to REPORT_PATH.

    Called only after successful non-dry-run rewrite. Overwrites any existing
    report file (idempotent report generation).

    Args:
        records: List of alerts that got rewritten to real_csv (PBI-parity values).
        eof_deprecated: List of alerts deprecated due to CSV EOF boundary
            (timestamps outside hour_kpi.csv coverage — e.g. 2026-03-23 01:00
            falls 1h beyond Phase 09 backfill EOF). Defaults to empty list.
    """
    eof_deprecated = eof_deprecated or []
    gen_ts = _now_canonical()
    lines = [
        "---",
        "phase: 17.4-d2-closure-tecnica-post-phase-17-3-downgrade",
        "type: backfill-rewrite-report",
        f"generated: {gen_ts}Z",
        f"db_path: {db_path}",
        f"alerts_rewritten: {len(records)}",
        f"alerts_eof_deprecated: {len(eof_deprecated)}",
        "channel_group: GOOGLE_ADEX",
        "rewrite_source: data/sentinel_db/hour_kpi.csv (via Plan 02 Path A _compute_hourly_totals_for_channel)",
        "---",
        "",
        "# Phase 17.4 — Backfill Rewrite Report (D2CLOSE-03)",
        "",
        f"**Generated:** {gen_ts} UTC",
        f"**Total alerts UPDATEd to real_csv:** {len(records)}",
        f"**Total alerts EOF-deprecated:** {len(eof_deprecated)} "
        "(timestamps outside `hour_kpi.csv` coverage — see CSV EOF section below)",
        "**Source of new values:** `data/sentinel_db/hour_kpi.csv` aggregated by "
        "(timestamp prefix YYYY-MM-DD HH, channel_group='GOOGLE_ADEX') via Plan 02 "
        "`_compute_hourly_totals_for_channel`.",
        "**Provenance flip:** `data_source='backfill'` → `data_source='real_csv'`.",
        "",
        "## Per-alert before/after",
        "",
        "| alert_id | timestamp | old_revenue (€) | new_revenue (€) | delta_eur (€) | delta_pct (%) |",
        "|----------|-----------|-----------------|-----------------|---------------|---------------|",
    ]

    total_delta_eur = 0.0
    max_delta_eur = 0.0
    for r in records:
        d_eur = r["new_revenue"] - r["old_revenue"]
        d_pct = (d_eur / r["old_revenue"] * 100.0) if r["old_revenue"] != 0 else 0.0
        total_delta_eur += d_eur
        if abs(d_eur) > max_delta_eur:
            max_delta_eur = abs(d_eur)
        lines.append(
            f"| {r['alert_id']} | {r['timestamp']} | {r['old_revenue']:.2f} | "
            f"{r['new_revenue']:.2f} | {d_eur:+.2f} | {d_pct:+.2f}% |"
        )

    mean_delta = (total_delta_eur / len(records)) if records else 0.0
    lines.extend(
        [
            "",
            "## Summary statistics",
            "",
            f"- Alerts rewritten: {len(records)}",
            f"- Alerts EOF-deprecated: {len(eof_deprecated)}",
            f"- Mean delta EUR (rewritten only): {mean_delta:+.2f}",
            f"- Max abs delta EUR (rewritten only): {max_delta_eur:.2f}",
            "- Source CSV: `data/sentinel_db/hour_kpi.csv` (no top-50 filter; "
            "Phase 11 SUMMARY verified PBI parity ±0.17%)",
            "- Helper: `backend.api.routes._compute_hourly_totals_for_channel(timestamp_str, 'GOOGLE_ADEX')`",
            "- Phase 17.3 root cause (tz-mismatch silent synthetic fallback) closed in Plan 02; "
            "this rewrite makes the closure visible in historical alert rows.",
        ]
    )

    # CSV EOF edge case section (only emitted if any alerts were affected)
    if eof_deprecated:
        lines.extend(
            [
                "",
                "## CSV EOF-deprecated alerts",
                "",
                "GOOGLE_ADEX alerts whose timestamp falls outside `hour_kpi.csv` coverage "
                f"({len(eof_deprecated)} alerts). CSV terminates at `2026-03-23 00:00:00` "
                "(Phase 09 backfill EOF boundary). Plan 02 Path A cannot supply real values "
                "for these — they are marked `deprecated=1` with reason "
                "`'synthetic-era pre-H6-fix, CSV hourly EOF boundary 2026-03-23'` so they "
                "share canonical synthetic-era provenance flag with the 199 non-GOOGLE_ADEX "
                "alerts deprecated by Migration 006.",
                "",
                "| alert_id | timestamp | old_revenue (€) | action |",
                "|----------|-----------|-----------------|--------|",
            ]
        )
        for r in eof_deprecated:
            lines.append(
                f"| {r['alert_id']} | {r['timestamp']} | {r['old_revenue']:.2f} | "
                "deprecated=1 (CSV EOF) |"
            )

    lines.extend(
        [
            "",
            "## Rollback",
            "",
            "1. Selective rollback: `sqlite3 data/vna_alerts.db < scripts/migrations/006_rollback.sql` "
            "(undoes Migration 006 marking ONLY — not this rewrite)",
            "2. Full rollback: `cp data/vna_alerts.db.pre-17.4-backfill-rewrite data/vna_alerts.db`",
            "3. Code rollback: `git checkout pre-17.4-backfill-rewrite` "
            "(reverts Migration 006 + driver source; live DB only restored via #2)",
        ]
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print per-alert before/after without writing to DB. Exit 0.",
    )
    ap.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"Path to SQLite DB (default: {DEFAULT_DB})",
    )
    args = ap.parse_args()

    if not args.db.exists():
        print(f"FATAL: DB not found at {args.db}")
        return 1

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row

    try:
        targets = conn.execute(SELECT_TARGETS_SQL).fetchall()
    except sqlite3.OperationalError as e:
        conn.close()
        print(f"FATAL: SELECT failed: {e}")
        return 1

    # Idempotency check: if no targets but expected count already in real_csv
    if len(targets) == 0:
        post = conn.execute(
            "SELECT COUNT(*) FROM alerts "
            "WHERE channel_group='GOOGLE_ADEX' AND data_source='real_csv'"
        ).fetchone()[0]
        conn.close()
        if post == EXPECTED_COUNT:
            print(
                f"IDEMPOTENT-NOOP: all {EXPECTED_COUNT} GOOGLE_ADEX backfill alerts "
                "already rewritten (data_source='real_csv')."
            )
            return 0
        print(
            f"WARNING: 0 targets found and {post} real_csv rows "
            f"(expected {EXPECTED_COUNT}). Manual inspection required."
        )
        return 1

    if len(targets) != EXPECTED_COUNT:
        print(
            f"WARNING: expected {EXPECTED_COUNT} targets, found {len(targets)}. "
            "Proceeding but report may be partial."
        )

    # Process each target alert
    records = []
    eof_deprecated = []  # alerts marked deprecated due to CSV EOF boundary
    print(f"{'DRY RUN: ' if args.dry_run else ''}Processing {len(targets)} GOOGLE_ADEX backfill alerts...")
    for i, row in enumerate(targets, 1):
        try:
            result = _compute_new_metrics(row)
        except Exception as e:
            conn.close()
            print(f"[{i}/{len(targets)}] {row['alert_id']} FAILED: {e}")
            return 2

        old_cur = float(row["revenue_current"])

        if result is None:
            # CSV coverage miss → deprecate (parallel to Migration 006 path for 199 non-GA alerts)
            print(
                f"[{i}/{len(targets)}] {row['alert_id']} {row['timestamp']} "
                f"CSV-EOF → deprecate (old=€{old_cur:.2f})"
            )
            eof_deprecated.append(
                {
                    "alert_id": row["alert_id"],
                    "timestamp": row["timestamp"],
                    "old_revenue": old_cur,
                    "reason": "synthetic-era pre-H6-fix, CSV hourly EOF boundary 2026-03-23",
                }
            )
            if not args.dry_run:
                conn.execute(
                    DEPRECATE_EOF_SQL,
                    (_now_canonical(), row["alert_id"]),
                )
            continue

        new_cur, new_base, new_delta_pct = result
        delta = new_cur - old_cur
        print(
            f"[{i}/{len(targets)}] {row['alert_id']} {row['timestamp']} "
            f"old=€{old_cur:.2f} new=€{new_cur:.2f} delta=€{delta:+.2f}"
        )

        records.append(
            {
                "alert_id": row["alert_id"],
                "timestamp": row["timestamp"],
                "old_revenue": old_cur,
                "new_revenue": new_cur,
                "new_baseline": new_base,
                "new_delta_pct": new_delta_pct,
            }
        )

        if not args.dry_run:
            conn.execute(
                UPDATE_SQL,
                (new_cur, new_base, new_delta_pct, _now_canonical(), row["alert_id"]),
            )

    if not args.dry_run:
        conn.commit()

    # Post-write verification (or dry-run summary)
    post_real_csv = conn.execute(
        "SELECT COUNT(*) FROM alerts "
        "WHERE channel_group='GOOGLE_ADEX' AND data_source='real_csv'"
    ).fetchone()[0]
    post_eof_deprecated = conn.execute(
        "SELECT COUNT(*) FROM alerts "
        "WHERE channel_group='GOOGLE_ADEX' AND deprecated=1 "
        "AND deprecation_reason='synthetic-era pre-H6-fix, CSV hourly EOF boundary 2026-03-23'"
    ).fetchone()[0]
    conn.close()

    expected_rewrite = len(records)
    expected_eof = len(eof_deprecated)

    if args.dry_run:
        print(
            f"\nDRY RUN complete: {expected_rewrite} alerts WOULD be UPDATEd to real_csv, "
            f"{expected_eof} alerts WOULD be deprecated (CSV-EOF). No DB writes."
        )
        print(
            f"Post-dry-run real_csv count (unchanged): {post_real_csv} "
            f"(expected {expected_rewrite} after actual rewrite)"
        )
        return 0

    # Verify post-write counts: rewrite matches what we processed; total
    # rewrite + eof_deprecated must equal the EXPECTED_COUNT (39) of targets seen.
    if post_real_csv != expected_rewrite:
        print(
            f"FAIL: post-rewrite real_csv count expected {expected_rewrite}, "
            f"got {post_real_csv}. Full rollback: "
            f"cp data/vna_alerts.db.pre-17.4-backfill-rewrite data/vna_alerts.db"
        )
        return 3
    if post_eof_deprecated != expected_eof:
        print(
            f"FAIL: post-rewrite EOF-deprecated count expected {expected_eof}, "
            f"got {post_eof_deprecated}. Full rollback: "
            f"cp data/vna_alerts.db.pre-17.4-backfill-rewrite data/vna_alerts.db"
        )
        return 3
    if (expected_rewrite + expected_eof) != EXPECTED_COUNT:
        print(
            f"FAIL: processed total {expected_rewrite + expected_eof} != EXPECTED_COUNT "
            f"{EXPECTED_COUNT} GOOGLE_ADEX backfill targets. Investigate before commit."
        )
        return 3

    # Emit report (includes both rewrite + EOF-deprecate sections)
    _emit_report(records, args.db, eof_deprecated=eof_deprecated)
    print(
        f"\nOK: rewrote {expected_rewrite} GOOGLE_ADEX backfill alerts "
        f"(data_source='backfill' → 'real_csv') + deprecated {expected_eof} EOF alerts. "
        f"Report: {REPORT_PATH}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
