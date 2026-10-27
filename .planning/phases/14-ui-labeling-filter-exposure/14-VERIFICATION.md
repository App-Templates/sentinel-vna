---
phase: 14-ui-labeling-filter-exposure
verified: 2026-04-30T22:30:00Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Visit /publishers in a browser, set sell_type_proxy=Open_Market&geo_cluster=ITA&publisher_tier=A&gross_net=net in URL. Reload. Verify all 6 filters re-render with correct selected state and revenue values are multiplied by 0.6."
    expected: "URL round-trips correctly. Filter dropdowns show pre-selected values. Revenue cards show net amounts (approx 60% of gross). Toggle reads 'Net'."
    why_human: "React Router useSearchParams URL round-trip requires a running browser with client-side navigation. Grep cannot verify state restoration on load."
  - test: "On PublishersPage with data loaded, toggle Gross/Net. Observe Total Revenue card, Top Publisher revenue line, and table Revenue column simultaneously."
    expected: "All three update in sync when toggling. Net = Gross x 0.6. Label suffix switches between '(gross)' and '(net)'. No inconsistency between cards and table."
    why_human: "Requires visual inspection of simultaneous multi-element update and label sync."
  - test: "Navigate to AlertDetailPage for a GOOGLE_ADEX alert. Toggle the GrossNetToggle on RevenueStatusSection (Step 1). Observe TriageSection (Step 2) Revenue row."
    expected: "Both Step 1 cards and Step 2 Revenue row update together. Step 2 shows net amount and '(net)' label. Delta % row is unchanged. Bacino + Coverage rows are unaffected."
    why_human: "Requires live page with real alert data to verify the B-1 state-lift threads correctly through both child components simultaneously."
  - test: "On the dashboard, verify ScopeBadge renders with the correct channel-palette color (not blank/gray) on KpiCards, RevenueStatus24h, and RevenueByChannel."
    expected: "ScopeBadge renders 'GOOGLE_ADEX only' with the blue badge palette from Badge.tsx channel variant. Visually distinct, not plain text."
    why_human: "Tailwind Badge variant palette inheritance requires a rendered browser to verify color output."
  - test: "On KpiCards, verify ReferencePeriodFootnote appears below the 4-card grid spanning the full width, and ScopeBadge appears right-aligned above the grid."
    expected: "col-span-full layout: badge row above all 4 cards, footnote row below all 4 cards, both spanning the full grid width. Timestamp reads '13 Jan 2026 08:57 UTC' format (or similar current date)."
    why_human: "Column span layout requires a rendered browser at multiple breakpoints (mobile/md/lg) to verify full-width spanning behavior."
---

# Phase 14: UI Labeling + Filter Exposure — Verification Report

**Phase Goal:** Every metric displayed has full disclosure (scope, period, gross/net, currency, timezone); derived filters exposed
**Verified:** 2026-04-30T22:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every metric card shows: reference period (as of [timestamp] UTC), channel scope badge, gross/net label with share % | VERIFIED | ReferencePeriodFootnote on 5/5 surfaces (counts: KpiCards=2, RS24h=2, RBC=2, RSS=2, TriageSection=2). ScopeBadge on 5/5 surfaces. GROSS_NET_LABELS used in RevenueStatusSection (count=2) and TriageSection via REV_SHARE_FACTOR. |
| 2 | PublishersPage filter state in URL (year, month, sell_type_proxy, publisher_tier, geo_cluster, gross_net) — shareable links | VERIFIED | useTopPublishersFilters hook uses useSearchParams (count=2). All 6 param names confirmed in hook (lines 109-115). useState(2025) and useState<SellTypeKey> removed (grep returns 0). |
| 3 | New derived filter UI: sell_type_proxy dropdown, geo_cluster filter, environment drill-down, gross/net toggle, publisher tier A/B/C | VERIFIED | 6 select elements confirmed (grep returns 6). TopNDisclaimer rendered (line 269). GrossNetToggle rendered (count=2). CLIENT-SIDE TIER HEURISTIC comment confirmed (line 25). |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/i18n-keys.ts` | 9 new constants + 1 helper | VERIFIED | All 10 exports confirmed: REFERENCE_PERIOD_COPY, SCOPE_BADGE_COPY, GROSS_NET_LABELS, REV_SHARE_FACTOR, TOP_N_DISCLAIMER_COPY, MONTH_LABELS, GEO_LABELS, PUBLISHER_TIER_LABELS, ENVIRONMENT_LABELS, emptyPublishersMultiFiltered (each count=1) |
| `frontend/src/lib/utils.ts` | formatTimestampUtc helper | VERIFIED | Export confirmed (count=1). timeZone:'UTC' appears twice (date + time portions). hour12:false confirmed. |
| `frontend/src/components/ui/ScopeBadge.tsx` | Channel scope disclosure primitive | VERIFIED | Exists. No inline 'GOOGLE_ADEX only' literal. Imports SCOPE_BADGE_COPY from i18n-keys. |
| `frontend/src/components/ui/ReferencePeriodFootnote.tsx` | Reference period footnote primitive | VERIFIED | Exists. Uses formatTimestampUtc. Imports REFERENCE_PERIOD_COPY. |
| `frontend/src/components/ui/GrossNetToggle.tsx` | Gross/net segmented control | VERIFIED | Exists. Imports GROSS_NET_LABELS. No inline 'Net (post rev-share 60%)' literal. |
| `frontend/src/components/ui/TopNDisclaimer.tsx` | Top-N publishers disclaimer | VERIFIED | Exists. Imports TOP_N_DISCLAIMER_COPY. target="_blank" + rel="noopener noreferrer" present. |
| `frontend/src/components/dashboard/KpiCards.tsx` | ScopeBadge above grid + ReferencePeriodFootnote below grid | VERIFIED | Both imports confirmed (count=1 each). timestamp={data.date} at line 108. |
| `frontend/src/components/dashboard/RevenueStatus24h.tsx` | ScopeBadge in CardHeader + ReferencePeriodFootnote at CardContent end | VERIFIED | Both imports confirmed. timestamp={data.date} at line 230. |
| `frontend/src/components/dashboard/RevenueByChannel.tsx` | ScopeBadge replaces stale paragraph + ReferencePeriodFootnote | VERIFIED | Stale 'GOOGLE_ADEX only' paragraph removed (grep returns 0). 'Multi-channel breakdown pending from IT' removed (grep returns 0). timestamp={data.date} at line 141. |
| `frontend/src/components/alerts/RevenueStatusSection.tsx` | ScopeBadge + GrossNetToggle + ReferencePeriodFootnote; mode prop from AlertDetailPage | VERIFIED | GrossNetToggle count=3 (import + 2 usages). REV_SHARE_FACTOR imported + used in multiplication. ReferencePeriodFootnote variant='card' at line 144. No useState. |
| `frontend/src/components/alerts/TriageSection.tsx` | ScopeBadge + ReferencePeriodFootnote + mode-aware Revenue row; mode prop from AlertDetailPage | VERIFIED | Both primitives imported (count=1 each). REV_SHARE_FACTOR imported + used at lines 68-69. ReferencePeriodFootnote variant='inline' at line 161. BASELINE_MISSING_COPY count=2 (preserved). A6 block preserved (count=2). A7 block preserved (count=1). |
| `frontend/src/pages/AlertDetailPage.tsx` | Page-level useState<GrossNetMode>('gross') threading to both children | VERIFIED | useState<GrossNetMode>('gross') at line 62 confirmed (count=1). |
| `frontend/src/hooks/useTopPublishersFilters.ts` | URL-state hook with 6 typed filters, whitelist, backward-compat | VERIFIED | Exists (177 lines). useSearchParams count=2. GrossNetMode exported (line 33). PublishersFilters interface exported (line 46). MONTH_LABELS used (count=2). sell_type compat (count=21 hits). |
| `frontend/src/pages/PublishersPage.tsx` | 6-filter row + TopNDisclaimer + GrossNetToggle + hook migration | VERIFIED | 6 selects confirmed. TopNDisclaimer at line 269. GrossNetToggle count=2. REV_SHARE_FACTOR imported and used via revenueMultiplier. emptyPublishersMultiFiltered count=2. computePublisherTier comment at line 25. |
| `frontend/src/api/client.ts` | useTopPublishers extended with optional month param | VERIFIED | OPS-02 deferral comment at line 252. queryKey with month at line 245. month count=6. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| i18n-keys.ts REV_SHARE_FACTOR | Plans 14-02/03/04/05 consumers | import { REV_SHARE_FACTOR } | WIRED | RevenueStatusSection line 11, TriageSection line 10, PublishersPage line 19 all import REV_SHARE_FACTOR. Zero inline 0.6 literals found in frontend/src (excluding i18n-keys.ts and Recharts opacity props). |
| utils.ts formatTimestampUtc | ReferencePeriodFootnote.tsx | import from utils | WIRED | ReferencePeriodFootnote imports and calls formatTimestampUtc. |
| ScopeBadge.tsx | SCOPE_BADGE_COPY + Badge.tsx | imports | WIRED | SCOPE_BADGE_COPY imported (5 references). Badge imported from './Badge'. |
| AlertDetailPage.tsx | RevenueStatusSection.tsx + TriageSection.tsx | useState<GrossNetMode> prop threading | WIRED | useState<GrossNetMode>('gross') at AlertDetailPage line 62. mode + onModeChange passed to RSS; mode passed to TriageSection. |
| PublishersPage.tsx | useTopPublishersFilters.ts | import | WIRED | import confirmed (count=1). No old useState(2025) or useState<SellTypeKey> found. |
| PublishersPage.tsx | TopNDisclaimer.tsx | import | WIRED | Import at line 8; render at line 269 with n={data.length}. |
| PublishersPage.tsx | GrossNetToggle.tsx | import | WIRED | Import confirmed; rendered with filters.gross_net + setFilter binding (count=2). |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| KpiCards.tsx | data.date → ReferencePeriodFootnote | useRevenueStatus24h TanStack Query | Yes — server-side API response field | FLOWING |
| RevenueStatus24h.tsx | data.date → ReferencePeriodFootnote | useRevenueStatus24h TanStack Query | Yes — server-side API response field | FLOWING |
| RevenueByChannel.tsx | data.date → ReferencePeriodFootnote | useRevenueStatus24h TanStack Query | Yes — server-side API response field | FLOWING |
| RevenueStatusSection.tsx | alert.timestamp → ReferencePeriodFootnote | alert prop from AlertDetailPage | Yes — alert data from DB query | FLOWING |
| TriageSection.tsx | alert.timestamp → ReferencePeriodFootnote | alert prop from AlertDetailPage | Yes — alert data from DB query | FLOWING |
| RevenueStatusSection.tsx | mode → revenue calculation | AlertDetailPage useState<GrossNetMode>('gross') | Yes — user-driven state, not hardcoded | FLOWING |
| PublishersPage.tsx | filters → revenue display | useTopPublishersFilters URL hook | Yes — URL params drive filter values | FLOWING |
| PublishersPage.tsx | data → publishers list | useTopPublishers TanStack Query | Yes — API call to /api/publishers/top | FLOWING |

Note on intentional no-op stubs: `filters.environment` and `filters.month` on PublishersPage are intentional forward-compat stubs documented in D-14.05-G + D-14.05-F. The filter UI ships now; backend predicates deferred to Phase 18+/OPS-02. These are not data-flow failures — the URL state round-trips correctly and the selects render, but the client-side filter predicate is a no-op. This is explicitly documented inline.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| TypeScript compiles cleanly | `cd frontend && npx tsc --noEmit -p tsconfig.app.json` | Exit 0, no output | PASS |
| Anti-creep AC#9: no inline 0.6 | `grep -rnE '\\* 0\\.6\\b\|0\\.6 \\*' frontend/src/ --include='*.tsx' --include='*.ts' \| grep -v i18n-keys.ts \| grep -v opacity` | No matches (exit 1 = no matches found) | PASS |
| Anti-creep AC#5: 'as of' confined | `grep -rnE "'as of " frontend/src/ --include='*.tsx' --include='*.ts'` | Only i18n-keys.ts:87 (the SSoT) | PASS |
| CR-01 Rules of Hooks fix | useMemo at lines 66+75, isLoading guard at line 85 | Hooks before early returns; no eslint-disable comments | PASS |
| WR-01 zero guard in TriageSection | Lines 60-61: `baselineBacino === 0 \|\| baselineCoverage === 0` | Guard confirmed | PASS |
| WR-02 reload loop protection | `authReloadAttempted` module flag at lines 14, 23-24 | Flag confirmed | PASS |
| 6 selects on PublishersPage | `grep -c '<select' PublishersPage.tsx` | 6 | PASS |
| AC#25 tier comment | `grep -n 'CLIENT-SIDE TIER HEURISTIC' PublishersPage.tsx` | Line 25, exact match | PASS |
| B-1 state lift: AlertDetailPage owns mode | `grep -n "useState<GrossNetMode>('gross')" AlertDetailPage.tsx` | Line 62 | PASS |
| B-1 state lift: RevenueStatusSection no useState | `grep -n "useState" RevenueStatusSection.tsx` | No matches | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CORR-02 | 14-01, 14-03, 14-04 | Alert revenue_current reference period explicit in UI | SATISFIED | ReferencePeriodFootnote on 5 surfaces with real timestamps from data.date / alert.timestamp |
| CORR-03 | 14-01, 14-02, 14-04, 14-05 | Revenue gross + net side-by-side with label "post rev-share 60%" | SATISFIED | GrossNetToggle on RevenueStatusSection + PublishersPage. REV_SHARE_FACTOR multiplication wired. GROSS_NET_LABELS used for label copy. AlertDetailPage page-level state threads to both child surfaces. |
| CORR-04 | 14-01, 14-02, 14-03, 14-05 | Channel scope badge prominent on dashboard + TopNDisclaimer on PublishersPage | SATISFIED | ScopeBadge on all 5 surfaces (KpiCards, RS24h, RBC, RSS, TriageSection). TopNDisclaimer on PublishersPage at line 269. |
| CORR-05 | 14-01, 14-02, 14-03, 14-04 | Reference period + currency + timezone label on every metric card | SATISFIED | ReferencePeriodFootnote card variant shows 'as of [timestamp] UTC, EUR'. Confirmed on all 5 surfaces. |
| CORR-06 | 14-05 | Filter state reflected in URL params (PublishersPage migrates to URL-state hook) | SATISFIED | useTopPublishersFilters uses useSearchParams. 6 filter keys in URL. No old useState for year/sellType. Backward-compat with ?sell_type= legacy params via useEffect migration. |
| CORR-11 | 14-01, 14-05 | Derived filter UI: sell_type_proxy, geo_cluster, environment, publisher tier A/B/C, gross/net toggle | SATISFIED | 6 selects confirmed. computePublisherTier heuristic with mandatory comment. ENVIRONMENT_LABELS + PUBLISHER_TIER_LABELS + GEO_LABELS all in i18n-keys.ts. Environment filter is intentional no-op pending backend extension (documented). |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| frontend/src/pages/PublishersPage.tsx | 127 | `weightedEcpm = totalRevenue / revenueMultiplier / totalImpressions * 1000` — undo-the-multiply pattern (IN-02 from review) | Warning | Fragile coupling: correct now but silently breaks if revenue aggregation changes. Not blocking — intentional per current architecture. |
| frontend/src/hooks/useTopPublishersFilters.ts | 166-170 | `hasActiveFilters` checks URL key presence, not value vs default — shows "clear" button for `?year=2025` (IN-07 from review) | Info | Minor UX confusion: operator may see "clear filters" affordance when no filter actually differs from defaults. Not blocking. |

These were identified in 14-REVIEW.md as INFO/WARNING findings. The 3 blocking issues (CR-01, WR-01, WR-02) were all fixed in 14-REVIEW-FIX.md and verified confirmed in the codebase.

### Human Verification Required

#### 1. URL Round-Trip Smoke Test

**Test:** Navigate to `/publishers?year=2026&month=04&sell_type_proxy=Open_Market&publisher_tier=A&geo_cluster=ITA&environment=WEB&gross_net=net` in browser. Reload the page.
**Expected:** All 6 filter dropdowns show the pre-selected values. Revenue cards show net amounts. GrossNetToggle reads 'Net'. Changing a filter updates the URL without page reload.
**Why human:** useSearchParams URL round-trip requires a running browser with React Router client-side navigation. Cannot be verified with grep.

#### 2. Gross/Net Revenue Sync Across PublishersPage

**Test:** On PublishersPage with data loaded, toggle between Gross and Net using the GrossNetToggle.
**Expected:** Total Revenue summary card, Top Publisher revenue line, and table Revenue column all update simultaneously. Net = Gross × 0.6. Label suffix switches ('(gross)' / '(net)').
**Why human:** Requires visual inspection of simultaneous multi-element state update. Cannot verify with static analysis.

#### 3. B-1 Mode Threading: AlertDetailPage → Both Children

**Test:** Open an AlertDetailPage for a GOOGLE_ADEX alert. Toggle GrossNetToggle on Step 1 (RevenueStatusSection).
**Expected:** Step 1 cards change to net values. Step 2 (TriageSection) Revenue row simultaneously changes to net amounts with '(net)' label. Delta % row stays unchanged. Bacino + Coverage rows unaffected.
**Why human:** Requires live alert data and visual confirmation that page-level state threads through to both child sections simultaneously.

#### 4. ScopeBadge Channel Palette Rendering

**Test:** On the dashboard, inspect ScopeBadge on KpiCards, RevenueStatus24h, and RevenueByChannel.
**Expected:** Badge renders 'GOOGLE_ADEX only' with channel-specific blue palette (bg-blue-50 text-blue-700 border-blue-200 from Badge.tsx line 28), not plain gray text.
**Why human:** Tailwind class-variant palette inheritance requires a rendered browser; static grep cannot verify the visual output of the delegated Badge variant.

#### 5. KpiCards Grid Layout: col-span-full at All Breakpoints

**Test:** View KpiCards on mobile, md, and lg screen widths with browser DevTools.
**Expected:** ScopeBadge row spans all columns above the 4-card grid. ReferencePeriodFootnote spans all columns below. On mobile (1 col), md (2 cols), lg (4 cols) — both rows span the full grid width.
**Why human:** CSS grid col-span-full behavior across responsive breakpoints requires a rendered browser.

### Gaps Summary

No quantitative gaps found. All 5 plans executed cleanly with commits verified:
- 14-01: `3807c85` — i18n-keys + utils foundation (139 insertions, 0 deletions)
- 14-02: `1325b9c` — 4 UI primitives (213 insertions, 0 deletions)
- 14-03: `f61582b` — dashboard wiring (16 insertions, 3 deletions — stale paragraph removed)
- 14-04: `64ff8b1` — alert detail wiring (79 insertions, 16 deletions — B-1 lift)
- 14-05: `1b58eb2` — publishers hook + page migration

Post-review fixes landed as separate commits:
- `b1f1eee` — CR-01: useMemo above early returns (Rules of Hooks)
- `5b78af1` — WR-01: TriageSection baseline zero guard
- `984b660` — WR-02: client.ts 401 reload-loop protection

All mechanical acceptance criteria verified. Phase goal is functionally achieved in the codebase. Remaining items are visual/browser-runtime verification that cannot be automated.

---

_Verified: 2026-04-30T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
