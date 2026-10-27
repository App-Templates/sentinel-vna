# Phase 17.2 UAT Log

**Deploy date (W-03):** 2026-05-20 (`.deploy-date`; rollback tag `pre-17.2-deploy-2026-05-20` → commit `d8527fd`)
**Initial deploy:** 2026-05-20T18:16:32Z (deployment `dpl_ERFHbCJzHVgewtoUXRVfpZWjzvgw`, per-deploy URL `https://sentinel-6qpat2ogw-stefano-hejais-projects.vercel.app`)
**Gap-closure deploy:** 2026-05-20T21:57:42Z (deployment `dpl_5gHyT8DKCSWjKYKrzu2N9PZJZDjh`, per-deploy URL `https://sentinel-1uacgrt02-stefano-hejais-projects.vercel.app`)
**Production canonical alias:** `https://sentinel-vna-stefano-hejais-projects.vercel.app`
**Operator:** Stefano Argiolas
**UAT executed:** 2026-05-20 (Checks 1-4 confirmed on initial deploy; Checks 5+6 initially FAIL on initial deploy → gap-closure shipped → re-UAT PASS on gap-closure deploy)

---

## 6-Check Results (one check per HOTFIX-01..06)

| # | HOTFIX | Check | Result | Evidence |
|---|--------|-------|--------|----------|
| 1 | HOTFIX-01 (V3) | AlertDetailPage Tab 1 Revenue Impact chart tooltip shows TWO distinct rows on hover — "Current Revenue" with one numeric value AND "Baseline" with a different numeric value (not "Baseline" on both rows) | **PASS** | Operator browser hover on Revenue Trend chart data point — tooltip renders two visually distinct labeled rows. Code: `RevenueTrendChart.tsx` formatter discriminates via `item.dataKey === 'revenue'` (3rd formatter arg) instead of `name === 'revenue'` (which compared against `<Line name="...">` display label and was always false). Commit `221dee4`. TypeScript clean (`npx tsc --noEmit` exit 0). |
| 2 | HOTFIX-02 (V4) | AlertDetailPage Tab 1 Revenue Impact chart heading reads "Revenue Trend (Last 7 Days)" (not "Revenue Trend (7 Weeks)") | **PASS** | Operator browser confirms heading literal "Revenue Trend (Last 7 Days)" rendered above the 7-daily-point chart (matches actual data granularity from `useAlertTrend` → `/api/alerts/{id}/trend` returning 7 daily MetricDataPoint values). Path A chosen per Phase 17.2 CONTEXT.md operator decision (label fix vs Path B backend data reshape). Commit `2159ea1`. |
| 3 | HOTFIX-03 (V5) | PublishersPage disclaimer ("Showing top N publishers") rendered as visually prominent amber-left-bordered callout with bolded N count (not `text-xs text-gray-500` footnote) | **PASS** | Operator browser confirms disclaimer rendered as `<div role="note">` with `border-l-4 border-amber-400 bg-amber-50 px-3 py-2 text-sm text-gray-800`; top-N count "35" wrapped in `<span class="font-semibold">`; link text always underlined (`underline hover:text-blue-900`, blue-700 for AA contrast on amber-50). Visual elevation from near-invisible footnote to unmissable callout. Commit `406862f`. |
| 4 | HOTFIX-06 (D1) | PublishersPage "Network totals" link href reactively reflects active filter state via query string (year/month/sell_type/country/tier/environment) — hovering URL changes when filter applied | **PASS** | Operator hovered link with no filter → bare `/api/metrics/network-totals` href. Applied "Open_Market" sell_type filter → hover URL updates to include `?sell_type=Open_Market`. Tested 2-3 filter combos (year+month, sell_type+geo) — each filter narrowing surfaces in the URL via `URLSearchParams` skipping the 'all' sentinel + undefined/empty values. Commit `6c953c6` (`composeNetworkTotalsHref` helper + `TopNDisclaimerFilters` interface + explicit destructure forward from PublishersPage). |
| 5 | HOTFIX-04 (B1) | AlertDetailPage Tabs 3 (Top Contributors), 4 (Geo Breakdown), 5 (Environment Split) all clickable AND render visible content (data card OR explicit "No <X> data available" empty-state card; NOT silent blank below tab strip; NOT error boundary fallback) | **PASS (after gap-closure)** | **Initial deploy `dpl_ERFHbCJzHVgewtoUXRVfpZWjzvgw`:** Tabs 3/4/5 clicks blanked AlertDetailPage via React error boundary catching `TypeError: Cannot read properties of undefined (reading 'toFixed')`. Wave 1 fix (commit `dba6c17` — dropped AlertDetailPage:259 short-circuit `Object.keys(env_split).length > 0` + added early-return empty-state cards to ContributorsSection + GeoBreakdownSection) unblocked the render path BUT exposed previously-hidden contract drift on the now-reachable `EnvironmentSplitSection` + `EnvironmentBarChart` + `ContributorsSection` + `GeoBreakdownSection` + `GeoBreakdownPieChart` consumers (all reading bare-key contract fields like `metrics.revenue` / `row.publisher_name` / `row.geo_cluster` / `row.current_revenue` instead of the producer's `_current`-suffix / `display_name` / `cluster` / `revenue_current` keys). **Gap-closure (7 commits `994ad23..8a3ed45`)** brought the type interface + 5 sibling consumers in line with the payload contract; **redeploy `dpl_5gHyT8DKCSWjKYKrzu2N9PZJZDjh`** unblocked Check 5. Operator re-tested in browser: Tab 3, Tab 4, Tab 5 each clickable; each renders the appropriate empty-state card (matches the 100% empty `contributors=[]` / `geo_breakdown=[]` cohort confirmed in snapshot at 238/238 alerts) or real content for the populated env_split cohort. **Result: PASS per tab (Tab 3, Tab 4, Tab 5 all pass).** |
| 6 | HOTFIX-05 (B2) | AlertDetailPage Tab 2 Triage Classification — Bacino (Impressions) + Coverage rows render REAL numeric values on Current column (not literal "0"); when `environment_split` is empty (legacy `?include_deprecated=true` cohort), Current shows "n/a" + Baseline shows "—" + disclosure copy "Bacino + Coverage non disponibili — environment_split mancante" rendered below table | **PASS (after gap-closure)** | **Initial deploy `dpl_ERFHbCJzHVgewtoUXRVfpZWjzvgw`:** Tab 2 was collateral damage from the same React error boundary firing on Tabs 3/4/5 (boundary wraps the entire alert detail view; sibling errors blank Tab 2 even though Wave 1 fix `f0a7303` had migrated TriageSection itself to read `bacino_current` / `coverage_current` + filter `amp_drift_detected`). **Gap-closure deploy `dpl_5gHyT8DKCSWjKYKrzu2N9PZJZDjh`** released the error boundary by aligning the sibling consumers' contract reads. Operator re-tested in browser: Tab 2 renders real Bacino + Coverage numbers on the populated env_split cohort (Path C primary fix surfaces values — e.g. ALT-20260123-010000-P2 shows 171,503 impressions aggregated from 95,534 WEB + 41,421 AMP + 34,548 APP, avg coverage 0.8161); the defensive 'n/a' + disclosure branch is in place for legacy empty-env_split alerts (which don't appear in the current live snapshot but are correctly handled if encountered). **Result: PASS for both Case A (defensive 'n/a' path code-verified by regression test `f0a7303`) and Case B (populated env_split — operator-verified in browser).** |

---

## Initial Failure + Gap-Closure Recovery (Checks 5 + 6)

**Pre-gap state on initial deploy `dpl_ERFHbCJzHVgewtoUXRVfpZWjzvgw` (2026-05-20T18:16Z):**

- Checks 1-4: PASS on first browser pass — Tabs 1 + PublishersPage chrome unchanged by the Wave 1 render-guard removal.
- Check 5: FAIL — clicking Tab 3, 4, or 5 surfaced `Cannot read properties of undefined (reading 'toFixed')` via the AlertDetailPage error boundary, blanking the whole alert view.
- Check 6: FAIL (collateral) — Tab 2 also blanked because the error boundary wraps the entire alert detail; sibling tab errors collapse Tab 2 even though TriageSection itself was already migrated to the new contract.

**Root cause (identical class to `17.2-05-DIAGNOSIS.md`):** Wave 1's HOTFIX-04 dropped the AlertDetailPage:259 short-circuit and HOTFIX-05 migrated TriageSection — those changes unblocked a render path that had been previously hidden by the guard. Once the path was reachable, 5 sibling consumers (`EnvironmentSplitSection`, `EnvironmentBarChart`, `ContributorsSection`, `GeoBreakdownSection`, `GeoBreakdownPieChart`) crashed because they were reading the old bare-key contract (`metrics.revenue`, `row.publisher_name`, `row.current_revenue`, `row.geo_cluster`, etc.) while the producer emits the new contract (`revenue_current`, `display_name`, `revenue_current`, `cluster + cluster_name`, etc.). The diagnosis document had explicitly flagged this as out-of-scope for Plan 05 (intentional Phase 17.3 candidate to keep HOTFIX-05 blast radius minimal); the gap-closure pulled that scope forward because the error boundary release made the latent drift visible AND blocking.

**Gap-closure commit chain (7 commits, all `fix(17.2-gap)` / `test(17.2-gap)` / `docs(17.2-gap)`):**

| # | SHA | Subject |
|---|-----|---------|
| 1 | `994ad23` | `fix(17.2-gap): TypeScript types match payload contract for env_split/contributors/geo_breakdown` |
| 2 | `4f9f404` | `fix(17.2-gap): EnvironmentSplitSection + BarChart read payload contract fields, filter amp_drift_detected scalar` |
| 3 | `0a3895c` | `fix(17.2-gap): ContributorsSection reads payload contract fields` |
| 4 | `cbb1621` | `fix(17.2-gap): GeoBreakdownSection + PieChart read payload contract fields` |
| 5 | `eaee9f9` | `fix(17.2-gap): ContributorsSection quota_of_drop scale (percentage, not fraction)` |
| 6 | `74291a1` | `test(17.2-gap): regression pin for alert detail sections × payload contract` |
| 7 | `8a3ed45` | `docs(17.2-gap): DEPLOY-LOG amended with gap-closure section (UAT Check 5+6)` |

Additional landmine surfaced by Rule 1 (auto-fix bugs) ONLY because the field rename made the previously-blocked render path reachable: **`quota_of_drop` is emitted as a percentage 0..100, not a 0..1 fraction.** Pre-existing `(quota_of_drop * 100).toFixed(1)` would have rendered as "1057%" / "4487%". Fixed in commit `eaee9f9` in the same atomic chain.

**Build + deploy:** Vite build `index-eGUUSawV.js` (TS exit 0, 2460 modules transformed, 2.15s), snapshot re-export 1004 JSON files (byte-stable vs Wave 1 — no backend code touched), `vercel --prod --yes` → `dpl_5gHyT8DKCSWjKYKrzu2N9PZJZDjh` ● Ready (build 664ms, Ready 19s post-upload, iad1).

**W-05 CDN byte-diff (gap-closure, 3 samples, first attempt — no retry):**

| Sample | Local snapshot | CDN endpoint | diff exit |
|--------|----------------|--------------|-----------|
| 1 | `frontend/dist/api/publishers_top.json` | `/api/publishers/top` | **0** ✅ |
| 2 | `frontend/dist/api/alerts/ALT-20260123-010000-P2.json` (canonical populated sample) | `/api/alerts/ALT-20260123-010000-P2` | **0** ✅ |
| 3 | `frontend/dist/api/alerts/ALT-20260323-130000-P2.json` (objective's empty-env_split alert) | `/api/alerts/ALT-20260323-130000-P2` | **0** ✅ |

**Operator re-UAT after hard-refresh (Cmd-Shift-R) on canonical alias:** Checks 5 + 6 PASS in browser. Wave 1 checks 1-4 remained PASS (same CDN snapshot, unchanged chrome).

---

## Summary

- **Total checks:** 6
- **PASS:** 6
- **PARTIAL:** 0
- **FAIL:** 0
- **Pending:** 0
- **Outcome:** **6/6 PASS** after gap-closure recovery (4/6 on initial deploy → 6/6 on gap-closure deploy `dpl_5gHyT8DKCSWjKYKrzu2N9PZJZDjh`).

## Process Gate (R-04 + R-05)

- **Operator email-Marco gate:** Cleared — 6/6 PASS authorizes external reply citing the live URL + per-HOTFIX status. Email send is OUT OF SCOPE of this UAT log (operator initiates externally).
- **Rollback path tested-mentally (not executed — not needed):**
  - Vercel: `vercel rollback sentinel-6qpat2ogw-stefano-hejais-projects.vercel.app` (= back to initial Wave 1 deploy `dpl_ERFHbCJzHVgewtoUXRVfpZWjzvgw`) OR `vercel rollback sentinel-1obzbccu2-stefano-hejais-projects.vercel.app` (= back to Phase 17.1 gap-closure baseline `dpl_APXL5nUScNqT9khMZwtcqNYQZxEr`).
  - Git: `git reset --hard pre-17.2-deploy-2026-05-20` (= back to commit `d8527fd`).

## Lessons (for Phase 17.3 + Phase 18)

1. **Contract drift across producer → consumer is detectable by source-grep tests on consumer field reads** — Wave 1 diagnose-first pattern (`17.2-04-DIAGNOSIS.md`, `17.2-05-DIAGNOSIS.md`) caught the TriageSection bug, but the parallel sibling drift (5 components) was triaged out-of-scope and only surfaced when the render guard was removed. Phase 18 hardening candidate: a `scripts/test_alert_sections_payload_contract.py`-style invariant grep run across ALL section consumers on every CI build, not just the section under active fix.
2. **Error boundary scope matters** — wrapping the entire AlertDetailPage means any sibling error blanks the whole detail view. Phase 17.3+ candidate: scope error boundaries per Tab so a Tab 5 crash doesn't blank Tab 2.
3. **Gap-closure within the same phase (R-04 chirurgico precedent from 17.1-04 D-17.1-04-F)** kept the rollback tag valid + R-05 operator authorization in scope. Same pattern applied here: 7 atomic commits + redeploy + re-UAT in-phase rather than punting to Phase 17.3.

---

*UAT log recorded 2026-05-20 (initial deploy) + amended 2026-05-20 (gap-closure recovery + re-UAT). Awaiting only the phase-close governance commit (this file's commit chain).*
