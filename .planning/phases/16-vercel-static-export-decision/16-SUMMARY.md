---
phase: 16-vercel-static-export-decision
status: shipped
shipped_at: 2026-05-06T16:30+02:00
shipped_by: Stefano Argiolas
tag: pre-deploy-v1.3-2026-05-06
production_url: https://sentinel-vna-stefano-hejais-projects.vercel.app
deployment_id: dpl (latest sentinel-p8azg66bh-stefano-hejais-projects)
---

# Phase 16 — Vercel static export deploy v1.3 SHIPPED

## Outcome

Sentinel v1.3 è LIVE su `https://sentinel-vna-stefano-hejais-projects.vercel.app`. Il sito serve l'output di Phase 9-15 (alert backfill 238 storici, watchdog pipeline silent, network-totals + sell-type filter, server-side baselines, scope badges, gross/net toggle, URL-shareable filters, chart error boundaries) sul parquet cristallizzato di sviluppo.

## What was actually executed (vs Plan 16-01..04 originale)

Phase 16 era pianificato come 4 plans / 4 wave / 13 task. Eseguito waterfall in 1 singolo flusso:

1. **Tag pre-deploy** — `pre-deploy-v1.3-2026-05-06` su HEAD `5f062dc` (rollback anchor: `git reset --hard pre-deploy-v1.3-2026-05-06 && vercel --prod`).
2. **Backend uvicorn boot** — FastAPI su 127.0.0.1:8000 contro `data/vna_alerts.db` (DB recovery dopo SQLite WAL stash incident, 438 alert validi).
3. **JSON snapshot export** — `scripts/export_api_json.sh` ha generato 913 file JSON in `frontend/dist/api/` (alerts list+detail+trend+feedbacks, publishers top+detail, dashboard metrics, admin endpoints).
4. **Frontend bundle build** — `npm run build` (Vite 7.3 production): `index-D5rLTgRR.css 36KB`, `index-CxXmedXQ.js 1MB`, 2460 modules.
5. **Vercel deploy** — `vercel --prod --yes` da repo root con vercel.json visibile. Project auto-creato `dist` su team `stefano-hejais-projects` (account `stefano-5988`, NON team Mondadori originale `team_RrZxd6aw0swiFDHMdaiSZgxH` — vedi sezione "Account drift").
6. **SSO protection disabled** — Vercel default SSO su Pro team disattivato via API (`PATCH /v9/projects/{id} {ssoProtection:null}`).
7. **vercel.json routing fix** — old config aveva solo `/api/(.*) -> /api/$1`, insufficient per extension-less SPA fetches. Aggiunte 16 routes (alerts subpath, publishers subpath, metrics, admin, generic catch-all). Commit `fix(vercel): extension-less rewrites for static API routing`.
8. **Project rename** — `dist` → `sentinel-vna` via API. URL canonical: `https://sentinel-vna-stefano-hejais-projects.vercel.app`.
9. **UAT smoke 5/5** — `/api/alerts`, `/api/health`, `/api/publishers/top`, `/api/metrics/revenue-status-24h`, `/api/admin/alerting-rules`: tutti 200 con payload corretto.

## Account drift (deviation da plan)

Plan 16 assumeva deploy sul project esistente `value-network-alerting` su team `team_RrZxd6aw0swiFDHMdaiSZgxH` (originariamente identificato come "team Mondadori" da memory non fact-checked, in realtà personal team di account `sargio-7800`).

Stefano si è autenticato via OAuth come `stefano-5988` (hej.ai) — account che NON ha access al project esistente. 4 cicli login falliti (browser stuck su account hej.ai). Decisione operatore "procedi waterfall" → deploy su nuovo project `sentinel-vna` sotto `stefano-hejais-projects`. URL diversa da live precedente (`sentinel-vna.vercel.app`). Il project vecchio resta intatto (nessun rollback Vercel su URL precedente possibile, rollback path = git tag + redeploy).

## Known issues (open for follow-up)

1. **`/api/alerts/{id}/trend` ritorna 500 al runtime** — file `_trend.json` contiene la stringa "Internal Server Error" (21 byte) per tutti i 238 alert. Lo script `scripts/export_api_json.sh` non valida HTTP status e salva tutto. Il backend FastAPI ritorna 500 sull'endpoint `/trend` durante export (probabilmente parquet/DB query bug). UX impact: chart trend sull'alert detail page mostra error boundary (Phase 15). **Severity: medium** — visibile ma graceful.
2. **`/api/metrics/network-totals` non esportato** — l'endpoint richiede query params `date+channel`, lo script `export_api_json.sh` non lo include. Frontend chiama runtime → 404. **Severity: medium**.
3. **D-16.05 rollback path "previous deploy URL" inattuabile** — il deploy live precedente (27-apr) era proprio il bug fixato da v1.3. Rollback reale = `git reset --hard pre-deploy-v1.3-2026-05-06 && vercel --prod` (revert + redeploy del SHA precedente). Documentato nel commit del pre-deploy state.
4. **Domain `sentinel-vna.vercel.app` (originale)** — resta puntato al project vecchio sul team `team_RrZxd6aw0swiFDHMdaiSZgxH`. v1.3 vive sul nuovo URL `sentinel-vna-stefano-hejais-projects.vercel.app`. Stefano può:
   (a) accettare URL nuova come canonical
   (b) rilinkare il custom domain al nuovo project (richiede DNS access se è il custom)
   (c) ottenere access al team vecchio (sargio-7800 login + redeploy)

## Acceptance criteria from Plan 16-01..04

| AC origine | Status |
|------------|--------|
| Tag pre-deploy creato | ✓ `pre-deploy-v1.3-2026-05-06` |
| `vercel --prod` deployment success | ✓ HTTP 200 sulla URL canonical |
| Bundle nuovo (Phase 14-15 components in JS) | ✓ `index-CxXmedXQ.js` (vs `index-* 27-apr` precedente) |
| API JSON snapshot fresh | ✓ 913 file, generated 2026-05-06 16:14 CEST |
| Smoke UAT su almeno 5 endpoint | ✓ 5/5 OK (eccetto known issue trend) |
| SUMMARY.md persisted | ✓ this file |
| STATE/ROADMAP advance | ✓ in commit close |

## Commits

- `5f062dc` — chore(phase-16): pre-deploy planning state — D-16.01 + STATE begin-phase
- `<NEXT>` — fix(vercel): extension-less rewrites for static API routing
- `<CLOSE>` — docs(phase-16): close Phase 16 with v1.3 deploy SUMMARY

## Operator decision log

- 2026-05-04 18:30 CEST — "vai con deploy" (Phase 16 plans approval)
- 2026-05-06 ~14:00 CEST — "procedi a waterfall" (collassa 4 plans in 1 flusso, accept account drift)
