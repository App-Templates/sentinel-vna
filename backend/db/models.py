import json
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class AlertStatus(str, Enum):
    OPEN = "OPEN"
    ACK = "ACK"
    RESOLVED = "RESOLVED"
    SNOOZED = "SNOOZED"


class AlertRule(str, Enum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A5 = "A5"  # Margin/eCPM drop
    A6 = "A6"  # Coverage zero


class ChannelGroup(str, Enum):
    GOOGLE = "GOOGLE"
    OPEN_BIDDING = "OPEN_BIDDING"


class EventType(str, Enum):
    ACK = "ACK"
    RESOLVE = "RESOLVE"
    RECHECK = "RECHECK"
    COMMENT = "COMMENT"


class RecheckStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AlertModel(BaseModel):
    alert_id: str = Field(
        ..., pattern=r"^ALT-\d{8}-\d{6}-P[012]$", description="Format: ALT-YYYYMMDD-HHMMSS-P1"
    )
    timestamp: datetime
    severity: Severity
    channel_group: ChannelGroup
    status: AlertStatus = AlertStatus.OPEN
    alert_rule: AlertRule
    revenue_current: float
    revenue_baseline: float
    revenue_delta_pct: float
    triage_label: str
    contributors_json: str = "[]"
    geo_breakdown_json: str = "[]"
    environment_split_json: str = "{}"
    insights_json: str = "{}"
    execution_time_sec: float = 0.0
    data_source: str = "athena"
    config_version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("contributors_json", "geo_breakdown_json", "environment_split_json", "insights_json")
    @classmethod
    def validate_json_string(cls, v: str) -> str:
        try:
            json.loads(v)
        except (json.JSONDecodeError, TypeError):
            raise ValueError(f"Invalid JSON string: {v}")
        return v

    @property
    def contributors(self) -> list:
        return json.loads(self.contributors_json)

    @property
    def geo_breakdown(self) -> list:
        return json.loads(self.geo_breakdown_json)

    @property
    def environment_split(self) -> dict:
        return json.loads(self.environment_split_json)

    @property
    def insights(self) -> dict:
        return json.loads(self.insights_json)


class AlertEventModel(BaseModel):
    event_id: Optional[int] = None
    alert_id: str
    event_type: EventType
    user_id: str
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RecheckQueueModel(BaseModel):
    queue_id: Optional[int] = None
    alert_id: str
    scheduled_at: datetime
    status: RecheckStatus = RecheckStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)


def generate_alert_id(severity: Severity, ts: Optional[datetime] = None) -> str:
    t = ts or datetime.utcnow()
    return f"ALT-{t.strftime('%Y%m%d')}-{t.strftime('%H%M%S')}-{severity.value}"


SQL_CREATE_ALERTS = """
CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('P0', 'P1', 'P2')),
    channel_group TEXT NOT NULL CHECK(channel_group IN ('GOOGLE', 'OPEN_BIDDING')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'ACK', 'RESOLVED', 'SNOOZED')),
    alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A0', 'A1', 'A2', 'A3', 'A5', 'A6')),
    revenue_current REAL NOT NULL,
    revenue_baseline REAL NOT NULL,
    revenue_delta_pct REAL NOT NULL,
    triage_label TEXT NOT NULL,
    contributors_json TEXT DEFAULT '[]',
    geo_breakdown_json TEXT DEFAULT '[]',
    environment_split_json TEXT DEFAULT '{}',
    insights_json TEXT DEFAULT '{}',
    execution_time_sec REAL DEFAULT 0.0,
    data_source TEXT DEFAULT 'athena',
    config_version TEXT DEFAULT '1.0.0',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

SQL_CREATE_ALERT_EVENTS = """
CREATE TABLE IF NOT EXISTS alert_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('ACK', 'RESOLVE', 'RECHECK', 'COMMENT')),
    user_id TEXT NOT NULL,
    comment TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);
"""

SQL_CREATE_RECHECK_QUEUE = """
CREATE TABLE IF NOT EXISTS recheck_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'COMPLETED', 'FAILED')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);
"""

SQL_CREATE_PIPELINE_RUNS = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    channel_group TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'LIVE',
    status TEXT NOT NULL,
    duration_sec REAL,
    llm_used INTEGER DEFAULT 0,
    llm_fallback INTEGER DEFAULT 0,
    alert_id TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL
);
"""

SQL_CREATE_BACKTEST_RESULTS = """
CREATE TABLE IF NOT EXISTS backtest_results (
    backtest_id TEXT PRIMARY KEY,
    start_date TEXT,
    end_date TEXT,
    channel TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    total_checks INTEGER DEFAULT 0,
    alerts_generated INTEGER DEFAULT 0,
    alerts_json TEXT DEFAULT '[]',
    step_hours INTEGER,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    error TEXT
);
"""

SQL_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);",
    "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_created ON pipeline_runs(created_at);",
]
