"""
LangGraph StateGraph - Value Network Alerting Pipeline

11-agent workflow:
  orchestrator -> data_fetcher_real -> data_validator -> anomaly_detector -> triage_classifier
  -> (conditional: alert_triggered?)
     -> YES: parallel_analysis (contributor + geo + env) -> insight_generator -> report_builder
        -> (conditional: mode != BACKTEST?)
           -> YES: notifier -> END
           -> NO: END
     -> NO: END

The graph is compiled once as a module-level singleton (get_compiled_graph()).
No checkpointer is used — each pipeline run is independent.
"""

from typing import Optional

from langgraph.graph import END, StateGraph

from backend.agents.anomaly_detector import anomaly_detector_agent
from backend.agents.contributor_analyzer import contributor_analyzer_agent
from backend.agents.data_fetcher_real import data_fetcher_agent
from backend.agents.data_validator import data_validator_agent
from backend.agents.environment_splitter import environment_splitter_agent
from backend.agents.geo_analyzer import geo_analyzer_agent
from backend.agents.insight_generator import insight_generator_agent
from backend.agents.notifier import notifier_agent
from backend.agents.orchestrator import orchestrator_agent
from backend.agents.report_builder import report_builder_agent
from backend.agents.triage_classifier import triage_classifier_agent
from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("workflow.graph")


# --- Conditional edge functions ---

def after_anomaly_detector(state: AlertState) -> str:
    """After anomaly_detector: bypass triage/analysis for A0 data gap alerts."""
    if state.get("alert_rule") == "A0":
        logger.info("A0 data gap alert, bypassing triage/analysis -> report_builder")
        return "a0_bypass"
    return "normal"


def should_continue_analysis(state: AlertState) -> str:
    """After triage: continue to parallel analysis if alert was triggered."""
    if state.get("alert_triggered"):
        logger.info("Alert triggered (severity=%s), continuing to analysis", state.get("severity"))
        return "continue"
    logger.info("No alert triggered, ending pipeline")
    return "end"


def should_notify(state: AlertState) -> str:
    """After report_builder: skip notifier in BACKTEST mode."""
    if state.get("mode") == "BACKTEST":
        logger.info("BACKTEST mode, skipping notification")
        return "skip"
    logger.info("LIVE mode, sending notifications")
    return "notify"


# --- Parallel analysis wrapper ---

def run_parallel_analyzers(state: AlertState) -> AlertState:
    """
    Run contributor_analyzer, geo_analyzer, and environment_splitter.
    In production with LangGraph, these could use a fan-out/fan-in pattern.
    For simplicity and reliability, we run them sequentially and merge results.
    Each agent only writes to its own state keys, so there are no conflicts.
    """
    logger.info("Starting parallel analysis phase")

    # Run all three analyzers - each writes to its own state key
    state = contributor_analyzer_agent(state)
    state = geo_analyzer_agent(state)
    state = environment_splitter_agent(state)

    logger.info(
        "Parallel analysis complete: contributors=%d, geo=%d, env_keys=%d",
        len(state.get("contributors", [])),
        len(state.get("geo_breakdown", [])),
        len(state.get("environment_split", {})),
    )

    return state


# --- Graph construction ---

def build_graph() -> StateGraph:
    """Build and return the compiled LangGraph workflow."""
    workflow = StateGraph(AlertState)

    # Add all nodes
    workflow.add_node("orchestrator", orchestrator_agent)
    workflow.add_node("data_fetcher", data_fetcher_agent)
    workflow.add_node("data_validator", data_validator_agent)
    workflow.add_node("anomaly_detector", anomaly_detector_agent)
    workflow.add_node("triage_classifier", triage_classifier_agent)
    workflow.add_node("parallel_analysis", run_parallel_analyzers)
    workflow.add_node("insight_generator", insight_generator_agent)
    workflow.add_node("report_builder", report_builder_agent)
    workflow.add_node("notifier", notifier_agent)

    # Sequential edges: entry -> orchestrator -> data pipeline
    workflow.set_entry_point("orchestrator")
    workflow.add_edge("orchestrator", "data_fetcher")
    workflow.add_edge("data_fetcher", "data_validator")
    workflow.add_edge("data_validator", "anomaly_detector")

    # Conditional: A0 data gap bypasses triage/analysis, goes to report_builder
    workflow.add_conditional_edges(
        "anomaly_detector",
        after_anomaly_detector,
        {"a0_bypass": "report_builder", "normal": "triage_classifier"},
    )

    # Conditional: after triage, continue if alert triggered
    workflow.add_conditional_edges(
        "triage_classifier",
        should_continue_analysis,
        {"continue": "parallel_analysis", "end": END},
    )

    # After parallel analysis -> insight -> report
    workflow.add_edge("parallel_analysis", "insight_generator")
    workflow.add_edge("insight_generator", "report_builder")

    # Conditional: after report, notify only in LIVE mode
    workflow.add_conditional_edges(
        "report_builder",
        should_notify,
        {"notify": "notifier", "skip": END},
    )

    # Notifier -> END
    workflow.add_edge("notifier", END)

    return workflow


_compiled_graph = None


def get_compiled_graph():
    """Return compiled graph singleton. Compiled once, reused across runs."""
    global _compiled_graph
    if _compiled_graph is None:
        workflow = build_graph()
        _compiled_graph = workflow.compile()
        logger.info("Graph compiled (singleton)")
    return _compiled_graph


# --- Convenience runner ---

def run_pipeline(
    trigger_type: str = "A1",
    channel_group: str = "GOOGLE",
    mode: str = "LIVE",
    timestamp: Optional[str] = None,
) -> AlertState:
    """
    Run the complete alerting pipeline.

    Args:
        trigger_type: A1 (spike/drop), A2 (drift), A3 (near-zero)
        channel_group: GOOGLE or OPEN_BIDDING
        mode: LIVE or BACKTEST
        timestamp: ISO format timestamp (defaults to now)

    Returns:
        Final AlertState with all results
    """
    from datetime import datetime, timezone

    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    initial_state: AlertState = {
        "trigger_type": trigger_type,
        "channel_group": channel_group,
        "mode": mode,
        "timestamp": timestamp,
        "execution_errors": [],
    }

    logger.info(
        "Starting pipeline: trigger=%s, channel=%s, mode=%s",
        trigger_type,
        channel_group,
        mode,
    )

    app = get_compiled_graph()
    result = app.invoke(initial_state)

    logger.info(
        "Pipeline complete: alert_triggered=%s, severity=%s, errors=%d",
        result.get("alert_triggered"),
        result.get("severity"),
        len(result.get("execution_errors", [])),
    )

    return result
