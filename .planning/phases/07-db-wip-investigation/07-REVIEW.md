---
phase: 07-db-wip-investigation
reviewed: 2026-04-22T21:15:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - scripts/migrations/000_wip_drift_baseline.sql
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-04-22T21:15:00Z
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Reviewed `scripts/migrations/000_wip_drift_baseline.sql`, a DDL-only migration
that forward-ports five tables (`alert_feedback`, `alert_assignments`,
`manual_interventions`, `alert_intervention_links`, `pending_notifications`)
and seven indexes captured as local drift in `data/vna_alerts.db`.

Overall the SQL is syntactically clean and functionally equivalent to the
eight `SQL_CREATE_*` strings for these tables in `backend/db/models.py` and
the corresponding entries in `SQL_CREATE_INDEXES`. No CHECK constraints,
column definitions, or FK definitions diverge between this migration and the
Python source-of-truth. Idempotency is achieved via `CREATE TABLE IF NOT
EXISTS` / `CREATE INDEX IF NOT EXISTS`, so re-running on a DB already at the
WIP state is a no-op.

Issues found are mostly about idempotency edge cases (BEGIN TRANSACTION +
IF NOT EXISTS interaction is fine, but the header comment claims a stricter
starting state than the script enforces), FK enforcement guarantees (SQLite
requires `PRAGMA foreign_keys=ON` at connection time, which the app sets in
`database.py` but the migration does not set for ad-hoc `sqlite3` CLI
invocations), and a few small quality items. No critical bugs and no
security concerns (DDL only, no dynamic values).

## Warnings

### WR-01: Idempotency claim in header comment is stricter than enforced

**File:** `scripts/migrations/000_wip_drift_baseline.sql:11-13`

**Issue:** The header states the migration "assumes it runs against a DB at
HEAD baseline". But the body uses `CREATE TABLE IF NOT EXISTS` throughout,
which is correct and permissive — it will succeed on a HEAD DB, a WIP DB,
or a fresh empty DB. The narrower precondition in the comment is misleading
for operators who will, in practice, run this against the WIP DB (to
normalize it into a replayable trail) and expect a no-op. If a future
reader takes the comment literally they may skip running it on WIP because
"we're already there", losing the point of forward-porting.

**Fix:** Loosen the comment to match the actual behavior, e.g.:

```sql
-- Idempotency: CREATE ... IF NOT EXISTS makes this migration safe to run
--   against any of: HEAD baseline DB, WIP DB (no-op), or a freshly
--   initialized DB. It adds 5 tables + 7 indexes if absent; skips what
--   already exists. It never alters existing tables.
```

### WR-02: Foreign key constraints are silently unenforced without PRAGMA foreign_keys=ON

**File:** `scripts/migrations/000_wip_drift_baseline.sql:43, 54, 86-87, 101`

**Issue:** SQLite, by default, parses and stores `FOREIGN KEY` declarations
but does NOT enforce them unless `PRAGMA foreign_keys=ON` is issued on the
connection. The application's runtime connection (`backend/db/database.py`
line 49) correctly sets this. But operators who apply this migration via
`sqlite3 data/vna_alerts.db < 000_wip_drift_baseline.sql` will get a
connection without the pragma, and — more importantly — any subsequent
ad-hoc `sqlite3` REPL session they use to probe the DB will also lack
enforcement. The four FK clauses and the `ON DELETE CASCADE` on
`pending_notifications` (line 101) will appear to work but will not reject
orphan inserts or cascade deletes in CLI use. This can mask data-integrity
bugs during manual verification.

**Fix:** Add a pragma at the top of the transaction so CLI applications
also enforce FKs while running the script:

```sql
BEGIN TRANSACTION;

-- Ensure FK checks fire during this migration (noop for app runtime which
-- already sets this in backend/db/database.py, but important for ad-hoc
-- sqlite3 CLI invocations).
PRAGMA foreign_keys = ON;
```

Note: per SQLite docs, `PRAGMA foreign_keys` cannot be changed inside a
transaction in some versions — if the runtime SQLite on the target is
affected, place the pragma before `BEGIN TRANSACTION;` instead.

### WR-03: pending_notifications uses ON DELETE CASCADE while sibling FK tables do not — cascade asymmetry

**File:** `scripts/migrations/000_wip_drift_baseline.sql:101`

**Issue:** `pending_notifications` is the ONLY FK in this migration with
`ON DELETE CASCADE`. `alert_feedback`, `alert_assignments`,
`alert_intervention_links`, and `manual_interventions` (via the link
table) all have plain FK references that default to `ON DELETE NO ACTION`.
This means deleting an `alerts` row with FKs ON would either fail (because
of `alert_feedback`/`alert_assignments`/`alert_intervention_links` rows
pointing to it) or — with FKs OFF, as per WR-02 — silently orphan those
rows while the `pending_notifications` rows vanish. The asymmetry likely
reflects intent ("notifications are queued, safe to drop when alert is
deleted; feedback is historical evidence, preserve it") but is not
documented anywhere in the file. For a reviewer six months from now the
mixed semantics will be surprising.

**Fix:** Add an inline comment above the `pending_notifications` FK
explaining the deliberate asymmetry, or confirm with the Phase 03/04
authors that feedback/assignments/intervention-links should also cascade
on alert deletion:

```sql
-- ON DELETE CASCADE is intentional here: queued notifications are
-- ephemeral and should be dropped if the source alert is removed.
-- Feedback/assignments/interventions use the default NO ACTION because
-- they are historical audit data that must outlive the parent alert.
FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
```

## Info

### IN-01: manual_interventions.intervention_id lacks an index but is referenced by alert_intervention_links

**File:** `scripts/migrations/000_wip_drift_baseline.sql:81-89`

**Issue:** `alert_intervention_links.intervention_id` has a FK reference to
`manual_interventions(intervention_id)`. There is an index on
`alert_intervention_links.alert_id` (line 89) which covers joins from the
alerts side, but no reverse index on
`alert_intervention_links.intervention_id`. If the dashboard ever lists
"alerts linked to this intervention" it will force a full scan on the
junction table.

**Fix:** Consider adding, if that query path is expected:

```sql
CREATE INDEX IF NOT EXISTS idx_intervention_links_intervention
    ON alert_intervention_links(intervention_id);
```

Only add if Phase 08 or later actually needs the query path — do not
pre-index speculatively. Per-project convention is to index on demand.

### IN-02: pending_notifications would benefit from an index on alert_id for FK maintenance

**File:** `scripts/migrations/000_wip_drift_baseline.sql:94-103`

**Issue:** With `ON DELETE CASCADE` on `pending_notifications(alert_id)`,
SQLite will execute a lookup on `alert_id` every time an `alerts` row is
deleted. The only index on this table is on `created_at`. An index on
`alert_id` would both speed up cascade deletes and support the likely
"notifications for this alert" query path.

**Fix:** Consider:

```sql
CREATE INDEX IF NOT EXISTS idx_pending_notifications_alert_id
    ON pending_notifications(alert_id);
```

Optional — flag only. The table is likely small (it's a pending queue
cleared by the digest runner), so the current scheme is acceptable.

### IN-03: `timestamp` columns typed as TEXT without format comment

**File:** `scripts/migrations/000_wip_drift_baseline.sql:42, 53, 61, 75, 85, 99, 100`

**Issue:** Multiple `timestamp` / `*_at` columns are declared `TEXT NOT
NULL` but the expected format (ISO-8601 UTC) is not asserted in a CHECK
and not documented in a column comment. The rest of the codebase stores
ISO-8601 strings (Python `datetime.utcnow().isoformat()`), but nothing in
this DDL prevents an operator from inserting `'yesterday'`. The existing
`alerts` and `alert_events` tables in HEAD have the same weakness, so this
migration is consistent with prior art — flagging for Phase 08 to consider
project-wide rather than blocking this one.

**Fix:** Low priority. If tightening is desired in a future migration,
either add `CHECK(timestamp LIKE '____-__-__T__:__:__%')` or introduce a
`CURRENT_TIMESTAMP` default. Skip for now to preserve parity with existing
tables.

### IN-04: Rollback block lists tables in reverse-create order but comments encourage .bak restore instead

**File:** `scripts/migrations/000_wip_drift_baseline.sql:109-117`

**Issue:** The rollback block is provided but immediately followed by a
comment ("In practice, prefer restoring from backup .db file") that
discourages its use. The rollback as written drops five tables in an order
that respects FK dependencies (`alert_intervention_links` before
`manual_interventions`, all leaf tables before `alerts`-referencing
tables) — this is correct. However, if an operator follows the "prefer
.bak" advice, the SQL rollback drifts out of sync with reality over time
as Phase 08+ adds more tables that should also be dropped on rollback.

**Fix:** Either (a) remove the SQL rollback block and rely solely on the
.bak restore path, or (b) keep the SQL rollback and remove the "prefer
.bak" nudge, since having two competing rollback procedures where one is
labeled "don't actually use this" is worse than picking one. Recommend
(b) — the SQL rollback is the audit trail, the .bak is the fast path.
Reword the comment to:

```sql
-- The SQL above is the canonical rollback for this migration alone.
-- For faster recovery when multiple migrations need to be unwound,
-- restore data/vna_alerts.db.bak* (the .bak naming matches the
-- pre-migration snapshot taken by Phase 07).
```

---

_Reviewed: 2026-04-22T21:15:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
