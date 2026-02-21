# Plan 01-03 Summary: Weekend Scheduling & Dual Thresholds

**Phase:** 01-alerting-evoluto
**Plan:** 03
**Status:** ✅ Complete
**Completed:** 2026-02-21
**Requirements met:** ALRT-04, ALRT-05

## What Was Built

Implemented weekend alerting coverage (7/7) with reduced frequency and dual threshold system to distinguish operational alerts from attention-level alerts.

### 1. Weekend Scheduling (ALRT-04)
- Weekend alerting runs 2x/day (10:00 and 18:00 UTC) instead of 12x/day weekday schedule
- Covers both EU and LATAM timezones effectively
- Weekday interval-based jobs skip on weekends when weekend mode is enabled
- A2 drift detection continues on regular 6h schedule regardless of day

### 2. Dual Threshold System (ALRT-05)
- **Operational thresholds** (-30% revenue drop): Trigger P0/P1/P2 based on magnitude, require immediate action
- **Attention thresholds** (-15% revenue drop): Trigger P2-WATCH severity, monitoring-only
- Distinguishes "must act now" alerts from "watch and monitor" alerts
- Reduces noise from minor fluctuations while maintaining visibility into trends

## Files Created/Modified

### Modified Files

1. **config/alerting_rules.yaml**
   - Added `weekend_schedule` section to `scheduling` with `enabled`, `times_per_day`, and `run_hours` fields
   - Added `dual_thresholds` section with `operational` and `attention` sub-configs
   - Attention alerts receive `P2-WATCH` severity

2. **backend/scheduler/scheduler.py** (254 lines, +57 lines)
   - Added `CronTrigger` import for cron-based scheduling
   - Added `weekend_alerting_cycle()` async function for weekend A1+A3 runs
   - Modified `run_alerting_cycle()` to skip on weekends when weekend schedule enabled
   - Added weekend job registration in `start_scheduler()` using CronTrigger
   - Updated scheduler startup logging to show weekend schedule info

3. **backend/agents/anomaly_detector.py** (639 lines, +98 lines)
   - Added `_evaluate_dual_thresholds()` helper function
   - Integrated dual threshold logic into A1 severity determination
   - P0: ≤ -30% (operational)
   - P1: ≤ -20% (operational)
   - P2: ≤ -30% but > -20% (operational)
   - P2-WATCH: ≤ -15% but > -30% (attention)
   - Backward compatible when `dual_thresholds.enabled=false`

4. **backend/utils/config_loader.py** (+21 lines)
   - Added `WeekendScheduleConfig` model
   - Added `DualThresholdLevelConfig` and `DualThresholdsConfig` models
   - Updated `SchedulingConfig` to include `weekend_schedule` field
   - Updated `AlertingConfig` to include `dual_thresholds` field

### No Files Created

All changes were extensions to existing files (brownfield approach).

## Key Decisions Made

1. **Weekend timing (10:00 + 18:00 UTC):** Chosen to cover both EU morning (11:00 CET) and LATAM afternoon/evening (depends on zone). No overnight runs to reduce noise.

2. **Weekend = 2x/day:** Balances coverage with reduced ops burden. Weekend traffic patterns differ from weekday, so aggressive alerting would create false positives.

3. **Weekday jobs skip on weekends:** When weekend mode is enabled, interval-based weekday jobs check `datetime.utcnow().weekday()` and return early on Sat/Sun (weekday 5,6). This prevents overlap and double-alerting.

4. **Dual threshold applies to A1 only (for now):** A2 drift and A3 near-zero don't use dual thresholds in this iteration. Could be extended in future.

5. **P2-WATCH severity:** New severity level distinct from P2. Ops team can filter for operational alerts (P0/P1/P2) vs attention alerts (P2-WATCH) in dashboard.

6. **Operational threshold = -30%:** Aligned with real-world "definitely a problem" signal. Attention threshold = -15% catches smaller declines that may become problems.

7. **Backward compatibility:** When `dual_thresholds.enabled=false`, falls back to original single-threshold logic using operational thresholds. Ensures smooth rollout.

## Deviations From Plan

### Minor Deviations
- **Added config_loader.py updates:** Plan didn't explicitly call out config model changes, but they were necessary to support new YAML fields. Added Pydantic models for `WeekendScheduleConfig`, `DualThresholdLevelConfig`, and `DualThresholdsConfig`.

### No Major Deviations
All core requirements met as specified in plan.

## Verification Results

All verification tests passed:

1. ✅ Config validation: YAML contains `weekend_schedule` with `times_per_day=2` and `run_hours=[10,18]`
2. ✅ Config validation: YAML contains `dual_thresholds` with operational (-30%) and attention (-15%) levels
3. ✅ Scheduler test: `weekend_alerting_cycle()` function exists and weekend config loads correctly
4. ✅ Scheduler test: CronTrigger import present and `day_of_week='sat,sun'` usage confirmed
5. ✅ Dual threshold test: `_evaluate_dual_thresholds()` correctly returns P0 for -35% and P2-WATCH for -18%

## Next Steps

1. **Monitor weekend alert volume:** After deployment, check if 2x/day is sufficient or needs adjustment
2. **Tune attention threshold:** -15% is a starting point; may need calibration based on ops feedback
3. **Consider extending dual thresholds to A2:** If gradual declines benefit from attention-level alerts, add dual thresholds to drift detection
4. **Dashboard filtering:** Ensure frontend can filter by P2-WATCH severity to separate attention alerts from operational alerts

## Success Criteria Met

- [x] Config file contains `weekend_schedule` with `times_per_day=2` and `run_hours=[10, 18]`
- [x] Config file contains `dual_thresholds` with operational (-30%) and attention (-15%) thresholds
- [x] `scheduler.py` contains `weekend_alerting_cycle()` function
- [x] `scheduler.py` adds CronTrigger jobs for Saturday/Sunday at configured hours
- [x] `scheduler.py` disables weekday jobs on weekends when weekend schedule is active
- [x] `anomaly_detector.py` contains `_evaluate_dual_thresholds()` function
- [x] `anomaly_detector.py` integrates dual thresholds into A1 severity logic
- [x] Attention alerts receive `P2-WATCH` severity distinct from `P2` operational severity
- [x] Weekend jobs are scheduled at 10:00 and 18:00 UTC as configured

## Commits

1. `feat(01-03): Add weekend_schedule and dual_thresholds config to alerting_rules.yaml`
2. `feat(01-03): Implement weekend scheduling in scheduler.py`
3. `feat(01-03): Implement dual threshold logic in anomaly_detector.py`
4. `feat(01-03): Add config models for weekend_schedule and dual_thresholds`
