from typing import TypedDict


class AlertState(TypedDict, total=False):
    # Input
    trigger_type: str  # A1/A2/A3
    timestamp: str
    channel_group: str  # GOOGLE/OPEN_BIDDING
    mode: str  # LIVE/BACKTEST

    # Data
    current_metrics: dict
    baseline_metrics: dict
    delta: dict
    historical_stats: dict

    # Results
    validation_status: str
    alert_triggered: bool
    alert_rule: str
    severity: str  # P0/P1/P2
    z_score: float
    confidence: float
    triage_label: str
    contributors: list
    geo_breakdown: list
    environment_split: dict

    # Output
    insights: dict
    alert_payload: dict
    markdown_report: str
    delivery_status: dict

    # Metadata
    execution_start: str
    execution_errors: list
    data_source: str
