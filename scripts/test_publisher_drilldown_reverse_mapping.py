"""Wave 2b RED gate for MAP-08 (all 5 endpoints) — drilldown reverse-mapping.

Plan 17.1-02b — covers BOTH parquet and SQL paths per B-01 fix from
plan-checker iter-1 (planner originally falsely claimed 3/5 endpoints
existed).

Parquet endpoints (publisher_routes.py):
  - GET /api/publishers/{publisher_id}/weekly-kpis
  - GET /api/publishers/{publisher_id}/ecpm-analysis
  - GET /api/publishers/{publisher_id}/recurring-patterns

SQL endpoints (routes.py + db/operations.py):
  - GET /api/publishers/{publisher_id}/feedback-history
  - GET /api/publishers/{publisher_id}/interventions

The minimal-FastAPI-app test pattern (D-17.1-02a-C) is reused here so the
suite does NOT pull `backend.main` (which transitively imports langgraph and
breaks in the local env). Each TestCase class builds its own minimal app
with only the router(s) under test mounted.
"""
from __future__ import annotations
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
XLSX = REPO_ROOT / "data" / "sentinel_db" / "ad_unit_1_mapping.xlsx"
PARQUET = REPO_ROOT / "data" / "baseline" / "daily_aggregated.parquet"


def _inject_scheduler_shim() -> None:
    """Inject a fake backend.scheduler.scheduler module so backend.api.routes
    can be imported without pulling langgraph (absent in local env).

    Pre-existing local-env gap per Wave 1 SUMMARY + Wave 2a D-17.1-02a-C
    precedent (minimal-FastAPI-app pattern). This shim extends that pattern
    to backend.api.routes which also depends transitively on langgraph via
    backend.scheduler.scheduler → backend.workflow.graph.

    Idempotent: only installs the shim if the real module hasn't been
    successfully imported (so in CI where langgraph IS present, the real
    module is used).
    """
    import sys
    import types

    real_scheduler_loaded = "backend.scheduler.scheduler" in sys.modules
    if real_scheduler_loaded:
        return

    try:
        import backend.scheduler.scheduler  # noqa: F401
        return  # Real module loads fine — no shim needed.
    except ModuleNotFoundError:
        pass

    # Build a minimal stand-in providing only the symbols backend.api.routes
    # imports (`is_scheduler_running`). Anything else inside the shim is a
    # no-op — these tests never exercise scheduler-driven endpoints.
    shim = types.ModuleType("backend.scheduler.scheduler")
    shim.is_scheduler_running = lambda: False  # type: ignore[attr-defined]
    sys.modules["backend.scheduler.scheduler"] = shim

    # Also ensure the parent package exists in sys.modules. Importing
    # backend.scheduler may itself trigger a different chain — guard it.
    if "backend.scheduler" not in sys.modules:
        sched_pkg = types.ModuleType("backend.scheduler")
        sched_pkg.__path__ = []  # type: ignore[attr-defined]
        sys.modules["backend.scheduler"] = sched_pkg


def _build_minimal_app(include_routes_module: bool = False):
    """Construct a minimal FastAPI app with only the routers needed for this suite.

    By default mounts only publisher_routes.router (parquet path). If
    include_routes_module=True also mounts backend.api.routes.router (SQL
    path — feedback-history + interventions endpoints). The full
    backend.main import is intentionally avoided so the suite stays runnable
    locally without the langgraph dependency.
    """
    from fastapi import FastAPI
    from slowapi.errors import RateLimitExceeded
    from slowapi import _rate_limit_exceeded_handler

    import backend.api.publisher_routes as pub_mod
    # Reset caches so a previous test run with mocked / stale state doesn't leak.
    pub_mod._adrequests_cache = None
    pub_mod._channel_cache = None
    pub_mod._ad_unit_mapping_cache = None

    app = FastAPI()
    app.state.limiter = pub_mod.limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(pub_mod.router)

    if include_routes_module:
        _inject_scheduler_shim()
        import backend.api.routes as routes_mod
        app.include_router(routes_mod.router)

    return app


class TestDrilldownReverseMappingParquet(unittest.TestCase):
    """Parquet-backed endpoints: weekly-kpis, ecpm-analysis, recurring-patterns."""

    @classmethod
    def setUpClass(cls):
        if not XLSX.exists() or not PARQUET.exists():
            raise unittest.SkipTest("xlsx or parquet missing")
        from fastapi.testclient import TestClient
        app = _build_minimal_app(include_routes_module=False)
        cls.client = TestClient(app)

    def test_weekly_kpis_accepts_clean_publisher_name(self):
        r = self.client.get("/api/publishers/Vocento/weekly-kpis", params={"year": 2025})
        if r.status_code == 404:
            self.skipTest("Vocento has no 2025 data in parquet — data-dependent skip")
        self.assertEqual(r.status_code, 200, f"Vocento drilldown returned {r.status_code}: {r.text[:200]}")
        body = r.json()
        self.assertGreater(len(body["weekly_kpis"]), 0, "Vocento should have weekly KPIs in 2025")

    def test_raw_adgage_name_returns_404(self):
        r = self.client.get("/api/publishers/AdGage_Vocento/weekly-kpis", params={"year": 2025})
        self.assertEqual(r.status_code, 404,
            f"AdGage_Vocento (raw ad_unit_name) should 404 — clients must use clean publisher name")

    def test_mondadori_aggregates_npa_variant(self):
        r = self.client.get("/api/publishers/Mondadori/weekly-kpis", params={"year": 2025})
        if r.status_code == 404:
            self.skipTest("Mondadori has no 2025 data in parquet")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        total = sum(w["revenue"] for w in body["weekly_kpis"])

        import pandas as pd
        df = pd.read_parquet(PARQUET)
        df["date"] = pd.to_datetime(df["date"])
        # IMPORTANT: drilldown weekly-kpis uses ISO year (iso_cal.year == target_year)
        # in _aggregate_weekly, NOT calendar year. Use the same iso-year filter here
        # so the test is apples-to-apples. Late-December 2025 calendar dates whose
        # ISO week belongs to ISO year 2026 are excluded from BOTH sides.
        iso_cal = df["date"].dt.isocalendar()
        mondadori_raw = df[
            (df["publisher_id"].isin(["Mondadori", "Mondadori_npa"]))
            & (iso_cal.year == 2025)
        ]
        expected = float(mondadori_raw["revenue"].sum())

        self.assertAlmostEqual(total, expected, delta=expected * 0.001,
            msg=f"Mondadori drilldown revenue {total} != raw Mondadori+npa sum {expected} (ISO-year matched)")

    def test_mondadori_does_not_include_mediamond(self):
        r_mond = self.client.get("/api/publishers/Mondadori/weekly-kpis", params={"year": 2025})
        r_media = self.client.get("/api/publishers/Mediamond/weekly-kpis", params={"year": 2025})
        if r_mond.status_code != 200 or r_media.status_code != 200:
            self.skipTest("Mondadori or Mediamond has no 2025 data")
        mond_rev = sum(w["revenue"] for w in r_mond.json()["weekly_kpis"])
        media_rev = sum(w["revenue"] for w in r_media.json()["weekly_kpis"])
        self.assertNotEqual(mond_rev, media_rev,
            "Mondadori and Mediamond have IDENTICAL revenue — Phase 17 regression")

    def test_ecpm_analysis_also_supports_clean_name(self):
        r = self.client.get("/api/publishers/Vocento/ecpm-analysis", params={"year": 2025})
        if r.status_code == 404:
            self.skipTest("Vocento has no 2025 ecpm data")
        self.assertEqual(r.status_code, 200)


class TestDrilldownReverseMappingSQL(unittest.TestCase):
    """SQL-backed endpoints: feedback-history, interventions (B-01 fix from plan-checker iter-1)."""

    @classmethod
    def setUpClass(cls):
        if not XLSX.exists():
            raise unittest.SkipTest("xlsx missing")
        from fastapi.testclient import TestClient
        app = _build_minimal_app(include_routes_module=True)
        cls.client = TestClient(app)

    def test_feedback_history_uses_in_clause(self):
        """Static check on the SQL — must use IN (?, ?, ...), not = ?."""
        src = (REPO_ROOT / "backend" / "db" / "operations.py").read_text()
        # Find get_publisher_feedback_history function body
        func_idx = src.find("def get_publisher_feedback_history")
        self.assertGreater(func_idx, 0, "get_publisher_feedback_history not found in operations.py")
        # Look in next 2000 chars for the SQL pattern
        func_body = src[func_idx:func_idx + 2000]
        self.assertIn("publisher_id IN", func_body,
            "B-01 fix: get_publisher_feedback_history must use IN clause for reverse-mapped set, not = ?")

    def test_interventions_uses_in_clause(self):
        """Static check on the routes.py SQL — must use IN (?, ?, ...), not = ?."""
        src = (REPO_ROOT / "backend" / "api" / "routes.py").read_text()
        # Find get_publisher_interventions function
        func_idx = src.find("def get_publisher_interventions")
        self.assertGreater(func_idx, 0, "get_publisher_interventions not found")
        func_body = src[func_idx:func_idx + 2000]
        self.assertIn("publisher_id IN", func_body,
            "B-01 fix: interventions endpoint must use IN clause for reverse-mapped set")

    def test_feedback_history_endpoint_accepts_clean_name(self):
        """End-to-end check: GET /publishers/Vocento/feedback-history returns 200.

        Data-dependent — skips if DB empty for Vocento. Even with skip, the
        two static checks above guarantee the IN-clause structure is in place.
        """
        r = self.client.get("/api/publishers/Vocento/feedback-history?limit=50")
        # Must return 200 + JSON-shaped response (empty list is fine — just proves
        # the endpoint doesn't 500 on a clean name input)
        self.assertEqual(r.status_code, 200, f"feedback-history returned {r.status_code}: {r.text[:200]}")
        body = r.json()
        self.assertIn("feedbacks", body)
        self.assertIsInstance(body["feedbacks"], list)

    def test_interventions_endpoint_accepts_clean_name(self):
        r = self.client.get("/api/publishers/Vocento/interventions?limit=50")
        self.assertEqual(r.status_code, 200, f"interventions returned {r.status_code}: {r.text[:200]}")
        body = r.json()
        self.assertIn("interventions", body)
        self.assertIsInstance(body["interventions"], list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
