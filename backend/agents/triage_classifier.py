"""
Triage Classifier Agent (Node 5)
Deterministic classification based on delta percentages.
Pure Python - no LLM needed.
"""

from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("agent.triage_classifier")


def triage_classifier_agent(state: AlertState) -> AlertState:
    """
    Classify the alert into one of:
    - MIXED: both bacino and coverage dropping significantly
    - TRAFFIC_DRIVEN: mainly bacino decline
    - COVERAGE_DRIVEN: mainly coverage decline
    - REVENUE_ONLY: revenue drop without matching bacino/coverage (incoherent)
    - MARGIN_DRIVEN: gross margin drops but revenue is stable (v1.2)
    - NO_ALERT: no alert triggered

    For A6 (coverage-zero), assigns probable cause:
    - GOOGLE_POLICY: Likely Google policy violation (sudden zero coverage)
    - MCM_CONFIG: Likely MCM misconfiguration (zero coverage with stable bacino)
    - ADS_TXT: Likely ads.txt issues (partial coverage drop to zero)
    - TECHNICAL_ISSUE: Likely technical problem (infrastructure/integration)
    """
    logger.info("Triage classifier started")

    if not state.get("alert_triggered"):
        logger.info("No alert triggered, skipping triage")
        return {
            **state,
            "triage_label": "NO_ALERT",
        }

    alert_rule = state.get("alert_rule")

    # --- A6 Coverage-Zero Triage ---
    if alert_rule == "A6":
        coverage_zero_metrics = state.get("coverage_zero_metrics", {})
        current_coverage = coverage_zero_metrics.get("current_coverage", 0)
        baseline_coverage = coverage_zero_metrics.get("baseline_coverage", 0)
        current_bacino = coverage_zero_metrics.get("current_bacino", 0)
        baseline_bacino = coverage_zero_metrics.get("baseline_bacino", 0)

        # Heuristic classification based on coverage drop pattern and bacino stability
        bacino_stable = abs((current_bacino - baseline_bacino) / baseline_bacino) < 0.1 if baseline_bacino > 0 else False
        coverage_was_healthy = baseline_coverage > 0.3  # Was coverage previously healthy (>30%)?

        if coverage_was_healthy and bacino_stable and current_coverage < 0.001:
            # Sudden zero coverage with stable bacino -> likely policy violation
            cause = "GOOGLE_POLICY"
        elif bacino_stable and current_coverage < 0.05:
            # Zero coverage with stable bacino but not sudden -> likely MCM config
            cause = "MCM_CONFIG"
        elif not bacino_stable and current_coverage < 0.01:
            # Coverage zero with bacino changes -> could be ads.txt or technical
            # Use baseline coverage as signal: if was high, likely ads.txt; if was low, technical
            if baseline_coverage > 0.2:
                cause = "ADS_TXT"
            else:
                cause = "TECHNICAL_ISSUE"
        else:
            # Fallback for edge cases
            cause = "TECHNICAL_ISSUE"

        logger.info(
            "A6 triage result: %s (current_coverage=%.4f, baseline_coverage=%.4f, bacino_stable=%s)",
            cause, current_coverage, baseline_coverage, bacino_stable
        )

        return {
            **state,
            "triage_label": cause,
            "coverage_zero_cause": cause,
        }

    # --- A8 Gross Margin Triage ---
    if alert_rule == "A8":
        gm_metrics = state.get("gross_margin_metrics", {})
        logger.info(
            "A8 triage result: MARGIN_DRIVEN (gross_margin_pct=%.1f%%)",
            gm_metrics.get("current_gross_margin_pct", 0),
        )
        return {
            **state,
            "triage_label": "MARGIN_DRIVEN",
        }

    # --- Existing A1/A2/A3/A5 Triage ---
    config = get_config()
    delta = state.get("delta", {})

    bac_pct = delta.get("bacino_pct", 0)
    cov_pct = delta.get("coverage_pct", 0)
    rev_pct = delta.get("revenue_pct", 0)

    traffic_thresh = config.triage.traffic_driven_threshold  # -10
    coverage_thresh = config.triage.coverage_driven_threshold  # -10

    bac_dropping = bac_pct <= traffic_thresh
    cov_dropping = cov_pct <= coverage_thresh

    # MARGIN_DRIVEN: gross margin drops but revenue is stable
    # Check if gross_margin_pct dropped significantly while revenue didn't
    current_metrics = state.get("current_metrics", {})
    baseline_metrics = state.get("baseline_metrics", {})
    current_gm = current_metrics.get("gross_margin_pct")
    baseline_gm = baseline_metrics.get("gross_margin_pct")

    margin_dropping = False
    if current_gm is not None and baseline_gm is not None and baseline_gm > 0:
        gm_delta_pct = ((current_gm - baseline_gm) / baseline_gm) * 100
        # Margin dropping significantly (>10%) while revenue is relatively stable (>-5%)
        margin_dropping = gm_delta_pct <= -10 and rev_pct > -5

    if margin_dropping:
        label = "MARGIN_DRIVEN"
    elif bac_dropping and cov_dropping:
        label = "MIXED"
    elif bac_dropping:
        label = "TRAFFIC_DRIVEN"
    elif cov_dropping:
        label = "COVERAGE_DRIVEN"
    else:
        label = "REVENUE_ONLY"

    logger.info(
        "Triage result: %s (bacino_pct=%.1f%%, coverage_pct=%.1f%%)",
        label,
        bac_pct,
        cov_pct,
    )

    return {
        **state,
        "triage_label": label,
    }
