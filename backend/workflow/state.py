from typing import TypedDict
try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired


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

    # Comparative alerting fields (v1.1)
    yesterday_comparison: NotRequired[dict]  # {delta_pct, same_hours_revenue_yesterday, current_hour_revenue, triggered}
    moving_average_14d: NotRequired[dict]    # {avg_revenue, delta_pct, divergence_hours, triggered}

    # v1.2 extended metrics
    revenue_gross: NotRequired[float]
    ecpm: NotRequired[float]
    rpm: NotRequired[float]
    ctr: NotRequired[float]
    viewability: NotRequired[float]
    gross_margin_pct: NotRequired[float]
    floor_cpm: NotRequired[float]
    clicks: NotRequired[int]
    viewable_impressions: NotRequired[int]

    # v1.2 alert engine additions
    gross_margin_metrics: NotRequired[dict]  # A8 gross margin alert details
    leading_indicator_warnings: NotRequired[list]  # CTR/viewability early warnings
    cross_channel_annotation: NotRequired[dict]  # probable_direct_campaign metadata
    coverage_zero_metrics: NotRequired[dict]  # A6 coverage zero details
    margin_metrics: NotRequired[dict]  # A5 margin details
    pricing_rule_metrics: NotRequired[dict]  # A7 pricing rule details
    drift_regression: NotRequired[dict]  # A2 drift regression details
