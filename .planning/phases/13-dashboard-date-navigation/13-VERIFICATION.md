---
phase: 13-dashboard-date-navigation
verified: 2026-04-30T17:46:53Z
status: human_needed
score: 15/15 must-haves verified
overrides_applied: 0
re_verification: null
human_verification:
  - test: "Open the dashboard in browser; load Vercel preview or `pnpm --filter frontend dev` localhost. Confirm RevenueStatus24h CardHeader renders the date <select> populated with 7 dates (Wed/Thu/Fri/... format, en-GB locale)."
    expected: "Date dropdown visible in CardHeader; selecting a different date triggers a refetch and the chart re-renders with the new day's hourly data."
    why_human: "Date select rendering + react-query refetch behavior + visible chart update cannot be verified by static grep — needs live browser session against /api/metrics/revenue-status-24h backend."
  - test: "On the same RevenueStatus24h widget, confirm the YoY 7w Area series renders as an amber dashed curve following an hour-by-hour shape (NOT a horizontal flat line). Confirm the legend reads 'YoY 7w {year}' (e.g. 'YoY 7w 2025') and the inline stats row shows 'YoY 7w (2025): €X' + 'vs YoY 7w: ±X%'."
    expected: "Amber dashed curve visible across the 24-hour x-axis with non-flat shape; legend label 'YoY 7w 2025' present; ReferenceLine no longer drawn."
    why_human: "Visual rendering of Recharts <Area> + amber dashed stroke + legend layout cannot be verified without actually painting the SVG. Backend smoke confirmed prev_year.hours is a 24-element nonzero numeric list, so the curve will not be flat — but the visual confirmation is still required."
  - test: "Manually click through the date dropdown across the 7 available dates and observe panel coordination."
    expected: "RevenueStatus24h date selector independently changes only the chart in that panel. KpiCards (rendered at DashboardPage level via lifted props) and RevenueByChannel (independent state) do NOT follow the date change. This is an INTENTIONAL design per UI-SPEC §Component Inventory line 164 (RevenueByChannel decoupled by design) but operators may experience it as misaligned dates across panels."
    why_human: "Operator UX judgment call — does the decoupled-by-design behavior feel acceptable? Code-review WR-01 flagged this as architectural disagreement; needs operator sign-off to confirm the spec-compliant behavior is the desired UX."
gaps: []
deferred:
  - truth: "Three dashboard panels (KpiCards / RevenueStatus24h / RevenueByChannel) share a single lifted selectedDate at DashboardPage level"
    addressed_in: "Future iteration (NOT in current ROADMAP scope)"
    evidence: "WR-01 in 13-REVIEW.md is an architectural concern, NOT a Phase 13 success criterion. UI-SPEC §Component Inventory line 164 explicitly designs RevenueByChannel with own selectedDate state. Phase 13 SC #1 only requires 'RevenueStatus24h date picker populated from available_dates, loads selected day without errors' — singular, panel-level. Lifted-state-up unification is not mandated by ROADMAP.md or UI-SPEC. Could be promoted to backlog if operator UX confirms it should."
---

# Phase 13: Dashboard Date Navigation Verification Report

**Phase Goal:** Operators navigate dashboard by date with YoY 7-week rolling baseline
**Verified:** 2026-04-30T17:46:53Z
**Status:** human_needed (all programmatic checks PASS; visual + UX confirmation required)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (15/15 verified)

| #   | Truth                                                                                                                                                  | Status     | Evidence                                                                                                                                           |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | RevenueStatus24h.tsx renders a date `<select>` in CardHeader populated from `data.available_dates`, conditional on `availableDates.length > 1` (SC #1) | ✓ VERIFIED | `RevenueStatus24h.tsx:71` `availableDates = data.available_dates ?? []`; `:81` `{availableDates.length > 1 && <select ...>}`; populated `:87 .map(d=>...)` |
| 2   | YoY 7w Area series with `dataKey="yoy"` + amber dashed stroke; legend + inline stats both contain `YoY 7w` literal followed by prev_year reference year (SC #2, AC #5/#6) | ✓ VERIFIED | `RevenueStatus24h.tsx:204` `dataKey="yoy"`; `:206` `stroke="var(--chart-amber, #f59e0b)"`; `:208` `strokeDasharray="8 4"`; `:120` inline stats `YoY 7w ({prevYear.date.slice(0,4)}):`; `:205` legend name. ReferenceLine + hourly_avg = 0 matches. |
| 3   | Commit D atomic on main: exactly 8 frontend files, alphabetical, byte-match UI-SPEC §File-Count Gate lines 449-457 (SC #3, AC #1)                       | ✓ VERIFIED | `git show 6c86545 --name-only | grep "^frontend/" | wc -l` = 8; alphabetical order matches UI-SPEC byte-for-byte. Diffstat: 8 files, +390 / -256.  |
| 4   | client.ts `useTopPublishers` byte-identical to Phase 12 ship-state `e001ec8` (D-13.02-B byte-identity)                                                  | ✓ VERIFIED | `diff <(git show e001ec8:client.ts | sed -n '/useTopPublishers/,/^}/p') <(sed -n '/useTopPublishers/,/^}/p' client.ts)` returns 0 diff. Signature `(year=2025, limit=35, sellType?: string)` preserved. |
| 5   | client.ts `PrevYearData` contains `hours?: number[]`; prior `hourly_avg: number` REMOVED                                                              | ✓ VERIFIED | `client.ts:297-303` interface body; `hours?: number[]` present at `:302`; `hourly_avg` absent (grep returns 0).                                   |
| 6   | client.ts `RevenueStatus24hResponse` contains `available_dates?: string[]`                                                                            | ✓ VERIFIED | `client.ts:313` `available_dates?: string[]`.                                                                                                     |
| 7   | client.ts `useRevenueStatus24h` uses path-based URL `/metrics/revenue-status-24h/${date}` (NOT `?date=`) (AC #4)                                       | ✓ VERIFIED | `client.ts:318` template literal path; `?date=` count = 0.                                                                                        |
| 8   | DatePicker.tsx is a NEW file with debounced `<input type="date">` wrapper, min/max from availableDates (AC #10)                                       | ✓ VERIFIED | `frontend/src/components/ui/DatePicker.tsx` 45 lines; `useState/useRef/useEffect` debounce; commit-on-blur and commit-on-Enter; min/max derived from `availableDates` first/last. |
| 9   | RevenueStatus24h + KpiCards + RevenueByChannel + RevenueTrendChart contain ZERO matches for `useTranslation`, `LanguageProvider`, `i18n/context` (AC #7) | ✓ VERIFIED | All 4 files: count 0 each.                                                                                                                       |
| 10  | RevenueStatus24h + RevenueTrendChart contain ZERO matches for IT strings: `Errore nel`, `Nessun dato`, `Ora:`, `Dati trend`, `it-IT` (AC #8)          | ✓ VERIFIED | Both files: count 0 each. RevenueTrendChart `:21` uses `en-GB` locale.                                                                            |
| 11  | RevenueStatus24h + RevenueTrendChart contain ≥ 2 total matches for `var(--chart-` (CSS var pattern, AC #11)                                            | ✓ VERIFIED | RevenueStatus24h: 13 matches; RevenueTrendChart: 8 matches. Total = 21.                                                                            |
| 12  | KpiCards.tsx exports `interface KpiCardsProps`; no-arg `export function KpiCards()` ABSENT (AC #13)                                                    | ✓ VERIFIED | `KpiCards.tsx:11` `export interface KpiCardsProps`; `:16` `export function KpiCards({ data, isLoading }: KpiCardsProps)`. Zero no-arg matches. |
| 13  | RevenueByChannel.tsx + DashboardPage.tsx contain ZERO matches for `selectedChannels` (AC #14)                                                          | ✓ VERIFIED | Both files: count 0 each. ChannelFilter usage also removed from DashboardPage.                                                                    |
| 14  | RevenueStatusSection.tsx contains ≥ 3 matches for `tabular-nums` (AC #15)                                                                              | ✓ VERIFIED | Count = 6.                                                                                                                                        |
| 15  | Phase 12 ship-state preserved: PublishersPage.tsx + TriageSection.tsx + alert.ts + lib/i18n-keys.ts (existing 5 exports) NOT in commit D diff           | ✓ VERIFIED | `git show 6c86545 --name-only` excludes all 4. Plan 13-01 `a3957aa` extended i18n-keys.ts (additive only); 5 Phase 12 exports preserved byte-identical. |

**Score:** 15/15 truths verified

### Required Artifacts (8/8 verified)

| Artifact                                                       | Expected                                                  | Status     | Details                                                                                                  |
| -------------------------------------------------------------- | --------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------- |
| `frontend/src/api/client.ts`                                   | PrevYearData.hours, available_dates, path-based URL       | ✓ VERIFIED | 484 lines; all 3 contract changes present at `:302`, `:313`, `:318`. useTopPublishers byte-identical.    |
| `frontend/src/components/dashboard/RevenueStatus24h.tsx`        | Date select + YoY 7w Area + REVENUE_LABELS consumer        | ✓ VERIFIED | 230 lines; date select `:81`; YoY Area `:202-213`; 15× REVENUE_LABELS references.                        |
| `frontend/src/components/dashboard/KpiCards.tsx`                | Lifted-prop KpiCards with KpiCardsProps + KPI_NO_DATA_COPY | ✓ VERIFIED | 104 lines; `interface KpiCardsProps` `:11`; `KPI_NO_DATA_COPY` consumed `:31`.                          |
| `frontend/src/components/dashboard/RevenueByChannel.tsx`        | Decoupled with own selectedDate; no selectedChannels prop  | ✓ VERIFIED | 144 lines; own `useState` `:19`; `selectedChannels` count = 0; 2× REVENUE_LABELS.                        |
| `frontend/src/components/charts/RevenueTrendChart.tsx`          | CSS-var-styled; en-GB locale                               | ✓ VERIFIED | 95 lines; `AXIS_STYLE/AXIS_LINE/GRID_STROKE/TOOLTIP_STYLE` constants `:25-33`; `en-GB` locale `:21`.     |
| `frontend/src/components/alerts/RevenueStatusSection.tsx`       | Card-wrapped with tabular-nums + uppercase tracking-wide   | ✓ VERIFIED | 112 lines; 6× tabular-nums; `<Card><CardContent>` migration done; `uppercase tracking-wide` labels present. |
| `frontend/src/components/ui/DatePicker.tsx`                     | NEW debounced `<input type="date">` wrapper                | ✓ VERIFIED | 45 lines; commit-on-blur and commit-on-Enter; min/max derived from availableDates.                       |
| `frontend/src/pages/DashboardPage.tsx`                          | Lift useRevenueStatus24h, pass to KpiCards; no ChannelFilter | ✓ VERIFIED | 89 lines; `:18` lifted hook; `:35` `<KpiCards data={revenueData} isLoading={revenueLoading} />`; ChannelFilter usage 0. |

### Key Link Verification

| From                                            | To                                                                | Via                                                                         | Status     | Details                                                                                          |
| ----------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------ |
| RevenueStatus24h.tsx                            | data.available_dates from API response                            | useRevenueStatus24h(selectedDate) react-query                              | ✓ WIRED    | `:20` hook call; `:71` reads `data.available_dates`; conditional `<select>` consumes it `:81-93`. |
| RevenueStatus24h.tsx                            | REVENUE_LABELS from frontend/src/lib/i18n-keys.ts (Plan 13-01)    | `import { REVENUE_LABELS } from '../../lib/i18n-keys'`                      | ✓ WIRED    | Import `:14`; 15 references throughout component.                                                |
| DashboardPage.tsx KpiCards invocation           | KpiCards lifted-prop interface                                    | `<KpiCards data={revenueData} isLoading={revenueLoading} />`                 | ✓ WIRED    | `:35` JSX matches `KpiCardsProps` shape exactly.                                                  |
| client.ts useRevenueStatus24h                   | Backend `GET /metrics/revenue-status-24h/{date}` (Phase 12 P03)   | `fetchJSON(path)` with path-based URL                                       | ✓ WIRED    | `:318` template literal path; orchestrator runtime smoke confirmed 200 OK + 7 dates + 24-pt curve. |

### Data-Flow Trace (Level 4)

| Artifact                                          | Data Variable        | Source                                       | Produces Real Data | Status      |
| ------------------------------------------------- | -------------------- | -------------------------------------------- | ------------------ | ----------- |
| RevenueStatus24h.tsx (date `<select>`)            | data.available_dates | Backend GET /metrics/revenue-status-24h     | Yes                | ✓ FLOWING   |
| RevenueStatus24h.tsx (YoY Area series)            | yoyHours = prevYear.hours | Backend response prev_year.hours        | Yes                | ✓ FLOWING   |
| KpiCards.tsx (RPM/CTR/Viewability/GrossMargin)    | data.hours[].* extended fields | Backend response hours array (lifted from DashboardPage) | Yes (when extended fields present) | ✓ FLOWING (with WR-02 caveat — silent-fail on field renames) |
| RevenueByChannel.tsx (24h chart)                  | data.hours           | Backend GET /metrics/revenue-status-24h/{date} | Yes              | ✓ FLOWING   |

**Orchestrator-performed runtime smoke (Task 5 / human-verify gate):**
- `available_dates` = 7-element list of dates (newest first, e.g. 2026-03-22 ... 2026-03-16) — confirms date `<select>` will populate
- `prev_year.hours` = 24-element list of nonzero numeric values (curve, NOT flat) — confirms YoY 7w Area will render an hour-by-hour curve
- `prev_year.hourly_avg` = ABSENT — confirms Phase 12 cleanup preserved
- backend response shape matches the new frontend consumer expectations

### Behavioral Spot-Checks

| Behavior                                | Command                                                      | Result                       | Status |
| --------------------------------------- | ------------------------------------------------------------ | ---------------------------- | ------ |
| TypeScript compile clean                | `cd frontend && npx tsc --noEmit -p tsconfig.app.json`       | exit 0, zero errors          | ✓ PASS |
| Vite production build clean             | `cd frontend && npx vite build`                              | exit 0, build 2.26s, dist OK | ✓ PASS |
| Phase 12 useTopPublishers byte-identity | `diff <(git show e001ec8:client.ts | sed -n '/useTopPublishers/,/^}/p') <(sed -n '/useTopPublishers/,/^}/p' client.ts)` | 0 diff lines | ✓ PASS |
| Commit D file count                     | `git show 6c86545 --name-only | grep "^frontend/" | wc -l`   | 8                            | ✓ PASS |
| Commit D byte-identity to UI-SPEC list  | sorted file list comparison vs UI-SPEC §File-Count Gate      | exact match                  | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan        | Description                                                                                  | Status     | Evidence                                                                                                  |
| ----------- | ------------------ | -------------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------- |
| WIP-05      | 13-01-PLAN, 13-02-PLAN | Commit D atomico — dashboard date navigation + new API contract (8 file)                  | ✓ SATISFIED | Commit `6c86545` lands all 8 files atomically; backend contract consumed at `client.ts:302/313/318`; date `<select>` rendered. NOTE: REQUIREMENTS.md row 156 still shows status `Pending` and phase mapping `12` (stale post-evolution; ROADMAP.md retargeted WIP-05 to Phase 13). Code is complete; ledger row needs phase-summary update. |

**REQUIREMENTS.md ledger drift (informational, NOT a gap):** Line 44 checkbox `[ ]` and line 156 `WIP-05 | 12 | Pending` reflect pre-evolution mapping. ROADMAP.md (canonical) shows Phase 13 owning WIP-05 as completed 2026-04-30. The flip-to-Complete on REQUIREMENTS.md is a phase-summary documentation task per Phase 12 D-12.01-03 precedent ("Status column UNCHANGED ... flip-to-Complete deferred to phase-summary at end-of-phase").

### Anti-Patterns Found

| File           | Line | Pattern | Severity | Impact |
| -------------- | ---- | ------- | -------- | ------ |
| (none found)   | —    | —       | —        | TODO/FIXME/PLACEHOLDER scan across all 8 modified files + i18n-keys.ts returned 0 matches. Comments referencing UI-SPEC line numbers are documentation, not code smells. |

**13-REVIEW.md findings (advisory, NOT blockers):**
- 0 critical, 6 warning, 6 info
- WR-01 (date-state lift incomplete across 3 panels): flagged as architectural disagreement with UI-SPEC §Component Inventory line 164 which explicitly designs RevenueByChannel as decoupled. Acknowledged as deferred-by-design (see Deferred section in frontmatter).
- WR-02 (KpiCards silent-fail on backend field renames via wide cast + `?? 0`): real silent-fail anti-pattern, but does not block Phase 13 SCs. Worth tracking; could be promoted to a backlog item or addressed in Phase 14/15.
- WR-03/04/05 (DatePicker fragility + zero consumers): the new DatePicker primitive ships unused by the 3 dashboard panels (they use plain `<select>`). The orchestrator and UI-SPEC §"DatePicker primitive" lines 285-287 anticipated this — DatePicker.tsx is a NEW primitive shipped for future use (e.g., Phase 14 alert date filters), explicitly NOT wired into Commit D.
- WR-06 (RevenueByChannel does not handle empty hours array): real edge case but not in mechanical AC; the `if (error || !data)` guard at `:23` does not check `data.hours.length === 0`. Worth tracking.
- IN-01..06: quality polish items.

None of these block goal achievement; the orchestrator already reviewed and accepted them.

### Deferred Items (informational)

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Three dashboard panels (KpiCards / RevenueStatus24h / RevenueByChannel) share a single lifted selectedDate | Future iteration (NOT in current ROADMAP scope) | UI-SPEC §Component Inventory line 164 designs RevenueByChannel as decoupled by design; ROADMAP SC #1 is panel-level ("RevenueStatus24h date picker..."). Lift-up unification not mandated. WR-01 is advisory only. |

### Human Verification Required

#### 1. Date selector in RevenueStatus24h CardHeader (live UI)

**Test:** Open the dashboard in a browser (Vercel preview or `pnpm --filter frontend dev` on localhost). Confirm RevenueStatus24h CardHeader renders the date `<select>` populated with 7 dates in `Wed, 23 Apr 2026` format (en-GB locale).
**Expected:** Date dropdown visible in CardHeader; selecting a different date triggers a refetch and the chart re-renders with the new day's hourly data; URL/route does not change (state is component-local, by design).
**Why human:** Date select rendering + react-query refetch behavior + visible chart update cannot be verified by static grep. Backend smoke confirmed the API returns 7 dates; live confirmation that Recharts re-renders is still required.

#### 2. YoY 7w Area series visual rendering

**Test:** On the same RevenueStatus24h widget, confirm the YoY 7w Area series renders as an amber dashed curve following an hour-by-hour shape (NOT a horizontal flat line). Confirm the legend reads `YoY 7w {year}` (e.g. `YoY 7w 2025`) and the inline stats row shows `YoY 7w (2025): €X` + `vs YoY 7w: ±X%`.
**Expected:** Amber dashed curve visible across the 24-hour x-axis with non-flat shape; legend label `YoY 7w 2025` present; ReferenceLine no longer drawn.
**Why human:** Visual rendering of Recharts `<Area>` + amber dashed stroke + legend layout cannot be verified without actually painting the SVG. Backend smoke already confirmed `prev_year.hours` is a 24-element nonzero numeric list, so the curve will not be flat — but the visual confirmation is still required.

#### 3. Decoupled-by-design panel coordination UX

**Test:** Manually click through the date dropdown across the 7 available dates and observe panel coordination.
**Expected:** RevenueStatus24h date selector independently changes only the chart in that panel. KpiCards (rendered at DashboardPage level via lifted props) and RevenueByChannel (independent state) do NOT follow the date change. This is INTENTIONAL per UI-SPEC §Component Inventory line 164 (RevenueByChannel decoupled by design) but operators may experience it as misaligned dates across panels.
**Why human:** Operator UX judgment call — does the decoupled-by-design behavior feel acceptable? Code-review WR-01 flagged this as architectural disagreement; operator sign-off needed to confirm spec-compliant behavior is the desired UX, or to promote a "lift selectedDate to DashboardPage" follow-up to backlog.

### Gaps Summary

**No gaps blocking Phase 13 goal achievement.** All 15 must-have truths verified, all 8 artifacts present and substantive, all 4 key links wired, all 5 behavioral spot-checks pass, anti-pattern scan clean, UI-SPEC mechanical AC #1-#15 all PASS (verified via grep gates), Phase 12 ship-state preserved byte-identical (PublishersPage, TriageSection, types/alert.ts, i18n-keys.ts existing 5 exports, useTopPublishers function body), Vite + TS clean.

The phase ships goal-complete from a code/contract standpoint. The `human_needed` status reflects the standard Phase 13 UI-SPEC §Acceptance Criteria "Re-verification path" requirement: "Visual validation: operator confirms the date selector appears in the live `RevenueStatus24h` card and changes trigger a data reload; YoY area series appears as amber dashed line in the chart." This visual validation is human-only.

**Advisory follow-ups (not Phase 13 blockers; for backlog consideration):**
- WR-02: KpiCards silent-fail on backend field renames (real silent-fail anti-pattern, not in mechanical AC).
- WR-03/04: DatePicker primitive is fragile (assumes descending sort; accepts non-membership dates) — currently unused so no impact, but should be hardened before any consumer wiring.
- WR-06: RevenueByChannel does not handle empty `data.hours` array — minor edge case.
- REQUIREMENTS.md row 156 status `Pending` + phase mapping `12` (stale; canonical is ROADMAP.md Phase 13). Phase-summary commit can flip the checkbox + update the phase mapping in the same atomic doc commit.

---

_Verified: 2026-04-30T17:46:53Z_
_Verifier: Claude (gsd-verifier)_
