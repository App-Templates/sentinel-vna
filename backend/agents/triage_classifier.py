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
    - NO_ALERT: no alert triggered
    """
    logger.info("Triage classifier started")

    if not state.get("alert_triggered"):
        logger.info("No alert triggered, skipping triage")
        return {
            **state,
            "triage_label": "NO_ALERT",
        }

    config = get_config()
    delta = state.get("delta", {})

    bac_pct = delta.get("bacino_pct", 0)
    cov_pct = delta.get("coverage_pct", 0)

    traffic_thresh = config.triage.traffic_driven_threshold  # -10
    coverage_thresh = config.triage.coverage_driven_threshold  # -10

    bac_dropping = bac_pct <= traffic_thresh
    cov_dropping = cov_pct <= coverage_thresh

    if bac_dropping and cov_dropping:
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
