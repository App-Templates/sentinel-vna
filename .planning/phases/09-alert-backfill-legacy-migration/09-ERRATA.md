# Phase 09 — ERRATA + Binding Overrides (post plan-checker 2026-04-23)

> **BINDING:** this file OVERRIDES the three PLAN.md files for the sections cited.
> Executors (gsd-executor, x9-builder, human) MUST read this FIRST and apply these
> overrides before following the plan body. The plan bodies are preserved as reference;
> any conflict is resolved in favor of ERRATA.

**Origin:** `gsd-plan-checker` verification returned 5 BLOCKER + 4 WARNING + 3 INFO
findings against baseline plans committed at `eae26db`. See DISCUSSION-LOG for the
full checker report. Below are the binding resolutions.

---

## B-1 — Backfill MUST persist alerts explicitly

**Affected:** `09-03-PLAN.md` Task 1 (lines 449-454, script body).

**Root cause:** `backend.workflow.graph.run_pipeline()` returns `AlertState` but does NOT call `create_alert()`. The only existing persistence path is `backend/backtest/runner_real.py:253-279`. The baseline plan Task 1 invokes `run_pipeline(...)` but ignores the return — backfill would produce **0 rows**, failing BACKFILL-01 Success #1.

**Override for 09-03 Task 1 script body** — replace the current per-tuple block in `scripts/backfill_alerts.py` main loop (current lines 444-464 of the plan's embedded script) with the block below. **Two code corrections vs ERRATA v1 (2026-04-23 iteration-2 checker findings NEW-B-6 + NEW-B-7):**

- **NEW-B-6 fix:** `record_pipeline_run(...)` uses canonical positional args per `backend/db/operations.py:250-262` — required params: `run_id, timestamp, channel_group, trigger_type, mode, status, duration_sec`; optional: `alert_id=`, `error_message=`. Previous draft passed non-existent kwargs (`alert_triggered=`, `errors=`) and omitted `status=`.
- **NEW-B-7 fix:** `generate_alert_id(severity, ts)` (models.py:190) is deterministic on `(severity, ts)` ONLY — all tuples on the same day at `00:00:00` would collide. Per-tuple `HH = CHANNELS.index(channel) * 3 + TRIGGERS.index(trigger)` yields 24 distinct HH/day → 24 distinct alert_ids/day per severity (deterministic, reproducible, bijective).

```python
from datetime import datetime, timezone
from backend.db.models import (
    AlertModel, AlertRule, AlertStatus, ChannelGroup, Severity, generate_alert_id,
)
from backend.db.operations import create_alert, record_pipeline_run
import json, time, uuid

# inside the per-tuple loop:
for i, (d, channel, trigger) in enumerate(remaining, 1):
    # NEW-B-7: disambiguate alert_id collisions by varying HH per (channel, trigger).
    # 8 channels × 3 triggers = 24 unique HH/day → distinct ts → distinct alert_id.
    hh = CHANNELS.index(channel) * len(TRIGGERS) + TRIGGERS.index(trigger)  # [0, 23]
    ts_dt = datetime(d.year, d.month, d.day, hh, 0, 0, tzinfo=timezone.utc)
    ts_iso = ts_dt.isoformat()
    key = _tuple_key(d, channel, trigger)
    run_id = f"bf-{uuid.uuid4().hex[:8]}"
    t0 = time.time()
    alert_written = False
    alert_id_for_log: "str | None" = None
    err_message: "str | None" = None
    try:
        logger.debug("[%d/%d] %s hh=%02d", i, len(remaining), key, hh)
        final_state = run_pipeline(
            trigger_type=trigger,
            channel_group=channel,
            mode="BACKTEST",
            timestamp=ts_iso,
        )
        duration = round(time.time() - t0, 3)

        # D-01/D-03 persist: run_pipeline returns AlertState but does NOT write.
        # Orchestrator is responsible for create_alert + record_pipeline_run.
        if final_state.get("alert_triggered"):
            alert_model = _build_alert_model_from_state(final_state, ts_iso)
            create_alert(alert_model)   # INSERT OR IGNORE — see §B-2
            alert_written = True
            alert_id_for_log = alert_model.alert_id

        errs = final_state.get("execution_errors") or []
        if errs:
            err_message = "; ".join(str(e) for e in errs)[:500]

        status = (
            "failed" if errs else ("success" if alert_written else "no_alert")
        )
        # NEW-B-6: canonical record_pipeline_run signature (operations.py:250-262).
        record_pipeline_run(
            run_id,                    # run_id
            ts_iso,                    # timestamp
            channel,                   # channel_group
            trigger,                   # trigger_type
            "BACKTEST",                # mode
            status,                    # status
            duration,                  # duration_sec
            alert_id=alert_id_for_log,
            error_message=err_message,
        )

        state["completed"].append(key)
        succeeded += 1
    except Exception as exc:
        logger.error("FAIL %s: %s", key, exc)
        state["failed_tuples"].append({"key": key, "error": str(exc)[:500]})
        # Still record the failed run for observability (best-effort; ignore record failures).
        try:
            record_pipeline_run(
                run_id, ts_iso, channel, trigger, "BACKTEST",
                "failed", round(time.time() - t0, 3),
                error_message=str(exc)[:500],
            )
        except Exception:
            pass
        failed_now += 1
    if i % 20 == 0 or i == len(remaining):
        _save_checkpoint(args.checkpoint_path, state)
```

Add this helper to the script (adapter between `AlertState` and `AlertModel`):

```python
def _build_alert_model_from_state(state: dict, ts_iso: str) -> "AlertModel":
    """Adapter: AlertState (nested dict from report_builder) → AlertModel (flat ORM).

    Source of truth for the nested shape: backend/agents/report_builder.py:23-61
    (_build_alert_payload). We extract the flat fields AlertModel expects.
    """
    from datetime import datetime
    payload = state.get("alert_payload") or {}
    revenue = payload.get("revenue") or {}
    ts = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))

    severity_raw = state.get("severity") or payload.get("severity") or "P2"
    try:
        severity_enum = Severity[severity_raw]
    except KeyError:
        severity_enum = Severity.P2

    # channel_group may be a string or enum depending on pipeline path
    ch_raw = state.get("channel_group") or payload.get("channel_group") or "GOOGLE_ADEX"
    try:
        channel_enum = ChannelGroup(ch_raw)
    except ValueError:
        channel_enum = ChannelGroup.GOOGLE_ADEX

    rule_raw = state.get("alert_rule") or payload.get("alert_rule") or "A1"
    try:
        rule_enum = AlertRule(rule_raw)
    except ValueError:
        rule_enum = AlertRule.A1

    alert_id = generate_alert_id(severity_enum, ts)
    return AlertModel(
        alert_id=alert_id,
        timestamp=ts,
        severity=severity_enum,
        channel_group=channel_enum,
        status=AlertStatus.OPEN,
        alert_rule=rule_enum,
        revenue_current=round(float(revenue.get("current") or 0), 2),
        revenue_baseline=round(float(revenue.get("baseline") or 0), 2),
        revenue_delta_pct=round(float(revenue.get("delta_pct") or 0), 2),
        triage_label=state.get("triage_label") or payload.get("triage_label") or "UNKNOWN",
        contributors_json=json.dumps(payload.get("contributors") or []),
        geo_breakdown_json=json.dumps(payload.get("geo_breakdown") or []),
        environment_split_json=json.dumps(payload.get("environment_split") or {}),
        insights_json=json.dumps(payload.get("insights") or {}),
        execution_time_sec=round(float(state.get("execution_time_sec") or 0), 3),
        data_source="backfill",
        config_version=state.get("config_version") or "1.0.0",
        created_at=ts,
        updated_at=ts,
    )
```

**Additional test** (add to `scripts/test_backfill_alerts.py`, test #13):

```python
def test_persists_alert_when_run_pipeline_triggers(self):
    """B-1 fix: verify the orchestrator actually calls create_alert."""
    fake_state = {
        "alert_triggered": True,
        "timestamp": "2026-02-01T12:00:00+00:00",
        "severity": "P1",
        "channel_group": "GOOGLE_ADEX",
        "alert_rule": "A1",
        "triage_label": "TEST",
        "alert_payload": {
            "revenue": {"current": 100.0, "baseline": 200.0, "delta_pct": -50.0},
            "contributors": [],
            "geo_breakdown": [],
            "environment_split": {},
            "insights": {},
        },
        "execution_errors": [],
    }
    with mock.patch("backend.workflow.graph.run_pipeline", return_value=fake_state):
        # init test DB via backend.db.database.init_db(self.db_path)
        # run script for 1-day / 1-channel / 1-trigger
        # assert: sqlite3(db_path).execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 1
        pass  # flesh out using subprocess invocation against --db-path self.db_path
```

**Acceptance additions for 09-03 Task 1** (append to existing `<acceptance_criteria>`):

- `grep -c "create_alert(alert_model)" scripts/backfill_alerts.py` returns at least `1`
- `grep -c "record_pipeline_run(" scripts/backfill_alerts.py` returns at least `1`
- `grep -c "_build_alert_model_from_state" scripts/backfill_alerts.py` returns exactly `2` (def + one call)
- Test #13 `test_persists_alert_when_run_pipeline_triggers` appears in `scripts/test_backfill_alerts.py` and passes

---

## B-2 — `create_alert` MUST be idempotent (`INSERT OR IGNORE`)

**Affected:** `09-03-PLAN.md` — new Task 1b inserted between Task 1 and Task 2.

**Root cause:** `backend/db/operations.py:36` uses plain `INSERT INTO alerts`. Re-running backfill would raise `sqlite3.IntegrityError` on duplicate PK, breaking D-07 idempotency.

**New Task 1b — Make `create_alert` idempotent**

```xml
<task type="auto" tdd="true">
  <name>Task 1b: Make create_alert idempotent (INSERT OR IGNORE) + paired test</name>

  <read_first>
    - backend/db/operations.py (lines 33-66, create_alert current implementation)
    - backend/db/models.py (AlertModel, generate_alert_id)
    - .planning/phases/09-alert-backfill-legacy-migration/09-CONTEXT.md §D-07 (REVISED 2026-04-23)
  </read_first>

  <files>
    backend/db/operations.py,
    scripts/test_operations_idempotency.py
  </files>

  <action>
    STEP 1 — modify `backend/db/operations.py:36`:
      FROM: `"""INSERT INTO alerts (`
      TO:   `"""INSERT OR IGNORE INTO alerts (`

    STEP 2 — create `scripts/test_operations_idempotency.py` with 2 tests:

    ```python
    #!/usr/bin/env python3
    """Phase 09 — idempotency tests for operations.create_alert (B-2 fix)."""
    import os, sqlite3, sys, tempfile, unittest
    from datetime import datetime, timezone
    from pathlib import Path
    REPO_ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(REPO_ROOT))

    from backend.db.database import init_db
    from backend.db.models import (
        AlertModel, AlertRule, AlertStatus, ChannelGroup, Severity, generate_alert_id,
    )
    from backend.db.operations import create_alert, get_alert_by_id

    class TestCreateAlertIdempotent(unittest.TestCase):
        def setUp(self):
            self.tmpdir = tempfile.mkdtemp()
            self.db_path = os.path.join(self.tmpdir, "t.db")
            os.environ["VNA_DB_PATH"] = self.db_path
            init_db(self.db_path)
            ts = datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
            self.alert = AlertModel(
                alert_id=generate_alert_id(Severity.P1, ts),
                timestamp=ts,
                severity=Severity.P1,
                channel_group=ChannelGroup.GOOGLE_ADEX,
                status=AlertStatus.OPEN,
                alert_rule=AlertRule.A1,
                revenue_current=100.0, revenue_baseline=200.0,
                revenue_delta_pct=-50.0, triage_label="TEST",
                contributors_json="[]", geo_breakdown_json="[]",
                environment_split_json="{}", insights_json="{}",
                execution_time_sec=0.1, data_source="test",
                config_version="1.0.0", created_at=ts, updated_at=ts,
            )
        def tearDown(self):
            import shutil; shutil.rmtree(self.tmpdir, ignore_errors=True)

        def test_first_insert_succeeds(self):
            create_alert(self.alert)
            with sqlite3.connect(self.db_path) as c:
                n = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            self.assertEqual(n, 1)

        def test_duplicate_insert_is_noop_no_exception(self):
            create_alert(self.alert)
            first = get_alert_by_id(self.alert.alert_id)
            # Second insert: MUST NOT raise IntegrityError; MUST NOT mutate existing row
            create_alert(self.alert)
            with sqlite3.connect(self.db_path) as c:
                n = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            self.assertEqual(n, 1, "INSERT OR IGNORE should skip the duplicate")
            after = get_alert_by_id(self.alert.alert_id)
            self.assertEqual(first["updated_at"], after["updated_at"],
                             "Existing row must NOT be mutated by duplicate insert")

    if __name__ == "__main__":
        unittest.main()
    ```

    STEP 3 — run the test:
    `.venv/bin/python scripts/test_operations_idempotency.py` → 2/2 green.

    Commit (R-11, single logical change):
    `fix(09-03): create_alert idempotent via INSERT OR IGNORE + paired test (D-07)`
  </action>

  <acceptance_criteria>
    - `grep -c "INSERT OR IGNORE INTO alerts" backend/db/operations.py` returns exactly `1`
    - `grep -c "^    \"\"\"INSERT INTO alerts" backend/db/operations.py` returns `0` (old form gone)
    - `.venv/bin/python scripts/test_operations_idempotency.py 2>&1 | grep -cE "^Ran 2 tests"` returns `1`
    - `.venv/bin/python scripts/test_operations_idempotency.py 2>&1 | tail -2 | grep -c "OK"` returns `1`
    - LIVE path regression check: `.venv/bin/python scripts/test_integration.py` (if exists + already-green pre-change) STILL passes — `INSERT OR IGNORE` does not change LIVE single-insert semantics.
  </acceptance_criteria>

  <done>
    create_alert is idempotent. Duplicate inserts no-op silently (no IntegrityError).
    Existing rows preserved (updated_at unchanged on duplicate). Backfill re-runs are safe.
  </done>
</task>
```

**Task ordering in 09-03:** Task 1 → **Task 1b (new)** → Task 2 → Task 3. Update wave 3 sequential order accordingly. No parallelism; each task commits before the next starts.

---

## B-3 — Split 09-01 Task 3 into 3a / 3b / 3c (R-11)

**Affected:** `09-01-PLAN.md` Task 3.

**Root cause:** Task 3 bundles `git tag` + DB backup + `apply_migration_002.py` execution + authoring 11-test suite + running drift detector + 2 interleaved commits. Violates R-11 (1 logical change → verify → commit → OK).

**Override:** Replace Task 3 with three atomic sub-tasks. Binding structure:

### Task 3a — Pre-phase safety checkpoint (no DB mutation)

- `git tag v1.3-pre-phase-09` on current HEAD
- `cp data/vna_alerts.db data/vna_alerts.db.pre-phase09.bak`
- Append backup path + SHA256 to plan dir as `.planning/phases/09-alert-backfill-legacy-migration/.pre-phase-09-backup.txt`
- Commit: `chore(09): pre-phase-09 snapshot (tag + DB backup)`

Acceptance:
- `git tag | grep -c "^v1.3-pre-phase-09$"` returns `1`
- `test -f data/vna_alerts.db.pre-phase09.bak`
- `sha256sum data/vna_alerts.db.pre-phase09.bak | cut -d' ' -f1` equals `sha256sum data/vna_alerts.db | cut -d' ' -f1` at commit time

### Task 3b — Apply migration 002 to live DB + idempotency smoke

- `.venv/bin/python scripts/apply_migration_002.py`
- Second invocation: stdout contains `Already applied — skipping` (or equivalent ledger-detected message)
- `sqlite3 data/vna_alerts.db "SELECT name FROM pragma_table_info('alerts') WHERE name IN ('deprecated','deprecation_reason')"` returns both names (2 rows)
- `sqlite3 data/vna_alerts.db "SELECT migration_id FROM vna_schema_migrations WHERE migration_id='002_add_alert_deprecation'"` returns exactly 1 row
- Commit: `chore(09-01): apply migration 002 to live DB`

### Task 3c — Author `test_migration_002_apply.py` + run HARD-03 drift detector

- Create `scripts/test_migration_002_apply.py` with 11 tests per baseline plan Task 3 spec
- Run it: 11/11 GREEN
- Run extended `scripts/test_models_sync.py` (Task 1 added 7 new tests): 16/16 GREEN
- Commit: `test(09-01): migration 002 apply-suite + HARD-03 drift-detector extension`

R-11 strict: 3a MUST commit and Stefano MUST OK before 3b starts. 3b MUST commit and Stefano MUST OK before 3c starts. Executor running autonomously treats the `<done>` + acceptance pass as the OK gate.

---

## B-5 — Harden 09-03 Task 3 commit gate (R-04 chirurgico 10/10)

**Affected:** `09-03-PLAN.md` Task 3, section "Atomic commits" + must_haves.truths #3 + acceptance criteria.

**Override — replace must_have truth #3 with:**

> "After backfill: `SELECT COUNT(DISTINCT date(timestamp)) FROM alerts WHERE deprecated=0 AND timestamp >= '2026-01-23'` returns exactly `parquet_calendar_days` (i.e., 60 for 2026-01-23 → 2026-03-23; value auto-computed from `(parquet_max - start + 1).days`). Any shortfall STOPS the commit until Stefano issues an explicit override per R-05."

**Override — replace Task 3 commit gate** (section: "Atomic commits" / end-of-task flow):

The commit gate for Task 3 final DB-binary commit is:

```
PASS iff:
  - final_state.failed_tuples == []
  - distinct_dates_written == expected_calendar_days
  - SELECT COUNT(*) FROM alerts WHERE timestamp >= '2026-01-23' AND deprecated=0 > 0
  - SELECT COUNT(*) FROM alerts WHERE deprecated=1 == 200  (09-02 invariant preserved)
  - test_models_sync.py exits 0  (HARD-03 still green)
```

**If ANY condition fails:** STOP. Do NOT commit the DB binary. Write a failure report to `.planning/phases/09-alert-backfill-legacy-migration/09-03-BACKFILL-FAILURES.md` with the failed-tuples table (date, channel, trigger, error message). Surface to Stefano with 3 options per R-05:

1. Investigate + fix root cause + retry (resume from checkpoint, no `--force`)
2. Commit with reduced coverage rationale (requires explicit "OK Stefano — accept N-day gap" approval recorded in the commit trailer)
3. Rollback via `rollback_plan` path #4 (full phase reset)

Remove these phrases from the plan (they violate R-04):
- "≥ 50 of 60 calendar days — ≤ 10 gap days allowed per fail-soft"
- "> 0 acceptable with fail-soft rationale"
- "Final failed_tuples count from checkpoint (0 for success; >0 acceptable with fail-soft rationale)"

D-06 `fail-soft per tuple` remains the SCRIPT execution behavior (continue across tuples during a single run). R-04 `chirurgico 10/10` governs the COMMIT gate (land nothing incomplete without explicit human OK).

---

## W-1 — Explicit byte-identity extraction code (09-01 Task 1 Test A)

**Override the pseudocode at `09-01-PLAN.md:194`** (and the corresponding test body in Task 1):

```python
def test_deprecated_check_clause_byte_identical(self):
    """Drift gate: CHECK(deprecated IN (0,1)) must be byte-identical between
    models.py SQL_CREATE_ALERTS and migrations/002_add_alert_deprecation.sql.
    """
    check_in_migration = _extract_check(self.migration_002_src, "deprecated")
    alerts_block = _extract_create_block(self.models_src, "SQL_CREATE_ALERTS")
    check_in_models = _extract_check(alerts_block, "deprecated")
    self.assertEqual(
        _normalize_ws(check_in_migration),
        _normalize_ws(check_in_models),
        f"CHECK(deprecated) drift: migration={check_in_migration!r} models={check_in_models!r}",
    )
```

Add class-level source loads in `setUpClass`:
```python
@classmethod
def setUpClass(cls):
    cls.migration_002_src = Path(REPO_ROOT / "scripts/migrations/002_add_alert_deprecation.sql").read_text()
    cls.models_src = Path(REPO_ROOT / "backend/db/models.py").read_text()
```

---

## W-2 — Edit ROADMAP.md amendment in same commit as COVERAGE-GAP.md

**Affected:** `09-03-PLAN.md` Task 3.

**Override:** Task 3 must edit `.planning/ROADMAP.md` line 97 in the same commit that creates `COVERAGE-GAP.md`:

FROM: `  2. Alert list UI shows ≥ 1 alert per week 2026-01-23 → today`
TO:   `  2. Alert list UI shows ≥ 1 alert per week 2026-01-23 → parquet_v2_max_date (2026-03-23); see .planning/phases/09-alert-backfill-legacy-migration/COVERAGE-GAP.md for v1.3.1 plant-seed`

Commit message: `docs(09-03): amend ROADMAP Success #2 + plant COVERAGE-GAP.md (D-09)`

Acceptance:
- `grep -c "parquet_v2_max_date" .planning/ROADMAP.md` returns at least `1`
- `grep -c "→ today" .planning/ROADMAP.md` in the Phase 09 block returns `0`
- `test -f .planning/phases/09-alert-backfill-legacy-migration/COVERAGE-GAP.md`

---

## W-3 — Formatter-resilient TRIGGERS assertion

**Affected:** `09-03-PLAN.md:490`.

**Override the acceptance criterion:**

FROM: `grep -c 'TRIGGERS = \["A1", "A2", "A3"\]' scripts/backfill_alerts.py returns exactly 1`
TO:   `.venv/bin/python -c "from scripts.backfill_alerts import TRIGGERS; assert TRIGGERS == ['A1','A2','A3'], TRIGGERS" && echo ok | grep -c ok returns 1`

---

## W-4 — Audit get_alerts callers

**Affected:** `09-03-PLAN.md` Task 2 `<read_first>`.

**Override — append to `<read_first>` of Task 2:**

- `grep -rn "get_alerts(" backend/ frontend/ scripts/` — verify no position-dependent consumers of the returned dict. Expected: only `backend/api/routes.py:125` (list endpoint caller) + any test harness. New dict keys `deprecated`, `deprecation_reason` are additive — position-dependent callers would break; key-indexed callers are safe. Document findings in the commit message.

---

## INFO — Polish items (non-blocking, apply inline)

- **I-1 (09-02 Task 1):** When expanding FIXTURE_ROWS, pass severity as an explicit 4th column rather than deriving via `rsplit("-", 1)[-1]`. Less fragile for future fixture additions.
- **I-2 (09-01 Task 1):** Place `deprecated INTEGER NOT NULL DEFAULT 0 CHECK(deprecated IN (0, 1))` and `deprecation_reason TEXT` at the END of `SQL_CREATE_ALERTS` body (after `updated_at` line), matching SQLite ADD COLUMN append semantics. Reduces future drift-gate risk.
- **I-3 (09-02 Task 3 `<done>` note):** Add: "NOTE: between 09-02 commit and 09-03 Task 3 completion, `/api/alerts` default response is an empty list (all 200 alerts have deprecated=1, no new alerts written yet). This transient state is expected; UI observers will see a 'no alerts' state until backfill completes."

---

## Summary — Executor runbook (post-errata)

New sequential execution order within Phase 09:

| Wave | Plan | Task | Change |
|------|------|------|--------|
| 1 | 09-01 | 1 | W-1 (Test A extraction code), I-2 (column position) |
| 1 | 09-01 | 2 | unchanged |
| 1 | 09-01 | **3a** (NEW) | pre-phase tag + backup |
| 1 | 09-01 | **3b** (NEW) | apply migration 002 + idempotency smoke |
| 1 | 09-01 | **3c** (NEW) | author test suite + HARD-03 drift detector |
| 2 | 09-02 | 1 | I-1 (severity as explicit fixture column) |
| 2 | 09-02 | 2 | unchanged |
| 2 | 09-02 | 3 | I-3 (transient empty-list note) |
| 3 | 09-03 | 1 | **B-1** (persist block + adapter + test #13), W-3 (TRIGGERS assert) |
| 3 | 09-03 | **1b** (NEW) | **B-2** (INSERT OR IGNORE + idempotency test) |
| 3 | 09-03 | 2 | W-4 (get_alerts caller audit) |
| 3 | 09-03 | 3 | **B-5** (hardened commit gate), W-2 (ROADMAP amendment) |

Total tasks post-errata: 3 (09-01) + 3 (09-02) + 4 (09-03) + 2 new (09-01 Task 3 split delta: +2 since 3 becomes 3a/3b/3c) + 1 new (09-03 Task 1b) = **13 tasks** (up from 9).

All deep-work rules (read_first, concrete action, grep-verifiable acceptance) still apply. Threat models from baseline plans REMAIN IN FORCE (STRIDE unchanged by these fixes).

---

*Phase: 09-alert-backfill-legacy-migration*
*Errata published: 2026-04-23*
*Author: orchestrator (surgical post-checker fixes — planner revision agent timed out before delivery)*
*Supersedes: sections in 09-01-PLAN.md, 09-02-PLAN.md, 09-03-PLAN.md as cited above*
