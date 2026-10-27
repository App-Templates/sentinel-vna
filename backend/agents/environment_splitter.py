"""
Environment Splitter Agent (Node 6c - parallel)
Splits metrics by environment (WEB, AMP, APP) and detects AMP drift.
Pure Python - no LLM needed.
"""

from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("agent.environment_splitter")


def environment_splitter_agent(state: AlertState) -> AlertState:
    """
    Split metrics by environment, detect AMP-specific drift.
    Output: dict with per-environment metrics and AMP drift flag.
    """
    logger.info("Environment splitter started")
    errors = list(state.get("execution_errors", []))

    delta = state.get("delta", {})
    env_deltas = delta.get("environment", {})
    current = state.get("current_metrics", {})
    baseline = state.get("baseline_metrics", {})

    env_current = current.get("environment", {})
    env_baseline = baseline.get("environment", {})

    environment_split = {}
    amp_drift_detected = False

    for env_name in ("WEB", "AMP", "APP"):
        ec = env_current.get(env_name, {})
        eb = env_baseline.get(env_name, {})
        ed = env_deltas.get(env_name, {})

        rev_current = ec.get("revenue", 0)
        rev_baseline = eb.get("revenue", 0)
        delta_abs = ed.get("revenue_delta_abs", rev_current - rev_baseline)
        delta_pct = ed.get("revenue_delta_pct", 0)

        environment_split[env_name] = {
            "revenue_current": round(rev_current, 2),
            "revenue_baseline": round(rev_baseline, 2),
            "delta_abs": round(delta_abs, 2),
            "delta_pct": round(delta_pct, 2),
            "bacino_current": ec.get("bacino", 0),
            "bacino_baseline": eb.get("bacino", 0),
            "coverage_current": round(ec.get("coverage", 0), 4),
            "coverage_baseline": round(eb.get("coverage", 0), 4),
        }

        # AMP drift detection: if AMP is down more than 8% while others are more stable
        if env_name == "AMP" and delta_pct <= -8:
            web_delta = env_deltas.get("WEB", {}).get("revenue_delta_pct", 0)
            app_delta = env_deltas.get("APP", {}).get("revenue_delta_pct", 0)
            # AMP is significantly worse than WEB and APP
            if delta_pct < web_delta - 5 or delta_pct < app_delta - 5:
                amp_drift_detected = True

    environment_split["amp_drift_detected"] = amp_drift_detected

    if amp_drift_detected:
        logger.info(
            "AMP drift detected: AMP delta=%.1f%%, WEB delta=%.1f%%, APP delta=%.1f%%",
            environment_split.get("AMP", {}).get("delta_pct", 0),
            environment_split.get("WEB", {}).get("delta_pct", 0),
            environment_split.get("APP", {}).get("delta_pct", 0),
        )
    else:
        logger.info("No AMP drift detected")

    return {
        **state,
        "environment_split": environment_split,
        "execution_errors": errors,
    }
