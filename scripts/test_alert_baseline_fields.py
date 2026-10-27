#!/usr/bin/env python3
"""Phase 11 API-03 — Nyquist Wave 0 RED test for top-level baseline_bacino + baseline_coverage in AlertDetail.

Authored before implementation per VALIDATION contract. Expected RED until Plan 02
extends AlertDetail and aggregates from `environment_split_json`. Wave 1 implementation
turns this GREEN. Kills the TriageSection.tsx:31-32 client-side heuristic.

Truth source: RESEARCH §6 — values ALREADY EXIST inside `environment_split_json`
(`bacino_baseline`, `coverage_baseline` per env). Plan 02 Opzione A: aggregate
on-the-fly inside `get_alert_by_id()`, NO DB migration. Schema: AlertDetail gains
`baseline_bacino: Optional[int]` + `baseline_coverage: Optional[float]` at top-level.

Run:  .venv/bin/python scripts/test_alert_baseline_fields.py
Exit: 0 = AlertDetail extended + aggregation correct (Wave 1 GREEN);
      non-zero = top-level fields missing or heuristic still in use (Wave 0 RED — expected today).
"""
import json
import os
import sqlite3
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Bypass auth for tests (require_auth is a no-op outside production).
os.environ["ENVIRONMENT"] = "development"

from fastapi.testclient import TestClient
from backend.main import app


# ---------------------------------------------------------------------------
# Fixture discovery — read-only against live data/vna_alerts.db
# ---------------------------------------------------------------------------

DB_PATH = REPO_ROOT / "data" / "vna_alerts.db"


def _first_non_deprecated_alert_id() -> str | None:
    """Discover a fresh alert with a populated environment_split_json blob.

    Read-only SELECT against live DB (project pattern — same as
    test_health_alerts_pipeline.py). Returns None if DB missing or no row matches.
    """
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    try:
        row = conn.execute(
            """SELECT alert_id FROM alerts
               WHERE deprecated = 0
                 AND environment_split_json IS NOT NULL
                 AND environment_split_json != '{}'
               LIMIT 1"""
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _first_deprecated_alert_id() -> str | None:
    """Discover a deprecated alert for graceful-degradation test."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    try:
        row = conn.execute(
            "SELECT alert_id FROM alerts WHERE deprecated = 1 LIMIT 1"
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


class TestAlertBaselineFields(unittest.TestCase):
    """API-03 schema extension — top-level baseline_bacino + baseline_coverage."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.alert_id = _first_non_deprecated_alert_id()
        cls.dep_alert_id = _first_deprecated_alert_id()
        if cls.alert_id is None:
            raise unittest.SkipTest(
                "no non-deprecated alerts with env_split in DB — phase prerequisite missing"
            )

    def _fetch_body(self, alert_id: str, include_deprecated: bool = False) -> dict:
        """GET /api/alerts/{alert_id} → response['alert'] dict."""
        url = f"/api/alerts/{alert_id}"
        if include_deprecated:
            url += "?include_deprecated=true"
        resp = self.client.get(url)
        self.assertEqual(
            resp.status_code,
            200,
            f"alert fetch must yield 200; got {resp.status_code}; body: {resp.text}",
        )
        envelope = resp.json()
        self.assertIn(
            "alert",
            envelope,
            f"AlertDetailResponse envelope must wrap 'alert' key; got: {list(envelope.keys())}",
        )
        return envelope["alert"]

    # -------------------------------------------------------------------------
    # Test 1: top-level baseline_bacino exists, non-None, positive int
    # -------------------------------------------------------------------------
    def test_alert_detail_includes_baseline_bacino_top_level(self):
        """RED today: AlertDetail schema lacks baseline_bacino field.

        GREEN after Plan 02: top-level (NOT inside environment_split) field exists,
        is non-None for non-deprecated alerts with env_split, and is a positive int.
        """
        body = self._fetch_body(self.alert_id)
        self.assertIn(
            "baseline_bacino",
            body,
            f"AlertDetail must include top-level 'baseline_bacino' (NOT nested in environment_split); "
            f"got keys: {sorted(body.keys())}",
        )
        self.assertIsNotNone(
            body["baseline_bacino"],
            "baseline_bacino must be non-None for non-deprecated alert with env_split",
        )
        self.assertIsInstance(
            body["baseline_bacino"],
            int,
            f"baseline_bacino must be int; got {type(body['baseline_bacino']).__name__}",
        )
        self.assertGreater(
            body["baseline_bacino"],
            0,
            f"baseline_bacino must be > 0; got {body['baseline_bacino']!r}",
        )

    # -------------------------------------------------------------------------
    # Test 2: top-level baseline_coverage exists, non-None, in [0.0, 1.0]
    # -------------------------------------------------------------------------
    def test_alert_detail_includes_baseline_coverage_top_level(self):
        """RED today: AlertDetail schema lacks baseline_coverage field.

        GREEN after Plan 02: top-level field exists, is non-None, in valid coverage range.
        """
        body = self._fetch_body(self.alert_id)
        self.assertIn(
            "baseline_coverage",
            body,
            f"AlertDetail must include top-level 'baseline_coverage'; "
            f"got keys: {sorted(body.keys())}",
        )
        self.assertIsNotNone(
            body["baseline_coverage"],
            "baseline_coverage must be non-None for non-deprecated alert with env_split",
        )
        self.assertIsInstance(
            body["baseline_coverage"],
            float,
            f"baseline_coverage must be float; got {type(body['baseline_coverage']).__name__}",
        )
        self.assertGreaterEqual(body["baseline_coverage"], 0.0)
        self.assertLessEqual(body["baseline_coverage"], 1.0)

    # -------------------------------------------------------------------------
    # Test 3: REGRESSION — baseline_coverage ≠ avgCoverage + 0.05 (heuristic killed)
    # -------------------------------------------------------------------------
    def test_baseline_coverage_not_heuristic_avgcov_plus_005(self):
        """REGRESSION TEST per VALIDATION contract: server-side baseline_coverage
        MUST NOT equal the killed TriageSection.tsx:32 heuristic
        `Math.min(avgCoverage + 0.05, 0.95)`.

        Compute avg_coverage from environment_split.coverage_current values
        (mirroring the heuristic input), then assert the server value differs.
        Tolerance 0.001 — if a single alert lands within that band by coincidence,
        the test flags for review (desired safety net).
        """
        body = self._fetch_body(self.alert_id)
        env = body.get("environment_split", {})
        # The heuristic uses non-None coverage_current values.
        coverages = [
            v.get("coverage_current")
            for v in env.values()
            if isinstance(v, dict) and v.get("coverage_current") is not None
        ]
        if not coverages:
            self.skipTest(
                f"alert {self.alert_id} has no coverage_current values in env_split — cannot run heuristic regression"
            )
        avg_coverage_from_env_split = sum(coverages) / len(coverages)
        heuristic_value = avg_coverage_from_env_split + 0.05
        server_value = body.get("baseline_coverage")
        self.assertIsNotNone(
            server_value,
            "baseline_coverage must be present to compare against killed heuristic",
        )
        delta = abs(server_value - heuristic_value)
        self.assertGreater(
            delta,
            0.001,
            f"baseline_coverage {server_value!r} matches killed heuristic "
            f"avg_coverage+0.05={heuristic_value:.4f} within 0.001 — server-side "
            f"computation must NOT replicate TriageSection.tsx:32 logic.",
        )

    # -------------------------------------------------------------------------
    # Test 4: deprecated alert — graceful degradation (None or 0)
    # -------------------------------------------------------------------------
    def test_deprecated_alert_baseline_fields_none(self):
        """Deprecated alerts → graceful (no panic) per RESEARCH §6 Pydantic Optional.

        Plan 02 Opzione A: env_split may be empty/legacy → both fields None or 0
        (Pydantic Optional default).
        """
        if self.dep_alert_id is None:
            self.skipTest("no deprecated alerts in DB — cannot test graceful degradation")
        body = self._fetch_body(self.dep_alert_id, include_deprecated=True)
        self.assertIn(
            "baseline_bacino",
            body,
            "AlertDetail must declare baseline_bacino field even when value is None",
        )
        self.assertIn(
            "baseline_coverage",
            body,
            "AlertDetail must declare baseline_coverage field even when value is None",
        )
        self.assertIn(
            body["baseline_bacino"],
            (None, 0),
            f"deprecated alert baseline_bacino must be None or 0; got {body['baseline_bacino']!r}",
        )
        self.assertIn(
            body["baseline_coverage"],
            (None, 0, 0.0),
            f"deprecated alert baseline_coverage must be None or 0; got {body['baseline_coverage']!r}",
        )

    # -------------------------------------------------------------------------
    # Test 5: aggregation rule — baseline_bacino == sum(env.bacino_baseline)
    # -------------------------------------------------------------------------
    def test_baseline_bacino_matches_aggregation_of_env_split(self):
        """Asserts the EXACT aggregation rule from RESEARCH §6 `_compute_baseline_from_env_split`.

        baseline_bacino == sum(v.bacino_baseline for v in env_split.values() if dict)
        """
        body = self._fetch_body(self.alert_id)
        env = body.get("environment_split", {})
        expected = sum(
            v.get("bacino_baseline", 0)
            for v in env.values()
            if isinstance(v, dict)
        )
        self.assertEqual(
            body.get("baseline_bacino"),
            expected,
            f"baseline_bacino {body.get('baseline_bacino')!r} must equal "
            f"sum(env.bacino_baseline)={expected!r}; env keys: {list(env.keys())}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
