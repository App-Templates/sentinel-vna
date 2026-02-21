# Plan 01-02 Summary: Comparative Alerting (Yesterday & 14d MA)

**Phase:** 01-alerting-evoluto
**Plan:** 02
**Completed:** 2026-02-21
**Status:** ✓ Complete

## What Was Built

Implemented comparative alerting logic to align SENTINEL with operational practices of the TAM&Yield team:

1. **Yesterday Comparison**: Compares current hour revenue vs same hour yesterday
   - Threshold: -30% (operational standard)
   - Severity mapping: P0 (< -30%), P1 (< -20%), P2 (< -10%)
   - Computed in `data_validator.py` for every alert

2. **14-Day Moving Average**: Compares current revenue vs 14-day same-weekday baseline
   - Divergence threshold: -25%
   - Sustained hours requirement: 3 consecutive hours
   - Severity: P1 when triggered
   - Computed in `anomaly_detector.py` for all trigger types

Both comparisons are stored in alert state for frontend visualization and operational decision-making.

## Files Created/Modified

### Created
- `.planning/phases/01-alerting-evoluto/01-02-SUMMARY.md` (this file)

### Modified
1. **config/alerting_rules.yaml**
   - Added `comparative_alerting` section with yesterday_comparison and moving_average_14d configs
   - Thresholds: -30% (yesterday), -25% (14d MA), 3 sustained hours

2. **backend/workflow/state.py**
   - Extended `AlertState` TypedDict with `yesterday_comparison` and `moving_average_14d` fields
   - Added NotRequired import for Python 3.9+ compatibility

3. **backend/agents/data_validator.py**
   - Added `_compute_yesterday_delta()` function (118 lines)
   - Integrated into `data_validator_agent()` to populate `yesterday_comparison` in state
   - Uses hourly parquet data for comparison

4. **backend/agents/anomaly_detector.py**
   - Added `_compute_14d_moving_average()` function (152 lines)
   - Integrated into `_statistical_fallback()` to populate `moving_average_14d` in state
   - Uses same-weekday pattern for seasonal stability
   - Implements consecutive hours verification (3 hours required)

5. **backend/utils/config_loader.py**
   - Added `YesterdayComparisonConfig`, `MovingAverage14dConfig`, and `ComparativeAlertingConfig` models
   - Integrated into `AlertingConfig` for validation

## Key Decisions

1. **Yesterday Comparison in data_validator**: Placed early in pipeline so all alerts have this context, even if they don't trigger on it.

2. **14d MA Uses Same-Weekday Pattern**: Only compares Monday-to-Monday, Tuesday-to-Tuesday, etc. to account for weekly seasonality. This gives more stable baselines than raw 14-day average.

3. **Consecutive Hours Verification**: 14d MA requires 3 consecutive hours below threshold to avoid false positives from single-hour spikes. Implemented by looking back and recomputing baseline for each hour.

4. **Severity Mapping for Yesterday**: Graduated severity (P0/P1/P2) based on magnitude of drop, not just binary trigger. Reflects operational urgency.

5. **Config Location**: Added `comparative_alerting` as separate section (not nested in existing rules) for clean separation from existing A1/A2/A3 logic.

6. **State Storage**: Both comparisons always computed and stored in state (when data available), even if not triggering. This enables frontend to show "today vs yesterday" and "today vs 14d avg" on every alert detail page.

## Deviations from Plan

None. All tasks executed as specified:
- Task 1: Config section added ✓
- Task 2: State fields added ✓
- Task 3: Yesterday comparison implemented ✓
- Task 4: 14d MA implemented ✓
- Config loader updated (necessary step not in plan but required for runtime)

## Verification Results

All verification tests passed:

```bash
✓ Config valid (YAML loads, thresholds correct)
✓ Functions and types importable
✓ Yesterday comparison computed: triggered=False, delta_pct=-4.4%
✓ 14d moving average computed: triggered=False, delta_pct=-6.5%
✓ Comparative alerting integrated
```

Test run with timestamp 2025-12-15T14:00:00Z (in data range) successfully computed both comparisons.

## Next Steps

- **Frontend Integration (Future)**: Add UI components to display yesterday_comparison and moving_average_14d on alert detail pages
- **Phase 1 Continuation**: Proceed to next plan in alerting-evoluto phase (drift regression or dual thresholds)
- **Production Validation**: Once in LIVE mode, monitor if -30% threshold for yesterday comparison aligns with ops team expectations

## Requirements Satisfied

- **DRIFT-02**: ✓ Comparative alerting logic implemented
- **DRIFT-03**: ✓ 14-day moving average baseline computed

## Commits

1. `feat(01-02): Add comparative_alerting config section to alerting_rules.yaml`
2. `feat(01-02): Extend AlertState TypedDict with comparison fields`
3. `feat(01-02): Implement yesterday comparison in data_validator.py`
4. `feat(01-02): Implement 14-day moving average comparison in anomaly_detector.py`
5. `feat(01-02): Add comparative_alerting to config loader models`
