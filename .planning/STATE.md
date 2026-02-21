# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Trovare gli alert in tempo quasi reale comunicando solo cio che e davvero importante — rendendo visibili i cali graduali che oggi nessuno nota.
**Current focus:** Phase 2 - Nuovi Tipi Alert (executing)

## Current Position

Phase: 2 of 6 (Nuovi Tipi Alert)
Plan: 2 of 4 in current phase
Status: Executing
Last activity: 2026-02-21 — Plan 02-02 (A6 Coverage-Zero Alert) completed

Progress: [████░░░░░░] 25%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 0.24 hours
- Total execution time: 1.35 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 (Alerting Evoluto) | 4 | 1.25h | 0.31h |
| 02 (Nuovi Tipi Alert) | 2 | 0.10h | 0.05h |

**Recent Trend:**
- Last 5 plans: 01-02 (0.2h), 01-04 (0.25h), 02-01 (0.03h), 02-02 (0.07h)
- Trend: Accelerating

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: BROWNFIELD — all phases extend existing platform, no rebuilds or refactors
- [Roadmap]: Phase 1 addresses #1 pain point (gradual decline) before new alert types
- [Roadmap]: Phases 2-5 are independent after Phase 1 (parallel-capable)
- [Roadmap]: Quick depth (5 phases) — compressed INTV+FEED into single Phase 3
- [Roadmap]: Phase 4 activates existing notifier agent (Block Kit code already present)
- [Roadmap]: Phase 5 activates existing Athena connector (already coded, disabled)
- [01-01]: Regression-first strategy for A2 (run regression before 7-day drift fallback)
- [01-01]: Conservative statistical thresholds (R² ≥ 0.5, p < 0.05) to avoid false positives
- [01-01]: Dynamic window selection (14-30 days) adapts to data availability
- [01-02]: Yesterday comparison with -30% threshold reflects TAM&Yield operational practice
- [01-02]: 14d moving average uses same-weekday pattern for seasonal stability
- [01-02]: Comparative data stored in state for all alerts, enabling frontend visualization
- [01-03]: Weekend scheduling 2x/day (10:00, 18:00 UTC) balances coverage with reduced ops burden
- [01-03]: Dual thresholds: operational (-30%) vs attention (-15%) to distinguish urgent vs monitoring alerts
- [01-03]: P2-WATCH severity for attention-level alerts, distinct from operational P2
- [01-04]: Dynamic step navigation shows 7-9 steps based on alert data availability
- [01-04]: Drift visualization uses Recharts LineChart with reconstructed trend from slope
- [01-04]: Comparative sections conditionally rendered only when data present
- [02-01]: eCPM thresholds more lenient (-25%/-15%) than revenue thresholds due to higher eCPM volatility
- [02-01]: min_impressions=1000 filter to prevent false positives from low-traffic hours
- [02-01]: Dict-based threshold config for flexibility to add severity levels
- [02-01]: Single-hour check initially; consecutive-hours verification deferred
- [02-02]: Coverage threshold 0.001 (0.1%) catches near-zero, not just exactly 0
- [02-02]: A6 always P1 severity — complete coverage loss = immediate revenue stop
- [02-02]: Heuristic triage uses bacino stability + baseline coverage as classification signals
- [02-02]: 4 coverage-zero causes: GOOGLE_POLICY, MCM_CONFIG, ADS_TXT, TECHNICAL_ISSUE

### Pending Todos

- [01-04]: Human verification of drift visualization in browser (pending)

### Roadmap Evolution

- Phase 6 added: Revisione Documentale — rivedere tutta la documentazione in-app (tecnica e operativa) dopo le modifiche delle fasi 1-5

### Blockers/Concerns

- Athena schema not verified yet (Phase 5 dependency)
- Slack workspace/channel creation needs ops team coordination (Phase 4)

## Session Continuity

Last session: 2026-02-21
Stopped at: Completed 02-02-PLAN.md (A6 Coverage-Zero Alert)
Resume file: .planning/phases/02-nuovi-tipi-alert/02-02-SUMMARY.md
