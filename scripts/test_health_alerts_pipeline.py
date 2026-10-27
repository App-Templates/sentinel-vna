#!/usr/bin/env python3
"""Phase 10 Plan 02 -- /api/health/alerts-pipeline endpoint tests (MONITOR-01).

Uses FastAPI TestClient against the live app. Tests READ-ONLY -- no DB
mutations. Verifies:
  * HTTP 200 + AlertsPipelineHealth schema compliance
  * Non-negative counts, nullable last_alert_at
  * Endpoint does not mutate alerts or pipeline_runs tables
  * Schema validation rejects malformed responses (via Pydantic)
"""
import os
import sqlite3
import sys
import unittest
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Bypass auth for tests (require_auth is no-op outside production).
os.environ["ENVIRONMENT"] = "development"

from fastapi.testclient import TestClient
from backend.main import app
from backend.api.schemas import AlertsPipelineHealth


class TestHealthAlertsPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db_path = REPO_ROOT / "data" / "vna_alerts.db"

    def _snapshot_counts(self) -> dict:
        conn = sqlite3.connect(str(self.db_path))
        try:
            alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            pr = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
            return {"alerts": alerts, "pipeline_runs": pr}
        finally:
            conn.close()

    def test_endpoint_returns_200(self):
        resp = self.client.get("/api/health/alerts-pipeline")
        self.assertEqual(resp.status_code, 200, f"body: {resp.text}")

    def test_response_matches_schema(self):
        resp = self.client.get("/api/health/alerts-pipeline")
        body = resp.json()
        # Pydantic validation -- if schema drifts, this raises.
        model = AlertsPipelineHealth(**body)
        self.assertIn("last_alert_at", body)
        self.assertIn("alerts_last_24h", body)
        self.assertIn("pipeline_runs_last_24h", body)
        self.assertGreaterEqual(body["alerts_last_24h"], 0)
        self.assertGreaterEqual(body["pipeline_runs_last_24h"], 0)

    def test_last_alert_at_is_null_or_iso8601(self):
        resp = self.client.get("/api/health/alerts-pipeline")
        body = resp.json()
        val = body["last_alert_at"]
        if val is not None:
            self.assertIsInstance(val, str)
            # Post-Plan-10.1-03 live DB is 100% canonical space-sep microseconds
            # per MONITOR-04. Pre-migration mixed format still accepted for
            # transitional compatibility (belt-and-suspenders — will be removed
            # once all writers proven canonical for 30+ days).
            try:
                datetime.fromisoformat(val.replace(" ", "T"))
            except Exception as e:
                self.fail(f"last_alert_at not ISO8601 parseable: {val!r}: {e}")

    def test_endpoint_does_not_mutate_db(self):
        pre = self._snapshot_counts()
        for _ in range(3):
            self.client.get("/api/health/alerts-pipeline")
        post = self._snapshot_counts()
        self.assertEqual(pre, post, f"DB mutated: pre={pre} post={post}")


import os
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Shared helpers for tmpdb-based tests (MONITOR-05 / D-10.1-04)
# ---------------------------------------------------------------------------

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
    get_alerts_pipeline_health(). Handles DB_PATH reset for the duration."""
    tmpdir = tempfile.mkdtemp(prefix="health_test_")
    db_path = os.path.join(tmpdir, "test.db")
    conn = sqlite3.connect(db_path)
    conn.executescript(PIPELINE_RUNS_SCHEMA + ALERTS_SCHEMA_MIN)
    conn.commit()
    conn.close()
    try:
        yield db_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _set_db(db_path: str):
    """Point backend.db.database at db_path (used in setUp/with-block)."""
    import backend.db.database as db_mod
    os.environ["VNA_DB_PATH"] = db_path
    db_mod._DB_PATH = None
    if hasattr(db_mod._local, "connection") and db_mod._local.connection is not None:
        try:
            db_mod._local.connection.close()
        except Exception:
            pass
        db_mod._local.connection = None


def _reset_db():
    """Restore database module to default state after a test."""
    import backend.db.database as db_mod
    if hasattr(db_mod._local, "connection") and db_mod._local.connection is not None:
        try:
            db_mod._local.connection.close()
        except Exception:
            pass
        db_mod._local.connection = None
    db_mod._DB_PATH = None
    os.environ.pop("VNA_DB_PATH", None)


def _canonical_ts(hours_ago: float = 0) -> str:
    ts = datetime.utcnow() - timedelta(hours=hours_ago)
    return ts.isoformat(sep=' ', timespec='microseconds')


def _seed_pipeline_runs(db_path: str, mode: str, count: int, hours_ago: float = 1.0):
    conn = sqlite3.connect(db_path)
    now = _canonical_ts(hours_ago)
    for i in range(count):
        conn.execute(
            """INSERT INTO pipeline_runs (run_id, timestamp, channel_group,
                   trigger_type, mode, status, duration_sec, created_at,
                   alerts_written_count)
               VALUES (?, ?, 'GOOGLE_ADEX', 'A1', ?, 'no_alert', 0.1, ?, 0)""",
            (f"run-{mode}-{i}", now, mode, now),
        )
    conn.commit()
    conn.close()


def _seed_alerts(db_path: str, count: int, hours_ago: float = 1.0):
    conn = sqlite3.connect(db_path)
    now = _canonical_ts(hours_ago)
    for i in range(count):
        conn.execute(
            """INSERT INTO alerts (alert_id, timestamp, severity, channel_group,
                    status, alert_rule, triage_label,
                    contributors_json, geo_breakdown_json,
                    environment_split_json, insights_json,
                    data_source, config_version,
                    created_at, updated_at)
               VALUES (?, ?, 'P1', 'GOOGLE_ADEX', 'OPEN', 'A1', 'UNKNOWN',
                       '[]', '[]', '{}', '{}', 'synthetic', '1.0.0', ?, ?)""",
            (f"alert-{i}", now, now, now),
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# MONITOR-05 / MAJOR-01: mode filter regression tests
# ---------------------------------------------------------------------------

class TestHealthEndpointModeFilter(unittest.TestCase):
    """MONITOR-05 / MAJOR-01: pipeline_runs_last_24h must exclude BACKTEST rows."""

    def setUp(self):
        self._db_ctx = _tmpdb_with_schema()
        self.db_path = self._db_ctx.__enter__()
        _set_db(self.db_path)

    def tearDown(self):
        _reset_db()
        self._db_ctx.__exit__(None, None, None)

    def test_pipeline_runs_last_24h_excludes_backtest_rows(self):
        from backend.db import operations as ops
        _seed_pipeline_runs(self.db_path, mode="LIVE", count=5, hours_ago=0.5)
        _seed_pipeline_runs(self.db_path, mode="BACKTEST", count=1442, hours_ago=0.5)
        result = ops.get_alerts_pipeline_health()
        self.assertEqual(
            result["pipeline_runs_last_24h"], 5,
            f"BACKTEST contamination NOT filtered: got {result['pipeline_runs_last_24h']}, expected 5",
        )

    def test_pipeline_runs_last_24h_zero_when_only_backtest(self):
        from backend.db import operations as ops
        _seed_pipeline_runs(self.db_path, mode="BACKTEST", count=10, hours_ago=0.5)
        result = ops.get_alerts_pipeline_health()
        self.assertEqual(result["pipeline_runs_last_24h"], 0)

    def test_alerts_last_24h_unchanged_by_mode_filter(self):
        """alerts query is independent of mode filter — only pipeline_runs gained it."""
        from backend.db import operations as ops
        _seed_alerts(self.db_path, count=3, hours_ago=0.5)
        _seed_pipeline_runs(self.db_path, mode="BACKTEST", count=1442, hours_ago=0.5)
        result = ops.get_alerts_pipeline_health()
        self.assertEqual(result["alerts_last_24h"], 3)
        self.assertEqual(result["pipeline_runs_last_24h"], 0)


# ---------------------------------------------------------------------------
# MONITOR-05 / MAJOR-03: temporal boundary regression tests
# ---------------------------------------------------------------------------

class TestHealthEndpointTemporalBoundary(unittest.TestCase):
    """MONITOR-05 / MAJOR-03: temporal comparison bit-identical across
    canonical-format rows, including calendar-day boundaries. Regression
    coverage — the actual fix is migration 004 (Plan 10.1-03) normalizing
    row format; this test asserts the fix holds."""

    def setUp(self):
        self._db_ctx = _tmpdb_with_schema()
        self.db_path = self._db_ctx.__enter__()
        _set_db(self.db_path)

    def tearDown(self):
        _reset_db()
        self._db_ctx.__exit__(None, None, None)

    def _seed_alert_raw(self, alert_id, created_at_raw):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO alerts (alert_id, timestamp, severity, channel_group,
                    status, alert_rule, triage_label,
                    contributors_json, geo_breakdown_json,
                    environment_split_json, insights_json,
                    data_source, config_version,
                    created_at, updated_at)
               VALUES (?, ?, 'P1', 'GOOGLE_ADEX', 'OPEN', 'A1', 'UNKNOWN',
                       '[]', '[]', '{}', '{}', 'synthetic', '1.0.0', ?, ?)""",
            (alert_id, created_at_raw, created_at_raw, created_at_raw),
        )
        conn.commit()
        conn.close()

    def test_temporal_query_bit_identical_on_canonical_rows(self):
        """All 3 rows canonical format, all within 24h of 'now' — count=3."""
        from backend.db import operations as ops
        self._seed_alert_raw("canon-1", _canonical_ts(0.5))    # ~30min ago
        self._seed_alert_raw("canon-2", _canonical_ts(12))     # 12h ago
        self._seed_alert_raw("canon-3", _canonical_ts(23.5))   # ~23.5h ago
        result = ops.get_alerts_pipeline_health()
        self.assertEqual(result["alerts_last_24h"], 3,
            f"Canonical-format rows under 24h miscount: {result!r}")

    def test_temporal_query_misses_t_separator_rows_pre_migration(self):
        """Simulates pre-migration state: rows with T-separator compared against
        datetime('now','-1 day') output (space-separator).

        String comparison semantics: 'T' (0x54) > space (0x20), so a T-separator
        row with the same date portion as the space-sep cutoff sorts ABOVE it.
        This means T-rows are over-counted as recent rather than under-counted.

        Post-migration 004, this ambiguity is gone — only canonical rows exist.
        This test documents the bug CLASS and confirms the string-compare and
        chronological-compare produce identical results for canonical rows.
        """
        from backend.db import operations as ops
        ts_naive = datetime.utcnow() - timedelta(hours=23)
        canonical = ts_naive.isoformat(sep=' ', timespec='microseconds')
        t_form = ts_naive.isoformat(sep='T', timespec='microseconds')
        self._seed_alert_raw("t-form-1", t_form)
        self._seed_alert_raw("canon-1", canonical)
        result = ops.get_alerts_pipeline_health()
        # Query the raw SQLite counts to confirm the split
        conn = sqlite3.connect(self.db_path)
        t_in_window = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE created_at LIKE '%T%'"
            " AND created_at >= datetime('now','-1 day')"
        ).fetchone()[0]
        s_in_window = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE created_at NOT LIKE '%T%'"
            " AND created_at >= datetime('now','-1 day')"
        ).fetchone()[0]
        conn.close()
        # Both rows are chronologically within the 24h window.
        # Total = t_in + s_in (the per-format split).
        self.assertEqual(t_in_window + s_in_window, result["alerts_last_24h"],
            "Split count must equal total — both T and space rows seeded within 24h")
        # The canonical space-sep row is always counted correctly (s_in_window=1).
        self.assertEqual(s_in_window, 1,
            "Canonical space-sep row must be counted by datetime() comparison")

    def test_max_created_at_returns_true_latest_across_canonical_rows(self):
        """Post-migration 004 MAX(created_at) returns true latest row."""
        from backend.db import operations as ops
        now = datetime.utcnow()
        t_latest = (now - timedelta(hours=1)).isoformat(sep=' ', timespec='microseconds')
        t_middle = (now - timedelta(hours=5)).isoformat(sep=' ', timespec='microseconds')
        t_earliest = (now - timedelta(hours=10)).isoformat(sep=' ', timespec='microseconds')
        self._seed_alert_raw("earliest", t_earliest)
        self._seed_alert_raw("middle", t_middle)
        self._seed_alert_raw("latest", t_latest)
        result = ops.get_alerts_pipeline_health()
        self.assertEqual(result["last_alert_at"], t_latest,
            f"MAX(created_at) wrong: got {result['last_alert_at']!r}, "
            f"expected {t_latest!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
