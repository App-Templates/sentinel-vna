---
phase: 09-alert-backfill-legacy-migration
reviewed: 2026-04-23T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - .gitignore
  - backend/agents/orchestrator.py
  - backend/api/routes.py
  - backend/api/schemas.py
  - backend/db/models.py
  - backend/db/operations.py
  - backend/utils/config_loader.py
  - scripts/apply_migration_002.py
  - scripts/backfill_alerts.py
  - scripts/deprecate_legacy_alerts.py
  - scripts/migrations/002_add_alert_deprecation.sql
  - scripts/migrations/002_rollback.sql
  - scripts/test_backfill_alerts.py
  - scripts/test_deprecate_legacy_alerts.py
  - scripts/test_migration_002_apply.py
  - scripts/test_models_sync.py
  - scripts/test_operations_idempotency.py
findings:
  critical: 0
  warning: 4
  info: 7
  total: 11
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-04-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 09 introduces an additive `deprecated INTEGER NOT NULL DEFAULT 0` + `deprecation_reason TEXT` schema change, soft-deprecates 200 legacy alerts, and adds a 1,440-tuple backfill orchestrator. Overall the work is **strongly engineered**:

- Migration 002 (forward + rollback) follows the Phase 08 incident-learning pattern (PRAGMA before BEGIN, ledger-INSERT-without-OR-REPLACE as idempotency guard, byte-identity drift gate via `test_models_sync.py`).
- The apply driver is a textbook chirurgico-10/10 implementation: lsof + flock + .bak via `sqlite3.Connection.backup()` + 4-stage post-apply verification + auto-restore on failure.
- The deprecate script's belt-and-suspenders filter (`timestamp < FIXED_DATE AND channel_group IN (...)`) plus `AND deprecated = 0` makes it provably idempotent.
- The backfill orchestrator's HH-offset disambiguation (`channel_idx * 3 + trigger_idx ∈ [0, 23]`) cleanly avoids alert_id collisions.
- Test suites are comprehensive (idempotency, fixture cleanup, leak detection, byte-identity, CHECK enforcement).

**No Critical issues found.** Four Warnings concern (1) `INSERT OR IGNORE` silently swallowing CHECK/NOT NULL violations beyond duplicate PKs in `create_alert`, (2) the backfill orchestrator setting `alert_written=True` purely on pipeline state without confirming actual DB persistence, (3) `config_loader.py` making three new v1.2 sections strictly required (no defaults) which contradicts the brief's "defensive handling of missing v1.2 sections" expectation, and (4) the backfill checkpoint exit-code logic that can keep returning 1 across resumes even after all remaining tuples succeed.

Info items cover dead code paths, fragile test assertions, naming/duplication, and a future-extension hazard in the HH-offset formula.

## Warnings

### WR-01: `INSERT OR IGNORE` silently swallows CHECK / NOT NULL constraint failures, not only duplicate PKs

**File:** `backend/db/operations.py:33-69`

**Issue:** Per SQLite docs, `INSERT OR IGNORE` suppresses **all** applicable constraint violations (UNIQUE, NOT NULL, CHECK), not only PK conflicts. The function's docstring frames the IGNORE behavior solely as "duplicate alert_id is silent no-op (D-07 idempotency contract)", and `create_alert` returns `alert.alert_id` unconditionally. If a future caller passes an `AlertModel` whose `channel_group` / `alert_rule` / `severity` value falls outside the CHECK domain (e.g., a typoed enum, or a row constructed by hand for tests), the INSERT silently no-ops — no row exists, no exception, and the function returns the alert_id as if the insert succeeded. The `test_operations_idempotency.py` suite proves duplicate-PK behavior but does NOT prove that a CHECK violation surfaces. This is a load-bearing primitive (the LIVE pipeline + the backfill orchestrator both rely on it) and the silent-failure mode is exactly the class Phase 08 established the drift gate to prevent.

**Fix:** Either (a) tighten the contract — keep `OR IGNORE`, but also call `cursor.rowcount` and log a WARNING when `rowcount == 0` and the row is not present afterwards (i.e., distinguish "duplicate PK silent skip" from "CHECK violation silent skip"); or (b) split idempotency into an explicit pre-check + plain `INSERT` so non-PK constraint violations surface as `sqlite3.IntegrityError`:

```python
def create_alert(alert: AlertModel) -> str:
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO alerts (...) VALUES (...)""",
            (...),
        )
        if cursor.rowcount == 0:
            # Either duplicate PK (idempotent skip) OR a CHECK/NOT NULL silent-fail.
            # Disambiguate by reading back.
            existing = conn.execute(
                "SELECT 1 FROM alerts WHERE alert_id = ?", (alert.alert_id,)
            ).fetchone()
            if existing is None:
                raise sqlite3.IntegrityError(
                    f"create_alert: row for {alert.alert_id} not present after "
                    f"INSERT OR IGNORE — likely CHECK/NOT NULL violation"
                )
            logger.debug("create_alert: duplicate PK %s — idempotent skip", alert.alert_id)
    return alert.alert_id
```

Also add a unit test in `test_operations_idempotency.py` that constructs an `AlertModel` bypassing Pydantic validation (e.g., via `model_construct`) with an out-of-domain `channel_group` and asserts the call raises rather than silently returning.

---

### WR-02: Backfill orchestrator sets `alert_written = True` without verifying the row actually persisted

**File:** `scripts/backfill_alerts.py:256-260`

**Issue:** The orchestrator's success-path is:

```python
if final_state.get("alert_triggered"):
    alert_model = _build_alert_model_from_state(final_state, ts_iso)
    create_alert(alert_model)  # INSERT OR IGNORE
    alert_written = True
    alert_id_for_log = alert_model.alert_id
```

`alert_written` is set purely on the absence of an exception from `create_alert`. Combined with WR-01, a silently-skipped INSERT (CHECK violation OR pre-existing PK from a re-run with `--force` after partial success) is recorded as `status="success"` in `pipeline_runs` and as a completed tuple in the checkpoint, even though no new row was written. This makes the post-backfill `COUNT(*) FROM alerts WHERE data_source='backfill'` an unreliable verification metric.

**Fix:** Change `create_alert` to return a richer signal (e.g., `(alert_id, was_inserted: bool)` tuple) and propagate. Minimum:

```python
# in operations.py
def create_alert(alert: AlertModel) -> tuple[str, bool]:
    with get_db() as conn:
        cursor = conn.execute("""INSERT OR IGNORE INTO alerts ...""", (...))
        was_inserted = cursor.rowcount == 1
    return alert.alert_id, was_inserted

# in backfill_alerts.py
alert_id_for_log, was_inserted = create_alert(alert_model)
alert_written = was_inserted
```

This also fixes the `--force` re-run case where 1,440 rows already exist: orchestrator would otherwise re-mark them all as "success" without inserting anything.

---

### WR-03: `AlertingConfig` v1.2 sections are strictly required, no defaults — contradicts "defensive handling" goal

**File:** `backend/utils/config_loader.py:202-226`

**Issue:** The three new v1.2 sections (`leading_indicator`, `cross_channel_detection`, `gross_margin_alert`) are declared as required `BaseModel` fields without `Optional[...]` or `Field(default=...)`. If `config/alerting_rules.yaml` is missing any of these sections (legitimate scenarios: rollback to v1.1 YAML, fresh-clone before YAML update, partial deploy), `AlertingConfig(**raw)` raises `pydantic.ValidationError`. The orchestrator (`backend/agents/orchestrator.py:57-62`) wraps `get_config()` in try/except and degrades to `config_version="unknown"` plus an `execution_errors` entry — but other call sites (anomaly_detector, scheduler) likely do NOT, so a missing section becomes a hard crash mid-pipeline. The brief explicitly lists "defensive handling of missing v1.2 YAML sections" as a concern; this implementation is fail-fast, not defensive.

The class docstrings explicitly state these were added to fix a silent-drift bug (`anomaly_detector.py:641` reading `config.leading_indicator` while Pydantic was stripping the section). That fix is correct in intent — but making the field strictly required swings the pendulum the other way: drift now → instant crash on every pipeline run with an outdated YAML.

**Fix:** Provide explicit defaults so a missing section degrades to a sensible "feature off" rather than a crash:

```python
class LeadingIndicatorConfig(BaseModel):
    enabled: bool = False
    metrics: list[str] = []
    drop_threshold_pct: float = 0.0
    baseline_weeks: int = 7
    severity: str = "P2"

# in AlertingConfig:
leading_indicator: LeadingIndicatorConfig = Field(default_factory=LeadingIndicatorConfig)
cross_channel_detection: CrossChannelDetectionConfig = Field(default_factory=CrossChannelDetectionConfig)
gross_margin_alert: GrossMarginAlertConfig = Field(default_factory=GrossMarginAlertConfig)
```

The drift-detector role is better served by a separate explicit assertion in startup (or in `test_models_sync.py`) that the YAML actually contains the sections — failing config validation loudly there, not at every pipeline run.

---

### WR-04: Backfill exit code reflects accumulated `failed_tuples` from prior runs, not current run outcome

**File:** `scripts/backfill_alerts.py:300`

**Issue:** `sys.exit(1 if state["failed_tuples"] else 0)` reads the persisted checkpoint's `failed_tuples` list, which accumulates across all `_save_checkpoint` calls. If run #1 has 5 failed tuples, then run #2 (resume) successfully completes the remaining work (zero new failures), the script still exits 1 — because `state["failed_tuples"]` is non-empty from run #1. CI / cron / monitoring will treat the resume as failure even though it's the desired terminal state. D-06 says "non-zero on any failure" but conflates within-run failure with historical failure.

**Fix:** Track `failed_now` separately (already computed at line 230) and base exit code on it:

```python
# Replace line 300:
sys.exit(1 if failed_now > 0 else 0)
```

If the intent really is "any historical failure means caller must retry / inspect", document this explicitly in the script header AND emit a clearer message:

```python
if state["failed_tuples"]:
    logger.warning(
        "Exiting non-zero: %d historical failures persisted in checkpoint "
        "(this run added %d). Inspect %s before treating backfill as complete.",
        len(state["failed_tuples"]), failed_now, args.checkpoint_path,
    )
    sys.exit(1)
sys.exit(0)
```

---

## Info

### IN-01: `_apply_lock_fd` / `_lock_fd` rely on process-exit cleanup, not explicit release

**File:** `scripts/apply_migration_002.py:379` and `scripts/deprecate_legacy_alerts.py:151`

**Issue:** Both scripts acquire an `fcntl.LOCK_EX` flock and bind the fd to a `# noqa: F841 — held for lock duration` local. The lock is correctly released by the OS on process exit (every code path leads to `sys.exit(...)`), but a future refactor that converts `main()` into a callable invoked from another script would lose the implicit release semantics. The pattern works as-is but is invisible to readers.

**Fix:** Document the contract more loudly with a wrapping context manager, OR add an explicit `try / finally: fd.close()` at the end of `main()` so the cleanup is structural rather than incidental. Even a one-line `atexit.register(fd.close)` is more explicit than the current `# noqa`.

---

### IN-02: `_already_applied()` raises `RuntimeError` with no caller try/except — top-level traceback on partial state

**File:** `scripts/apply_migration_002.py:153-157` and `382-388`

**Issue:** When the partial-state branch fires (`cols_present != ledger_present`), the raised `RuntimeError` propagates uncaught from `main()`, producing a Python traceback rather than a clean log line + non-zero exit. Operationally this is a hostile UX for the Stefano-typed "partial state requires manual inspection" scenario the rule is designed to surface.

**Fix:** Wrap the call:

```python
try:
    already_done = _already_applied(conn)
except RuntimeError as exc:
    _log(f"FATAL: {exc}")
    sys.exit(1)
finally:
    conn.close()
```

---

### IN-03: `_build_alert_model_from_state` — `ts_iso.replace("Z", "+00:00")` is a no-op for backfill-generated timestamps

**File:** `scripts/backfill_alerts.py:117`

**Issue:** `ts_iso` is built at line 237 as `ts_dt.isoformat()` where `ts_dt` carries `tzinfo=timezone.utc`. Python's `datetime.isoformat()` produces `+00:00` for UTC, never `Z`. The `.replace("Z", "+00:00")` is therefore dead code in the backfill path. Harmless (in fact useful if the adapter is reused for other ts_iso shapes) but worth documenting.

**Fix:** Either drop the replace, or add a comment noting that the adapter is also reused for ISO strings containing "Z" (e.g., from external callers / stored payloads). One-line clarification.

---

### IN-04: Fragile assertion in `test_dry_run_does_not_write` — `assertIn("3", stdout)` matches noise

**File:** `scripts/test_deprecate_legacy_alerts.py:210`

**Issue:** `self.assertIn("3", result.stdout)` will match substrings of timestamps in the `[HH:MM:SS]` log prefix (e.g., `[13:45:23]`), the candidate-row count message, or any incidental "3" in stdout. The test passes because the dry-run output also legitimately contains "3", but the assertion is not actually verifying what it claims.

**Fix:**

```python
self.assertIn("3 rows would be deprecated", result.stdout)
```

This matches the actual phrase printed by `deprecate_legacy_alerts.py:163-165`.

---

### IN-05: `_run_main` has unreachable return — `bf.main()` always calls `sys.exit()`

**File:** `scripts/test_backfill_alerts.py:142-146`

**Issue:** `backfill_alerts.main()` ends every code path with `sys.exit(...)`, so the `return 0` after `bf.main()` is dead code. Doesn't cause a failure but is misleading.

**Fix:** Drop the `return 0` line, or change `_run_main` docstring to `"Always raises SystemExit; returns the exit code."`.

---

### IN-06: HH-offset formula has implicit upper bound at 23 — silent breakage on TRIGGERS extension

**File:** `scripts/backfill_alerts.py:235`

**Issue:** `hh = CHANNELS.index(channel) * len(TRIGGERS) + TRIGGERS.index(trigger)` produces values in `[0, len(CHANNELS) * len(TRIGGERS) - 1]` = `[0, 23]` today (8 × 3). If a future Phase adds a 4th trigger or a 9th channel, hh exceeds 23 and `datetime(d.year, d.month, d.day, hh, ...)` raises `ValueError: hour must be in 0..23`. Comment at lines 232-234 mentions the constraint but no assertion guards it.

**Fix:** Add an assertion at module load or at the top of `main()`:

```python
assert len(CHANNELS) * len(TRIGGERS) <= 24, (
    f"HH-offset formula assumes channels*triggers <= 24 (got "
    f"{len(CHANNELS)}*{len(TRIGGERS)}={len(CHANNELS)*len(TRIGGERS)})"
)
```

Cheaper than discovering it at tuple #25 in a 1,440-tuple backfill.

---

### IN-07: `assigned_to` validation duplicated between Pydantic regex and route-level `endswith` check

**File:** `backend/api/schemas.py:193` and `backend/api/routes.py:316-317`

**Issue:** `AssignRequest.assigned_to` is constrained by the regex `^[a-zA-Z0-9._%+-]+@adkaora\.com$` at the Pydantic boundary. `routes.py:316-317` then re-checks `if not body.assigned_to.endswith("@adkaora.com")`. The Pydantic constraint is strictly stronger (it also bans subdomains like `evil@sub.adkaora.com.attacker.tld`), so the route-level check is redundant and slightly weaker.

**Fix:** Drop lines 316-317 from `routes.py` — the schema validation already enforces the contract and produces a 422 with a clearer error message. Less code, single source of truth.

---

---

_Reviewed: 2026-04-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
