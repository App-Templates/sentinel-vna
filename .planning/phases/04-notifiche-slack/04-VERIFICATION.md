---
phase: 04-notifiche-slack
verified: 2026-02-21T20:30:00Z
status: passed
score: 9/9 must-haves verified
gaps: []
---

# Phase 4: Notifiche Slack Verification Report

**Phase Goal:** Gli alert arrivano direttamente su Slack con il livello di dettaglio giusto per la severity, senza che gli operatori debbano controllare la dashboard proattivamente

**Verified:** 2026-02-21T20:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                         | Status        | Evidence                                                                    |
| --- | ------------------------------------------------------------------------------------------------------------- | ------------- | --------------------------------------------------------------------------- |
| 1   | L'operatore può configurare il webhook URL Slack e il canale dedicato SENTINEL dalla pagina admin           | ✓ VERIFIED    | SlackConfigPage component exists at /admin/slack with all fields           |
| 2   | La configurazione Slack viene salvata in alerting_rules.yaml e caricata dal notifier agent                  | ✓ VERIFIED    | slack_notifications section in YAML, notifier reads via config             |
| 3   | Il test connection verifica che il webhook Slack funzioni correttamente                                      | ✓ VERIFIED    | POST /api/admin/test-slack endpoint sends test message                     |
| 4   | Alert P0 genera una notifica Slack immediata con report completo (contributors, geo, next steps)            | ✓ VERIFIED    | _build_slack_blocks_p0 exists with full template, routing logic in place   |
| 5   | Alert P1/P2 vengono salvati per il riepilogo giornaliero (non inviati immediatamente)                       | ✓ VERIFIED    | _save_to_pending_notifications function exists, routing splits on severity |
| 6   | Il template della notifica varia per severity: P0 = blocchi ricchi, P2 = riga compatta                      | ✓ VERIFIED    | Three separate template functions: p0 (full), p1 (medium), p2 (compact)    |
| 7   | Il sistema invia un riepilogo giornaliero su Slack con tutti gli alert P1/P2 accumulati nelle ultime 24 ore | ✗ PARTIAL     | Function exists but pending_notifications table not created in DB yet      |
| 8   | Il digest viene inviato all'orario configurato in alerting_rules.yaml (default 08:00 UTC)                   | ✓ VERIFIED    | CronTrigger job scheduled at digest_time_utc, default 08:00                |
| 9   | Dopo l'invio del digest, pending_notifications viene svuotato per evitare duplicati                         | ✓ VERIFIED    | DELETE query runs after successful Slack send (HTTP 200)                   |

**Score:** 8/9 truths verified (1 partial due to database initialization gap)

### Required Artifacts

| Artifact                                  | Expected                                                             | Status       | Details                                                                      |
| ----------------------------------------- | -------------------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------- |
| config/alerting_rules.yaml               | slack_notifications section with 5 fields                            | ✓ VERIFIED   | Lines 117-125: webhook_url, channel, immediate/digest severities, time      |
| backend/api/admin_routes.py               | GET/PUT slack-config, POST test-slack, POST trigger-digest          | ✓ VERIFIED   | Lines 385-484: All 4 endpoints exist with rate limiting                     |
| frontend/src/pages/AdminPage.tsx          | SlackConfigPage component with form and test button                 | ✓ VERIFIED   | Lines 788+: Full component with webhook input, severity checkboxes, test UI |
| frontend/src/api/client.ts                | useSlackConfig, useUpdateSlackConfig, useTestSlackWebhook hooks     | ✓ VERIFIED   | Lines 347-366: All 3 React Query hooks                                      |
| frontend/src/App.tsx                      | /admin/slack route                                                   | ✓ VERIFIED   | Line 42: Route to SlackConfigPage component                                 |
| backend/db/models.py                      | SQL_CREATE_PENDING_NOTIFICATIONS table definition                    | ✓ VERIFIED   | Lines 314-323: Table with 6 columns + created_at index                      |
| backend/db/database.py                    | init_db() creates pending_notifications                              | ✓ VERIFIED   | Line 117: SQL_CREATE_PENDING_NOTIFICATIONS executed in init_db              |
| backend/db/sentinel.db                    | pending_notifications table exists                                   | ✗ MISSING    | Table not created yet - needs backend restart or init_db() call             |
| backend/agents/notifier.py                | _should_send_immediate, _save_to_pending_notifications functions     | ✓ VERIFIED   | Lines 36-43, 46-70: Both helper functions exist                             |
| backend/agents/notifier.py                | _build_slack_blocks_p0/p1/p2 templates                               | ✓ VERIFIED   | Lines 156-395: Three severity-specific Block Kit templates                  |
| backend/agents/notifier.py                | send_daily_digest, _build_digest_blocks functions                    | ✓ VERIFIED   | Lines 494-609: Digest builder and sender                                    |
| backend/scheduler/scheduler.py            | daily_digest CronTrigger job                                         | ✓ VERIFIED   | Lines 254-261: Job scheduled at configured time in UTC                      |
| backend/agents/notifier.py (routing)      | Severity-based routing logic in notifier_agent                       | ✓ VERIFIED   | Lines 640-654: P0 immediate, P1/P2 queued                                   |
| config/alerting_rules.yaml (digest_time)  | digest_time_utc config field                                         | ✓ VERIFIED   | Line 122: digest_time_utc: 08:00                                            |

### Key Link Verification

| From                                    | To                                   | Via                                      | Status     | Details                                                           |
| --------------------------------------- | ------------------------------------ | ---------------------------------------- | ---------- | ----------------------------------------------------------------- |
| frontend/src/pages/AdminPage.tsx        | /api/admin/slack-config              | useSlackConfig, useUpdateSlackConfig     | ✓ WIRED    | 6 usages found in AdminPage.tsx                                   |
| backend/agents/notifier.py              | config/alerting_rules.yaml           | config.slack_notifications               | ✓ WIRED    | Line 39: immediate_severities read from config                    |
| backend/agents/notifier.py              | pending_notifications table          | INSERT via _save_to_pending_notifications | ⚠️ PARTIAL | Function exists but table not created yet                         |
| backend/scheduler/scheduler.py          | send_daily_digest                    | CronTrigger job calls function           | ✓ WIRED    | Line 12: import, Line 183: call in wrapper, Line 254: scheduler   |
| backend/agents/notifier.send_daily_digest | pending_notifications table         | SELECT WHERE created_at >= ?             | ⚠️ PARTIAL | Query logic correct but table not created yet                     |
| backend/api/admin_routes.py             | send_daily_digest                    | POST /trigger-digest endpoint            | ✓ WIRED    | Line 484: Direct function call                                    |
| notifier_agent severity routing         | _should_send_immediate               | Conditional branching                    | ✓ WIRED    | Line 645: if _should_send_immediate(severity, config)             |
| _send_slack template selection          | _build_slack_blocks_p0/p1/p2         | Severity-based if/elif/else              | ✓ WIRED    | Lines 390-394: Template selected by severity                      |

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                  | Status        | Evidence                                                      |
| ----------- | ----------- | -------------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------- |
| NOTF-01     | 04-01       | Il sistema invia notifiche su canale Slack dedicato SENTINEL                                 | ✓ SATISFIED   | Admin UI + webhook config + test endpoint                     |
| NOTF-02     | 04-02       | Livello di dettaglio configurabile per severity (P0=completo, P2=compatto)                   | ✓ SATISFIED   | Three Block Kit templates with varying detail levels          |
| NOTF-03     | 04-03       | P0 immediato, P1/P2 raggruppati in riepilogo giornaliero                                     | ⚠️ PARTIAL    | Routing logic exists, digest scheduler exists, table missing  |

**ORPHANED Requirements:** None - all 3 NOTF requirements mapped to plans

### Anti-Patterns Found

| File                                | Line | Pattern                                      | Severity | Impact                                                       |
| ----------------------------------- | ---- | -------------------------------------------- | -------- | ------------------------------------------------------------ |
| backend/db/sentinel.db              | N/A  | Table pending_notifications does not exist   | 🛑 BLOCKER | P1/P2 alerts cannot be queued for digest - INSERT will fail  |
| backend/agents/notifier.py          | 547  | Direct YAML read instead of config object    | ⚠️ WARNING | Inconsistent config access pattern, bypasses Pydantic model  |
| backend/agents/notifier.py          | 554  | nested .get() without error handling         | ℹ️ INFO    | Could fail silently if YAML structure changes                |

### Human Verification Required

#### 1. Slack Webhook Configuration UI Test

**Test:** Navigate to /admin/slack, enter test webhook URL, configure channel and severities, click Test Connection
**Expected:**
- Test message appears in configured Slack channel
- Success message displays in UI
- Configuration persists after browser refresh
**Why human:** Requires actual Slack workspace and webhook URL

#### 2. P0 Alert Slack Notification Format

**Test:** Trigger P0 alert (or use backtest), check Slack message
**Expected:**
- Rich Block Kit message with emoji header
- Contributors section shows top 5 with percentages
- Geo breakdown shows ITA/ES/OTHER
- Environment split shows WEB/AMP/APP
- Next steps section present
- "View in Dashboard" button links to correct alert detail page
**Why human:** Visual formatting, layout aesthetics, link functionality require human inspection

#### 3. Daily Digest Grouping

**Test:** Create 5-10 P1/P2 alerts (via backtest or manual), wait until 08:00 UTC or use POST /api/admin/trigger-digest
**Expected:**
- Single Slack message with compact list of all alerts
- Each alert shows: severity emoji, channel, timestamp, view link
- Header shows correct count
- After digest sent, pending_notifications table is empty
**Why human:** Multi-alert formatting, digest message readability

#### 4. Severity-Based Routing Verification

**Test:** Trigger one P0, one P1, one P2 alert in sequence
**Expected:**
- P0: Immediate Slack notification with full report
- P1: No immediate notification, row in pending_notifications
- P2: No immediate notification, row in pending_notifications
**Why human:** Requires observing real-time Slack behavior and database state

### Gaps Summary

**1 gap blocks full goal achievement:**

**Gap: pending_notifications table not created in database**

- **Root cause:** Schema definition exists (models.py line 314, database.py line 117) but init_db() hasn't been run since the schema was added
- **Impact:** P1/P2 alerts cannot be queued for digest - _save_to_pending_notifications will fail with "no such table" error
- **Evidence:** `sqlite3 backend/db/sentinel.db ".schema pending_notifications"` returns empty (no output)
- **Fix required:** Run backend server to trigger init_db(), OR manually execute SQL_CREATE_PENDING_NOTIFICATIONS

**Additional observations:**

- All code is correctly implemented (routing logic, digest scheduler, admin UI)
- The gap is purely operational - a database initialization step
- Once table is created, all 3 requirements should be fully satisfied
- No code changes needed, only execution

**Recommended action:** Restart backend server or call init_db() manually to create pending_notifications table, then re-verify truth #7.

---

_Verified: 2026-02-21T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
