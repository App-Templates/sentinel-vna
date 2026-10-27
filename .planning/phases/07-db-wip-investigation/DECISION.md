# DB WIP Reconciliation Decision — Phase 07

**Decided:** 2026-04-22T21:00:00Z
**Requirement:** WIP-01
**Input reports:** schema-diff.md, models-py-check.md

## Decision

```
FORWARD_PORT
```

## Rationale

- **schema-diff.md § Drift Summary**: WIP contains 5 structural tables (`alert_feedback`, `alert_assignments`, `manual_interventions`, `alert_intervention_links`, `pending_notifications`) and 7 indexes not present in HEAD. These are Phase 03 (operator workflow) and Phase 04 (Slack notifications) features that were applied to the local DB binary without a tracked migration script.
- **schema-diff.md § Risk Assessment**: These 5 tables are live application features wired to active API routes (`backend/api/admin_routes.py`, `backend/api/routes.py`). Resetting to HEAD would break runtime functionality.
- **schema-diff.md § Expected vs Actual**: The WIP did NOT patch `channel_group` CHECK — it remains `IN ('GOOGLE', 'OPEN_BIDDING')` in both WIP and HEAD. The `alert_rule` CHECK is also unchanged in both DBs (A0-A3 only). Phase 08 owns these two CHECK expansions exclusively.
- **models-py-check.md § Comparison Matrix**: The 5 WIP tables exactly match their counterpart `SQL_CREATE_*` declarations in `backend/db/models.py` (models.py lines 251-324). The drift is structurally correct — no remodeling needed.
- **FORWARD_PORT rationale**: The drift is partially useful (all 5 new tables = keepers) and partially deferred to Phase 08 (channel_group and alert_rule CHECK fixes). FORWARD_PORT is more precise than PRESERVE because the migration script must explicitly call out that `channel_group` and `alert_rule` CHECK expansions are DEFERRED to Phase 08 (001_expand_channel_groups.sql), not included in this baseline.
- **No data loss risk**: The 5 added tables are purely additive. No existing table was altered, dropped, or had columns changed.

## Decision Tree Applied

- Drift severity (from schema-diff.md Risk Assessment): **MEDIUM**
- Does WIP drift contain useful structural changes Phase 08 would otherwise recreate? **YES** — 5 tables for operator workflow + Slack notifications are WIP drift that Phase 08 SCHEMA-01/02 does not plan to create
- Will Phase 08's migration (SCHEMA-01/02) supersede WIP drift? **YES partially** — Phase 08 will expand `channel_group` and `alert_rule` CHECKs (not present in WIP drift), but will NOT recreate the 5 structural tables
- Does ORM (models.py) already match the WIP state? **YES** — all 5 WIP tables match their `SQL_CREATE_*` constants in models.py exactly

Decision logic applied: WIP drift is structural AND partially overlaps with Phase 08 scope (Phase 08 owns CHECK fixes; WIP drift owns new tables) → **FORWARD_PORT** (author migration script capturing only the keeper tables; explicitly defer CHECK changes to Phase 08).

## Consequences

- **For Phase 08**: Phase 08 must assume the DB schema includes the 6 HEAD tables PLUS the 5 WIP tables (total 11 tables as in wip-schema.sql). The `channel_group` CHECK (`IN ('GOOGLE', 'OPEN_BIDDING')`) and `alert_rule` CHECK (`IN ('A0', 'A1', 'A2', 'A3')`) are still stale in both HEAD and WIP — Phase 08's first migration task is to expand both CHECKs via `001_expand_channel_groups.sql` running against the state produced by `000_wip_drift_baseline.sql`.
- **For the binary file `data/vna_alerts.db`**: The binary retains its ` M` (modified, unstaged) git status permanently. Phase 07 authors no `git add data/vna_alerts.db`. Phase 08's first task will operationally apply `000_wip_drift_baseline.sql` against `git show HEAD:data/vna_alerts.db` to produce a clean tracked starting point, then apply `001_expand_channel_groups.sql`.
- **For scripts/migrations/**: Task 5 will author `000_wip_drift_baseline.sql` capturing only the 5 new tables and their indexes. The `channel_group` and `alert_rule` CHECK expansions are explicitly deferred with a `-- DEFERRED to 001_expand_channel_groups.sql (Phase 08)` comment.

## Rollback Plan

- Phase 07 produces only text artifacts under `.planning/phases/07-db-wip-investigation/` and one `.sql` file under `scripts/migrations/`. All are reversible via `git revert` of the Phase 07 commits (task commits 6990249, cef9fd1, f94f4ea, and this task's commit).
- The binary DB file `data/vna_alerts.db` is NEVER staged by Phase 07. Its WIP state is preserved on disk exactly as it was before Phase 07 started (SHA256: 3f65d19d435f3fc1dad83cb2cfbfbd2cc0639fecb68cac27e5048a8c9d5d62b2).
