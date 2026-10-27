---
phase: 15
plan: 04
subsystem: frontend/uat
tags: [ui-resilience, corr-07, corr-10, uat, manual-regression, wave-3, signed]
dependency_graph:
  requires:
    - .planning/phases/15-ui-resilience/15-01-SUMMARY.md (i18n keys SSoT — empty-state copy source)
    - .planning/phases/15-ui-resilience/15-02-SUMMARY.md (ChartErrorBoundary primitive)
    - .planning/phases/15-ui-resilience/15-03-SUMMARY.md (chart consumers + 3 wraps at call sites)
  provides:
    - "Operator-signed UAT verdicts: 3/3 PASS"
    - "ROADMAP Phase 15 SC #3 (manual regression: malformed payload → fallback) CLOSED"
    - "Reproducible objective evidence under uat-evidence/ (DOM + console + screenshots)"
  affects:
    - .planning/ROADMAP.md (Phase 15 completion eligible)
    - .planning/REQUIREMENTS.md (CORR-07, CORR-10 validated end-to-end via runtime UAT, not just code grep)
---

# 15-04 SUMMARY — Manual Regression UAT (Wave 3 close)

## Outcome

**3/3 UAT PASS** — operator-signed by Stefano, 2026-05-04. Phase 15 (UI Resilience) ready for verifier + close.

| UAT | Verdict | Evidence |
|-----|---------|----------|
| #1 — Empty-state copy verbatim (CORR-07) | PASS | `uat-evidence/uat1-baseline.{json,png}` — natural empty-state on alert with `revenue_trend: null`; `<p class="text-sm text-gray-400">No 7-week history. Alert < 7 days old or data not yet aggregated.</p>` |
| #2 — Fallback chart-area scoped (CORR-10) | PASS | `uat-evidence/uat2-forced-throw.{json,png}` — escalated injection (`'force-error' as any`) → `[ChartErrorBoundary]` console line, fallback `<p class="text-sm text-gray-500">Chart unavailable. Reload the page if this persists.</p>`, no `min-h-screen`, adjacent sections intact |
| #3 — Malformed payload → fallback (ROADMAP SC #3) | PASS | `uat-evidence/uat3-malformed-array.{json,png}` — escalated `[null]` injection → `TypeError: Cannot read properties of null (reading 'timestamp')` caught by boundary |

## Verification commands run

```bash
# Final defensive gate (Task 3 of 15-04-PLAN)
git diff frontend/src/components/alerts/RevenueStatusSection.tsx     # → empty
git diff frontend/src/components/alerts/EnvironmentSplitSection.tsx  # → empty
git diff frontend/src/components/alerts/GeoBreakdownSection.tsx      # → empty
cd frontend && npx tsc --noEmit -p tsconfig.app.json                 # → exit 0
cd frontend && npm run build                                         # → exit 0 (2460 modules, 2.13s)
```

All zero-residual-diff checks PASSED. T-15-04-01 (high — accidental commit of UAT injection) fully mitigated.

## Findings (logged for future hardening, not phase blockers)

1. **UI-SPEC UAT #2 documentation gap:** stated injection `data={null as any}` does NOT trigger `ChartErrorBoundary` because `RevenueTrendChart:37` has defensive `(data ?? []).map(...)` — null is normalized to empty array, exercising the empty-state branch (UAT #1 path), not the error branch. Boundary works correctly when an actual throw happens (proven by escalated `'force-error'` injection). Recommend a 1-line clarification in `15-UI-SPEC.md` UAT #2 procedure: clarify `null` exercises empty-state, suggest non-array payload to exercise fallback.
2. **UI-SPEC UAT #3 stated injection too soft:** `[{timestamp:null, revenue:NaN}]` is tolerated by Recharts (renders chart with NaN gaps). UI-SPEC line 184 itself anticipates this and authorizes escalation. Used `[null]` — credible real-world malformed payload (array with null entry, simulating a bad upstream record), which triggers `p.timestamp` lookup throw → boundary catch → fallback.
3. Both findings are minor — Phase 15 satisfies CORR-07 + CORR-10 + ROADMAP SC #3 with strong runtime evidence.

## Reproducibility

UAT executed by Claude Code orchestrator using scripted Playwright (chromium-headless-shell v1217) running from `/tmp/sentinel-uat` (isolated install — zero footprint on repo dependencies). Pre-seeded `localStorage.sentinel_user` to bypass `AuthGuard` (which is localStorage-only per `frontend/src/components/auth/AuthGuard.tsx`). Backend FastAPI at `localhost:8000`, frontend Vite at `localhost:5173`. Target alert `ALT-20260323-130000-P2` (revenue_trend null, environment_split + geo_breakdown populated → exercises both empty-state and normal-data paths).

Full UAT script at `/tmp/sentinel-uat/uat.mjs` (ephemeral; logic captured in `15-04-UAT-REPORT.md`).

## Decision references

- **D-15.03 Option C** (prop-injection regression in dev): validated by all 3 UAT injections + revert cycle.
- **D-15.04** (no auto-reload): validated by UAT #2 — fallback shows static text "Reload the page if this persists.", no `window.location.reload()` in boundary.
- **D-15.02** (chart-area scoped fallback): validated by `bodyHasMinHScreen: false` in UAT #2 + #3 evidence JSON.

## Closure

Phase 15 (CORR-07 + CORR-10) **complete in code AND validated at runtime**:
- ROADMAP SC #1 (3 charts wrapped in ErrorBoundary) — closed by 15-03 Wave 2 + UAT #2/#3 runtime confirmation
- ROADMAP SC #2 (diagnostic empty states verbatim) — closed by 15-01 + 15-03 + UAT #1 runtime confirmation
- ROADMAP SC #3 (manual regression: malformed payload → fallback) — closed by UAT #3 runtime confirmation

Ready to advance to next phase. Deploy strategy decision (Phase 11-14 still unpushed; live Vercel from 2026-04-27 WIP) remains open per STELLA-POLARE §"Decisioni operatore aperte" #5 — orthogonal to Phase 15 closure.
