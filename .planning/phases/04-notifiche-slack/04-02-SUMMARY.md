---
phase: 04-notifiche-slack
plan: 02
subsystem: notifications
tags: [slack, severity-routing, block-kit, digest-queue]
dependency_graph:
  requires: [04-01]
  provides: [severity-routing, slack-templates, digest-queue]
  affects: [notifier-agent, pending-notifications-table]
tech_stack:
  added: []
  patterns: [severity-based-routing, block-kit-templates, database-queue]
key_files:
  created: []
  modified:
    - backend/db/models.py
    - backend/db/database.py
    - backend/agents/notifier.py
decisions:
  - "pending_notifications table accumulates P1/P2 alerts for daily digest with created_at index for efficient queries"
  - "immediate_severities config controls which severity levels trigger immediate Slack (default: P0 only)"
  - "Three Block Kit templates provide different detail levels: P0 full report, P1 medium, P2 compact"
  - "delivery_status distinguishes slack_sent (immediate) vs slack_queued (digest) for observability"
  - "Action buttons in all Slack messages link to dashboard alert detail page"
metrics:
  duration_minutes: 3
  tasks_completed: 3
  files_modified: 3
  commits: 3
  completed_at: "2026-02-21T19:17:53Z"
---

# Phase 04 Plan 02: Severity-Based Notification Routing Summary

**One-liner:** P0 alerts trigger immediate Slack with full report (contributors, geo, env, next steps), P1/P2 queued for daily digest with compact templates.

## Objective Achievement

Esteso il notifier agent con routing severity-based: P0 inviato immediatamente con template completo, P1/P2 salvati in DB per digest giornaliero con template compatto.

**Status:** COMPLETE
**Output:** Tre template Slack Block Kit (P0/P1/P2), logica di routing basata su immediate_severities config, tabella pending_notifications per accumulare alert in attesa di digest.

## Tasks Completed

### Task 1: Add pending_notifications table to schema
**Commit:** 2878ab0
**Files:** backend/db/models.py, backend/db/database.py

Added `SQL_CREATE_PENDING_NOTIFICATIONS` to models.py with:
- `id` (PRIMARY KEY AUTOINCREMENT)
- `alert_id` (FK to alerts.alert_id ON DELETE CASCADE)
- `severity` (TEXT NOT NULL)
- `channel_group` (TEXT NOT NULL)
- `timestamp` (TEXT NOT NULL)
- `created_at` (TEXT NOT NULL)

Created index `idx_pending_notifications_created_at` for efficient digest queries (e.g., "all pending from last 24h").

Updated `database.py`:
- Imported `SQL_CREATE_PENDING_NOTIFICATIONS` from models
- Added `conn.execute(SQL_CREATE_PENDING_NOTIFICATIONS)` to `init_db()`

Verified table exists in SQLite schema with 6 columns and created_at index.

### Task 2: Implement severity-based routing in notifier agent
**Commit:** 89c182a
**Files:** backend/agents/notifier.py

Added helper functions:

1. **`_should_send_immediate(severity: str, config) -> bool`:**
   - Loads `immediate_severities` from `config.slack_notifications.immediate_severities`
   - Returns `severity in immediate_severities`
   - Defaults to `["P0"]` if config missing

2. **`_save_to_pending_notifications(state: AlertState) -> bool`:**
   - Extracts alert_id, severity, channel_group, timestamp from `state.alert_payload`
   - Inserts into `pending_notifications` table with `created_at = datetime.now(timezone.utc).isoformat()`
   - Returns True on success, logs error and returns False on failure

Updated `notifier_agent()`:
- After saving to DB, checks if `_should_send_immediate(severity, config)`
- If True: submits `_send_slack` to thread pool executor → logs "Sending immediate notification for {severity} alert"
- If False: calls `_save_to_pending_notifications(state)` → logs "Saved {severity} alert to pending notifications for daily digest"
- Added `slack_queued` field to `delivery_status` dict (set True for digest alerts)
- Email behavior unchanged (still controlled by `config.notifications.email_enabled`)

Verified helper functions exist, routing log messages present, and P0/P1/P2 routing logic works correctly.

### Task 3: Create three severity-specific Slack Block Kit templates
**Commit:** e0cb6e2
**Files:** backend/agents/notifier.py

Replaced single `_build_slack_blocks()` with three severity-specific functions:

**1. `_build_slack_blocks_p0(state: AlertState) -> List[dict]` (full report):**
- Header: emoji + severity + revenue delta + channel
- Section: alert_id, rule, revenue current/baseline, triage classification
- Divider
- Section: Key Findings (top 3 from `insights.top_findings`)
- Section: Top Contributors (top 5 with delta_pct + quota_of_drop)
- Section: Geo Breakdown (ITA/ES/OTHER with percentages)
- Section: Environment Split (WEB/AMP/APP with percentages)
- Section: Next Steps (top 3 from `insights.next_steps`)
- Context: confidence + data source + timestamp
- Action button: "View in Dashboard" → `https://sentinel.adkaora.com/alerts/{alert_id}`

**2. `_build_slack_blocks_p1(state: AlertState) -> List[dict]` (medium):**
- Header: emoji + severity + revenue delta + channel
- Section: alert_id, rule, revenue current/baseline, triage classification
- Section: Top Contributors (top 3 only)
- Section: Next Steps (top 2 only)
- Context: confidence + data source + timestamp
- Action button: "View Details" → `https://sentinel.adkaora.com/alerts/{alert_id}`

**3. `_build_slack_blocks_p2(state: AlertState) -> List[dict]` (compact):**
- Single section: emoji + severity + revenue delta_pct + channel + triage + alert_id
  - Format: `"{emoji} *{severity}*: Revenue {delta_pct:+.1f}% | {channel} | {triage} | Alert: \`{alert_id}\`"`
- Action button: "View Details" → `https://sentinel.adkaora.com/alerts/{alert_id}`
- No dividers, no multi-line fields, no insights (single-line compact format)

Updated `_send_slack(state)`:
- Extracts severity from `state.alert_payload`
- If `severity == "P0"`: calls `_build_slack_blocks_p0(state)`
- Elif `severity == "P1"`: calls `_build_slack_blocks_p1(state)`
- Else: calls `_build_slack_blocks_p2(state)`
- Preserves existing retry logic, webhook URL loading, timeout handling

Verified all 3 template functions exist and `_send_slack` selects template based on severity.

## Verification Results

All verification criteria passed:

1. **pending_notifications table exists in SQLite schema** ✅
   - Table has 6 columns: id, alert_id, severity, channel_group, timestamp, created_at
   - Index `idx_pending_notifications_created_at` exists
   - FK constraint to alerts(alert_id) ON DELETE CASCADE

2. **P0 alerts trigger immediate Slack notification** ✅
   - `_should_send_immediate("P0", config)` returns True
   - P0 alerts submitted to thread pool executor for immediate send
   - Log message: "Sending immediate notification for P0 alert"

3. **P1/P2 alerts saved to pending_notifications without sending Slack** ✅
   - `_should_send_immediate("P1", config)` returns False
   - `_should_send_immediate("P2", config)` returns False
   - P1/P2 alerts call `_save_to_pending_notifications(state)`
   - Log message: "Saved {severity} alert to pending notifications for daily digest"

4. **P0 Slack message has full report** ✅
   - `_build_slack_blocks_p0` includes contributors (top 5), geo breakdown, env split, findings (top 3), next steps (top 3)
   - Action button links to dashboard

5. **P2 Slack message is compact** ✅
   - `_build_slack_blocks_p2` is single-line format with only essential info
   - No dividers, no multi-line fields, no insights

6. **delivery_status distinguishes slack_sent vs slack_queued** ✅
   - `delivery_status["slack_sent"]` set for immediate notifications
   - `delivery_status["slack_queued"]` set for digest notifications
   - Log message includes both: `"Notifier complete: db=%s, slack_sent=%s, slack_queued=%s, email=%s"`

## Success Criteria

- [x] pending_notifications table in models.py with alert_id FK and created_at index
- [x] _should_send_immediate helper checks immediate_severities config
- [x] _save_to_pending_notifications inserts digest alerts to DB
- [x] notifier_agent routes P0 → immediate Slack, P1/P2 → pending table
- [x] Three Block Kit templates with different detail levels (P0 full, P1 medium, P2 compact)
- [x] _send_slack selects template based on severity

## Deviations from Plan

None - plan executed exactly as written.

## Key Insights

1. **Severity-based routing reduces notification fatigue:** By sending P0 alerts immediately and batching P1/P2 into a daily digest, the system balances urgency with noise reduction. Operators receive critical alerts instantly but aren't overwhelmed by lower-priority alerts throughout the day.

2. **Template detail level matches urgency:** P0 templates include full context (geo, env, contributors, findings, next steps) for immediate investigation, while P2 templates are compact single-line summaries suitable for batch review. This visual hierarchy reinforces the severity classification.

3. **Database queue enables flexible digest scheduling:** The `pending_notifications` table decouples alert detection from digest delivery. A future cron job can query `WHERE created_at >= datetime('now', '-24 hours')` to send daily digests, without affecting the core alert pipeline.

4. **Action buttons provide direct navigation:** All Slack messages include a "View in Dashboard" or "View Details" button linking to the alert detail page. This reduces friction for operators investigating alerts from Slack.

5. **delivery_status observability:** Distinguishing `slack_sent` vs `slack_queued` in the delivery status enables monitoring of routing behavior. Future dashboards can show "X alerts sent immediately, Y alerts queued for digest" metrics.

6. **Config-driven routing enables A/B testing:** The `immediate_severities` config field allows dynamic adjustment of routing rules. For example, changing from `["P0"]` to `["P0", "P1"]` would send both P0 and P1 alerts immediately without code changes.

## Next Steps

Plan 04-03 will implement the daily digest job that queries `pending_notifications`, groups alerts by severity/channel, builds a summary Slack message, and sends it to the configured channel. This completes the notification routing system.

## Self-Check

Verifying all created files and commits exist:

**Files:**
- ✅ backend/db/models.py (modified, contains SQL_CREATE_PENDING_NOTIFICATIONS)
- ✅ backend/db/database.py (modified, imports and creates pending_notifications table)
- ✅ backend/agents/notifier.py (modified, contains routing logic and 3 templates)

**Commits:**
- ✅ 2878ab0: feat(04-02): add pending_notifications table for digest alerts
- ✅ 89c182a: feat(04-02): implement severity-based routing in notifier agent
- ✅ e0cb6e2: feat(04-02): create three severity-specific Slack Block Kit templates

**Verification:**
- ✅ pending_notifications table exists in SQLite with correct schema
- ✅ _should_send_immediate returns True for P0, False for P1/P2
- ✅ All three Block Kit template functions exist and are called by _send_slack
- ✅ delivery_status includes slack_queued field

## Self-Check: PASSED

All files modified as expected. All commits exist in git history. All verification criteria met.
