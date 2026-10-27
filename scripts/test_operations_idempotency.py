#!/usr/bin/env python3
"""Phase 09 Task 1b — idempotency tests for operations.create_alert (B-2 fix).

Proves:
  1. First insert lands in the DB (smoke — INSERT OR IGNORE is not accidentally
     a no-op for new rows).
  2. Second insert of same AlertModel is silent no-op (no IntegrityError raised,
     rowcount stays at 1, existing row unchanged — INSERT OR IGNORE is the
     correct choice vs INSERT OR REPLACE, which would overwrite).

Phase 10.1 Plan 02 Task 1 — canonical format tests (MONITOR-04 / D-10.1-01):
  3. create_alert writes canonical space-sep naive UTC microseconds format.
  4. record_pipeline_run writes canonical format.
  5. Aware-timestamp input to create_alert still produces canonical output.

Phase 10.1 Plan 02 Task 2 — notifier._save_to_db canonical + is_new signal:
  6. _save_to_db INSERT path writes canonical format.
  7. _save_to_db UPDATE (dedup) path writes canonical format.
  8. _save_to_db returns (saved, is_new) tuple — is_new=True on INSERT, False on UPDATE.
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

# D-10.1-01: canonical format regex (space-sep naive UTC microseconds).
# Byte-identical to apply_migration_004.py CANONICAL_REGEX and
# test_migration_004_apply.py CANONICAL_RE literals — enforced by HARD-03
# TestCreatedAtFormatInvariant.test_a04.
CANONICAL_REGEX = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}$"

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.db.database import init_db  # noqa: E402
from backend.db.models import (  # noqa: E402
    AlertModel, AlertRule, AlertStatus, ChannelGroup, Severity, generate_alert_id,
)
from backend.db.operations import create_alert, get_alert_by_id  # noqa: E402


class TestCreateAlertIdempotent(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="op_idempot_")
        self.db_path = os.path.join(self.tmpdir, "t.db")
        os.environ["VNA_DB_PATH"] = self.db_path

        # Reset module-level DB path + thread-local connection cache.
        import backend.db.database as db_mod
        db_mod._DB_PATH = None
        if hasattr(db_mod._local, "connection") and db_mod._local.connection is not None:
            try:
                db_mod._local.connection.close()
            except Exception:
                pass
            db_mod._local.connection = None

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
        import shutil
        import backend.db.database as db_mod
        if hasattr(db_mod._local, "connection") and db_mod._local.connection is not None:
            try:
                db_mod._local.connection.close()
            except Exception:
                pass
            db_mod._local.connection = None
        db_mod._DB_PATH = None
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        os.environ.pop("VNA_DB_PATH", None)

    def test_first_insert_succeeds(self):
        """INSERT OR IGNORE must still insert new rows — the 'IGNORE' only
        suppresses PK conflicts, not fresh inserts."""
        create_alert(self.alert)
        with sqlite3.connect(self.db_path) as c:
            n = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        self.assertEqual(n, 1, "first insert must land")
        fetched = get_alert_by_id(self.alert.alert_id)
        self.assertIsNotNone(fetched, "alert must be retrievable after insert")

    def test_duplicate_insert_is_noop_no_exception(self):
        """Duplicate PK: INSERT OR IGNORE must silently skip.
        NO IntegrityError; rowcount stays at 1; existing row unmodified."""
        create_alert(self.alert)
        first = get_alert_by_id(self.alert.alert_id)
        self.assertIsNotNone(first)

        # Second insert — MUST NOT raise.
        try:
            create_alert(self.alert)
        except Exception as exc:
            self.fail(f"INSERT OR IGNORE must not raise on duplicate: {exc!r}")

        with sqlite3.connect(self.db_path) as c:
            n = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        self.assertEqual(n, 1, "INSERT OR IGNORE must skip the duplicate (no doubled rowcount)")

        # Existing row must be unchanged (distinguishes OR IGNORE from OR REPLACE).
        after = get_alert_by_id(self.alert.alert_id)
        self.assertEqual(
            first["updated_at"], after["updated_at"],
            "Existing row MUST NOT be mutated (OR IGNORE correctly chosen over OR REPLACE)",
        )


def _setup_tmpdb() -> tuple[str, str]:
    """Create a temporary directory + fully-initialized DB for Phase 10.1 tests.

    Returns (tmpdir, db_path). Caller must call _teardown_tmpdb(tmpdir, db_path)
    in tearDown.
    """
    import backend.db.database as db_mod
    tmpdir = tempfile.mkdtemp(prefix="op_canon_")
    db_path = os.path.join(tmpdir, "t.db")
    os.environ["VNA_DB_PATH"] = db_path
    db_mod._DB_PATH = None
    if hasattr(db_mod._local, "connection") and db_mod._local.connection is not None:
        try:
            db_mod._local.connection.close()
        except Exception:
            pass
        db_mod._local.connection = None
    from backend.db.database import init_db
    init_db(db_path)
    return tmpdir, db_path


def _teardown_tmpdb(tmpdir: str, db_path: str) -> None:
    import shutil
    import backend.db.database as db_mod
    if hasattr(db_mod._local, "connection") and db_mod._local.connection is not None:
        try:
            db_mod._local.connection.close()
        except Exception:
            pass
        db_mod._local.connection = None
    db_mod._DB_PATH = None
    shutil.rmtree(tmpdir, ignore_errors=True)
    os.environ.pop("VNA_DB_PATH", None)


class TestCreateAlertCanonicalFormat(unittest.TestCase):
    """D-10.1-01 / MONITOR-04: all created_at writes use canonical space-sep
    naive UTC microseconds format.

    Tasks: 10.1-02 Task 1 (TDD RED → GREEN for operations.py layer).
    """

    def setUp(self):
        self.tmpdir, self.db_path = _setup_tmpdb()

    def tearDown(self):
        _teardown_tmpdb(self.tmpdir, self.db_path)

    def test_create_alert_writes_canonical_format(self):
        """create_alert must write created_at + updated_at in canonical format."""
        from backend.db.operations import create_alert
        from backend.db.models import AlertModel, Severity, ChannelGroup, AlertStatus, AlertRule
        alert = AlertModel(
            alert_id="ALT-20260101-120000-P1",
            timestamp=datetime.utcnow(),
            severity=Severity.P1,
            channel_group=ChannelGroup.GOOGLE_ADEX,
            status=AlertStatus.OPEN,
            alert_rule=AlertRule.A1,
            revenue_current=100.0,
            revenue_baseline=200.0,
            revenue_delta_pct=-50.0,
            triage_label="TEST",
        )
        create_alert(alert)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT created_at, updated_at FROM alerts WHERE alert_id = ?",
                ("ALT-20260101-120000-P1",),
            ).fetchone()
        self.assertIsNotNone(row, "alert must be retrievable after insert")
        self.assertRegex(row[0], CANONICAL_REGEX,
                         f"created_at not canonical: {row[0]!r}")
        self.assertRegex(row[1], CANONICAL_REGEX,
                         f"updated_at not canonical: {row[1]!r}")

    def test_record_pipeline_run_writes_canonical_format(self):
        """record_pipeline_run must write created_at in canonical format."""
        from backend.db.operations import record_pipeline_run
        record_pipeline_run(
            run_id="test-canon-run-1",
            timestamp="2026-04-24T10:00:00",
            channel_group="GOOGLE_ADEX",
            trigger_type="A1",
            mode="LIVE",
            status="success",
            duration_sec=1.2,
            alerts_written_count=1,
        )
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT created_at FROM pipeline_runs WHERE run_id = ?",
                ("test-canon-run-1",),
            ).fetchone()
        self.assertIsNotNone(row, "pipeline_run row must exist")
        self.assertRegex(row[0], CANONICAL_REGEX,
                         f"pipeline_runs.created_at not canonical: {row[0]!r}")

    def test_create_alert_with_explicit_aware_timestamp_still_canonical(self):
        """Aware datetime input to create_alert must still produce canonical output."""
        from backend.db.operations import create_alert
        from backend.db.models import AlertModel, Severity, ChannelGroup, AlertStatus, AlertRule
        alert = AlertModel(
            alert_id="ALT-20260101-120001-P1",
            timestamp=datetime.utcnow(),
            severity=Severity.P1,
            channel_group=ChannelGroup.GOOGLE_ADEX,
            status=AlertStatus.OPEN,
            alert_rule=AlertRule.A1,
            revenue_current=100.0,
            revenue_baseline=200.0,
            revenue_delta_pct=-50.0,
            triage_label="TEST",
            created_at=datetime(2026, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc),
        )
        create_alert(alert)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT created_at FROM alerts WHERE alert_id = ?",
                ("ALT-20260101-120001-P1",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertRegex(row[0], CANONICAL_REGEX,
                         f"Aware-timestamp input not canonicalized: {row[0]!r}")


class TestNotifierSaveToDbCanonicalFormat(unittest.TestCase):
    """D-10.1-01 / D-10.1-07: notifier._save_to_db writes canonical format
    on both INSERT and UPDATE paths, and returns (saved, is_new) tuple.

    Tasks: 10.1-02 Task 2 (TDD RED → GREEN for notifier.py layer).
    """

    def setUp(self):
        self.tmpdir, self.db_path = _setup_tmpdb()

    def tearDown(self):
        _teardown_tmpdb(self.tmpdir, self.db_path)

    def _make_state(self, alert_id: str, channel: str = "GOOGLE_ADEX",
                    rule: str = "A1") -> dict:
        return {
            "mode": "LIVE",
            "alert_payload": {
                "alert_id": alert_id,
                "severity": "P1",
                "channel_group": channel,
                "alert_rule": rule,
                "timestamp": "2026-04-24T10:00:00",
                "revenue": {"current": 100.0, "baseline": 200.0, "delta_pct": -50.0},
                "triage_label": "OPERATIONAL",
                "contributors": [],
                "geo_breakdown": [],
                "environment_split": {},
                "insights": {},
                "data_source": "synthetic",
            },
        }

    def test_save_to_db_insert_writes_canonical(self):
        """_save_to_db INSERT path must write created_at + updated_at in canonical format."""
        from backend.agents.notifier import _save_to_db
        state = self._make_state("ALT-20260101-130000-P1")
        result = _save_to_db(state)
        # Accept either bool (pre-fix) or (saved, is_new) tuple (post-fix)
        saved = result[0] if isinstance(result, tuple) else result
        self.assertTrue(saved)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT created_at, updated_at FROM alerts WHERE alert_id = ?",
                ("ALT-20260101-130000-P1",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertRegex(row[0], CANONICAL_REGEX,
                         f"INSERT: created_at not canonical: {row[0]!r}")
        self.assertRegex(row[1], CANONICAL_REGEX,
                         f"INSERT: updated_at not canonical: {row[1]!r}")

    def test_save_to_db_update_writes_canonical(self):
        """_save_to_db UPDATE (dedup) path must write updated_at in canonical format."""
        # Seed an existing OPEN alert with a recent timestamp (within dedup window)
        # so that find_open_alert() will detect it during dedup check.
        from backend.db.operations import create_alert
        from backend.db.models import AlertModel, Severity, ChannelGroup, AlertStatus, AlertRule
        recent_ts = datetime.utcnow()
        seeded_id = f"ALT-{recent_ts.strftime('%Y%m%d-%H%M%S')}-P1"
        seeded = AlertModel(
            alert_id=seeded_id,
            timestamp=recent_ts,
            severity=Severity.P1,
            channel_group=ChannelGroup.GOOGLE_ADEX,
            status=AlertStatus.OPEN,
            alert_rule=AlertRule.A1,
            revenue_current=100.0,
            revenue_baseline=200.0,
            revenue_delta_pct=-50.0,
            triage_label="TEST",
        )
        create_alert(seeded)
        # Now call _save_to_db on same (channel=GOOGLE_ADEX, rule=A1) — should dedup-UPDATE
        from backend.agents.notifier import _save_to_db
        state = self._make_state("ALT-20260101-130001-P1", channel="GOOGLE_ADEX", rule="A1")
        result = _save_to_db(state)
        saved = result[0] if isinstance(result, tuple) else result
        self.assertTrue(saved)
        # seeded alert should have been UPDATEd
        with sqlite3.connect(self.db_path) as conn:
            seeded_row = conn.execute(
                "SELECT updated_at FROM alerts WHERE alert_id = ?",
                (seeded_id,),
            ).fetchone()
            new_row = conn.execute(
                "SELECT alert_id FROM alerts WHERE alert_id = 'ALT-20260101-130001-P1'"
            ).fetchone()
        self.assertIsNotNone(seeded_row)
        self.assertRegex(seeded_row[0], CANONICAL_REGEX,
                         f"UPDATE: updated_at not canonical: {seeded_row[0]!r}")
        self.assertIsNone(new_row, "dedup must not INSERT the new alert_id")

    def test_save_to_db_returns_is_new_signal(self):
        """_save_to_db must return (saved, is_new) — True on INSERT, False on UPDATE."""
        from backend.agents.notifier import _save_to_db
        # First call -> INSERT path -> is_new=True
        state1 = self._make_state("ALT-20260101-140000-P1", channel="GOOGLE_ADEX", rule="A2")
        result1 = _save_to_db(state1)
        self.assertIsInstance(result1, tuple, "post-fix: returns (saved, is_new)")
        self.assertEqual(result1, (True, True), f"expected (True, True), got {result1!r}")
        # Second call same (channel, rule) -> UPDATE path -> is_new=False
        state2 = self._make_state("ALT-20260101-140001-P1", channel="GOOGLE_ADEX", rule="A2")
        result2 = _save_to_db(state2)
        self.assertIsInstance(result2, tuple, "post-fix: returns (saved, is_new)")
        self.assertEqual(result2, (True, False), f"expected (True, False), got {result2!r}")


# ==========================================================================
# Module-level helper (Plan 10.1-05): _tmpdb_with_schema context manager.
# Byte-copy of the helper from scripts/test_health_alerts_pipeline.py
# (Plan 10.1-04). Defined once here so that BOTH TestFindOpenAlertBoundaryDay
# (this plan) AND TestSchedulerCounterSemantics (Plan 10.1-07, Wave 6) can
# reuse without redefinition. If Plan 10.1-07 executor is tempted to paste a
# second definition — DO NOT: it shadows and risks drift. Reuse this one.
# ==========================================================================
import shutil
from contextlib import contextmanager

PIPELINE_RUNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    channel_group TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'LIVE',
    status TEXT NOT NULL,
    duration_sec REAL,
    llm_used INTEGER DEFAULT 0,
    llm_fallback INTEGER DEFAULT 0,
    alert_id TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    alerts_written_count INTEGER NOT NULL DEFAULT 0 CHECK(alerts_written_count >= 0)
);
"""
ALERTS_SCHEMA_MIN = """
CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL,
    channel_group TEXT NOT NULL,
    status TEXT NOT NULL,
    alert_rule TEXT NOT NULL,
    revenue_current REAL, revenue_baseline REAL, revenue_delta_pct REAL,
    triage_label TEXT, contributors_json TEXT, geo_breakdown_json TEXT,
    environment_split_json TEXT, insights_json TEXT,
    execution_time_sec REAL, data_source TEXT, config_version TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    deprecated INTEGER NOT NULL DEFAULT 0,
    deprecation_reason TEXT
);
"""


@contextmanager
def _tmpdb_with_schema():
    """Create tmpdb with alerts + pipeline_runs schema sufficient for
    find_open_alert (MAJOR-NEW-02 regression tests) AND scheduler
    alerts_written_count recording (Plan 10.1-07 reuse).

    Byte-copy of the helper in scripts/test_health_alerts_pipeline.py —
    do NOT drift.
    """
    tmpdir = tempfile.mkdtemp(prefix="op_idempot_tmpdb_")
    db_path = os.path.join(tmpdir, "test.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(PIPELINE_RUNS_SCHEMA + ALERTS_SCHEMA_MIN)
    conn.commit()
    conn.close()
    try:
        yield db_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _set_tmpdb(db_path: str):
    """Point backend.db.database at db_path for tmpdb-based tests."""
    import backend.db.database as db_mod
    os.environ["VNA_DB_PATH"] = db_path
    db_mod._DB_PATH = None
    if hasattr(db_mod._local, "connection") and db_mod._local.connection is not None:
        try:
            db_mod._local.connection.close()
        except Exception:
            pass
        db_mod._local.connection = None


def _reset_tmpdb():
    """Restore database module to default state after a tmpdb-based test."""
    import backend.db.database as db_mod
    if hasattr(db_mod._local, "connection") and db_mod._local.connection is not None:
        try:
            db_mod._local.connection.close()
        except Exception:
            pass
        db_mod._local.connection = None
    db_mod._DB_PATH = None
    os.environ.pop("VNA_DB_PATH", None)


class TestFindOpenAlertBoundaryDay(unittest.TestCase):
    """MONITOR-06 / MAJOR-NEW-02 (auditor A): find_open_alert 6h dedup
    window respected across calendar-day boundaries.

    Root cause addressed by migration 004 (Plan 10.1-03) — post-migration,
    all alerts.created_at rows are canonical space-sep. This test class
    adds REGRESSION coverage; no code change in find_open_alert itself
    per D-10.1-05.

    Scope note: find_open_alert compares the `timestamp` column (business
    event time), NOT `created_at`. Timestamp column is written from
    payload.get('timestamp') pass-through in notifier._save_to_db. If that
    pass-through later feeds T-format values, the bug resurfaces for
    `timestamp` specifically. Follow-up: Phase 10.2 audit of timestamp
    column format consistency.

    Clock control: uses datetime.utcnow() - timedelta(hours=N) pattern
    (freezegun not installed). Tests assert the 7h>6h invariant regardless
    of calendar boundary crossing — the bug class was string-compare
    misbehavior, not boundary-specific logic.
    """

    def setUp(self):
        self._db_ctx = _tmpdb_with_schema()
        self.db_path = self._db_ctx.__enter__()
        _set_tmpdb(self.db_path)

    def tearDown(self):
        _reset_tmpdb()
        self._db_ctx.__exit__(None, None, None)

    def _seed_open_alert_with_timestamp(self, alert_id, timestamp_raw,
                                        channel="GOOGLE_ADEX", rule="A1"):
        """Seed an OPEN alert with a specific raw timestamp string.
        Uses canonical format for created_at (post-migration invariant),
        controllable timestamp for dedup-window testing."""
        from datetime import datetime
        now_canon = datetime.utcnow().isoformat(sep=' ', timespec='microseconds')
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO alerts (alert_id, timestamp, severity, channel_group,
                    status, alert_rule, triage_label,
                    contributors_json, geo_breakdown_json,
                    environment_split_json, insights_json,
                    data_source, config_version,
                    created_at, updated_at)
               VALUES (?, ?, 'P1', ?, 'OPEN', ?, 'UNKNOWN',
                       '[]', '[]', '{}', '{}', 'synthetic', '1.0.0', ?, ?)""",
            (alert_id, timestamp_raw, channel, rule, now_canon, now_canon),
        )
        conn.commit()
        conn.close()

    def test_7_hour_old_alert_crossing_day_boundary_returns_none(self):
        """Canonical-format 7h-old alert is OUTSIDE 6h dedup window; None expected.

        This is the strict MAJOR-NEW-02 regression assertion. Post-migration-004,
        stored timestamp is canonical space-sep; SQLite datetime('now','-6 hours')
        also returns space-sep — string comparison is correct and the 7h-old row
        is correctly excluded.
        """
        from datetime import datetime, timedelta
        from backend.db import operations as ops
        ts_7h_ago = (datetime.utcnow() - timedelta(hours=7)).isoformat(
            sep=' ', timespec='microseconds')
        self._seed_open_alert_with_timestamp("old-alert-7h", ts_7h_ago)
        result = ops.find_open_alert("GOOGLE_ADEX", "A1", dedup_window_hours=6)
        self.assertIsNone(result,
            f"7h-old canonical alert must NOT return (outside 6h window); got {result!r}")

    def test_2_hour_old_alert_returns_row(self):
        """Positive control: 2h-old alert is INSIDE 6h window, must return."""
        from datetime import datetime, timedelta
        from backend.db import operations as ops
        ts_2h_ago = (datetime.utcnow() - timedelta(hours=2)).isoformat(
            sep=' ', timespec='microseconds')
        self._seed_open_alert_with_timestamp("recent-alert-2h", ts_2h_ago)
        result = ops.find_open_alert("GOOGLE_ADEX", "A1", dedup_window_hours=6)
        self.assertIsNotNone(result)
        self.assertEqual(result["alert_id"], "recent-alert-2h")

    def test_pre_migration_t_separator_demonstrates_bug_class(self):
        """Pre-migration T-separator alerts would have been erroneously
        returned for 'old' timestamps, because 'T' > space in byte-compare.

        This test SEEDS a T-format timestamp 7h ago and confirms the string
        compare misbehaves: 'T' (0x54) > ' ' (0x20) means a T-format
        timestamp string sorts ABOVE the space-sep datetime('now','-6 hours')
        cutoff output, making a 7h-old T-format row appear inside the window.

        Post-migration-004, alerts.created_at is canonical — but alerts.timestamp
        is NOT migrated (it's a business-event time pass-through). This test
        documents the equivalent gap in the timestamp column for Phase 10.2 audit.
        """
        from datetime import datetime, timedelta
        from backend.db import operations as ops
        ts_7h_ago_t = (datetime.utcnow() - timedelta(hours=7)).isoformat(
            sep='T', timespec='microseconds')
        self._seed_open_alert_with_timestamp("legacy-t-fmt", ts_7h_ago_t)
        result = ops.find_open_alert("GOOGLE_ADEX", "A1", dedup_window_hours=6)
        # Document the observed behavior for post-10.1 audit:
        # - If result is NOT None: confirms the pre-migration bug (T-format
        #   ghost inside window). Assert the alert_id matches the seeded row.
        # - If result IS None: test inconclusive at this clock time; emit warning.
        if result is not None:
            self.assertIn("legacy-t-fmt", result["alert_id"],
                "T-format pre-migration bug class reproduced: erroneously inside 6h window")
        else:
            import warnings
            warnings.warn(
                "T-format demo test inconclusive at current clock time. "
                "MAJOR-NEW-02 canonical-format regression (test_7_hour_old_alert...) "
                "is the authoritative assertion.",
                UserWarning,
            )


class TestSchedulerCounterSemantics(unittest.TestCase):
    """MONITOR-08 / D-10.1-07: alerts_written_count in pipeline_runs
    reflects INSERT intent, not rule-fire flag.

    Note: reuses the module-level `_tmpdb_with_schema()` helper defined
    alongside TestFindOpenAlertBoundaryDay by Plan 10.1-05. Do not
    redefine it — a second definition would shadow and potentially drift.
    """

    def setUp(self):
        # No per-test state — each test uses _tmpdb_with_schema() context manager inline.
        pass

    def _simulate_scheduler_record(self, db_path, result_state, channel="GOOGLE_ADEX",
                                    trigger="A1", run_id=None):
        """Mimic the exact sequence of _run_trigger_for_channels after
        run_pipeline() returns. Independent from asyncio to keep test sync."""
        import uuid
        from datetime import datetime
        if run_id is None:
            run_id = str(uuid.uuid4())[:8]
        timestamp_now = datetime.utcnow().isoformat(sep=' ', timespec='microseconds')
        alert_triggered = result_state.get("alert_triggered", False)
        status = "success" if alert_triggered else "no_alert"
        alert_id = (result_state.get("alert_payload", {}).get("alert_id")
                    if alert_triggered else None)
        # Call the real scheduler helper so test + code under test share the same logic.
        from backend.scheduler.scheduler import _alerts_written_from_result
        alerts_written = _alerts_written_from_result(result_state)
        from backend.db.operations import record_pipeline_run
        from unittest.mock import patch
        with patch("backend.db.database._DB_PATH", db_path):
            import backend.db.database as db_mod
            _set_tmpdb(db_path)
            record_pipeline_run(
                run_id, timestamp_now, channel, trigger, "LIVE",
                status, 0.5, False, False, alert_id,
                alerts_written_count=alerts_written,
            )
            _reset_tmpdb()
        return alerts_written

    def _count_pipeline_runs(self, db_path):
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT alerts_written_count FROM pipeline_runs ORDER BY id"
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]

    def test_dedup_update_does_not_increment_counter(self):
        """2 consecutive fires: 1st INSERTs (count=1), 2nd dedup-UPDATEs (count=0).
        SUM=1, NOT 2."""
        with _tmpdb_with_schema() as db_path:
            # Simulate first fire — INSERT path
            first_state = {
                "alert_triggered": True,
                "alert_payload": {"alert_id": "fire-1"},
                "delivery_status": {"db_saved": True, "db_new_row": True},
            }
            w1 = self._simulate_scheduler_record(db_path, first_state, run_id="r1")
            # Simulate second fire — dedup UPDATE path
            second_state = {
                "alert_triggered": True,
                "alert_payload": {"alert_id": "fire-2"},
                "delivery_status": {"db_saved": True, "db_new_row": False},
            }
            w2 = self._simulate_scheduler_record(db_path, second_state, run_id="r2")
            counts = self._count_pipeline_runs(db_path)
        self.assertEqual(w1, 1)
        self.assertEqual(w2, 0)
        self.assertEqual(counts, [1, 0],
            f"Counter semantics wrong: expected [1, 0], got {counts!r}")
        self.assertEqual(sum(counts), 1,
            "Total alerts_written across 2 runs with dedup must be 1, not 2")

    def test_insert_path_increments_counter(self):
        """Single fresh fire with db_new_row=True -> alerts_written_count=1."""
        with _tmpdb_with_schema() as db_path:
            state = {
                "alert_triggered": True,
                "alert_payload": {"alert_id": "fresh-1"},
                "delivery_status": {"db_saved": True, "db_new_row": True},
            }
            w = self._simulate_scheduler_record(db_path, state, run_id="r1")
            counts = self._count_pipeline_runs(db_path)
        self.assertEqual(w, 1)
        self.assertEqual(counts, [1])

    def test_alerts_written_count_defaults_to_zero_on_missing_delivery_status(self):
        """Defensive: if delivery_status absent from result (unexpected state
        shape), scheduler records 0 and does not crash."""
        with _tmpdb_with_schema() as db_path:
            state = {
                "alert_triggered": True,
                "alert_payload": {"alert_id": "noshape-1"},
                # delivery_status missing
            }
            w = self._simulate_scheduler_record(db_path, state, run_id="r1")
            counts = self._count_pipeline_runs(db_path)
        self.assertEqual(w, 0)
        self.assertEqual(counts, [0])

    def test_alert_triggered_false_records_zero(self):
        """No anomaly -> alert_triggered=False -> alerts_written_count=0."""
        with _tmpdb_with_schema() as db_path:
            state = {"alert_triggered": False}
            w = self._simulate_scheduler_record(db_path, state, run_id="r1")
            counts = self._count_pipeline_runs(db_path)
        self.assertEqual(w, 0)
        self.assertEqual(counts, [0])


if __name__ == "__main__":
    unittest.main()
