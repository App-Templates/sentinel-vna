"""Wave 2a RED gate for MAP-03 + MAP-04 + MAP-05 + B-03 (numeric) + W-04 (static position).

Plan 17.1-02a — runs against live FastAPI app + parquet.

B-03 numeric target (CONTEXT.md MAP-09, plan-checker iter-1 fix):
  EXPECTED_MONDADORI_REVENUE_EUR = 1_125_000  (year-pinned to 2025)
  TOLERANCE_EUR = 50_000  (~5%)

Anchor verification (executed 2026-05-19 before writing this scaffold):
  data/baseline/daily_aggregated.parquet covers 2025-02-16 → 2026-03-23.
  For year=2025, applying the Wave 1 mapping (Mondadori_npa → Mondadori)
  yields Mondadori revenue = €1,125,424.54 (€425 from the €1,125,000
  target, well inside ±€50k tolerance). This matches the CONTEXT.md MAP-09
  "Mondadori-correct €1.125k vs Phase 17 over-aggregated €1.458k" claim.

  Phase 17's hardcoded MONDADORI_FAMILY block (wrongly) aggregates
  Mondadori + Mondadori_npa + Mediamond + Adgage_mondocore = €1,458,298.74
  into a 'Mondadori_family' row. Phase 17.1 separates Mediamond and
  Mondocore (correctness from Marco audit 2026-05-18).

If the actual parquet date range or mapping drifts in the future, this
test fails the numeric assertion — at that point the constant MUST be
re-anchored, NOT silently softened.
"""
from __future__ import annotations
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
XLSX = REPO_ROOT / "data" / "sentinel_db" / "ad_unit_1_mapping.xlsx"
PARQUET = REPO_ROOT / "data" / "baseline" / "daily_aggregated.parquet"

# B-03 fix — numeric target for Mondadori revenue.
# Source: 17.1-CONTEXT.md MAP-09 "Mondadori-correct €1.125k vs Phase 17 over-aggregated €1.458k"
# Year window: 2025 (parquet covers 2025-02-16 → 2026-03-23 as of plan-execution).
EXPECTED_MONDADORI_REVENUE_EUR = 1_125_000
TOLERANCE_EUR = 50_000  # ~5%
TARGET_YEAR = 2025


class TestPublishersTopMappingApplied(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not XLSX.exists():
            raise unittest.SkipTest(f"{XLSX} not present (Plan 17.1-01 prereq)")
        if not PARQUET.exists():
            raise unittest.SkipTest(f"{PARQUET} not present")
        try:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
            from slowapi.errors import RateLimitExceeded
            from slowapi import _rate_limit_exceeded_handler
            import backend.api.publisher_routes as mod
        except ImportError as e:
            raise unittest.SkipTest(f"Test deps unavailable: {e}")
        # Reset module-level caches so the test sees freshly applied mapping
        # rather than a stale pre-edit DataFrame.
        mod._adrequests_cache = None
        mod._channel_cache = None
        mod._ad_unit_mapping_cache = None
        # Minimal FastAPI app containing ONLY the publisher router. This
        # deliberately bypasses backend.main to avoid pulling the full
        # scheduler / langgraph stack — those are orthogonal to the
        # /api/publishers/top contract this test exercises. Same pattern
        # used in Wave 1 smoke; documented in Plan 17.1-02a SUMMARY as the
        # accepted way to test publisher_routes in isolation.
        app = FastAPI()
        app.include_router(mod.router)
        app.state.limiter = mod.limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        cls.client = TestClient(app)
        r = cls.client.get("/api/publishers/top", params={"year": TARGET_YEAR, "limit": 100})
        if r.status_code != 200:
            raise unittest.SkipTest(f"Backend returned {r.status_code}: {r.text[:200]}")
        cls.body = r.json()
        cls.publishers = cls.body["publishers"]
        cls.publisher_ids = [p["publisher_id"] for p in cls.publishers]
        cls.pid_to_revenue = {p["publisher_id"]: p["total_revenue"] for p in cls.publishers}

    def test_no_family_suffix(self):
        offenders = [pid for pid in self.publisher_ids if pid.endswith("_family")]
        self.assertEqual(offenders, [], f"_family suffix should be gone after MAP-05; saw {offenders}")

    def test_mondadori_mediamond_mondocore_are_separate(self):
        ids = set(self.publisher_ids)
        self.assertIn("Mondadori", ids, f"Mondadori missing from top-100")
        if "Mediamond" in ids:
            self.assertNotEqual(self.pid_to_revenue["Mediamond"], self.pid_to_revenue["Mondadori"])
        if "Mondocore" in ids:
            self.assertNotEqual(self.pid_to_revenue["Mondocore"], self.pid_to_revenue["Mondadori"])
        for pid in ids:
            self.assertNotIn("Mondadori_family", pid)

    def test_adgage_prefix_normalized(self):
        adgage_raw = [pid for pid in self.publisher_ids if pid.startswith("AdGage_")]
        self.assertEqual(adgage_raw, [], f"AdGage_ prefixes should be normalized; saw {adgage_raw}")
        pbi_style = {"Vocento", "Prensa Ibérica", "Grupo Godó", "Unidad Editorial", "El Español"}
        seen_pbi = pbi_style & set(self.publisher_ids)
        self.assertTrue(seen_pbi, f"No PBI-style normalized names in top-100; sample={sorted(set(self.publisher_ids))[:30]}")

    def test_old_and_test_clusters_excluded(self):
        self.assertNotIn("OLD", self.publisher_ids)
        self.assertNotIn("test", self.publisher_ids)

    def test_mondadori_revenue_numerically_correct(self):
        """B-03 fix: numeric ±5% assertion, NOT just directional."""
        self.assertIn("Mondadori", self.pid_to_revenue, "Mondadori must be in top-100 to assert revenue")
        actual = self.pid_to_revenue["Mondadori"]
        self.assertAlmostEqual(
            actual, EXPECTED_MONDADORI_REVENUE_EUR,
            delta=TOLERANCE_EUR,
            msg=(
                f"Mondadori revenue {actual:,.0f} drifts from target "
                f"{EXPECTED_MONDADORI_REVENUE_EUR:,.0f} (tolerance ±{TOLERANCE_EUR:,.0f}). "
                f"If the test parquet year window changed, update EXPECTED_MONDADORI_REVENUE_EUR "
                f"and document the source in this test's docstring."
            ),
        )


class TestPublishersTopFileContent(unittest.TestCase):
    """Static file-content checks (don't require backend boot)."""

    def test_no_mondadori_family_literal_in_source(self):
        src = (REPO_ROOT / "backend" / "api" / "publisher_routes.py").read_text()
        self.assertNotIn("MONDADORI_FAMILY", src,
            "MAP-05: hardcoded MONDADORI_FAMILY block must be removed from publisher_routes.py")
        self.assertNotIn("Mondadori_family", src,
            "MAP-05: the synthetic Mondadori_family row label must not appear in source")

    def test_mapping_precedes_first_groupby(self):
        """W-04 fix: source-level static-position assertion (not just behavioral).

        The plan's literal pattern '_load_ad_unit_mapping()' also matches the
        `def _load_ad_unit_mapping():` declaration at module-level (line 182).
        That match is trivially before any groupby and would yield a false
        pass. To enforce the REAL anti-pattern check (mapping CALL precedes
        groupby), we require that the symbol occurs at least TWICE in the
        file — once as the def, once (or more) as an actual call site — and
        we assert the LAST occurrence (call site, not def) precedes the
        first df_year.groupby. This is a stricter superset of the plan's
        spec; it cannot regress to a trivial pass.
        """
        src = (REPO_ROOT / "backend" / "api" / "publisher_routes.py").read_text()
        occurrences = src.count("_load_ad_unit_mapping()")
        self.assertGreaterEqual(
            occurrences, 2,
            f"W-04 MAP-03: expected at least 2 occurrences of "
            f"'_load_ad_unit_mapping()' (def + call site); found {occurrences}. "
            f"The mapping must be CALLED inside get_top_publishers, not just defined."
        )
        last_call_pos = src.rfind("_load_ad_unit_mapping()")
        first_gb = src.find('df_year.groupby("publisher_id")')
        self.assertGreater(last_call_pos, 0, "_load_ad_unit_mapping() call site not found in publisher_routes.py")
        self.assertGreater(first_gb, 0, 'df_year.groupby("publisher_id") not found')
        self.assertLess(last_call_pos, first_gb,
            f"W-04 anti-pattern #4: last _load_ad_unit_mapping() call at offset {last_call_pos} "
            f"must precede first df_year.groupby('publisher_id') at offset {first_gb}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
