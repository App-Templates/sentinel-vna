from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class AckRequest(BaseModel):
    user_id: Optional[str] = None  # Ignored; user extracted from session
    comment: Optional[str] = None


class ResolveRequest(BaseModel):
    user_id: Optional[str] = None  # Ignored; user extracted from session
    comment: Optional[str] = None


class RecheckRequest(BaseModel):
    user_id: Optional[str] = None  # Ignored; user extracted from session


class CommentRequest(BaseModel):
    user_id: Optional[str] = None  # Ignored; user extracted from session
    comment: str


class BacktestRequest(BaseModel):
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    step_hours: int = 2


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AlertSummary(BaseModel):
    alert_id: str
    timestamp: str
    severity: str
    channel_group: str
    status: str
    alert_rule: str
    revenue_current: float
    revenue_baseline: float
    revenue_delta_pct: float
    triage_label: str
    created_at: str


class AlertEvent(BaseModel):
    event_id: int
    alert_id: str
    event_type: str
    user_id: str
    comment: Optional[str] = None
    timestamp: str


class AlertDetail(BaseModel):
    alert_id: str
    timestamp: str
    severity: str
    channel_group: str
    status: str
    alert_rule: str
    revenue_current: float
    revenue_baseline: float
    revenue_delta_pct: float
    triage_label: str
    contributors: list = []
    geo_breakdown: list = []
    environment_split: dict = {}
    insights: dict = {}
    execution_time_sec: float
    data_source: str
    config_version: str
    created_at: str
    updated_at: str
    events: list[AlertEvent] = []
    assignment: Optional[dict] = None


class AlertListResponse(BaseModel):
    alerts: list[AlertSummary]
    total: int
    limit: int
    offset: int


class AlertDetailResponse(BaseModel):
    alert: AlertDetail


class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "OK"


class RecheckResponse(BaseModel):
    success: bool = True
    scheduled_at: str


class BacktestStartResponse(BaseModel):
    backtest_id: str
    status: str = "PENDING"


class BacktestAlertSummary(BaseModel):
    alert_id: str
    timestamp: str
    severity: str
    channel_group: str
    alert_rule: str
    revenue_delta_pct: float
    triage_label: str


class BacktestDateRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    step_hours: Optional[int] = None


class BacktestResultResponse(BaseModel):
    backtest_id: str
    status: str
    date_range: BacktestDateRange = BacktestDateRange()
    total_checks: int = 0
    alerts_generated: int = 0
    alerts: list[BacktestAlertSummary] = []
    error: Optional[str] = None


class TrendPoint(BaseModel):
    timestamp: str
    revenue: float
    baseline_revenue: float
    bacino: int
    coverage: float


class AlertTrendResponse(BaseModel):
    trend: list[TrendPoint]


class HealthResponse(BaseModel):
    status: str
    version: str
    db_ok: bool
    scheduler_running: bool
    timestamp: str
    pipeline_metrics: Optional[dict] = None


# ---------------------------------------------------------------------------
# Feedback schemas
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    feedback_type: str  # Must match FeedbackCategory enum values
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    feedback_id: int
    alert_id: str
    user_id: str
    feedback_type: str
    comment: Optional[str] = None
    timestamp: str


class FeedbackHistoryResponse(BaseModel):
    feedbacks: list[FeedbackResponse]
    total: int


# ---------------------------------------------------------------------------
# Assignment schemas
# ---------------------------------------------------------------------------

class AssignRequest(BaseModel):
    assigned_to: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@adkaora\.com$")


class AssignmentResponse(BaseModel):
    assignment_id: int
    alert_id: str
    assigned_to: str
    assigned_by: str
    assigned_at: str
