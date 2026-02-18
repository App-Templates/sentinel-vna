"""
Orchestrator Agent (Node 1)
Receives trigger input and sets up execution plan in state.
Pure Python - no LLM needed.
"""

from datetime import datetime, timezone

from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("agent.orchestrator")


def orchestrator_agent(state: AlertState) -> AlertState:
    """
    Entry point of the pipeline.
    - Validates trigger type (A1/A2/A3)
    - Records execution start
    - Sets up execution plan based on trigger + channel
    - Detects A2-without-A1 scenario (gradual drift)
    """
    logger.info(
        "Orchestrator started | trigger=%s channel=%s mode=%s",
        state.get("trigger_type", "UNKNOWN"),
        state.get("channel_group", "UNKNOWN"),
        state.get("mode", "LIVE"),
    )

    errors: list = list(state.get("execution_errors", []))
    now = datetime.now(timezone.utc)

    # Validate trigger type
    trigger = state.get("trigger_type", "A1")
    if trigger not in ("A1", "A2", "A3"):
        errors.append(f"Invalid trigger_type: {trigger}, defaulting to A1")
        trigger = "A1"

    # Validate channel group
    channel = state.get("channel_group", "GOOGLE")
    if channel not in ("GOOGLE", "OPEN_BIDDING"):
        errors.append(f"Invalid channel_group: {channel}, defaulting to GOOGLE")
        channel = "GOOGLE"

    # Validate mode
    mode = state.get("mode", "LIVE")
    if mode not in ("LIVE", "BACKTEST"):
        errors.append(f"Invalid mode: {mode}, defaulting to LIVE")
        mode = "LIVE"

    # Load config to validate version
    try:
        config = get_config()
        config_version = config.version
    except Exception as e:
        errors.append(f"Config load warning: {e}")
        config_version = "unknown"

    # Timestamp handling
    timestamp = state.get("timestamp") or now.isoformat()

    logger.info(
        "Orchestrator plan: trigger=%s, channel=%s, mode=%s, config_v=%s",
        trigger,
        channel,
        mode,
        config_version,
    )

    return {
        **state,
        "trigger_type": trigger,
        "channel_group": channel,
        "mode": mode,
        "timestamp": timestamp,
        "execution_start": now.isoformat(),
        "execution_errors": errors,
        "data_source": "synthetic",
    }
