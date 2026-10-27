---
status: partial
phase: 13-dashboard-date-navigation
source: ["13-VERIFICATION.md"]
started: 2026-04-30T19:45:00Z
updated: 2026-04-30T19:45:00Z
---

## Current Test

[awaiting human visual testing — orchestrator auto-approved phase completion based on
mechanical AC 15/15 + API runtime smoke + TS/Vite build green; visual sign-off remains
optional via `/gsd-verify-work 13`]

## Tests

### 1. Date selector renders + refetches per selection
expected: RevenueStatus24h CardHeader shows a `<select>` populated from `data.available_dates` (en-GB date format). Picking a date triggers `useRevenueStatus24h(selectedDate)` refetch via path-based URL `/api/metrics/revenue-status-24h/{date}` and re-renders the card.
result: [pending — browser verification required]

### 2. YoY 7w amber dashed Area renders as hour-by-hour curve (not flat)
expected: Recharts ComposedChart shows three series: solid blue (revenue), dashed gray (Baseline 7w), and **dashed amber (YoY 7w)**. The amber series MUST curve hour-by-hour (24-point shape), not be a flat horizontal line. Legend reads `YoY 7w {prev_year}`. Inline stats row contains `YoY 7w (<prev_year>): <amount>`.
result: [pending — browser verification required]
indirect_evidence: API smoke confirmed `prev_year.hours` returns 24 distinct nonzero numeric values, so the data backing the curve exists and is well-shaped.

### 3. Decoupled-by-design panel coordination UX confirmation
expected: Per UI-SPEC §Component Inventory line 164, RevenueStatus24h's date `<select>` is intentionally LOCAL — it does NOT lift state to DashboardPage. KpiCards consume `useRevenueStatus24h()` via DashboardPage lift; RevenueByChannel manages its own `selectedDate` independently. Operator confirms this decoupled UX is the desired behavior (vs promoting a "lift selectedDate to DashboardPage" item to backlog for a future phase).
result: [pending — operator design sign-off required]
notes: Code-review WR-01 flagged this as "incomplete lift", but it is BY DESIGN per the UI-SPEC. This UAT item exists to confirm the operator agrees with the spec's intent.

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
