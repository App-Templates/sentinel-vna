---
phase: 19-v1-demand-layer-v2-om-distribution
deployed_at: 2026-05-22T14:18Z
operator_pre_authorization: "vai su tutto, come un treno. agisci sempre da voto 10/10" (2026-05-22)
gating: Marco Manduca email feedback 2026-05-19 — V1 (Demand layer) + V2 (OM distribution)
---

# Phase 19 — Deploy Log

## Rollback anchors

- **Pre-deploy git tag:** `pre-19-deploy-2026-05-22` on commit `667f32f`
- **Previous production deployment:** `dpl_feLh7MNo3YRXB2PT8BJwWXmJrfLS` (Phase 17.4, 2026-05-21)
- **Previous canonical alias target:** Vercel rollback via `vercel rollback sentinel-c6ahj0gop-stefano-hejais-projects.vercel.app`
- **Git tag rollback:** `git checkout pre-19-deploy-2026-05-22` (local code reset; live deploy unaffected without redeploy)

## Commits shipped this phase

| SHA | Subject |
|-----|---------|
| `c61a0da` | feat(19): demand-layer taxonomy + mapping (backend Phase 19 V1) |
| `7aa16f1` | feat(19): expose demand_layer in /api/alerts + /api/alerts/{id} (V1) |
| `8501aa0` | feat(19): demand-layer UI — types, lib, badge, list+detail (frontend V1) |
| `09ff45d` | feat(19): Open Market distribution panel — intra-OM shift detection (V2) |
| `667f32f` | docs(19): Marco Manduca reply draft — 8/9 closed + Sample 2 honest disclosure |

## API snapshot regeneration

- Command: `bash scripts/export_api_json.sh "http://127.0.0.1:8765"` (uvicorn on 8765 for export only)
- Output: 404 JSON files in `frontend/dist/api/`
- Demand layer coverage: 38/38 live (non-deprecated) alerts include `demand_layer` field
- Sample 1 snapshot verified post-export: `ALT-20260322-010000-P2.json` — channel_group=GOOGLE_ADEX, demand_layer=OPEN_MARKET, revenue_current=662.67, data_source=real_csv (byte-perfect preserved)

## Deploy

- **Pre-deploy local regression:** 72 passed + 12 skipped (zero regression vs baseline 58+12; +6 new demand_layer tests + recovered models_sync skipped→pass)
- **Pre-deploy TS typecheck:** `npx tsc --noEmit` → exit 0
- **Pre-deploy frontend build:** `npx vite build` → 2.84s, 2462 modules, 1054.84 kB JS / 36.53 kB CSS / 0.47 kB index.html (warning on chunk size is pre-existing)
- **`vercel --prod --yes` invoked:** 2026-05-22T14:18Z
- **Upload size:** 1.9MB
- **Deployment URL (per-deploy):** `https://sentinel-ffv0bkmrv-stefano-hejais-projects.vercel.app`
- **Inspect:** `https://vercel.com/stefano-hejais-projects/sentinel-vna/5VPcDy2iBWrYL8vUJbHqxbJEDpMi`
- **Canonical production alias:** `https://sentinel-vna-stefano-hejais-projects.vercel.app`
- **Status:** Production Ready in 13s

## W-05 CDN smoke (3/3 PASS, first attempt)

| Probe | URL | Verdict | Notes |
|-------|-----|---------|-------|
| Sample 1 alert detail + demand_layer | `/api/alerts/ALT-20260322-010000-P2` | PASS | demand_layer=OPEN_MARKET, revenue_current=662.67, data_source=real_csv |
| Alerts list demand_layer coverage | `/api/alerts?limit=500` | PASS | 38/38 alerts include demand_layer; layers seen: {OPEN_MARKET} |
| Network totals (Phase 17.4 regression) | `/api/metrics/network-totals?date=2026-03-23&channel=GOOGLE_ADEX` | PASS | revenue_gross=€13,725.14 |

All 38 non-deprecated alerts surface as OPEN_MARKET because the Phase 17.4 backfill rewrote only GOOGLE_ADEX (the only channel with hourly CSV data). HBM / HBP / TAM / OPEN_BIDDING / DIRECT / DEAL alerts existed pre-fix in synthetic-era and were deprecated=1 in Phase 17.4 closure. Once Phase 21 Athena hourly ingestion lands, new alerts in those channels will populate DIRETTA / DEAL / OPEN_MARKET buckets.

## V1 + V2 feature surface live

- **V1 demand_layer field:** present in `AlertSummary` + `AlertDetail` schemas → consumed by `frontend/src/types/alert.ts:Alert.demand_layer`.
- **V1 UI badge:** `DemandLayerBadge` renders in `AlertDetailPage` header next to `ChannelBadge` + new "Demand" column in `AlertsTable` (dashboard list).
- **V2 OM distribution panel:** new `currentStep === 'open_market'` tab in `AlertDetailPage`. Visible only when `alert.demand_layer === 'OPEN_MARKET'`. Since `channel_breakdown` is unpopulated on current live alerts, the panel renders the honest data-availability disclosure tied to the Phase 21 Athena dependency — exactly as designed.

## Marco email status

- Draft committed: `.planning/intel/marco-2026-05-19/EMAIL-MARCO-REPLY-DRAFT.md`
- 8/9 points closed and verifiable on live CDN
- 1/9 (D2 Sample 2 HBM byte-perfect) open with structural disclosure
- Pending: operator OK on text + send (anti-pattern: never send without explicit Stefano approval)

## Rollback procedure (if needed)

1. **CDN rollback (Vercel):** `vercel rollback sentinel-c6ahj0gop-stefano-hejais-projects.vercel.app`
   - Reverts to Phase 17.4 deployment `dpl_feLh7MNo3YRXB2PT8BJwWXmJrfLS`
   - Live alerts lose `demand_layer` field; UI gracefully degrades (`demandLayerFor` fallback returns 'OPEN_MARKET' for unknown shapes — no React crash)
2. **Code rollback:** `git -C /Users/admintemp/Downloads/Claude/value-network-alerting checkout pre-19-deploy-2026-05-22` then redeploy with prior dist
3. **Tag preservation:** `pre-19-deploy-2026-05-22` is permanent; can be re-deployed via `vercel --prod --yes` from that checkout
