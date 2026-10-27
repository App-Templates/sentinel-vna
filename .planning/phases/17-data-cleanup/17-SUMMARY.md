---
phase: 17-data-cleanup
status: shipped
shipped_at: 2026-05-07
shipped_by: Stefano Argiolas
requirements: [CLEAN-01, CLEAN-02]
production_url: https://sentinel-vna-stefano-hejais-projects.vercel.app
---

# Phase 17 — Data Cleanup SHIPPED

## CLEAN-01: floor_cpm dead column

**Decision: documented as dead, no schema change.**

`floor_cpm` is referenced in `backend/agents/data_fetcher_real.py` (weighted-average aggregation) but the source parquet (`data/sentinel_db/daily_kpi.csv` / `daily_adrequests.csv`) returns `None` for every observed row (verified 2026-05-07 across 3 publishers' weekly KPIs sample).

The aggregation logic survives gracefully — `if 'floor_cpm' in df_filtered.columns` → all-None branch → returns `None`. UI receives `null` and renders "—".

**Why not removed from schema now:** schema migration touches `backend/db/models.py`, `backend/api/schemas.py`, multiple frontend types, and a CHECK constraint. Phase 18 (schema gate + contract tests) is the appropriate place to bundle schema cleanup with regression coverage. Premature removal here risks breaking response shape silently.

**Documentation owed in Phase 18:** `DATA_INTEGRATION.md` must list `floor_cpm` as deprecated/dead with rationale + removal target.

## CLEAN-02: Mondadori family aggregation

**Implementation: backend `/api/publishers/top` collapses Mondadori + Mondadori_npa + Mediamond + Adgage_mondocore into single `Mondadori_family` row.**

Before:
- Mondadori: €959,261 (8.17%)
- Mondadori_npa: €166,163 (1.41%)
- Mediamond: €332,874 (2.83%)

After (Mondadori_family aggregated):
- **Mondadori_family: €1,458,298 (12.42%)** — now #1 in revenue share

Production-verified (`https://sentinel-vna-stefano-hejais-projects.vercel.app/api/publishers/top`):
```
1. Mondadori_family       12.42%  €1,458,298
2. AdGage_Vocento          9.86%  €1,157,530
3. AdGage_PrensaIberica    8.61%  €1,010,699
```

**Code change:** `backend/api/publisher_routes.py` `get_top_publishers`:
- pre-mapping `df_year["publisher_id"]` BEFORE the `groupby` — collapses 4 publisher_ids to `Mondadori_family`
- same pre-mapping for `df_ch_year` (Google% calculation) for consistency

**Frontend:** `frontend/src/pages/PublishersPage.tsx` — DataTable `onRowClick` skips navigation when `publisher_id` ends with `_family` (drilldown to family-level detail not yet implemented; clicking individual publishers in URL still works).

**Known gap (deferred):** drilldown `/api/publishers/Mondadori_family/...` returns 404. Family-aggregated detail endpoints would require similar pre-mapping in `get_publisher_detail`, `get_publisher_weekly_kpis`, etc. — deferred to Phase 18 alongside contract tests that pin family aggregation behavior.

## Closes Vito email RC-b

> "I numeri Mondadori non sono aggregati: Mondadori, Mondadori_npa e Mediamond appaiono separati invece di essere parte dello stesso bacino commerciale."

Aggregation logic now active in publishers/top. The dashboard "top publishers" view shows Mondadori_family as a single line with combined revenue/share. Vito's PBI mental model matches.

## Commits

- `<NEXT>` — feat(api): Phase 17 CLEAN-02 Mondadori family aggregation in publishers/top
- `<NEXT>` — feat(ui): Phase 17 — disable family drilldown click in PublishersPage
- `<CLOSE>` — docs(phase-17): close Phase 17 with v1.3 redeploy

## Roadmap impact

Phase 17 [x] complete. Phase 18 (Hardening + PBI Contract Tests + Docs) absorbs:
- floor_cpm schema removal + DATA_INTEGRATION.md update
- Family-aggregated detail endpoints (Mondadori_family drilldown)
- Contract test pinning Mondadori_family aggregation invariant
