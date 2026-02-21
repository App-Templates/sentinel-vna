---
phase: 02-nuovi-tipi-alert
verified: 2026-02-21T15:35:00Z
status: passed
score: 3/3 must-haves verified
---

# Phase 2: Nuovi Tipi Alert Verification Report

**Phase Goal:** SENTINEL rileva i tre pattern operativi critici che oggi non copre: margine sotto soglia, coverage azzerata, pricing rule errate -- come nuove regole nel sistema A0-A3 esistente
**Verified:** 2026-02-21T15:35:00Z
**Status:** PASSED
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Quando il margine % di un publisher scende sotto la soglia configurata, l'operatore riceve un alert con dettaglio margine attuale vs soglia | VERIFIED | `_detect_margin_anomaly()` at anomaly_detector.py:468-529 computes eCPM delta vs baseline, triggers with P1(-25%)/P2(-15%) thresholds from config. Frontend RevenueStatusSection.tsx:55-91 conditionally renders eCPM Analysis grid with current/baseline/delta. |
| 2 | Quando la coverage di un publisher va a zero, il sistema genera un alert con triage dedicato che indica la causa probabile (policy Google, MCM, ads.txt) | VERIFIED | `_detect_coverage_zero()` at anomaly_detector.py:532-577 detects coverage < 0.001 threshold with min_bacino guard. Triage classifier at triage_classifier.py:41-78 handles A6 and assigns one of GOOGLE_POLICY, MCM_CONFIG, ADS_TXT, TECHNICAL_ISSUE. Frontend TriageSection.tsx:109-139 shows amber cause panel with label and description. |
| 3 | Quando coverage cala e contemporaneamente il CPM schizza, il sistema genera un alert "pricing rule errata" con evidenza della correlazione | VERIFIED | `_detect_pricing_rule_issue()` at anomaly_detector.py:580-666 detects coverage drop <= -15% AND eCPM spike >= +20%, computes correlation_score. Frontend TriageSection.tsx:142-180 shows purple panel with coverage change, CPM change, and inverse correlation score. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `config/alerting_rules.yaml` | A5 margin, A6 coverage-zero, A7 pricing-rule config sections | VERIFIED | Lines 59-86: margin_alert (P1:-25%, P2:-15%, min_impressions:1000), coverage_zero_alert (threshold:0.001, min_bacino:100, severity:P1), pricing_rule_alert (coverage_drop:-15, cpm_spike:20, correlation:-0.7, severity:P1). Version 1.1.3. |
| `backend/db/models.py` | A5, A6, A7 enum values + CHECK constraint | VERIFIED | Lines 22-29: AlertRule enum has A5, A6, A7. Line 128: CHECK constraint includes 'A5', 'A6', 'A7'. |
| `backend/agents/anomaly_detector.py` | _detect_margin_anomaly, _detect_coverage_zero, _detect_pricing_rule_issue functions + dispatch | VERIFIED | 1160 lines. Functions at lines 468, 532, 580. Dispatch in _statistical_fallback at lines 771-837 (A5, A6, A7 trigger blocks with state updates including metrics dicts). |
| `backend/utils/config_loader.py` | MarginAlertConfig, CoverageZeroAlertConfig, PricingRuleAlertConfig models | VERIFIED | Lines 73-101: All three Pydantic models present with correct fields. AlertingConfig includes all three at lines 162-164. |
| `backend/agents/triage_classifier.py` | A6-specific triage with 4 probable causes | VERIFIED | 112 lines. Lines 41-78: A6 branch with heuristic classification into GOOGLE_POLICY, MCM_CONFIG, ADS_TXT, TECHNICAL_ISSUE based on bacino stability and baseline coverage health. |
| `frontend/src/types/alert.ts` | TypeScript types for A5/A6/A7 metrics | VERIFIED | Lines 3, 36-39, 42-74: AlertRule includes A5/A6/A7. MarginMetrics, CoverageZeroMetrics, PricingRuleMetrics interfaces. CoverageZeroCause union type. |
| `frontend/src/components/alerts/RevenueStatusSection.tsx` | Conditional eCPM grid for A5 | VERIFIED | Lines 55-91: Conditional block renders eCPM current/baseline/delta when alert.margin_metrics present. |
| `frontend/src/components/alerts/TriageSection.tsx` | A6 cause panel + A7 correlation panel | VERIFIED | 204 lines. Lines 109-139: A6 amber cause panel. Lines 142-180: A7 purple correlation panel. Lines 186-204: getCoverageZeroCauseLabel and getCoverageZeroCauseDescription helper functions with all 4 cause types. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| anomaly_detector.py | config/alerting_rules.yaml | config.margin_alert, config.coverage_zero_alert, config.pricing_rule_alert | WIRED | Lines 771, 794, 817: each A5/A6/A7 block accesses config fields. Config loads via get_config() at line 738. |
| anomaly_detector.py | AlertState | stores margin_metrics, coverage_zero_metrics, pricing_rule_metrics | WIRED | Lines 780, 803, 825: each trigger block returns state dict with respective metrics key. |
| triage_classifier.py | AlertState | reads alert_rule=A6, assigns coverage_zero_cause | WIRED | Line 41: checks alert_rule == "A6". Line 77: returns state with coverage_zero_cause=cause. |
| AlertDetailPage.tsx | TriageSection.tsx | passes full alert object | WIRED | Line 170: `<TriageSection alert={alert} />`. TriageSection reads alert.alert_rule, alert.coverage_zero_cause, alert.pricing_rule_metrics. |
| AlertDetailPage.tsx | RevenueStatusSection.tsx | passes full alert object | WIRED | Line 157: `<RevenueStatusSection alert={alert} trendData={trendData} />`. RevenueStatusSection reads alert.margin_metrics. |
| frontend/src/types/alert.ts | backend API | TypeScript interfaces match backend AlertState structure | WIRED | MarginMetrics fields (current_ecpm, baseline_ecpm, ecpm_delta_pct, impressions) match margin_metrics dict in anomaly_detector.py:514-521. CoverageZeroMetrics match coverage_zero_metrics dict. PricingRuleMetrics match pricing_rule_metrics dict. |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| ALRT-01 | 02-01, 02-04 | Il sistema genera alert quando il margine % scende sotto soglia configurabile per publisher/gruppo | SATISFIED | A5 detection function + config thresholds + frontend display verified |
| ALRT-02 | 02-02, 02-04 | Il sistema rileva coverage=zero e classifica con triage dedicato (policy Google, MCM, ads.txt) | SATISFIED | A6 detection + 4-cause triage classification + frontend cause panel verified |
| ALRT-03 | 02-03, 02-04 | Il sistema rileva correlazione coverage-down + CPM-up come indicatore di pricing rule errata | SATISFIED | A7 detection with correlation score + frontend correlation evidence panel verified |

No orphaned requirements found. REQUIREMENTS.md maps ALRT-01, ALRT-02, ALRT-03 to Phase 2, and all three are covered by plans 02-01 through 02-04.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | - | - | - | No TODO/FIXME/PLACEHOLDER/stubs detected in any Phase 2 modified files |

### Human Verification Required

### 1. A5 Margin Alert Visual Display

**Test:** Navigate to alert detail page for an A5 alert, check Step 1 (Revenue Status)
**Expected:** eCPM Analysis section shows current eCPM, baseline eCPM, and eCPM Change percentage with correct color coding (red for negative)
**Why human:** Visual rendering and layout correctness cannot be verified programmatically

### 2. A6 Coverage-Zero Cause Panel

**Test:** Navigate to alert detail page for an A6 alert, check Step 2 (Triage)
**Expected:** Amber panel shows "Probable Cause" with one of the 4 cause labels, description text, and current/baseline coverage percentages
**Why human:** Visual layout, color contrast, and readability of diagnostic description need human judgment

### 3. A7 Pricing Rule Correlation Display

**Test:** Navigate to alert detail page for an A7 alert, check Step 2 (Triage)
**Expected:** Purple panel shows "Pricing Rule Issue Detected" with coverage change (red), CPM change (green), and inverse correlation score
**Why human:** Visual correctness of the dual-metric comparison layout

### 4. No A5/A6/A7 Alerts in DB Yet

**Test:** Verify that the 179 existing alerts in DB are all A0-A3, and that no real A5/A6/A7 alerts have been generated yet
**Expected:** New alert types only trigger when the scheduler/pipeline runs with appropriate trigger_type. Existing alerts remain unaffected.
**Why human:** Requires running the pipeline with A5/A6/A7 trigger types or generating test data to see frontend rendering in action

### Gaps Summary

No gaps found. All three observable truths from the ROADMAP.md Success Criteria are fully verified:

1. **A5 Margin Alert (ALRT-01):** Backend detection with eCPM computation, configurable P1/P2 thresholds, min_impressions filter, and frontend eCPM comparison display -- all implemented and wired.

2. **A6 Coverage-Zero Alert (ALRT-02):** Backend detection with coverage threshold (0.001) and min_bacino guard, triage classifier with 4 domain-specific probable causes (GOOGLE_POLICY, MCM_CONFIG, ADS_TXT, TECHNICAL_ISSUE), and frontend amber cause diagnosis panel -- all implemented and wired.

3. **A7 Pricing-Rule Alert (ALRT-03):** Backend detection with inverse correlation analysis (coverage drop + CPM spike), normalized correlation scoring, and frontend purple correlation evidence panel -- all implemented and wired.

All artifacts pass three-level verification (exists, substantive, wired). No anti-patterns or stubs detected. TypeScript compilation passes clean. Python imports verified. Config validates successfully.

---

_Verified: 2026-02-21T15:35:00Z_
_Verifier: Claude (gsd-verifier)_
