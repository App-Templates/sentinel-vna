---
phase: 15-ui-resilience
plan: 04
type: uat-report
status: signed
verification_method: scripted-headless-chromium
captured_by: claude-code-orchestrator
captured_at: 2026-05-04T17:50:00Z
signed_by: stefano
signed_at: 2026-05-04T18:00:00Z
target_alert_id: ALT-20260323-130000-P2
dev_server: http://localhost:5173 (vite v7.3.1)
backend: http://localhost:8000 (uvicorn — backend.main:app, ENVIRONMENT=development)
auth_bypass: pre-seeded localStorage key `sentinel_user` with stub @adkaora.com user (matches AuthGuard.loadUser() contract)
---

# Phase 15 UI Resilience — Plan 15-04 UAT Report

**Method:** Scripted headless Chromium (Playwright 1.59 in `/tmp/sentinel-uat`, isolated from repo). Each scenario navigated to `/alerts/ALT-20260323-130000-P2`, waited for `networkidle` + 1.5s, then captured DOM + console + page errors + screenshot. Source-side prop injection used for UAT #2 / #3 via Edit tool, with revert + `git diff` empty gate before report close.

Evidence persisted under `.planning/phases/15-ui-resilience/uat-evidence/`:
- `uat1-baseline.{json,png}` — empty-state copy capture
- `uat2-null-absorbed.json` — UI-SPEC's stated `null as any` injection (FAILED to trigger fallback — finding documented below)
- `uat2-forced-throw.{json,png}` — escalated injection (`'force-error' as any`) that DID trigger fallback
- `uat3-attempt-a-tolerated.json` — UI-SPEC's stated `[{timestamp:null, revenue:NaN}]` injection (Recharts tolerated, no throw)
- `uat3-malformed-array.{json,png}` — escalated `[null]` injection that DID trigger fallback per ROADMAP SC #3

---

## UAT #1 — Empty-state diagnostic copy (CORR-07)

**Method:** No injection needed. Target alert `ALT-20260323-130000-P2` has `revenue_trend: null` from backend → triggers `RevenueTrendChart` empty-state branch naturally (chart line 37: `(data ?? []).map(...)` → `[]` → line 43 `if (chartData.length === 0)` returns empty-state JSX).

**DOM evidence (uat1-baseline.json):**
```
tag: <p>
class: text-sm text-gray-400
text: "No 7-week history. Alert < 7 days old or data not yet aggregated."
```

**Verbatim verification vs UI-SPEC line 195 (HTML `&lt;` → JS `<`):**
- UI-SPEC: `'No 7-week history. Alert < 7 days old or data not yet aggregated.'`
- Observed:  `No 7-week history. Alert < 7 days old or data not yet aggregated.`
- ✓ Byte-identical (except surrounding quotes — render strips them as expected)

**Style verification vs UI-SPEC line 102 + 113:**
- Required class: `text-sm text-gray-400`
- Observed class: `text-sm text-gray-400` ✓

**Other observations:**
- Body has `min-h-screen`: **false** ✓ (no full-page takeover; empty-state is in-place)
- `Chart unavailable` matches: 0 ✓ (correct — empty-state path, NOT error path)
- Page errors: 0 ✓
- ChartErrorBoundary did NOT fire (no `[ChartErrorBoundary]` console line) — correct: empty data is not an error.
- Adjacent section heading still rendered: `Revenue Trend (7 Weeks)` (the empty-state replaces the chart inside the section, the section's structural heading survives).

**Screenshot:** `uat-evidence/uat1-baseline.png` (full page).

**Verdict: PASS** — empty-state diagnostic copy renders verbatim with required style; Phase 15 SC #2 met for RevenueTrendChart.

---

## UAT #2 — ErrorBoundary fallback chart-sized (CORR-10)

### Sub-attempt A — UI-SPEC's stated `data={null as any}` injection

**Source edit:** `frontend/src/components/alerts/RevenueStatusSection.tsx:142–144` — `data={trendData}` → `data={null as any}`.

**Result (uat2-null-absorbed.json):**
- `Chart unavailable` matches: **0**
- ChartErrorBoundary did NOT fire
- Empty-state copy "No 7-week history..." STILL visible (reused empty-state path)

**Finding:** UI-SPEC UAT #2 plan injection (`null as any`) is **insufficient to trigger the boundary**. `RevenueTrendChart:37` defensively normalizes nullish input via `(data ?? []).map(...)`, so `null` produces `[]`, which goes through the empty-state branch — NOT the error branch. This is a defensive code feature, not a bug. The plan's expectation needs to be escalated to a payload that actually throws. This is exactly the escalation path UI-SPEC line 184 anticipates for UAT #3 ("If recharts tolerates the bad data, escalate the malformed payload to harder forms"). UAT #2 deserves the same caveat.

### Sub-attempt B — escalated `data={'force-error' as any}` injection (non-array → forces .map throw)

**Source edit:** `data={null as any}` → `data={'force-error' as any}`.

**DOM evidence (uat2-forced-throw.json):**
```
tag: <p>
class: text-sm text-gray-500
text: "Chart unavailable. Reload the page if this persists."
```

**Console evidence (verbatim from page.on('console')):**
```
[error] TypeError: (data ?? []).map is not a function
    at RevenueTrendChart (http://localhost:5173/src/components/charts/RevenueTrendChart.tsx:28:34)
    ...
[error] [ChartErrorBoundary] TypeError: (data ?? []).map is not a function
    at RevenueTrendChart (http://localhost:5173/src/components/charts/RevenueTrendChart.tsx:28:34)
    ...
```

**UI-SPEC line 411 pass criteria check:**
- (a) Fallback is chart-sized, NOT full-page (no `min-h-screen` takeover): **YES** — `bodyHasMinHScreen: false`.
- (b) Adjacent sections render normally: **YES** — `Revenue Trend (7 Weeks)` heading still present (the section wrapper survives; only the chart inside the boundary is replaced).
- (c) Browser devtools `console.error` shows `[ChartErrorBoundary]` diagnostic line: **YES** — captured verbatim above.

**Page errors:** 0 (fully contained — no React unhandled rejection, no full-page crash).

**Screenshot:** `uat-evidence/uat2-forced-throw.png`.

**Revert:** `data={'force-error' as any}` → `data={[null] as any}` (next escalation for UAT #3) → ultimately back to `data={trendData}` post-UAT.

**Verdict: PASS** — fallback renders chart-area scoped, console diagnostic fires per D-15.04, adjacent sections functional, no page crash. Boundary contract satisfied. UI-SPEC line 411 (a)(b)(c) all green.

**Finding logged:** UI-SPEC UAT #2 stated injection (`null as any`) does NOT trigger the boundary because of defensive `??` guard in `RevenueTrendChart:37`. Plan-level documentation gap, not a phase ship blocker — phase 15 still satisfies CORR-10 because the boundary works correctly when an actual throw happens. Recommend Phase 15-follow-up note in UI-SPEC: clarify that `null` injection exercises empty-state, NOT fallback.

---

## UAT #3 — Malformed payload → fallback (closes ROADMAP SC #3)

### Sub-attempt A — UI-SPEC's stated `data={[{ timestamp: null, revenue: NaN }] as any}` injection

**Result (uat3-attempt-a-tolerated.json):**
- `Chart unavailable` matches: **0**
- ChartErrorBoundary did NOT fire
- Recharts containers: 1 (chart rendered, gracefully ignoring NaN)
- Page errors: 0

**Finding:** Recharts is tolerant of in-record NaN/null fields. The malformed entries pass through `.map()` (it's an array — `.map` works) and Recharts simply renders gaps. This validates UI-SPEC's anticipated escalation note line 184. Not a phase blocker; ROADMAP SC #3 needs a payload that actually triggers a render-time throw to demonstrate boundary behavior.

### Sub-attempt B — escalated `data={[null] as any}` injection (array shape preserved, but entry access throws)

**Source edit:** `data={[{ timestamp: null, revenue: NaN }] as any}` → `data={[null] as any}`.

**DOM evidence (uat3-malformed-array.json):**
```
tag: <p>
class: text-sm text-gray-500
text: "Chart unavailable. Reload the page if this persists."
```

**Console evidence:**
```
[error] TypeError: Cannot read properties of null (reading 'timestamp')
    at http://localhost:5173/src/components/charts/RevenueTrendChart.tsx:29:29
    at Array.map (<anonymous>)
    at RevenueTrendChart (http://localhost:5173/src/components/charts/RevenueTrendChart.tsx:28:34)
    ...
[error] [ChartErrorBoundary] TypeError: Cannot read properties of null (reading 'timestamp')
    ...
```

This is more realistic than the `'force-error'` injection from UAT #2 because it simulates a credible API failure mode: an upstream service returns an array with a null entry instead of a fully-shaped record. The chart accesses `p.timestamp` on a null `p`, throws TypeError, ErrorBoundary catches it, fallback renders.

**UI-SPEC line 416 pass criteria check:**
- Page does NOT crash to blank: ✓ (page errors: 0, all other sections rendered)
- `<ChartErrorBoundary>` fallback UI replaces ONLY the broken chart: ✓ (fallback in chart-area, adjacent `Revenue Trend (7 Weeks)` heading still visible)
- Rest of page intact: ✓

**Screenshot:** `uat-evidence/uat3-malformed-array.png`.

**Revert:** `data={[null] as any}` → `data={trendData}` (ALL temporary edits removed).

**Verdict: PASS** — malformed payload (`[null]`) triggers fallback as ROADMAP SC #3 requires. Page does not crash; boundary scopes to chart area; adjacent functionality preserved.

**ROADMAP Success Criterion #3** ("Manual regression: inject malformed payload → UI shows fallback instead of crash"): **CLOSED**.

---

## Cleanup verification (Task 3 defensive gate)

| Check | Command | Result |
|-------|---------|--------|
| Zero residual diff in RevenueStatusSection | `git diff frontend/src/components/alerts/RevenueStatusSection.tsx` | ✓ empty |
| Zero residual diff in EnvironmentSplitSection | `git diff frontend/src/components/alerts/EnvironmentSplitSection.tsx` | ✓ empty |
| Zero residual diff in GeoBreakdownSection | `git diff frontend/src/components/alerts/GeoBreakdownSection.tsx` | ✓ empty |
| TS compile clean | `cd frontend && npx tsc --noEmit -p tsconfig.app.json` | ✓ exit 0 |
| Vite build clean | `cd frontend && npm run build` | ✓ exit 0 (2460 modules, 2.13s) |

T-15-04-01 (high — UAT injection edit committed by accident) **fully mitigated** — all 3 alert-section files verified clean before this report was written.

---

## Findings beyond UAT pass/fail

1. **UI-SPEC UAT #2 documentation gap:** stated injection `data={null as any}` does NOT trigger ChartErrorBoundary — empty-state guard absorbs it. Phase 15 still ships correct because the boundary fires on real throws (proven by sub-attempt B with `'force-error'`), but UI-SPEC should note that null is exercised by empty-state, not fallback. Recommend a 1-line clarification in `15-UI-SPEC.md` UAT #2 procedure (separate phase or inline patch).

2. **UI-SPEC UAT #3 stated injection insufficient:** `[{timestamp:null, revenue:NaN}]` is too soft — Recharts tolerates it. UI-SPEC line 184 itself anticipates this and authorizes escalation; this UAT used `[null]` which credibly simulates a real bad-record API failure. ROADMAP SC #3 met.

3. **Verification mode:** This UAT was captured by the Claude Code orchestrator using scripted headless Chromium (Playwright in `/tmp/sentinel-uat`, isolated from repo footprint). Operator (Stefano) is the firmatario and must approve below. Evidence is fully reproducible from the JSON + PNG artifacts persisted under `uat-evidence/`.

---

## Operator Sign-Off

- **UAT #1 (empty-state copy):** PASS
- **UAT #2 (ErrorBoundary fallback chart-sized):** PASS
- **UAT #3 (malformed payload → fallback):** PASS
- **ROADMAP SC #3 (manual regression):** CLOSED
- **Operator:** Stefano
- **Date:** 2026-05-04
- **All temporary injection edits reverted:** YES (verified by `git diff` returning empty on all 3 alert-section files — see Cleanup verification table above)

**Sign-off context:** Stefano reviewed the UAT evidence (3 PNG screenshots, 6 evidence JSON files, browser live render at `localhost:5173`) on 2026-05-04 ~18:00 CEST and approved with the verbal directive "dai procedi". The orchestrator transcribed the approval into this section per Stefano's authorization. Frontmatter (`status: signed`, `signed_by: stefano`, `signed_at: 2026-05-04T18:00:00Z`) is the canonical signal; this body section mirrors it for human-readable archival.
