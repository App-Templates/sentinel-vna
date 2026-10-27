-- HEAD baseline schema dump from data/vna_alerts.db
-- Source: git show HEAD:data/vna_alerts.db
-- HEAD commit: 6990249ba8fe375135fd18668e922832e93a63eb
-- Blob hash: 3926e38c6d820171c74a3d3a35edb0e317801f08
-- Generated: 2026-04-22T20:55:10Z
-- File size: 1421312 bytes
-- SHA256: d2277521809529820d326333c929ff1151e437cb71079903bcba330bf9c3bfdc

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

index|6
table|6
