---
phase: 02-nuovi-tipi-alert
plan: 03
subsystem: alerting
tags: [anomaly-detection, ecpm, coverage, correlation, pricing-rules, pydantic]

# Dependency graph
requires:
  - phase: 02-01
    provides: "A5 margin alert pattern and _detect_margin_anomaly function structure"
provides:
  - "A7 pricing-rule alert detection (inverse coverage/CPM correlation)"
  - "PricingRuleAlertConfig Pydantic model"
  - "_detect_pricing_rule_issue() function in anomaly_detector"
affects: [02-04, 03-interventi-feed]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Inverse correlation heuristic (normalized delta scoring)"]

key-files:
  created: []
  modified:
    - "config/alerting_rules.yaml"
    - "backend/db/models.py"
    - "backend/agents/anomaly_detector.py"
    - "backend/utils/config_loader.py"

key-decisions:
  - "Correlation score uses normalized delta heuristic [-2, 0] rather than Pearson over multi-hour window"
  - "min_impressions=500 (lower than A5's 1000) to catch pricing issues in moderate traffic"
  - "A7 always P1 severity since pricing errors cause immediate revenue loss"
  - "Correlation threshold -0.7 balances sensitivity with false positive avoidance"

patterns-established:
  - "Inverse correlation detection: normalize deltas to [-1,0] and [0,1], compute combined score"

requirements-completed: [ALRT-03]

# Metrics
duration: 3min
completed: 2026-02-21
---

# Phase 2 Plan 3: A7 Pricing-Rule Alert Summary

**A7 pricing-rule alert detecting inverse coverage/CPM correlation to identify aggressive floor pricing that blocks valid demand**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-21T14:50:45Z
- **Completed:** 2026-02-21T15:13:04Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- A7 pricing-rule alert configuration with coverage_drop_threshold=-15%, cpm_spike_threshold=20%, correlation_strength=-0.7
- AlertRule enum and SQL CHECK constraint extended with A7
- _detect_pricing_rule_issue() function with inverse correlation scoring between coverage and eCPM
- Full integration into anomaly_detector_agent dispatch chain

## Task Commits

Each task was committed atomically:

1. **Task 1: Add A7 pricing-rule alert configuration and enum value** - `dafd7a2` (feat)
2. **Task 2: Implement A7 pricing-rule detection with correlation analysis** - `df881cd` (feat)

## Files Created/Modified
- `config/alerting_rules.yaml` - Added pricing_rule_alert section, bumped to v1.1.3
- `backend/db/models.py` - Added A7 to AlertRule enum and SQL CHECK constraint
- `backend/agents/anomaly_detector.py` - Added _detect_pricing_rule_issue() and A7 dispatch in _statistical_fallback
- `backend/utils/config_loader.py` - Added PricingRuleAlertConfig model and pricing_rule_alert field to AlertingConfig

## Decisions Made
- Used simplified inverse correlation heuristic (normalized delta scoring) instead of full Pearson correlation over multi-hour window. This is sufficient for detecting the coverage-down/CPM-up pattern without requiring historical data fetching. Can be upgraded later.
- Set min_impressions=500 (lower than A5's 1000) because pricing issues can manifest at moderate traffic levels.
- A7 is always P1 — pricing configuration errors cause immediate, preventable revenue loss.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- A7 detection ready for frontend visualization (Plan 02-04)
- pricing_rule_metrics structure stored in AlertState for frontend consumption
- Future improvement: full Pearson correlation over multi-hour windows for increased accuracy

## Self-Check: PASSED

All 4 modified files verified present. Both task commits (dafd7a2, df881cd) confirmed in git log.

---
*Phase: 02-nuovi-tipi-alert*
*Completed: 2026-02-21*
