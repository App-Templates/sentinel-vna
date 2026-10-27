---
phase: 07-db-wip-investigation
plan: 01
subsystem: database
tags: [sqlite, schema-migration, drift-analysis, silent-failure, channel-group]

# Dependency graph
requires:
  - phase: 01-alerting-evoluto
    provides: alert_events, recheck_queue, pipeline_runs tables (HEAD baseline)
  - phase: 03-operator-workflow
    provides: alert_feedback, alert_assignments, manual_interventions, alert_intervention_links tables (WIP drift)
  - phase: 04-notifiche-slack
    provides: pending_notifications table (WIP drift)
provides:
  - wip-schema.sql: text schema dump of WIP data/vna_alerts.db (11 tables, 13 indexes)
  - head-schema.sql: text schema dump of git HEAD baseline (6 tables, 6 indexes)
  - schema-diff.md: structured drift report identifying 5 new tables in WIP
  - models-py-check.md: ORM cross-check confirming channel_group + alert_rule CHECK staleness
  - DECISION.md: FORWARD_PORT decision with traced rationale
  - scripts/migrations/000_wip_drift_baseline.sql: idempotent migration for Phase 03/04 WIP drift
affects:
  - 08-schema-migration (must start from 11-table baseline; owns channel_group + alert_rule CHECK fixes)
  - 09-backfill (must wait for Phase 08 CHECK expansion before re-running pipeline)

# Tech tracking
tech-stack:
  added: [sqlite3 CLI readonly schema dump, shasum SHA256 traceability]
  patterns:
    - "Migration baseline pattern: WIP drift captured as idempotent DDL before schema work begins"
    - "Read-only investigation: sqlite3 -readonly .schema for DDL extraction, never .dump"
    - "Temp file isolation: git show HEAD:db > $(mktemp) + trap EXIT for HEAD blob extraction"

key-files:
  created:
    - .planning/phases/07-db-wip-investigation/wip-schema.sql
    - .planning/phases/07-db-wip-investigation/head-schema.sql
    - .planning/phases/07-db-wip-investigation/schema-diff.md
    - .planning/phases/07-db-wip-investigation/models-py-check.md
    - .planning/phases/07-db-wip-investigation/DECISION.md
    - scripts/migrations/000_wip_drift_baseline.sql
  modified: []

key-decisions:
  - "FORWARD_PORT: WIP DB contains 5 Phase 03/04 structural tables not in HEAD; these are keeper features, not superseded by Phase 08; migration script authored to track them"
  - "alert_rule CHECK also stale: DB has A0-A3 only vs models.py A0-A7; Phase 08 must fix both channel_group AND alert_rule CHECKs"
  - "channel_group CHECK NOT locally patched in WIP: both HEAD and WIP have same stale GOOGLE+OPEN_BIDDING only; WIP drift is additive table drift only"

patterns-established:
  - "Phase investigation pattern: dump WIP schema, dump HEAD schema, diff, cross-check ORM, decide, author migration baseline — all read-only on DB binary"
  - "Migration naming: 000_wip_drift_baseline.sql (baseline) → 001_expand_channel_groups.sql (Phase 08)"

requirements-completed: [WIP-01]

# Metrics
duration: 15min
completed: 2026-04-22
---

# Phase 07 Plan 01: DB WIP Investigation Summary

**FORWARD_PORT decision: WIP DB has 5 Phase 03/04 tables not in HEAD git baseline; channel_group CHECK stale in both WIP and HEAD; migration 000_wip_drift_baseline.sql authored to unblock Phase 08**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-22T20:52:00Z
- **Completed:** 2026-04-22T21:10:00Z
- **Tasks:** 5 of 5
- **Files modified/created:** 6

## Decision

**FORWARD_PORT**

The WIP `data/vna_alerts.db` contains 5 structural tables (Phase 03/04 operator workflow + Slack notifications) that are not present in the git HEAD baseline and are not planned for Phase 08. A tracked migration `scripts/migrations/000_wip_drift_baseline.sql` was authored to capture this drift as a replayable, reviewable SQL artifact.

## Key Findings

- **WIP has 5 extra tables vs HEAD**: `alert_feedback`, `alert_assignments`, `manual_interventions`, `alert_intervention_links`, `pending_notifications` — all matching `backend/db/models.py` SQL constants exactly. Phase 03/04 work was applied locally to the DB binary without a tracked migration.
- **Intel hypothesis confirmed**: `channel_group` CHECK is `IN ('GOOGLE', 'OPEN_BIDDING')` in BOTH WIP and HEAD. The WIP did NOT locally patch the 7-channel expansion. SCHEMA-01 starts from scratch.
- **Second silent-failure vector found**: `alert_rule` CHECK in both DBs is `IN ('A0', 'A1', 'A2', 'A3')` but `models.py SQL_CREATE_ALERTS` declares `IN ('A0', 'A1', 'A2', 'A3', 'A5', 'A6', 'A7')`. A5/A6/A7 INSERTs fail silently — Phase 08 must fix this too.
- **Read-only invariant confirmed**: `data/vna_alerts.db` retains ` M` (space-M, unstaged modified) status throughout. No staging, no writing, no altering of the binary.
- **Migration validates cleanly**: `sqlite3 :memory: < 000_wip_drift_baseline.sql` exits 0; applies against full base schema without error.

## Artifacts Produced

| Artifact | Path | Purpose |
|----------|------|---------|
| wip-schema.sql | `.planning/phases/07-db-wip-investigation/wip-schema.sql` | WIP DB DDL (11 tables, 13 indexes, SHA256 traceability) |
| head-schema.sql | `.planning/phases/07-db-wip-investigation/head-schema.sql` | HEAD baseline DDL (6 tables, 6 indexes, blob hash) |
| schema-diff.md | `.planning/phases/07-db-wip-investigation/schema-diff.md` | Structured drift report with unified diff |
| models-py-check.md | `.planning/phases/07-db-wip-investigation/models-py-check.md` | ORM cross-check, comparison matrix, implication for Phase 08 |
| DECISION.md | `.planning/phases/07-db-wip-investigation/DECISION.md` | FORWARD_PORT decision, rationale, consequences |
| 000_wip_drift_baseline.sql | `scripts/migrations/000_wip_drift_baseline.sql` | Idempotent DDL for 5 WIP tables; defers CHECK fixes to Phase 08 |

## Task Commits

1. **Task 1: Dump WIP DB schema** - `6990249` (feat)
2. **Task 2: Dump HEAD baseline DB schema** - `cef9fd1` (feat)
3. **Task 3: Schema drift report and models.py cross-check** - `f94f4ea` (feat)
4. **Task 4: Record FORWARD_PORT decision** - `8b2de30` (feat)
5. **Task 5: Author 000_wip_drift_baseline.sql migration** - `fa0736e` (feat)

## Phase 08 Handoff

Phase 08 (SCHEMA-01/02) must start by applying `000_wip_drift_baseline.sql` against `git show HEAD:data/vna_alerts.db` to reach the 11-table starting state. Then `001_expand_channel_groups.sql` must expand BOTH the `channel_group` CHECK (to all 7 v1.2 channels: GOOGLE_ADEX, DEAL, DIRECT, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, OPEN_BIDDING) AND the `alert_rule` CHECK (add A5, A6, A7), plus sync `ChannelGroup` enum and `SQL_CREATE_ALERTS` in `backend/db/models.py`.

## Decisions Made

- **FORWARD_PORT over PRESERVE**: More precise — explicitly calls out that channel_group/alert_rule CHECK changes are DEFERRED to Phase 08, preventing confusion about what 000 covers vs what 001 covers.
- **alert_rule additional finding documented**: Not in original intel scope, discovered during ORM cross-check. Surfaced in schema-diff.md and models-py-check.md for Phase 08 awareness.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] sqlite3 -readonly failed on main repo DB path**
- **Found during:** Task 1 (initial DB verification)
- **Issue:** `sqlite3 -readonly /Users/.../value-network-alerting/data/vna_alerts.db` returned error code 14 (unable to open DB file) due to WAL mode contention with the WAL files shared across the symlinked worktree path vs main repo path.
- **Fix:** Used the worktree-local absolute path instead (`$WT/data/vna_alerts.db`). Verified mtime unchanged after read — read-only invariant confirmed.
- **Files modified:** N/A (command adjustment only)
- **Committed in:** `6990249` (Task 1 commit)

**2. [Rule 3 - Blocking] Worktree working tree diverged from HEAD at execution start**
- **Found during:** Pre-execution setup
- **Issue:** Worktree branch was at commit `7ca7808` (older branch state) but expected base was `ac599fa`. After `git reset --soft`, working tree still reflected old state; `07-db-wip-investigation/` directory was not present in working tree.
- **Fix:** Extracted plan file and intel files from HEAD via `git show HEAD:<path>`. Confirmed intel files matched HEAD blob hashes (no content modification). Proceeded with correct execution context.
- **Files modified:** N/A (recovery only; no plan artifacts affected)
- **Committed in:** N/A (pre-execution recovery)

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking issues, neither affecting plan outputs)
**Impact on plan:** Zero scope creep. Both fixes were path/environment issues resolved without altering any plan artifact content.

## Issues Encountered

- `ugrep` aliased as `grep` on this macOS system causes issues with `--` style options; used `python3 -c "... in content"` for string membership checks throughout verification steps. No impact on correctness.

## Read-Only Invariant Confirmed

`data/vna_alerts.db` status at plan completion: ` M data/vna_alerts.db` (space-M = unstaged modified). File never staged, never written, never altered. SHA256 before/after matches `3f65d19d435f3fc1dad83cb2cfbfbd2cc0639fecb68cac27e5048a8c9d5d62b2`.

## Next Phase Readiness

- Phase 08 (SCHEMA-01/02) is unblocked: all inputs available in schema-diff.md + DECISION.md + models-py-check.md
- Migration sequence defined: `000_wip_drift_baseline.sql` (this plan) → `001_expand_channel_groups.sql` (Phase 08)
- No blockers or concerns for Phase 08 start

---
*Phase: 07-db-wip-investigation*
*Completed: 2026-04-22*
