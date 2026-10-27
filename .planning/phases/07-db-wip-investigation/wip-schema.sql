-- WIP schema dump from data/vna_alerts.db
-- Source: working-directory (M status, uncommitted)
-- Generated: 2026-04-22T20:53:25Z
-- File size: 1421312 bytes
-- SHA256: 3f65d19d435f3fc1dad83cb2cfbfbd2cc0639fecb68cac27e5048a8c9d5d62b2

CREATE TABLE alert_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('ACK', 'RESOLVE', 'RECHECK', 'COMMENT')),
    user_id TEXT NOT NULL,
    comment TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE recheck_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'COMPLETED', 'FAILED')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);
CREATE TABLE pipeline_runs (
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
CREATE INDEX idx_pipeline_runs_created ON pipeline_runs(created_at);
CREATE TABLE backtest_results (
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
CREATE TABLE alerts (
    alert_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('P0', 'P1', 'P2')),
    channel_group TEXT NOT NULL CHECK(channel_group IN ('GOOGLE', 'OPEN_BIDDING')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'ACK', 'RESOLVED', 'SNOOZED')),
    alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A0', 'A1', 'A2', 'A3')),
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
CREATE INDEX idx_alerts_timestamp ON alerts(timestamp);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE TABLE alert_feedback (
    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL CHECK(feedback_type IN (
        'REAL',
        'FALSE_POSITIVE_MANUAL_INTERVENTION',
        'FALSE_POSITIVE_SEASONALITY',
        'FALSE_POSITIVE_TECHNICAL',
        'FALSE_POSITIVE_PUBLISHER_CAMPAIGN',
        'FALSE_POSITIVE_MARKET_NOISE'
    )),
    comment TEXT,
    publisher_id TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);
CREATE INDEX idx_feedback_publisher ON alert_feedback(publisher_id);
CREATE TABLE alert_assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL UNIQUE,
    assigned_to TEXT NOT NULL,
    assigned_by TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);
CREATE INDEX idx_assignments_assigned_to ON alert_assignments(assigned_to);
CREATE TABLE manual_interventions (
    intervention_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    publisher_id TEXT NOT NULL,
    intervention_type TEXT NOT NULL CHECK(intervention_type IN (
        'PRICING_RULE',
        'FLOOR_CPM',
        'DEMAND_PARTNER_CONFIG',
        'AD_UNIT_SETUP',
        'POLICY_CHANGE',
        'OTHER'
    )),
    description TEXT NOT NULL,
    value_before TEXT,
    value_after TEXT,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE alert_intervention_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    intervention_id INTEGER NOT NULL,
    linked_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id),
    FOREIGN KEY (intervention_id) REFERENCES manual_interventions(intervention_id)
);
CREATE INDEX idx_interventions_timestamp ON manual_interventions(timestamp);
CREATE INDEX idx_interventions_publisher ON manual_interventions(publisher_id);
CREATE INDEX idx_intervention_links_alert ON alert_intervention_links(alert_id);
CREATE TABLE pending_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    channel_group TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);
CREATE INDEX idx_pending_notifications_created_at ON pending_notifications(created_at);
index|13
table|11
