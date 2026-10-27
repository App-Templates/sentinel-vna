# WIP Audit — 56 Files Uncommitted

**Agent:** Explore subagent (read-only, 500 MB budget)
**Date:** 2026-04-22
**Scope:** `/Users/admintemp/Downloads/Claude/value-network-alerting` branch `main`
**WIP totals:** 2410 insertions, 1966 deletions

## Inventory by theme

| Theme | Files | Lines ± |
|---|---|---|
| frontend/components/alerts/* | 12 | +327/-285 |
| frontend/components/dashboard/* | 7 | +381/-179 |
| frontend/components/charts/* | 3 | +126/-86 |
| frontend/pages/* | 9 | +1412/-1368 |
| frontend/components/ui/* | 7 | +112/-71 |
| frontend/components/layout/* | 4 | +236/-37 |
| frontend/other (main, index.css, client, lib) | 6 | +179/-157 |
| backend/api/* | 2 | +72/-15 |
| scripts/* | 1 | +67/-32 |
| config/deploy (vercel, vite) | 2 | +22/-8 |
| data/db (sqlite binary) | 3 | Bin diff |
| .gitignore | 2 | +2/0 |
| **TOTAL** | **56** | **+2410/-1966** |

## Semantic summary

### frontend/components/alerts (12 files)
Cohesive styling polish. Card component migration + `tabular-nums` typography + uppercase tracking-wide labels. **Non-breaking.**
- P0-3 overlap: TriageSection touched only for tabular-nums; `revenueRatio * 0.95` heuristic **NOT removed**.

### frontend/components/dashboard (7 files)
Mixed cohesive + experimental.
- **RevenueStatus24h (+196 lines)**: major refactor — date picker (`available_dates`), YoY comparison con hourly distribution, i18n labels, Card migration. **New feature.**
- KpiCards, RevenueByChannel: minor styling.
- **Contract change**: expects `available_dates: string[]` + `prev_year.hours: number[]` (was `hourly_avg: number`). Backend must match.

### frontend/pages (9 files)
Mixed: i18n + feature refactor.
- **DocsPage (1786 lines ±)**: complete IT→EN translation + slate palette.
- **PublishersPage (+200)**: year selector → year+month; default 2026; bacino/coverage → fill_rate.
- **PublisherDetailPage (+384)**: IT→EN translation, locale `it-IT` → `en-US`, MetricCard adoption.
- Altre pages: minor i18n + styling.
- P0-4 overlap: RevenueStatusSection aggiornato con date header, ma manca ancora label esplicita "7-week rolling avg" su baseline. **Partial fix.**

### frontend/components/ui (7 files)
Refinement. Card/Button/Badge/DataTable/Skeleton/DeltaIndicator/MetricCard polish. Non-breaking CSS.

### frontend/components/layout (4 files)
i18n + styling overhaul.
- Sidebar (+194): nav labels via `useNavItems()` + `useTranslation()`. LanguageSwitcher stub referenced but not in diff.

### frontend/other
Design system + type system.
- **index.css (+126)**: design tokens (--color-severity-*, --color-status-*, --chart-*), typography scale, focus ring, scrollbar.
- **main.tsx**: LanguageProvider wrapper.
- **client.ts**: `useRevenueStatus24h(date?)` path-based; `PrevYearData` interface updated; `useTopPublishers(year, month?)`.
- **lib/utils.ts**: minor additions.
- **API contract changes**: hours[] replaces hourly_avg.

### backend/api (2 files)
Data correctness fixes — cohesive.
- **routes.py (+57)**:
  - `/metrics/revenue-status-24h/{date_path}` nuovo endpoint
  - Complete-day detection (≥20h data) vs partial days
  - Default last complete day (non day.max())
  - `available_dates` list (last 7 complete days)
  - **YoY: single-day lookup → 7-week rolling average** (more robust baseline)
- **publisher_routes.py (+15)**: bacino deduplication fix — group by (pub, date, env, geo) → divide by channel count → sum. **Data correctness fix for P0-4 (bacino overcount)**.
- P0-1 sentinel_db migration: not touched (già fatto in v1.2).
- P0-2 sell_type filter: not touched.

### scripts (1 file)
Experimental. `export_api_json.sh` refactor: nested dir structure (publishers/{id}, alerts/{id}/*.json), date-based exports, multi-year. Non-functional if backend doesn't return `available_dates`.

### config/deploy (2 files)
**Breaking architectural change.**
- `vercel.json`: removed old `routes` array + outputDirectory. Replaced with `cleanUrls: true`, `trailingSlash: false`, `rewrites: /api/(.*) → /api/$1.json`, CORS headers for API.
- **Implication**: API responses expected as static JSON files. **Deployment model shift from SPA+backend to SSG+CDN-hosted API cache.**
- `vite.config.ts (+3)`: minor.

### data/db (3 files binary diff)
SQLite `vna_alerts.db + WAL` locally mutated. **NO migration script in WIP.**
- P0-1 overlap red flag: schema may have changed without tracking.

### .gitignore (2 files)
`.vercel` added. Proper housekeeping. No credential leaks.

## Atomic-commit proposal

**56 file NON coerenti come singolo commit.** Split in 5 atomic:

### Commit A — Frontend Design System & i18n Infrastructure
10 file foundational:
- `frontend/src/index.css`
- `frontend/src/main.tsx`
- `frontend/src/components/ui/{Button,Card,Badge,Skeleton}.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/lib/utils.ts`
- `.gitignore` additions

Rationale: enables i18n + design consistency. Non-breaking.

### Commit B — Frontend i18n Content
10 file pure localization:
- `frontend/src/pages/DocsPage.tsx` (IT→EN)
- `frontend/src/pages/PublisherDetailPage.tsx`
- `frontend/src/components/layout/*` (nav label i18n)
- Altre page i18n tweaks

Rationale: pure translation. Deferrable or separate review.

### Commit C — Backend Data Correctness Fixes
2 file:
- `backend/api/routes.py` (YoY rolling avg, complete-day detection, available_dates)
- `backend/api/publisher_routes.py` (bacino dedup, fill_rate fix)

Rationale: data correctness. Independent of frontend. Land first.

### Commit D — Frontend Dashboard Features & Date Navigation
8 file:
- `frontend/src/components/dashboard/RevenueStatus24h.tsx`
- `frontend/src/api/client.ts` (new types)
- `frontend/src/components/alerts/RevenueStatusSection.tsx`
- `frontend/src/components/charts/*`
- `frontend/src/pages/PublishersPage.tsx`
- `frontend/src/pages/{DashboardPage,AlertsListPage}.tsx`

Rationale: feature coherence. **Depends on C** (backend contract). **Includes API contract change**.

### Commit E — Deployment & Static Export Layer [⚠ SHELVE]
5 file:
- `vercel.json` (static export routing)
- `vite.config.ts`
- `scripts/export_api_json.sh` (nested exports, date-based)
- `data/vna_alerts.db*` (seed/migration)
- `frontend/vite.config.ts`

Rationale: **architectural shift** (SPA → SSG). Risk of deployment breakage. Not tied to Milestone 1 completion. **SHELVE for v1.3.1.**

## P0 overlap with WIP

| P0 Item | Status in WIP | Evidence |
|---|---|---|
| P0-3 Triage baseline heuristic | **Not fixed.** | TriageSection.tsx: only tabular-nums added. Logic unmodified (`revenueRatio * 0.95`) |
| P0-4 Revenue reference period | **Partially fixed.** | Date header added; "7-week rolling avg" label still missing |
| P0-2 sell_type filter | **Not touched.** | publisher_routes.py refactored only for bacino dedup |
| P0-1 sentinel_db migration | **Already done in v1.2 commit**, but DB WIP detected without migration script |

## Risk signals

| Category | Finding | Severity |
|---|---|---|
| DB WIP | `vna_alerts.db*` binary diff; no migration script | 🔴 HIGH — schema changes untracked |
| .gitignore | `.vercel` added, no credential leaks | 🟢 Low |
| Vercel config | rewrite + cleanUrls; shifts to static export | 🟡 MEDIUM — architectural change |
| API contract breaking | RevenueStatus24hResponse shape changed | 🟡 MEDIUM — FE+BE in WIP, sync risk |
| Deployment architecture shift | export_api_json.sh + vercel.json | 🟡 MEDIUM — out of scope |
| Incomplete i18n | LanguageSwitcher referenced but not in diff | 🟡 LOW |

## Verdict

**Mixed pile: 2 coherent features + 3 infrastructure/experimental changes.**

Structure:
1. **v1.2 in-flight data correctness** (Commit A, C, D) — 25 file, aligned P0
2. **i18n translation** (Commit B) — 10 file, deferrable
3. **Architectural experimentation** (Commit E) — 5 file, out of v1.2 scope
4. **Unresolved P0** — P0-2, P0-3 untouched; P0-4 partial

## Safest next step

1. **Immediate (before commit)**:
   - `git stash` Commit E
   - Investigate `data/vna_alerts.db` WIP (dump schema + migration script if needed)
2. **Commit order**:
   - A (design) → merge
   - C (backend fixes) → test, merge
   - D (dashboard nav) → land on C, e2e test
   - B (i18n) → parallel or after (orthogonal)
   - HOLD E
3. **Follow-up phase**:
   - P0-2 sell_type filter
   - P0-3 triage heuristic removal or documentation

## Memory footprint
Peak RSS ~180 MB (git diff + file reads, under 500 MB budget).
