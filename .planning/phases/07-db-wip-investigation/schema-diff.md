# Schema Drift Report — data/vna_alerts.db (WIP vs HEAD)

**Generated:** 2026-04-22T20:57:00Z
**WIP source:** working-directory (` M` status, SHA256: 3f65d19d435f3fc1dad83cb2cfbfbd2cc0639fecb68cac27e5048a8c9d5d62b2)
**HEAD source:** git show HEAD:data/vna_alerts.db @ 6990249 (blob 3926e38c6d820171c74a3d3a35edb0e317801f08)

## Drift Summary

- **5 tables added in WIP** (not present in HEAD): `alert_feedback`, `alert_assignments`, `manual_interventions`, `alert_intervention_links`, `pending_notifications`
- **7 indexes added in WIP** (not present in HEAD): `idx_feedback_publisher`, `idx_assignments_assigned_to`, `idx_interventions_timestamp`, `idx_interventions_publisher`, `idx_intervention_links_alert`, `idx_pending_notifications_created_at`, plus one on `alert_feedback`
- **6 tables preserved unchanged**: `alert_events`, `sqlite_sequence`, `recheck_queue`, `pipeline_runs`, `backtest_results`, `alerts` — DDL is byte-identical between WIP and HEAD
- **No columns added, removed, or type-changed** on any existing table
- **No CHECK constraints changed** on any existing table — `channel_group IN ('GOOGLE', 'OPEN_BIDDING')` is IDENTICAL in both WIP and HEAD
- **No views or triggers** in either WIP or HEAD
- **No tables removed** between HEAD and WIP

Summary of object counts: HEAD has 6 tables + 6 indexes; WIP has 11 tables + 13 indexes.

## Expected vs Actual (Intel Hypothesis Check)

Intel hypothesis (from `.planning/intel/sentinel-2026-04-22/RECONCILIATION.md`): HEAD CHECK is `channel_group IN ('GOOGLE', 'OPEN_BIDDING')` (v1.0, 2 channels).

- [x] HEAD CHECK matches hypothesis: **YES** — `channel_group TEXT NOT NULL CHECK(channel_group IN ('GOOGLE', 'OPEN_BIDDING'))`
- [x] WIP CHECK matches HEAD (drift did NOT patch it): **YES** — WIP also has `CHECK(channel_group IN ('GOOGLE', 'OPEN_BIDDING'))` — unchanged
- [ ] WIP CHECK already expanded (drift DID patch it locally): **NO** — WIP did NOT locally patch the channel_group CHECK. The 7-channel expansion (GOOGLE_ADEX, DEAL, DIRECT, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, OPEN_BIDDING) is still missing from both DBs.

**Critical implication**: The WIP DB retains the stale 2-channel CHECK that caused 2590 silent-failure pipeline runs. The WIP schema additions (Phase 03/04 tables) are structural work that was committed in code but never captured in a tracked migration.

## Additional Finding: alert_rule CHECK also stale in BOTH DBs

The DB schema (both HEAD and WIP) has:
```sql
alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A0', 'A1', 'A2', 'A3'))
```

But `backend/db/models.py` `SQL_CREATE_ALERTS` now declares:
```sql
alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A0', 'A1', 'A2', 'A3', 'A5', 'A6', 'A7'))
```

A5/A6/A7 alert rules were added in Phase 02 (eCPM drop, coverage-zero, pricing rule alerts). The DB CHECK has never been updated — this is a second silent-failure vector for Phase 02 alert types if they try to INSERT.

## Unified Diff

```diff
--- head-schema.sql (6 tables, 6 indexes)
+++ wip-schema.sql (11 tables, 13 indexes)
@@ -71,6 +71,71 @@
 CREATE INDEX idx_alerts_timestamp ON alerts(timestamp);
 CREATE INDEX idx_alerts_status ON alerts(status);
 CREATE INDEX idx_alerts_severity ON alerts(severity);
-
-index|6
-table|6
+CREATE TABLE alert_feedback (
+    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
+    alert_id TEXT NOT NULL,
+    user_id TEXT NOT NULL,
+    feedback_type TEXT NOT NULL CHECK(feedback_type IN (
+        'REAL',
+        'FALSE_POSITIVE_MANUAL_INTERVENTION',
+        'FALSE_POSITIVE_SEASONALITY',
+        'FALSE_POSITIVE_TECHNICAL',
+        'FALSE_POSITIVE_PUBLISHER_CAMPAIGN',
+        'FALSE_POSITIVE_MARKET_NOISE'
+    )),
+    comment TEXT,
+    publisher_id TEXT,
+    timestamp TEXT NOT NULL,
+    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
+);
+CREATE INDEX idx_feedback_publisher ON alert_feedback(publisher_id);
+CREATE TABLE alert_assignments (
+    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
+    alert_id TEXT NOT NULL UNIQUE,
+    assigned_to TEXT NOT NULL,
+    assigned_by TEXT NOT NULL,
+    assigned_at TEXT NOT NULL,
+    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
+);
+CREATE INDEX idx_assignments_assigned_to ON alert_assignments(assigned_to);
+CREATE TABLE manual_interventions (
+    intervention_id INTEGER PRIMARY KEY AUTOINCREMENT,
+    timestamp TEXT NOT NULL,
+    publisher_id TEXT NOT NULL,
+    intervention_type TEXT NOT NULL CHECK(intervention_type IN (
+        'PRICING_RULE',
+        'FLOOR_CPM',
+        'DEMAND_PARTNER_CONFIG',
+        'AD_UNIT_SETUP',
+        'POLICY_CHANGE',
+        'OTHER'
+    )),
+    description TEXT NOT NULL,
+    value_before TEXT,
+    value_after TEXT,
+    user_id TEXT NOT NULL,
+    created_at TEXT NOT NULL
+);
+CREATE TABLE alert_intervention_links (
+    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
+    alert_id TEXT NOT NULL,
+    intervention_id INTEGER NOT NULL,
+    linked_at TEXT NOT NULL,
+    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id),
+    FOREIGN KEY (intervention_id) REFERENCES manual_interventions(intervention_id)
+);
+CREATE INDEX idx_interventions_timestamp ON manual_interventions(timestamp);
+CREATE INDEX idx_interventions_publisher ON manual_interventions(publisher_id);
+CREATE INDEX idx_intervention_links_alert ON alert_intervention_links(alert_id);
+CREATE TABLE pending_notifications (
+    id INTEGER PRIMARY KEY AUTOINCREMENT,
+    alert_id TEXT NOT NULL,
+    severity TEXT NOT NULL,
+    channel_group TEXT NOT NULL,
+    timestamp TEXT NOT NULL,
+    created_at TEXT NOT NULL,
+    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
+);
+CREATE INDEX idx_pending_notifications_created_at ON pending_notifications(created_at);
+index|13
+table|11
```

## Risk Assessment

- **Severity of drift**: MEDIUM — The 5 added tables represent 2 months of Phase 03 (operator workflow) and Phase 04 (Slack notifications) schema changes that were never captured as migration scripts. No existing table was altered or dropped. Risk is medium because the drift is additive-only (no data loss risk) but was silently committed to the binary without a tracked migration.
- **Does WIP drift partially or fully address SCHEMA-01 (7-channel CHECK)?** NO — WIP did NOT patch the channel_group CHECK. The 7-channel expansion is entirely absent from both WIP and HEAD. SCHEMA-01 must add this from scratch.
- **Can Phase 08 proceed without preserving WIP?** NO — The 5 tables in WIP are live application features (feedback, assignments, interventions, notifications). They must be forward-ported via a tracked migration script. If Phase 08 starts from a `git show HEAD:data/vna_alerts.db` reset, it would lose the Phase 03/04 schema and break those runtime features.
