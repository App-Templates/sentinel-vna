---
phase: 06-revisione-documentale
plan: 01
subsystem: documentation
tags: [docs, operational, alert-rules, severity, comparative-alerting]

requires:
  - phase: 01-alerting-evoluto
    provides: "Drift regression, comparative alerting, dual thresholds, P2-WATCH"
  - phase: 02-nuovi-tipi-alert
    provides: "A5 margin/eCPM, A6 coverage-zero, A7 pricing-rule alerts"

provides:
  - "Updated operational documentation for all 7 alert rules (A0-A3, A5-A7)"
  - "P2-WATCH severity level documentation with dual threshold explanation"
  - "Drift regression methodology (linear regression with R², p-value)"
  - "Comparative alerting section (yesterday vs 14d moving average)"
  - "A6 coverage-zero triage categories (GOOGLE_POLICY, MCM_CONFIG, ADS_TXT, TECHNICAL_ISSUE)"

affects: [operators, training-materials, onboarding]

tech-stack:
  added: []
  patterns: ["Documentation-as-code in React component"]

key-files:
  created: []
  modified:
    - frontend/src/pages/DocsPage.tsx

key-decisions:
  - "Alert rules section now documents all 7 rules with accurate thresholds and trigger conditions"
  - "Comparative alerting gets dedicated section after metrics for visibility"
  - "A6 coverage-zero triage documented as distinct from standard TRAFFIC/COVERAGE/MIXED/REVENUE_ONLY"
  - "Dual threshold system explained in severity section to clarify P2-WATCH vs P2 distinction"

patterns-established:
  - "Operational docs updated atomically per feature area (alert rules, severity, comparative)"

requirements-completed: []

duration: 0.05h
completed: 2026-02-21
---

# Phase 06 Plan 01: Operational Documentation Update Summary

**Updated DocsPage.tsx operational sections to reflect all Phase 1-2 features: A5/A6/A7 rules, drift regression, comparative alerting, dual thresholds, P2-WATCH severity**

## Performance

- **Duration:** 0.05h (3 minutes)
- **Started:** 2026-02-21T20:16:00Z
- **Completed:** 2026-02-21T20:19:09Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- Alert rules section updated from 4 to 7 rules with accurate descriptions for A5 (Margin/eCPM Drop), A6 (Coverage Zero), A7 (Pricing Rule Error)
- A6 coverage-zero triage categories documented as dedicated classification (GOOGLE_POLICY, MCM_CONFIG, ADS_TXT, TECHNICAL_ISSUE)
- Severity section extended with P2-WATCH level and dual threshold system explanation
- A2 drift rule updated to describe both linear regression (primary) and 7-day moving average (fallback)
- New comparative alerting section added documenting yesterday comparison and 14-day moving average
- All sections integrated into OP_SECTIONS navigation

## Task Commits

Each task was committed atomically:

1. **Task 1: Update alert-rules section for A5/A6/A7** - `5cf5fe0` (feat)
2. **Task 2: Update severity section for P2-WATCH and dual thresholds** - `eed973b` (feat)
3. **Task 3: Update A2 drift section for regression and comparative alerting** - `06365b2` (feat)

## Files Created/Modified

- `frontend/src/pages/DocsPage.tsx` - Updated operational documentation sections:
  - Alert rules section: changed title from "A0, A1, A2, A3" to "A0, A1, A2, A3, A5, A6, A7"
  - Added 3 new table rows for A5, A6, A7 with accurate thresholds
  - Updated info box from "quattro regole" to "sette regole" with expanded explanation
  - Extended triage section with A6 coverage-zero classification logic
  - Severity section: changed title to include P2-WATCH
  - Added P2-WATCH table row with -15% attention threshold
  - Added dual threshold system paragraph explaining operational vs attention levels
  - A2 table row: updated description from "7 giorni consecutivi" to "regressione lineare (14-30gg) o media mobile 7gg"
  - A2 trigger condition: replaced "media mobile -8%" with full regression thresholds (slope, R², p-value, cumulative drop)
  - Added new comparative alerting section after metrics with 3 subsections
  - Added "comparative" to OP_SECTIONS array

## Decisions Made

- **Alert rules scope:** Documented all 7 rules (A0, A1, A2, A3, A5, A6, A7) to reflect current implementation state
- **A6 triage prominence:** Placed A6 coverage-zero triage explanation in triage section (not buried in alert detail) for operator visibility
- **Comparative alerting placement:** New section after metrics (before pipeline) to highlight Phase 1 comparative feature
- **A2 description balance:** Mentioned both regression (primary) and 7-day MA (fallback) to accurately reflect detection logic
- **Dual threshold explanation:** Added to both severity section (primary) and contextual adjustments (reinforcement)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - documentation updates only.

## Next Phase Readiness

- Operational documentation now accurately reflects all alert types and detection mechanisms implemented in Phases 1-2
- Operators can reference docs for A5/A6/A7 alert thresholds, P2-WATCH severity, drift regression parameters, and comparative alerting behavior
- Ready for Phase 6 Plan 2 (technical documentation update)

## Self-Check: PASSED

✅ DocsPage.tsx file exists and modified
✅ All 3 task commits (5cf5fe0, eed973b, 06365b2) confirmed in git log
✅ A5/A6/A7 badges present (1 occurrence each)
✅ P2-WATCH severity documented
✅ Drift regression methodology documented
✅ Dual threshold system explained
✅ Comparative alerting section created
✅ A6 triage categories documented

---
*Phase: 06-revisione-documentale*
*Completed: 2026-02-21*
