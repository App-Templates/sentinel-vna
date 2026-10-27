-- Migration: 000_wip_drift_baseline
-- Purpose: Capture the 2-month WIP drift in data/vna_alerts.db as a replayable,
--          reviewable SQL artifact so Phase 08 can build deterministically on top.
-- Decision: FORWARD_PORT (see .planning/phases/07-db-wip-investigation/DECISION.md)
-- Generated: 2026-04-22T21:05:00Z
-- Traceability:
--   HEAD baseline schema: .planning/phases/07-db-wip-investigation/head-schema.sql
--   WIP observed schema:  .planning/phases/07-db-wip-investigation/wip-schema.sql
--   Drift report:         .planning/phases/07-db-wip-investigation/schema-diff.md

-- Idempotency: this migration assumes it runs against a DB at HEAD baseline
--              (i.e. an operator who starts from `git show HEAD:data/vna_alerts.db`
--               and wants to reach the WIP state minus row data).
--              The migration includes only the DDL delta (5 new tables + 7 indexes).
--              It does NOT modify existing tables (alerts, alert_events, recheck_queue,
--              pipeline_runs, backtest_results).

-- DEFERRED to 001_expand_channel_groups.sql (Phase 08):
--   ALTER TABLE alerts → expand channel_group CHECK to 7 v1.2 channels
--   ALTER TABLE alerts → expand alert_rule CHECK to include A5, A6, A7
--   These are Phase 08 SCHEMA-01/02 responsibilities.

BEGIN TRANSACTION;

-- ==== Schema changes (forward-port of WIP drift — Phase 03: Operator Workflow) ====

-- Table: alert_feedback (Phase 03-01: operator feedback on alerts)
CREATE TABLE IF NOT EXISTS alert_feedback (
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
CREATE INDEX IF NOT EXISTS idx_feedback_publisher ON alert_feedback(publisher_id);

-- Table: alert_assignments (Phase 03-02: operator assignment tracking)
CREATE TABLE IF NOT EXISTS alert_assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL UNIQUE,
    assigned_to TEXT NOT NULL,
    assigned_by TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);
CREATE INDEX IF NOT EXISTS idx_assignments_assigned_to ON alert_assignments(assigned_to);

-- Table: manual_interventions (Phase 03-03: manual intervention logging)
CREATE TABLE IF NOT EXISTS manual_interventions (
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
CREATE INDEX IF NOT EXISTS idx_interventions_timestamp ON manual_interventions(timestamp);
CREATE INDEX IF NOT EXISTS idx_interventions_publisher ON manual_interventions(publisher_id);

-- Table: alert_intervention_links (Phase 03-03: alert↔intervention junction)
CREATE TABLE IF NOT EXISTS alert_intervention_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    intervention_id INTEGER NOT NULL,
    linked_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id),
    FOREIGN KEY (intervention_id) REFERENCES manual_interventions(intervention_id)
);
CREATE INDEX IF NOT EXISTS idx_intervention_links_alert ON alert_intervention_links(alert_id);

-- ==== Schema changes (forward-port of WIP drift — Phase 04: Slack Notifications) ====

-- Table: pending_notifications (Phase 04-02: digest notification queue)
CREATE TABLE IF NOT EXISTS pending_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    channel_group TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_pending_notifications_created_at ON pending_notifications(created_at);

-- ==== End schema changes ====

COMMIT;

-- Rollback (for emergency manual revert; test before relying on it):
--   BEGIN;
--   DROP TABLE IF EXISTS pending_notifications;
--   DROP TABLE IF EXISTS alert_intervention_links;
--   DROP TABLE IF EXISTS manual_interventions;
--   DROP TABLE IF EXISTS alert_assignments;
--   DROP TABLE IF EXISTS alert_feedback;
--   COMMIT;
-- In practice, prefer restoring from backup .db file (data/vna_alerts.db.bak*).
--
-- Post-migration state: DB has 11 tables matching wip-schema.sql (Phase 03/04 drift resolved).
-- Next migration: 001_expand_channel_groups.sql (Phase 08 SCHEMA-01/02)
--   → expands channel_group CHECK to 7 v1.2 channels
--   → expands alert_rule CHECK to A0-A7
--   → syncs backend/db/models.py ChannelGroup enum + SQL_CREATE_ALERTS
