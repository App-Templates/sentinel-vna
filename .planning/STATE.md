# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Trovare gli alert in tempo quasi reale comunicando solo cio che e davvero importante — rendendo visibili i cali graduali che oggi nessuno nota.
**Current focus:** Phase 1 - Alerting Evoluto

## Current Position

Phase: 1 of 5 (Alerting Evoluto)
Plan: 3 of ? in current phase
Status: In progress
Last activity: 2026-02-21 — Plan 01-03 completed (Weekend Scheduling & Dual Thresholds)

Progress: [████░░░░░░] 40%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 0.4 hours
- Total execution time: 0.8 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 (Alerting Evoluto) | 2 | 0.8h | 0.4h |

**Recent Trend:**
- Last 5 plans: 01-01 (0.5h), 01-03 (0.3h)
- Trend: Accelerating (need 3+ plans for statistical trend)

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
- [01-03]: Weekend scheduling 2x/day (10:00, 18:00 UTC) balances coverage with reduced ops burden
- [01-03]: Dual thresholds: operational (-30%) vs attention (-15%) to distinguish urgent vs monitoring alerts
- [01-03]: P2-WATCH severity for attention-level alerts, distinct from operational P2

### Pending Todos

None yet.

### Blockers/Concerns

- Athena schema not verified yet (Phase 5 dependency)
- Slack workspace/channel creation needs ops team coordination (Phase 4)

## Session Continuity

Last session: 2026-02-21
Stopped at: Plan 01-03 completed and committed
Resume file: .planning/phases/01-alerting-evoluto/01-03-SUMMARY.md
