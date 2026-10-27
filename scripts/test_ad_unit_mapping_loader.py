"""Wave 0 RED gate for MAP-02 — _load_ad_unit_mapping() contract test.

Plan 17.1-01 Task 2 — runs against live data/sentinel_db/ad_unit_1_mapping.xlsx.
Skips if the xlsx is absent (Task 1 not yet executed).
"""
from __future__ import annotations
import os
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
XLSX = REPO_ROOT / "data" / "sentinel_db" / "ad_unit_1_mapping.xlsx"


class TestLoadAdUnitMapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not XLSX.exists():
            raise unittest.SkipTest(f"{XLSX} not present (Plan 17.1-01 Task 1 prereq)")
        from backend.api.publisher_routes import _load_ad_unit_mapping
        # staticmethod wrapper prevents Python's bound-method semantics from
        # passing `self` as a positional argument when called via `self.loader()`.
        cls.loader = staticmethod(_load_ad_unit_mapping)
        import backend.api.publisher_routes as mod
        mod._ad_unit_mapping_cache = None

    def test_returns_dict(self):
        m = self.loader()
        self.assertIsInstance(m, dict)
        self.assertGreaterEqual(len(m), 432)

    def test_mondadori_npa_collapses_to_mondadori(self):
        m = self.loader()
        self.assertEqual(m["Mondadori_npa"], "Mondadori")
        self.assertEqual(m["Mondadori"], "Mondadori")

    def test_mediamond_and_mondocore_separate_from_mondadori(self):
        m = self.loader()
        self.assertEqual(m["Mediamond"], "Mediamond")
        self.assertEqual(m["Adgage_mondocore"], "Mondocore")
        self.assertNotEqual(m["Mediamond"], "Mondadori")
        self.assertNotEqual(m["Adgage_mondocore"], "Mondadori")

    def test_adgage_prefix_normalizes(self):
        m = self.loader()
        self.assertEqual(m["AdGage_Vocento"], "Vocento")

    def test_old_and_test_clusters_present(self):
        m = self.loader()
        publishers = set(m.values())
        self.assertIn("OLD", publishers)
        self.assertIn("test", publishers)

    def test_cache_returns_same_object(self):
        m1 = self.loader()
        m2 = self.loader()
        self.assertIs(m1, m2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
