---
phase: 02-nuovi-tipi-alert
plan: 02
subsystem: alerting
tags: [coverage-zero, A6, triage, anomaly-detection, pydantic]

requires:
  - phase: 01-alerting-evoluto
    provides: "anomaly_detector with A1/A2/A3 detection, config_loader infrastructure"
provides:
  - "A6 coverage-zero alert rule with P1 severity"
  - "CoverageZeroAlertConfig Pydantic model"
  - "_detect_coverage_zero() function in anomaly_detector"
  - "A6 triage classification with 4 probable causes (GOOGLE_POLICY, MCM_CONFIG, ADS_TXT, TECHNICAL_ISSUE)"
affects: [02-04-frontend-visualization, alert-dashboard, report-builder]

tech-stack:
  added: []
  patterns:
    - "Coverage-zero detection pattern: coverage = impressions/bacino, threshold 0.1%, min_bacino guard"
    - "Heuristic triage classification based on bacino stability and baseline coverage health"

key-files:
  created: []
  modified:
    - config/alerting_rules.yaml
    - backend/db/models.py
    - backend/utils/config_loader.py
    - backend/agents/anomaly_detector.py
    - backend/agents/triage_classifier.py

key-decisions:
  - "Coverage threshold 0.001 (0.1%) catches near-zero scenarios, not just exactly 0"
  - "min_bacino=100 filters out low-traffic periods where zero coverage is expected"
  - "A6 always P1 severity because complete coverage loss = immediate revenue stop"
  - "Heuristic triage uses bacino stability + baseline coverage health as classification signals"

patterns-established:
  - "A6 dispatch pattern: check in _statistical_fallback before A3, after A5"
  - "Coverage-zero triage bypasses standard MIXED/TRAFFIC/COVERAGE labels, uses domain-specific causes"

requirements-completed: [ALRT-02]

duration: 4min
completed: 2026-02-21
---

# Phase 2 Plan 2: A6 Coverage-Zero Alert Summary

**A6 coverage-zero alert detecting complete coverage loss (coverage < 0.1%) with heuristic triage classifying root cause into GOOGLE_POLICY, MCM_CONFIG, ADS_TXT, or TECHNICAL_ISSUE**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-21T14:44:41Z
- **Completed:** 2026-02-21T14:48:21Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- A6 coverage-zero alert configuration with coverage_threshold=0.001, min_bacino=100, consecutive_hours=2, severity=P1
- _detect_coverage_zero() function comparing impressions/bacino ratio against threshold with bacino guard
- A6 triage classifier assigning probable cause from 4 domain-specific categories based on bacino stability and baseline coverage health

## Task Commits

Each task was committed atomically:

1. **Task 1: Add A6 config and enum** - `a1814c9` (feat)
2. **Task 2: Implement A6 detection in anomaly_detector** - `bf72050` (feat)
3. **Task 3: Extend triage classifier for A6** - `f3dec93` (feat)

## Files Created/Modified
- `config/alerting_rules.yaml` - Added coverage_zero_alert section, bumped version to 1.1.2
- `backend/db/models.py` - Added A6 to AlertRule enum and SQL CHECK constraint
- `backend/utils/config_loader.py` - Added CoverageZeroAlertConfig model and field to AlertingConfig
- `backend/agents/anomaly_detector.py` - Added _detect_coverage_zero() function and A6 dispatch in _statistical_fallback
- `backend/agents/triage_classifier.py` - Added A6-specific triage with 4 probable cause labels

## Decisions Made
- Coverage threshold 0.001 (0.1%) catches near-zero scenarios, not just exactly 0
- min_bacino=100 filters out low-traffic periods where zero coverage is expected
- A6 always P1 severity because complete coverage loss = immediate revenue stop
- Heuristic triage uses bacino stability + baseline coverage health as classification signals (GOOGLE_POLICY for sudden zero with stable bacino and healthy baseline, MCM_CONFIG for gradual zero with stable bacino, ADS_TXT for zero with unstable bacino and previously healthy coverage, TECHNICAL_ISSUE as fallback)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Concurrent execution with plan 02-01**
- **Found during:** Task 1, Task 2
- **Issue:** Plan 02-01 (A5 margin alert) was executing concurrently and modified models.py, config_loader.py, and anomaly_detector.py before this plan's edits
- **Fix:** Adapted edits to build on top of 02-01's changes (A5 already in enum, MarginAlertConfig already in config_loader, _detect_margin_anomaly already in anomaly_detector)
- **Files modified:** All 5 target files
- **Verification:** All imports and config loading verified successfully
- **Committed in:** a1814c9, bf72050

---

**Total deviations:** 1 auto-fixed (1 blocking - concurrent execution)
**Impact on plan:** Minor adaptation to account for 02-01 running in parallel. No scope creep.

## Issues Encountered
- config_loader.py changes were committed by 02-01's concurrent commit (56ea126) rather than in the 02-02 task 2 commit. The CoverageZeroAlertConfig class is correctly present in the file and importable.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- A6 alert rule fully integrated into anomaly detection pipeline
- Triage classifier handles A6 with domain-specific causes
- Ready for frontend visualization (plan 02-04) to display coverage-zero metrics and probable cause
- coverage_zero_metrics and coverage_zero_cause stored in AlertState for downstream agents

---
*Phase: 02-nuovi-tipi-alert*
*Completed: 2026-02-21*
