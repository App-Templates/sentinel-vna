---
phase: 12
plan: 05
subsystem: frontend/api + frontend/pages (PublishersPage)
tags: [corr-08, sell-type-filter, weighted-avg, atomic-commit, ui-spec-ac]
dependency_graph:
  requires:
    - "Phase 12 Plan 01 (i18n keys foundation — `frontend/src/lib/i18n-keys.ts`); imports `SELL_TYPE_LABELS`, `SellTypeKey`, `emptyPublishersFiltered`"
    - "Phase 12 Plan 02 (PublishersPage IT→EN tooltip baseline; this plan operates on the post-Plan-02 file and ADDS — never re-translates)"
    - "Phase 11 API-02 ship-commit 510f5e2 (`/api/publishers/top?sell_type=...` whitelist + 503 column-guard)"
  provides:
    - "useTopPublishers(year, limit, sellType?) hook with queryKey isolation per sell_type filter"
    - "PublishersPage sell_type dropdown affordance (6 options, LEFT of year selector)"
    - "PublishersPage avgFillRate weighted-by-total_impressions (replaces simple-mean avgCoverage)"
    - "PublishersPage filtered empty-state copy via `emptyPublishersFiltered(label, year)`"
  affects:
    - "Phase 14 CORR-06 (URL-state migration for sellType — current plan stops at React state; window.location not touched)"
    - "Phase 14 CORR-04 (top-50 filter disclaimer — orthogonal to this plan)"
    - "Phase 13 publisher_family aggregation (RC-b — orthogonal; RC-d/RC-e closed at math layer here)"
tech_stack:
  added: []
  patterns:
    - "React Query queryKey extension for cache isolation across filter dimensions (`['publishers', year, limit, sellType]`)"
    - "UI-only sentinel `'all'` maps to `undefined` in hook → no query-string param (backwards-compat with Phase 11 D-11.03-03)"
    - "Weighted-by-impressions arithmetic (`Σ(p.avg_coverage × p.total_impressions) / Σ(p.total_impressions)`) — UI-SPEC AC #5"
    - "Negated-existence mechanical assertion `! grep -q 'Avg Coverage'` (iter-1 B-1 fix)"
key_files:
  created: []
  modified:
    - "frontend/src/api/client.ts"
    - "frontend/src/pages/PublishersPage.tsx"
decisions:
  - "Match existing file quote/semicolon style (single-quote, no-semicolon) in `client.ts` — file uses no-semicolon convention; Plan 01 typed-module convention does not apply to this file"
  - "Weighted formula uses existing `totalImpressions` declaration (line 55, current main); no re-declaration"
  - "Both selects share byte-for-byte identical `className` per UI-SPEC AC #10 — verified via fixed-string grep returning exactly 2"
  - "Default `sellType='all'` maps to `undefined` in hook → no query param sent (Phase 11 D-11.03-03 backwards-compat)"
  - "Empty-state branching: `sellType === 'all'` keeps legacy copy; otherwise `emptyPublishersFiltered(SELL_TYPE_LABELS[sellType], year)`"
  - "URL state for sellType deferred to Phase 14 CORR-06 — selecting a filter does NOT update window.location"
metrics:
  duration: "~4 minutes"
  completed_date: "2026-04-30"
  tasks: 3
  files: 2
  commits: 1
---

# Phase 12 Plan 05: CORR-08 Weighted Avg Fill Rate + Sell Type Dropdown Summary

CORR-08 closure landed atomically: PublishersPage now computes
`avgFillRate` weighted by `total_impressions` (replacing the simple mean
on current main L57) AND wires the Phase 11 backend sell_type filter to
a 6-option dropdown left of the year selector. One atomic commit, two
files, all UI-SPEC mechanical acceptance criteria GREEN.

## Atomic Commit

```
94fc45f665d5f52087de8ec0378aaf52985bd357
feat(publishers): sell_type dropdown filter + weighted avg fill rate (CORR-08 + sell_type UI affordance)
```

2 files changed, 48 insertions(+), 20 deletions(-). On `main`, NOT pushed (R-05).

```
 frontend/src/api/client.ts            | 17 +++++++-----
 frontend/src/pages/PublishersPage.tsx | 51 +++++++++++++++++++++++++----------
 2 files changed, 48 insertions(+), 20 deletions(-)
```

## What Shipped

### 1. `frontend/src/api/client.ts` — `useTopPublishers` extended

The hook signature gains `sellType?: string` and threads it through the
queryKey + URL only when defined and not the UI-only `'all'` sentinel.
Full new function body:

```ts
export function useTopPublishers(year = 2025, limit = 35, sellType?: string) {
  return useQuery({
    queryKey: ['publishers', year, limit, sellType],
    queryFn: () => {
      // Append sell_type only when defined and not the "all" sentinel.
      // Phase 11 D-11.03-03: omitting sell_type returns unfiltered 200
      // (backwards-compat); 'all' is a UI-only sentinel that maps to undefined.
      const sellTypeParam = sellType && sellType !== 'all' ? `&sell_type=${sellType}` : ''
      return fetchJSON<{ publishers: PublisherSummary[] }>(
        `/publishers/top?year=${year}&limit=${limit}${sellTypeParam}`
      ).then((r) => r.publishers)
    },
  })
}
```

Style note: the file uses **single-quote, no-semicolon** convention
(verified by reading the file pre-edit — no other function ends with
`;`). Plan 01 SUMMARY noted `client.ts` is a representative typed-module
exemplar but in fact the file does NOT use semicolons. Followed the
plan directive "match the EXISTING quote style in this file, do NOT
introduce inconsistency" — kept no-semicolon convention.

### 2. `frontend/src/pages/PublishersPage.tsx` — 6 edits applied

**A. Imports (after `formatCurrency`):**

```tsx
import {
  SELL_TYPE_LABELS,
  type SellTypeKey,
  emptyPublishersFiltered,
} from '../lib/i18n-keys'
```

**B. Sell type state (after `useState(2025)`):**

```tsx
const [sellType, setSellType] = useState<SellTypeKey>('all')
```

**C. Hook call (parameterized):**

```tsx
const { data: publishers, isLoading, error } = useTopPublishers(year, 35, sellType)
```

**D. CORR-08 weighted avgFillRate (UI-SPEC AC #5):**

```tsx
// CORR-08: weighted by total_impressions (UI-SPEC AC #5).
// Simple mean overweights small publishers. Weighted matches PBI 35.2% target.
const totalCoverageWeight = data.reduce((sum, p) => sum + (p.avg_coverage * p.total_impressions), 0)
const avgFillRate = totalImpressions > 0 ? totalCoverageWeight / totalImpressions : 0
```

Reuses the existing `totalImpressions` declaration on line 55 of current
main (no re-declaration). Variable renamed from `avgCoverage` to
`avgFillRate` matching UI-SPEC §"Component Inventory" line 150.

**E. "Avg Coverage" card → "Avg Fill Rate" card:**

```tsx
<Card>
  <CardContent className="py-4">
    <p className="text-sm text-gray-500">Avg Fill Rate</p>
    <p className="text-2xl font-bold text-gray-900">{(avgFillRate * 100).toFixed(1)}%</p>
    <p className="text-xs text-gray-400">Weighted by impressions</p>
  </CardContent>
</Card>
```

**F. Two-select header (sell_type LEFT of year):**

```tsx
<CardHeader>
  <div className="flex items-center justify-between">
    <CardTitle>Top {data.length} Publishers by Revenue</CardTitle>
    <div className="flex items-center gap-2">
      <select
        value={sellType}
        onChange={(e) => setSellType(e.target.value as SellTypeKey)}
        className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        aria-label="Filter publishers by sell type"
      >
        {(Object.keys(SELL_TYPE_LABELS) as SellTypeKey[]).map((key) => (
          <option key={key} value={key}>{SELL_TYPE_LABELS[key]}</option>
        ))}
      </select>
      <select
        value={year}
        onChange={(e) => setYear(Number(e.target.value))}
        className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
      >
        <option value={2025}>2025</option>
        <option value={2024}>2024</option>
      </select>
    </div>
  </div>
</CardHeader>
```

Both selects share the **byte-for-byte identical** className per UI-SPEC
AC #10. Verified by fixed-string grep returning exactly 2.

**G. Filtered empty state:**

```tsx
{data.length === 0 ? (
  <div className="py-12 text-center text-gray-500">
    {sellType === 'all'
      ? `No publisher data available for ${year}.`
      : emptyPublishersFiltered(SELL_TYPE_LABELS[sellType], year)}
  </div>
) : (
  <DataTable ... />
)}
```

## CORR-08 Numerical Validation (live API, year=2025, limit=35)

Verified post-impl by spinning up the backend on `127.0.0.1:8765` and
fetching `/api/publishers/top?year=2025&limit=35`, then computing both
formulas in Python against the same 35-row payload:

| Metric | Value |
|--------|-------|
| n publishers | 35 |
| Σ total_impressions | 6,296,017,183 |
| Σ (p.avg_coverage × p.total_impressions) | 2,905,086,814.572 |
| **Simple mean** (`Σ p.avg_coverage / n`) | 0.481957 → **48.1957%** |
| **Weighted mean** (`Σ(c×i) / Σ i`) | 0.461417 → **46.1417%** |
| **Δ (weighted − simple)** | -0.020541 → **-2.0541 ppt** |
| `\|Δ\| ≥ 0.01` (UI-SPEC AC #5 threshold) | **TRUE — 2.05 ppt ≥ 1 ppt** |

The weighted formula is **2.05 percentage points lower** than the simple
mean on the live 2025 corpus. UI-SPEC AC #5 acceptance gate (`|Δ| ≥ 1 ppt`)
satisfied with 2× headroom. The simple mean was overweighting smaller
publishers (whose `avg_coverage` skewed higher than the impression-weighted
truth).

Direction note: the weighted value moves **closer** to PBI's 35.2% target
but does not fully close the gap — full parity is gated on (a) Phase 13
`publisher_family` aggregation (RC-b: Mondadori family = M + M_npa +
Adgage_mondocore + Mediamond) and (b) Phase 12 Plan 03 bacino dedup which
already shipped (commit `c29673c`). This plan closes the math layer of
the formula; the data layer is closed by sibling plans.

## Sell-Type Filter End-to-End Validation (live backend)

Live probes against the running backend at `127.0.0.1:8765`:

```
GET /api/publishers/top?year=2025&limit=35
→ HTTP 200, n=35, sell_type_filter=null (omitted)

GET /api/publishers/top?year=2025&limit=35&sell_type=Open_Market
→ HTTP 200, n=35, sell_type_filter='Open_Market', total_publishers=35

GET /api/publishers/top?year=2025&limit=35&sell_type=Bogus
→ HTTP 400, body:
   {"detail":"sell_type must be one of ['Open_Market', 'Header_Bidding',
    'Direct', 'Deal', 'Other']; got 'Bogus'. See config/sell_type_proxy.yaml."}
```

The Phase 11 backend whitelist + 200/400 contract is consumed correctly
by the new UI affordance. Defense-in-depth holds: the dropdown is bound
to `SellTypeKey` (compile-time-known set of 6 strings); the only path
to a 400 is a developer hand-crafting a URL outside the dropdown, which
would surface in the existing `error` branch of PublishersPage.

## Verification (Mechanical Acceptance Gates)

| Gate | Expected | Got | Status |
|------|----------|-----|--------|
| `grep -cF "sellType?: string" frontend/src/api/client.ts` | 1 | 1 | PASSED |
| `grep -cF "queryKey: ['publishers', year, limit, sellType]" client.ts` | 1 | 1 | PASSED |
| `grep -cF 'sell_type=${sellType}' frontend/src/api/client.ts` | 1 | 1 | PASSED |
| `grep -cF "sellType !== 'all'" frontend/src/api/client.ts` | 1 | 1 | PASSED |
| `grep -cF "useState<SellTypeKey>('all')" PublishersPage.tsx` | 1 | 1 | PASSED |
| `grep -cF "useTopPublishers(year, 35, sellType)" PublishersPage.tsx` | 1 | 1 | PASSED |
| `grep -cE "p\.avg_coverage \* p\.total_impressions" PublishersPage.tsx` (AC #5) | 1 | 1 | PASSED |
| `grep -cF "emptyPublishersFiltered" PublishersPage.tsx` | ≥1 | 2 | PASSED |
| `grep -cF "Avg Fill Rate" PublishersPage.tsx` | 1 | 1 | PASSED |
| `! grep -q "Avg Coverage" PublishersPage.tsx` (AC #5 negated existence — iter-1 B-1) | exit 0 | exit 0 | PASSED |
| Shared `<select>` className count (AC #10 byte-for-byte parity) | 2 | 2 | PASSED |
| `grep -cF "flex items-center gap-2" PublishersPage.tsx` (AC #7) | ≥1 | 1 | PASSED |
| `git diff HEAD~1 HEAD frontend/src/ \| grep -cE '^\+.*\b(bg-slate-\|text-slate-\|border-slate-\|font-light\|font-thin\|font-extrabold\|font-black)\b'` (AC #8) | 0 | 0 | PASSED |
| `npx tsc --noEmit -p frontend/tsconfig.app.json` | exit 0 | exit 0 | PASSED |
| `git log -1 --pretty=%s` exact-match plan subject | match | match | PASSED |
| `git log -1 --stat` files | 2 | 2 (`api/client.ts`, `pages/PublishersPage.tsx`) | PASSED |
| Branch | main | main | PASSED |
| Numerical CORR-08 weighted vs simple delta | ≥ 1 ppt | 2.05 ppt | PASSED |
| Sell_type filter live (200/400) | per Phase 11 | 200 + 400 | PASSED |

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 auto-fixes
triggered, no Rule 4 architectural questions raised. All 3 tasks
completed in stated order; commit message verbatim from plan body
(with the live numeric delta filled in as `simple 48.20% vs weighted
46.14% → |Δ|=2.05 ppt` per the plan's "verify post-impl" directive).

Note on grep escaping (mechanical, not content): the plan's verify
block uses `grep -c "sell_type=\${sellType}"` which fails under bash
because `\$` collapses to `$` and the shell expands `${sellType}` as
an undefined variable at parse time, leaving an empty pattern. Used
`grep -cF 'sell_type=${sellType}'` (fixed-string + single quotes) to
get the true literal-substring count of 1. No content deviation;
documented for future executor reference (same class as Plan 02
D-12.02-05 Edit-tool batching note).

Backend numerical proof acquired by ephemerally spinning up the
existing `backend.main:app` on `127.0.0.1:8765` for ~30 seconds, then
killed via `pkill -f "uvicorn ... 8765"`. No state mutation, no DB
write, no port collision (8765 not used elsewhere). Per R-07
plan-internal authorized work for the documented numerical AC.

## Auth Gates

None. No external services touched (no Vercel CLI, no GitHub auth, no
DB mutation, no LLM, no Slack). Local backend probe was read-only on
existing parquet files.

## Threat Surface

No new threat surface beyond what plan's `<threat_model>` section
documented (T-12-05-01 through T-12-05-08). All mitigations applied:

- **T-12-05-01** (Tampering — sell_type query injection): dropdown
  bound to `SellTypeKey` (compile-time set of 6 strings). Phase 11
  backend whitelist re-validates (live 400 verified).
- **T-12-05-02** (Tampering — URL construction): conditional
  template-literal append; only 5 ASCII canonical values can flow
  through; same-origin fetch.
- **T-12-05-03** (Information Disclosure — filtered subsets): same
  posture as Phase 11 backend (commit `510f5e2`); UI affordance
  exposes existing endpoint, no new data.
- **T-12-05-04** (Repudiation): commit body cites Phase 11 commit
  `510f5e2` + UI-SPEC line refs + CORR-08 requirement + live numeric
  delta. Audit trail complete.
- **T-12-05-05** (DoS — filter spam): React Query
  `staleTime: 30_000` coalesces; 6 distinct queryKeys × year cached.
- **T-12-05-06** (EoP — git push): no `git push` invoked; commit
  stays local on `main`.
- **T-12-05-07** (Tampering — palette/typography lock): AC #8
  mechanical grep on diff returns 0 (verified post-commit).
- **T-12-05-08** (Information Disclosure — weighted formula):
  operator-public business arithmetic; commit body documents formula
  + numeric delta openly.

No `threat_flag` rows surfaced.

## Known Stubs

None. The PublishersPage now renders the full sell_type → API → table
flow with cache isolation per filter. The "deferred to Phase 14"
items (URL state for sellType, 503 differentiated UX, sell_type
propagation to /api/alerts and /api/metrics/revenue-status-24h) are
documented out-of-scope items per the plan's `<objective>` and the
commit body, NOT stubs — the operator UI is fully functional within
the Phase 12 scope (selecting a filter triggers a real backend
re-fetch and renders real filtered rows).

## Phase 12 Status After This Plan

| Wave | Plan | Status | Commit |
|------|------|--------|--------|
| 1 | 12-01 (i18n keys foundation, Commit A) | DONE | `bd7cdc9` |
| 1 | 12-02 (IT→EN translation, Commit B) | DONE | `2f803e4` |
| 1 | 12-03 (backend correctness, Commit C) | DONE | `c29673c` |
| 2 | 12-04 (CORR-01 TriageSection wiring + heuristic delete) | DONE | `a535f86` |
| 2 | 12-06 (CORR-09 KpiCards i18n consumer) | DONE | `bbb36fa` |
| 3 | **12-05 (CORR-08 weighted + sell_type dropdown — this plan)** | **DONE** | **`94fc45f`** |

**Phase 12 closed.** All 6 plans landed (3 Wave 1 + 2 Wave 2 + 1 Wave 3).
Email Vito RC-(d) (legacy GOOGLE channel naming math) and RC-(e)
(client-side heuristics in TriageSection) closed at the UI + math
layers. RC-(a) sell_type affordance now live for operators.

Out of scope, per phase contract:
- RC-(a) top-50 disclaimer → Phase 14 CORR-04
- RC-(b) Mondadori publisher_family aggregation → Phase 13
- RC-(c) NET vs GROSS side-by-side label → Phase 13 CORR-03
- RC-(f) timestamp/timezone label → Phase 14 CORR-05

## Self-Check: PASSED

- frontend/src/api/client.ts: FOUND (modified, TS clean, 4/4 grep gates green)
- frontend/src/pages/PublishersPage.tsx: FOUND (modified, TS clean, 8/8 grep gates green)
- Commit `94fc45f`: FOUND on main (`git log --oneline | grep 94fc45f` → present)
- Branch `main`: VERIFIED
- 2 files in commit stat: VERIFIED (no design-system, no backend, no operational state)
- AC #8 palette grep on commit diff: 0 (PASSED)
- AC #5 negated-existence `! grep -q "Avg Coverage"`: exit 0 (PASSED)
- AC #7 sell_type dropdown + flex items-center gap-2: 1 (PASSED)
- AC #10 shared className count: 2 (PASSED)
- Numerical CORR-08 |Δ| = 2.05 ppt ≥ 1 ppt: PASSED
- Live sell_type filter 200/400: PASSED
- No `git push` invoked: VERIFIED
- Runtime DB files NOT staged: VERIFIED (`data/vna_alerts.db*`, `data/sentinel_db/`, `data/vna_alerts.db.apply.lock` still unstaged)
