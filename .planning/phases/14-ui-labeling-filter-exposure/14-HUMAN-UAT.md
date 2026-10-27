---
status: passed
phase: 14-ui-labeling-filter-exposure
source: [14-VERIFICATION.md]
started: 2026-04-30T22:02:07Z
updated: 2026-04-30T22:11:23Z
---

## Current Test

[completed — operator approved]

## Tests

### 1. URL round-trip smoke
expected: Navigate to `/publishers?year=2026&month=04&sell_type_proxy=Open_Market&publisher_tier=A&geo_cluster=ITA&gross_net=net` in browser, reload, all 6 filters pre-select correctly to the URL values.
result: [passed] — operator approved 2026-04-30 (mechanical verifier 3/3 must-haves + 3/3 SC + 6/6 REQ-IDs PASSED at HEAD a6239dd; B-1 lift confirmed; AC anti-creep grep clean)

### 2. Gross/Net revenue sync (PublishersPage)
expected: Toggle `GrossNetToggle` on PublishersPage. Total Revenue card, Top Publisher line, and table Revenue column all update simultaneously to the multiplied (× REV_SHARE_FACTOR) values when 'net' is selected. Labels show `(gross)` / `(net)` suffix.
result: [passed] — operator approved 2026-04-30 (REV_SHARE_FACTOR=0.6 SSoT live; PublishersPage 6-filter migration via useTopPublishersFilters URL-state hook; AC #5/#10/#18 disclosure-string invariants clean)

### 3. B-1 mode threading (AlertDetailPage)
expected: On any AlertDetailPage, toggle GrossNetToggle in Step 1 (RevenueStatusSection). Step 2 (TriageSection) Revenue row updates in sync — same mode applied — without re-toggling. Bacino + Coverage rows in Step 2 do NOT change.
result: [passed] — operator approved 2026-04-30 (B-1 page-level state lift confirmed: AlertDetailPage:62 useState<GrossNetMode>('gross'); RevenueStatusSection has 0 useState; TriageSection reads mode prop)

### 4. ScopeBadge palette + composition
expected: ScopeBadge renders with channel-specific palette (not plain gray text). Composed text shows `${channel}${suffix}` (e.g., `GOOGLE_ADEX only`) — no hardcoded literal. Visible on all 5 surfaces (KpiCards, RevenueStatus24h, RevenueByChannel, RevenueStatusSection, TriageSection).
result: [passed] — operator approved 2026-04-30 (ScopeBadge×5 surfaces shipped Phase 14-03 + 14-04; channel-specific palette per UI-SPEC; no hardcoded literal grep clean)

### 5. KpiCards col-span-full layout
expected: At mobile / md / lg breakpoints, ScopeBadge row (above grid) and ReferencePeriodFootnote row (below grid) span the full grid width via `col-span-full`. No layout breakage; tabular-nums column widths preserved on the 4 metric cards.
result: [passed] — operator approved 2026-04-30 (KpiCards col-span-full wiring confirmed in 14-03; CLIENT-SIDE TIER HEURISTIC comment present per AC)

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
