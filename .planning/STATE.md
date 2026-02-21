# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-19)

**Core value:** Trovare gli alert in tempo quasi reale comunicando solo cio che e davvero importante — rendendo visibili i cali graduali che oggi nessuno nota.
**Current focus:** Phase 6 - Revisione Documentale (in progress)

## Current Position

Phase: 6 of 6 (Revisione Documentale)
Plan: 3 of 4 in current phase
Status: In Progress
Last activity: 2026-02-21 — Plan 06-03 (Slack Notifications Documentation) completed

Progress: [███████████] 67%

## Performance Metrics

**Velocity:**
- Total plans completed: 16
- Average duration: 0.12 hours
- Total execution time: 1.88 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 (Alerting Evoluto) | 4 | 1.25h | 0.31h |
| 02 (Nuovi Tipi Alert) | 4 | 0.22h | 0.05h |
| 03 (Operator Workflow) | 3 | 0.21h | 0.07h |
| 04 (Notifiche Slack) | 3 | 0.03h | 0.01h |
| 06 (Revisione Documentale) | 3 | 0.12h | 0.04h |

**Recent Trend:**
- Last 5 plans: 04-01 (0.07h), 04-02 (0.05h), 06-01 (0.05h), 06-02 (0.03h), 06-03 (0.04h)
- Trend: Stable

*Updated after each plan completion*
| Phase 04 P01 | 0.07 | 3 tasks | 5 files |
| Phase 04 P02 | 0.05 | 3 tasks | 3 files |
| Phase 04 P03 | 0.03 | 3 tasks | 3 files |
| Phase 06 P01 | 0.05 | 3 tasks | 1 files |
| Phase 06 P02 | 0.03 | 3 tasks | 1 files |
| Phase 06 P03 | 0.04 | 3 tasks | 1 files |

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
- [02-03]: Correlation score uses normalized delta heuristic [-2, 0] rather than Pearson over multi-hour window
- [02-03]: min_impressions=500 (lower than A5's 1000) to catch pricing issues in moderate traffic
- [02-03]: A7 always P1 severity since pricing errors cause immediate revenue loss
- [02-03]: Correlation threshold -0.7 balances sensitivity with false positive avoidance
- [02-04]: eCPM display in RevenueStatusSection (not new section) since margin is revenue-related
- [02-04]: Coverage-zero and pricing-rule panels in TriageSection since they extend triage diagnosis
- [02-04]: Helper functions for cause labels/descriptions kept local to TriageSection
- [Phase 03-01]: 6-category feedback taxonomy (REAL + 5 FALSE_POSITIVE variants) covers all common false positive root causes
- [Phase 03-01]: Automatic publisher_id extraction from alert contributors enables historical tracking without frontend complexity
- [Phase 03-01]: Publisher feedback history includes alert context (JOIN with alerts) for pattern analysis
- [Phase 03-01]: 6-category feedback taxonomy (REAL + 5 FALSE_POSITIVE variants) covers all common false positive root causes
- [Phase 03-01]: Automatic publisher_id extraction from alert contributors enables historical tracking without frontend complexity
- [Phase 03-01]: Publisher feedback history includes alert context (JOIN with alerts) for pattern analysis
- [Phase 03-02]: UNIQUE constraint on alert_id enforces one assignment per alert
- [Phase 03-02]: INSERT OR REPLACE pattern handles reassignment automatically
- [Phase 03-02]: Email validation enforces @adkaora.com domain at schema level
- [Phase 03-03]: Junction table pattern for alert-intervention many-to-many links
- [Phase 03-03]: Timestamp-based baseline filtering excludes entire hour if intervention occurred
- [Phase 03-03]: Global intervention filtering across all publishers (conservative approach to prevent baseline contamination)
- [Phase 03]: Radio group for feedback categories provides clear visual hierarchy
- [Phase 03]: Two-button intervention save pattern supports quick logging and alert-specific tracking
- [Phase 03]: Assignment in header, panels at bottom keeps operator workflow separate from alert analysis
- [Phase 04]: Slack configuration stored in alerting_rules.yaml for consistency with other alert rules
- [Phase 04]: Three-endpoint pattern (GET/PUT/TEST) for Slack admin config management
- [Phase 04]: Immediate vs digest severity separation for flexible notification routing
- [Phase 04-02]: pending_notifications table accumulates P1/P2 alerts for daily digest with created_at index
- [Phase 04-02]: Three Block Kit templates provide different detail levels based on severity (P0 full, P1 medium, P2 compact)
- [Phase 04-02]: delivery_status distinguishes slack_sent (immediate) vs slack_queued (digest) for observability
- [Phase 06-01]: Alert rules section documents all 7 rules with accurate thresholds and trigger conditions
- [Phase 06-01]: Comparative alerting section added after metrics for visibility of Phase 1 feature
- [Phase 06-01]: A6 coverage-zero triage documented in triage section for operator visibility
- [Phase 06-02]: Three dedicated sections for operator workflow (feedback, assignment, intervention) improve discoverability vs single workflow section
- [Phase 06-02]: Operator workflow sections placed after FAQ (foundational → advanced knowledge flow)
- [Phase 06-02]: Inline feedback loop explanation in pipeline section shows Phase 3 integration without duplicate documentation
- [Phase 06]: Slack notifications section placed after operator workflow sections for logical flow (workflow → notifications)
- [Phase 06]: Daily digest scheduler documented in both operational and technical sections for different audiences

### Pending Todos

- [01-04]: Human verification of drift visualization in browser (pending)

### Roadmap Evolution

- Phase 6 added: Revisione Documentale — rivedere tutta la documentazione in-app (tecnica e operativa) dopo le modifiche delle fasi 1-5

### Blockers/Concerns

- Athena schema not verified yet (Phase 5 dependency)
- Slack workspace/channel creation needs ops team coordination (Phase 4)

## Session Continuity

Last session: 2026-02-21
Stopped at: Completed 06-03-PLAN.md (Slack Notifications Documentation)
Resume file: .planning/phases/06-revisione-documentale/06-03-SUMMARY.md
