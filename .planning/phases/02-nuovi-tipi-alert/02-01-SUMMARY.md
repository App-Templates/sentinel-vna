---
phase: 02-nuovi-tipi-alert
plan: 01
subsystem: alerting
tags: [ecpm, margin, anomaly-detection, pydantic, yaml-config]

requires:
  - phase: 01-alerting-evoluto
    provides: anomaly_detector.py foundation, config_loader.py, AlertState pattern

provides:
  - A5 margin/eCPM alert rule with P1/P2 severity thresholds
  - _detect_margin_anomaly() function in anomaly_detector.py
  - MarginAlertConfig and MarginThresholdConfig Pydantic models
  - A5 enum value in AlertRule and database CHECK constraint

affects: [02-04-frontend-visualization, 04-notifiche-slack]

tech-stack:
  added: []
  patterns: [eCPM computation (revenue/impressions*1000), min_impressions filter for reliable metrics]

key-files:
  created: []
  modified:
    - config/alerting_rules.yaml
    - backend/db/models.py
    - backend/agents/anomaly_detector.py
    - backend/utils/config_loader.py

key-decisions:
  - "eCPM thresholds more lenient than revenue (-25%/-15% vs -10%/-15%) due to higher eCPM volatility"
  - "min_impressions=1000 filter prevents false positives from low-traffic hours"
  - "Dict-based threshold config (ecpm_drop_thresholds[P1/P2]) for flexibility to add severity levels"
  - "Single-hour check initially; consecutive-hours verification deferred to future iteration"

patterns-established:
  - "New alert type pattern: YAML config -> Pydantic model -> detection function -> trigger dispatch"
  - "Margin metrics dict structure: current_ecpm, baseline_ecpm, ecpm_delta_pct, impressions counts"

requirements-completed: [ALRT-01]

duration: 2min
completed: 2026-02-21
---

# Phase 02 Plan 01: A5 Margin Alert Summary

**A5 eCPM margin alert detecting pricing efficiency drops with configurable P1 (-25%) / P2 (-15%) thresholds and min-impressions filter**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-21T14:44:34Z
- **Completed:** 2026-02-21T14:46:52Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- A5 margin alert configuration added to alerting_rules.yaml with eCPM drop thresholds (P1: -25%, P2: -15%)
- AlertRule enum extended with A5 value and database CHECK constraint updated
- `_detect_margin_anomaly()` function implemented with eCPM computation, min_impressions filter, and severity classification
- MarginAlertConfig and MarginThresholdConfig Pydantic models added to config_loader.py
- A5 trigger dispatch integrated into `_statistical_fallback()` in anomaly_detector.py
- 5 functional tests passed: P1 trigger, P2 trigger, no-trigger, low-impressions, zero-baseline

## Task Commits

Each task was committed atomically:

1. **Task 1: Add A5 margin alert configuration** - `06bfbef` (feat)
2. **Task 2: Add A5 enum and database schema** - `eaabe28` (feat)
3. **Task 3: Implement A5 margin detection** - `56ea126` (feat)

## Files Created/Modified
- `config/alerting_rules.yaml` - Added margin_alert section with P1/P2 thresholds, min_impressions, baseline_weeks; bumped version to 1.1.1
- `backend/db/models.py` - Added A5 to AlertRule enum and SQL CHECK constraint
- `backend/agents/anomaly_detector.py` - Added _detect_margin_anomaly() function and A5 trigger dispatch in _statistical_fallback()
- `backend/utils/config_loader.py` - Added MarginThresholdConfig, MarginAlertConfig models and margin_alert field to AlertingConfig

## Decisions Made
- eCPM thresholds set at -25% (P1) and -15% (P2), more lenient than revenue A1 thresholds, because eCPM has higher natural volatility
- min_impressions=1000 ensures eCPM calculations are statistically meaningful (avoids divide-by-small-number noise)
- Used dict-based threshold config (`ecpm_drop_thresholds: {P1: ..., P2: ...}`) instead of fixed attributes, allowing future severity levels
- Single-hour eCPM check for initial implementation; consecutive-hours verification can be added in future iteration if false-positive rate is too high

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- A5 alert rule is fully integrated into the anomaly detection pipeline
- Frontend visualization for A5 margin metrics will be handled in plan 02-04
- Scheduler A5 trigger scheduling will be needed (currently A5 can only be triggered when trigger_type="A5" is passed to the pipeline)

---
*Phase: 02-nuovi-tipi-alert*
*Plan: 01*
*Completed: 2026-02-21*
