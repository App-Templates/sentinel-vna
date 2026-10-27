# Phase 09 Coverage Gap Disclosure

**Created:** 2026-04-23 (during Phase 09 Plan 03)
**Scope:** BACKFILL-01 deliverable boundary
**Authority:** 09-CONTEXT.md §D-08, §D-09; 09-03-PLAN.md Task 3 STEP 1b (W-2 fix)

## ROADMAP Amendment

**Original ROADMAP Phase 09 Success Criterion #2:**

> Alert list UI shows ≥ 1 alert per week 2026-01-23 → today

**Amended Success Criterion #2 (landed 2026-04-23):**

> Alert list UI shows ≥ 1 alert per week 2026-01-23 → **parquet_v2_max_date (2026-03-23)**

The amendment is binding on the Phase 09 plan verifier and on any downstream consumer. The word "today" no longer appears in the Phase 09 block of `.planning/ROADMAP.md`. The scope anchor is `parquet_max_date` (also written `parquet_v2_max_date` elsewhere in the context docs) — both refer to `2026-03-23`.

## Gap

No fresh-schema alerts can be generated for the range **2026-03-24 → today** (currently 2026-04-23, 31 days) because:

1. Phase 08 Plan 04 built `data/baseline/daily_aggregated.parquet` with `max_date = 2026-03-23` from `data/sentinel_db/daily_kpi.csv` captured at that snapshot.
2. Extending parquet past 2026-03-23 requires re-running `scripts/etl_csv_to_parquet.py` against newer upstream CSV.
3. Re-running ETL would:
   - Change parquet SHA, which Phase 08 validated against exact checksums.
   - Require re-running the Mondadori Feb 2026 fill-rate regression suite (Phase 08 Plan 05) — a recomputed parquet may drift the 35.2% figure outside the ±1.5 ppt tolerance and turn an otherwise-passing gate red.
   - Introduce scope creep beyond "Alert Backfill" into "ETL Refresh".

The gap is explicit and auditable — it is neither a silent failure nor a forgotten requirement. Consumers (UI, MONITOR-01 plant-seed in Phase 10) that query `/api/alerts` for dates in the gap window will legitimately receive `total=0` for `deprecated=0`.

## Plant-Seed (v1.3.1 or Phase 10)

Resolution options (not executed in Phase 09):

- **Option A (preferred):** Phase 10 MONITOR-01 adds an ETL refresh cron job
  (e.g., daily `etl_csv_to_parquet.py --incremental`) that keeps parquet current.
  A subsequent backfill re-run then closes the gap automatically: the orchestrator
  is idempotent (D-07 + B-2 INSERT OR IGNORE), so re-running over [2026-03-24, N]
  only inserts the new rows.
- **Option B:** v1.3.1 one-shot ETL refresh + backfill re-run for the delta window.
  Scoped as a single plan, with a fresh `v1.3.1-pre-etl-refresh` tag and a new
  Mondadori fill-rate regression gate against the refreshed parquet.

Either option requires an explicit "OK Stefano" because it touches Phase 08
validated checksums — per R-04 chirurgico 10/10 and R-05 no-action-without-OK.

## Verification

Post-backfill queries that prove the gap boundary:

```sql
-- Expected: ≥ 1 alert per ISO week 2026-01-23 → 2026-03-23 (9 weeks)
SELECT strftime('%Y-W%W', timestamp) AS iso_week, COUNT(*) AS n
FROM alerts
WHERE deprecated = 0
  AND timestamp >= '2026-01-23T00:00:00'
  AND timestamp <= '2026-03-23T23:59:59'
GROUP BY iso_week
ORDER BY iso_week;
-- Every row must have n >= 1.

-- Expected: 0 alerts in the gap window (confirms the gap)
SELECT COUNT(*) FROM alerts
WHERE deprecated = 0 AND timestamp > '2026-03-23T23:59:59';
-- Expected: 0 until ETL refresh closes the gap.
```

## References

- `.planning/phases/09-alert-backfill-legacy-migration/09-CONTEXT.md` §D-08 (date range), §D-09 (ROADMAP amendment)
- `.planning/phases/08-schema-migration-etl-extensions/08-04-SUMMARY.md` (parquet v2 schema + max_date provenance)
- `.planning/ROADMAP.md` §Phase 09 Success Criteria (amended line)
- `.planning/phases/09-alert-backfill-legacy-migration/09-ERRATA.md` §W-2 (W-2 override requiring this file + ROADMAP edit in the same commit)
