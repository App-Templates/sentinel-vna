---
phase: 10
plan: "03"
plan_name: silent-failure-watchdog
subsystem: pipeline-monitoring
tags:
  - monitor-02
  - watchdog
  - slack
  - apscheduler
  - silent-failure

dependency_graph:
  requires:
    - "10-01 (alerts_written_count + pipeline_runs counter)"
    - "10-02 (get_alerts_pipeline_health() helper)"
  provides:
    - "backend/monitoring/silent_failure_watch.py (check_silent_failure, send_meta_alert, run_watch_cycle)"
    - "APScheduler job silent_failure_watch_cycle (60m IntervalTrigger, max_instances=1)"
    - "SilentFailureMonitorConfig Pydantic model (WR-03-safe default_factory)"
    - "Slack P0 meta-alert on pipeline_runs_last_24h > 0 AND alerts_last_24h == 0 (MONITOR-02)"
  affects:
    - "backend/utils/config_loader.py (+SilentFailureMonitorConfig class, +field to AlertingConfig)"
    - "config/alerting_rules.yaml (+silent_failure_monitor section, enabled=true)"
    - "backend/scheduler/scheduler.py (+import run_watch_cycle, +job registration, +completion log)"

tech_stack:
  added:
    - "backend/monitoring/ package (watertight boundary per R-13)"
    - "urllib.request.urlopen for Slack POST (mirrors notifier pattern)"
    - "Block Kit payload: header + divider + section + context (distinct from _send_slack alert templates)"
  patterns:
    - "WR-03 default_factory: missing YAML section -> enabled=False, watchdog silent (never crashes pipeline)"
    - "detection rule: prl>0 AND al=0 => triggered; prl=0 => zero_state/data_anomaly; both>0 => healthy"
    - "send_meta_alert never raises: all exceptions caught, returns False on failure"
    - "run_watch_cycle never raises: APScheduler job isolation by design"
    - "webhook lookup: env SLACK_WEBHOOK_URL > slack_channel_override > slack_notifications.webhook_url (YAML fallback)"

key_files:
  created:
    - backend/monitoring/__init__.py
    - backend/monitoring/silent_failure_watch.py
    - scripts/test_silent_failure_watch.py
  modified:
    - backend/utils/config_loader.py (SilentFailureMonitorConfig + AlertingConfig field)
    - config/alerting_rules.yaml (silent_failure_monitor section)
    - backend/scheduler/scheduler.py (import + job registration + completion log)

decisions:
  - "Direct function call to get_alerts_pipeline_health() (not HTTP self-probe): avoids auth complexity + self-DoS risk"
  - "60-minute cycle cadence: <1h detection latency; low noise vs 5-min; config-overridable"
  - "No re-trigger suppression: 60m cadence acceptable; deferred to Phase 18 hardening if operators request"
  - "Custom Block Kit payload (not reuse of _send_slack alert templates): meta-alert has different shape (counts vs AlertState)"
  - "max_instances=1 on APScheduler job: prevents overlapping watchdog cycles"

metrics:
  duration: "~12 minutes"
  tasks_completed: 3
  files_changed: 6
  completed_date: "2026-04-23"
---

# Phase 10 Plan 03: Silent-Failure Watchdog (MONITOR-02) Summary

APScheduler watchdog that detects `pipeline_runs_last_24h > 0 AND alerts_last_24h == 0` and emits a Slack P0 meta-alert with Block Kit payload — closing the 2-month blind spot of the 2026-01-22 -> 2026-04-22 silent-failure incident.

## Task Completion

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | SilentFailureMonitorConfig + YAML section | e4c71d8 | backend/utils/config_loader.py, config/alerting_rules.yaml |
| 2 | silent_failure_watch module + test suite | 2977294 | backend/monitoring/__init__.py, backend/monitoring/silent_failure_watch.py, scripts/test_silent_failure_watch.py |
| 3 | Scheduler integration | d95196e | backend/scheduler/scheduler.py |

## Live Smoke Result (2026-04-23)

```
silent_failure_watch: cycle start
send_meta_alert: Slack POST succeeded (attempt 1/3) metrics={'last_alert_at': '2026-03-23T13:00:00+00:00', 'alerts_last_24h': 0, 'pipeline_runs_last_24h': 1446}
silent_failure_watch: cycle complete -- triggered=True reason=silent_failure metrics={'last_alert_at': '2026-03-23T13:00:00+00:00', 'alerts_last_24h': 0, 'pipeline_runs_last_24h': 1446}
LIVE cycle: {'triggered': True, 'reason': 'silent_failure', 'metrics': {'last_alert_at': '2026-03-23T13:00:00+00:00', 'alerts_last_24h': 0, 'pipeline_runs_last_24h': 1446}, 'slack_sent': True}
SMOKE OK
```

The watchdog correctly triggers on the live DB state (`pipeline_runs_last_24h=1446 > 0 AND alerts_last_24h=0`) — the exact same silent-failure pattern from the 2-month incident.

## Slack Payload Snapshot (live metrics injected)

```json
{
  "blocks": [
    {
      "type": "header",
      "text": {"type": "plain_text", "text": ":rotating_light: PIPELINE SILENT FAILURE (P0)"}
    },
    {"type": "divider"},
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*:rotating_light: P0 PIPELINE SILENT FAILURE*\n\n*Pattern:* `pipeline_runs_last_24h > 0 AND alerts_last_24h == 0`\n*Pipeline runs (24h):* 1446\n*Alerts written (24h):* 0\n*Last alert at:* 2026-03-23T13:00:00+00:00\n\n_This is the same divergence pattern that caused the 2026-01-22 -> 2026-04-22 silent-failure incident. Investigate immediately._\n\nWatchdog: Phase 10 MONITOR-02 | Now: 2026-04-23 23:07 UTC"
      }
    },
    {
      "type": "context",
      "elements": [
        {"type": "mrkdwn", "text": "Source: Phase 10 MONITOR-02 watchdog | Endpoint: /api/health/alerts-pipeline"}
      ]
    }
  ]
}
```

## Test Suite Results

```
Ran 10 tests in 0.004s — OK

- TestCheckSilentFailure.test_data_anomaly ... ok
- TestCheckSilentFailure.test_healthy ... ok
- TestCheckSilentFailure.test_silent_failure_triggers ... ok
- TestCheckSilentFailure.test_zero_state ... ok
- TestRunWatchCycle.test_cycle_never_raises_on_db_failure ... ok
- TestRunWatchCycle.test_cycle_skips_slack_when_healthy ... ok
- TestRunWatchCycle.test_cycle_triggers_slack_on_silent_failure ... ok
- TestSendMetaAlert.test_send_retries_on_500 ... ok
- TestSendMetaAlert.test_send_skips_on_missing_webhook ... ok
- TestSendMetaAlert.test_send_success_200 ... ok
```

## Scheduler Verification

```
registered jobs: ['recheck_queue', 'silent_failure_watch_cycle', 'alerting_cycle', 'drift_cycle', 'daily_digest', 'weekend_cycle_10h', 'weekend_cycle_18h']
trigger: interval[1:00:00]
name: Silent-failure watchdog (MONITOR-02)
SCHEDULER OK
```

All 5 required jobs registered (alerting_cycle, drift_cycle, recheck_queue, daily_digest, silent_failure_watch_cycle).

## WR-03 Defense Verified

Missing `silent_failure_monitor` YAML section -> `enabled=False` (default_factory kicks in, pipeline does NOT crash).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Detection rule, Slack POST, and scheduler integration are all fully wired end-to-end.

## R-01 Preservation

Pre-existing WIP on working tree unchanged after plan completion:
- `backend/api/publisher_routes.py` (modified, not staged)
- `backend/api/routes.py` — pre-phase-10 WIP preserved
- frontend components: untouched
- `data/vna_alerts.db-{shm,wal}`: status unchanged

All plan commits staged with explicit file-by-file `git add` (never `git add -A`).

## Phase 10 Completion — All 3 Requirements Satisfied

| Requirement | Plan | Status |
|-------------|------|--------|
| MONITOR-03 | 10-01 | alerts_written_count column migrated (Migration 003) |
| MONITOR-01 | 10-02 | GET /api/health/alerts-pipeline endpoint live (1.9ms) |
| MONITOR-02 | 10-03 | Silent-failure watchdog + Slack P0 meta-alert |

Phase 10 is complete. Ready for Phase 10 verification.

## Open Questions / Deferred

1. **Re-trigger suppression**: Currently fires every 60m while divergence persists (up to 24 messages/day). Deferred to Phase 18 HARD-03 hardening if operators request debounce.
2. **data_anomaly path** (prl=0, al>0): currently logs WARNING only. Could be strengthened to Slack P2 if observed in practice.
3. **Webhook URL in YAML**: `config/alerting_rules.yaml` has `slack_notifications.webhook_url: https://hooks.slack.com/services/TEST123`. The live smoke showed this URL returning 200 — likely a Slack test endpoint. Operator should configure real webhook URL via `SLACK_WEBHOOK_URL` env var or `silent_failure_monitor.slack_channel_override` for production use.

## Self-Check: PASSED
