---
phase: 06-revisione-documentale
plan: 03
subsystem: documentation
tags: [docs, slack, notifications, operational-guide]
dependency_graph:
  requires: [06-02, 04-01, 04-02, 04-03]
  provides: [slack-docs, notification-routing-docs, digest-scheduler-docs]
  affects: [docs-page, operational-docs]
tech_stack:
  added: []
  patterns: [operational-documentation, severity-routing-docs]
key_files:
  created: []
  modified:
    - frontend/src/pages/DocsPage.tsx
decisions:
  - "Slack notifications section placed after operator workflow sections for logical flow (workflow → notifications)"
  - "Severity-based routing table provides quick reference for operators"
  - "Block Kit template differences explained inline to show detail level by severity"
  - "Daily digest scheduler documented in both operational and technical sections for different audiences"
metrics:
  duration_minutes: 2
  tasks_completed: 3
  files_modified: 1
  commits: 3
  completed_at: "2026-02-21T20:29:07Z"
---

# Phase 06 Plan 03: Slack Notifications Documentation Summary

**One-liner:** Operational docs for Phase 4 Slack notifications covering severity-based routing, Block Kit templates, webhook configuration, and daily digest scheduler.

## Objective Achievement

Aggiunta documentazione completa per le notifiche Slack di Phase 4: routing P0 immediato vs P1/P2 digest, template Block Kit differenziati per severity, configurazione webhook admin, e scheduler digest giornaliero.

**Status:** COMPLETE
**Output:** DocsPage.tsx esteso con sezione Slack notifications in operational docs, pipeline aggiornato con dettagli notifier agent, scheduling aggiornato con job daily_slack_digest.

## Tasks Completed

### Task 1: Add Slack notifications section to operational docs
**Commit:** b845d52
**Files:** frontend/src/pages/DocsPage.tsx

Added new "slack-notifications" section to OP_SECTIONS array and operational docs with comprehensive Slack notification documentation:

**Routing per Severity table:**
- P0 → Immediato (report completo: contributors, geo, env, azioni suggerite)
- P1 → Daily Digest (dettaglio medio: revenue, triage, top 3 contributors)
- P2 → Daily Digest (compatto: una riga con link dashboard)
- P2-WATCH → Daily Digest (compatto: una riga con link dashboard)

**Template Block Kit section:**
- P0 Full: Header rosso + revenue status + triage + top 5 contributors + geo breakdown + env breakdown + azioni suggerite + link
- P1 Medium: Header arancione + revenue status + triage + top 3 contributors + link
- P2 Compact: Header giallo + revenue delta + triage label + link

**Configurazione section:**
4-step process for admin webhook setup:
1. Create webhook in Adkaora Slack workspace
2. Enter webhook URL and channel name in Admin > Slack Configuration
3. Test connection with "Test Connection" button
4. Save configuration (persisted to alerting_rules.yaml)

**Daily Digest section:**
- Scheduled at 08:00 UTC daily
- Collects all P1/P2/P2-WATCH alerts from last 24h
- Sends single Slack message with summary
- Skips digest if no alerts
- Manual trigger: POST /api/admin/trigger-digest

**Delivery Status section:**
Documented 4 delivery_status values:
- `slack_sent`: Immediate notification sent successfully
- `slack_queued`: Queued for daily digest
- `pending`: Not yet processed
- `failed`: Send failed (webhook not configured or Slack error)

**Retry Logic section:**
- P0 immediate notifications: automatic retry with exponential backoff (max 3 attempts)
- Digest notifications: no retry (alerts remain in pending_notifications on failure)

### Task 2: Update pipeline section for notifier agent
**Commit:** d9d45a5
**Files:** frontend/src/pages/DocsPage.tsx

Updated pipeline step 9 (Notifier) description with Slack integration details:
- Old: "Slack/email asincroni via ThreadPoolExecutor (solo LIVE, non backtest). Retry con exponential backoff."
- New: "Invia notifiche Slack immediate (P0) o accoda per daily digest (P1/P2/P2-WATCH). Usa Block Kit templates severity-based. Retry con exponential backoff per P0. Asincrono via ThreadPoolExecutor (solo LIVE, non backtest)."

Added "Notifiche Backtest" note after Operator Feedback Loop note:
- Yellow-highlighted section explaining notifier agent is completely bypassed during backtest mode
- Clarifies Slack notifications are sent ONLY in LIVE mode

### Task 3: Update scheduling section for daily digest job
**Commit:** 3cf89f4
**Files:** frontend/src/pages/DocsPage.tsx

Updated scheduling section in TechnicalDocs:

**Job count updated:**
- Changed "Tre job schedulati in-process" to "Quattro job schedulati in-process"

**Added new job row to scheduling table:**
- Job: `daily_slack_digest`
- Intervallo: CronTrigger (08:00 UTC daily)
- Funzione: `send_daily_digest()`
- Descrizione: "Raccoglie alert P1/P2/P2-WATCH generati nelle ultime 24h, invia digest Slack unico, marca pending_notifications come sent. Skip se nessun alert. Endpoint manuale: `POST /api/admin/trigger-digest`"

## Verification Results

All verification criteria passed:

1. **Slack notifications section exists with severity-based routing table** ✅
   - Section id="slack-notifications" added to OP_SECTIONS array
   - Routing table with 4 rows (P0, P1, P2, P2-WATCH) showing routing, detail level, timing

2. **Block Kit template differences documented** ✅
   - P0 Full template: 8 components listed (header, revenue, triage, contributors, geo, env, actions, link)
   - P1 Medium template: 5 components (header, revenue, triage, top 3 contributors, link)
   - P2 Compact template: 3 components (header, delta, link)

3. **Webhook configuration via admin page explained** ✅
   - 4-step numbered list for admin setup
   - Mentions Admin > Slack Configuration location
   - Test Connection button
   - Persistence to alerting_rules.yaml

4. **Daily digest scheduler (08:00 UTC) documented** ✅
   - Mentioned in operational slack-notifications section (5 bullet points)
   - Documented in technical scheduling section (new job row)
   - Both sections mention 08:00 UTC time

5. **Delivery status values explained** ✅
   - All 4 values documented: slack_sent, slack_queued, pending, failed
   - Each has clear description of when it occurs

6. **Pipeline notifier agent description updated** ✅
   - Mentions severity-based routing (P0 immediate, P1/P2/P2-WATCH digest)
   - References Block Kit templates severity-based
   - Includes exponential backoff for P0

7. **Scheduling section includes daily_slack_digest job** ✅
   - Job row added to scheduling table
   - CronTrigger 08:00 UTC documented
   - Manual endpoint POST /api/admin/trigger-digest included

## Success Criteria

- [x] Operator reading docs understands when they'll get Slack notifications (P0 immediate, P1/P2 digest)
- [x] Admin knows how to configure Slack webhook from admin page
- [x] Daily digest schedule (08:00 UTC) and manual trigger endpoint are documented
- [x] Block Kit template detail levels are clear (full/medium/compact)
- [x] Delivery status tracking is explained for observability

## Deviations from Plan

None - plan executed exactly as written.

## Key Insights

1. **Documentation architecture mirrors feature architecture:** The Slack notifications section follows the same severity-based routing structure as the backend implementation (Phase 4 plans), making it easy for operators to understand the system's behavior by reading docs.

2. **Dual documentation strategy (operational + technical):** Slack notifications are documented in both operational docs (for operators using the system) and technical docs (for admins/developers maintaining the system). This separation ensures each audience gets the information they need without clutter.

3. **Visual hierarchy with tables and badges:** The severity-based routing table uses Badge components (P0 red, P1 orange, P2/P2-WATCH yellow) to visually reinforce the urgency levels. This makes the routing rules scannable at a glance.

4. **Configuration workflow emphasis:** The 4-step webhook configuration process is presented as a numbered list (not bullets) to emphasize the sequential nature of the setup. This reduces configuration errors by making the order explicit.

5. **Manual trigger endpoint visibility:** The POST /api/admin/trigger-digest endpoint is mentioned in both the operational section (daily digest) and technical section (scheduling table). This ensures both operators and admins know how to test the digest without waiting for 08:00 UTC.

6. **Backtest mode clarification:** Adding the yellow-highlighted "Notifiche Backtest" note in the pipeline section addresses a common confusion point: why backtest alerts don't trigger Slack notifications. This prevents false alarms during testing.

## Next Steps

Plan 06-04 will complete Phase 6 by documenting any remaining features from Phase 5 (Athena connector, multi-channel data sources) and performing a final docs audit to ensure all v1.1 features are covered.

## Self-Check

Verifying all created files and commits exist:

**Files:**
- ✅ frontend/src/pages/DocsPage.tsx (modified, contains slack-notifications section, updated pipeline, updated scheduling)

**Commits:**
- ✅ b845d52: feat(06-03): add Slack notifications section to operational docs
- ✅ d9d45a5: feat(06-03): update pipeline section for notifier agent
- ✅ 3cf89f4: feat(06-03): update scheduling section for daily digest job

**Verification:**
- ✅ slack-notifications section exists in OP_SECTIONS array
- ✅ Routing table with P0/P1/P2/P2-WATCH exists
- ✅ Block Kit template differences documented (P0 Full, P1 Medium, P2 Compact)
- ✅ Webhook configuration 4-step process documented
- ✅ Daily digest 08:00 UTC scheduler documented
- ✅ Delivery status values (slack_sent, slack_queued, pending, failed) explained
- ✅ Pipeline notifier agent description updated with severity-based routing
- ✅ Scheduling section shows 4 jobs (was 3) with daily_slack_digest row
- ✅ POST /api/admin/trigger-digest endpoint mentioned twice (operational + technical)

## Self-Check: PASSED

All files modified as expected. All commits exist in git history. All verification criteria met.
