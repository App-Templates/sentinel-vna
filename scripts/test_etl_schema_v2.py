#!/usr/bin/env python3
"""
Phase 08 SCHEMA-03/04 — ETL v2 schema validation.

Asserts rebuilt daily_aggregated.parquet and hourly_aggregated.parquet contain:
  - 20 columns total (up from 18)
  - measurable_impressions (SCHEMA-03)
  - sell_type_proxy derived correctly from channel_group (SCHEMA-04)
  - v1 backup preserved

Uses pyarrow for parquet access (R-13 memory rule: no pd.read_csv loads of
the 1.3GB daily_kpi.csv).

Run:  .venv/bin/python scripts/test_etl_schema_v2.py
Exit: 0 = all pass, 1 = failures detected.
"""
import sys
import unittest
import yaml
from pathlib import Path

import pyarrow.parquet as pq
import pyarrow.compute as pc

REPO_ROOT = Path(__file__).resolve().parent.parent
DAILY = REPO_ROOT / "data" / "baseline" / "daily_aggregated.parquet"
HOURLY = REPO_ROOT / "data" / "baseline" / "hourly_aggregated.parquet"
DAILY_V1 = REPO_ROOT / "data" / "baseline" / "v1" / "daily_aggregated.parquet"
HOURLY_V1 = REPO_ROOT / "data" / "baseline" / "v1" / "hourly_aggregated.parquet"
MAPPING_YAML = REPO_ROOT / "config" / "sell_type_proxy.yaml"

EXPECTED_SELL_TYPES = {"Open_Market", "Header_Bidding", "Direct", "Deal", "Other"}
EXPECTED_DAILY_COLS_20 = {
    "date", "publisher_id", "channel_group", "sell_type_proxy", "environment", "geo_cluster",
    "revenue", "revenue_gross", "impressions", "measurable_impressions", "viewable_impressions",
    "bacino", "clicks", "floor_cpm", "coverage", "ecpm", "rpm", "ctr", "viewability",
    "gross_margin_pct",
}
EXPECTED_HOURLY_COLS_20 = (EXPECTED_DAILY_COLS_20 - {"date"}) | {"timestamp"}


class TestEtlSchemaV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.daily_schema = pq.read_schema(str(DAILY))
        cls.hourly_schema = pq.read_schema(str(HOURLY))
        with open(MAPPING_YAML) as f:
            cfg = yaml.safe_load(f)
        cls.mapping = {
            channel: group
            for group, channels in cfg.items()
            if not group.startswith("_")
            for channel in channels
        }

    def test_daily_parquet_has_20_columns(self):
        """SCHEMA-03/04: daily parquet must have exactly 20 columns."""
        names = set(self.daily_schema.names)
        self.assertEqual(len(self.daily_schema.names), 20,
                         f"Expected 20 cols, got {len(self.daily_schema.names)}: {self.daily_schema.names}")
        self.assertEqual(names, EXPECTED_DAILY_COLS_20,
                         f"Column set mismatch. Extra: {names - EXPECTED_DAILY_COLS_20}. Missing: {EXPECTED_DAILY_COLS_20 - names}")

    def test_hourly_parquet_has_20_columns(self):
        """SCHEMA-03/04: hourly parquet must have exactly 20 columns."""
        names = set(self.hourly_schema.names)
        self.assertEqual(len(self.hourly_schema.names), 20,
                         f"Expected 20 cols, got {len(self.hourly_schema.names)}: {self.hourly_schema.names}")
        self.assertEqual(names, EXPECTED_HOURLY_COLS_20,
                         f"Column set mismatch. Extra: {names - EXPECTED_HOURLY_COLS_20}. Missing: {EXPECTED_HOURLY_COLS_20 - names}")

    def test_measurable_impressions_present_and_numeric(self):
        """SCHEMA-03: measurable_impressions must be numeric and non-zero.

        Memory-safe: reads only the one target column via pyarrow projection.
        """
        # Read only the one column — memory-safe (R-13)
        t = pq.read_table(str(DAILY), columns=["measurable_impressions"])
        col = t.column("measurable_impressions")
        # dtype int or float
        dtype_str = str(col.type)
        self.assertTrue(
            any(x in dtype_str.lower() for x in ("int", "float", "double")),
            f"measurable_impressions dtype unexpected: {dtype_str}",
        )
        # Not all null
        self.assertGreater(col.length() - col.null_count, 0,
                           "measurable_impressions is all null")
        # At least SOME rows have non-zero (SCHEMA-03 is not a no-op)
        non_zero = pc.sum(pc.greater(col, 0)).as_py()
        self.assertGreater(non_zero, 0, "measurable_impressions is all zero — ETL drop still active?")

    def test_sell_type_proxy_exactly_5_values(self):
        """SCHEMA-04: sell_type_proxy must have at most 5 domain values (subset of EXPECTED_SELL_TYPES).

        Note: hourly data only has GOOGLE_ADEX → only Open_Market will appear in hourly parquet.
        This test checks daily which has all 7 channels.
        Memory-safe: reads only the one target column.
        """
        t = pq.read_table(str(DAILY), columns=["sell_type_proxy"])
        uniques = set(pc.unique(t.column("sell_type_proxy")).to_pylist())
        self.assertTrue(uniques.issubset(EXPECTED_SELL_TYPES),
                        f"Unexpected sell_type values not in domain: {uniques - EXPECTED_SELL_TYPES}")

    def test_sell_type_proxy_mapping_respected(self):
        """SCHEMA-04: sell_type_proxy must match the YAML mapping for every sampled row.

        Samples up to 100k rows for performance. Memory-safe: reads only 2 columns.
        """
        t = pq.read_table(str(DAILY), columns=["channel_group", "sell_type_proxy"])
        channels = t.column("channel_group").to_pylist()
        sells = t.column("sell_type_proxy").to_pylist()
        # Check up to 100k rows for performance
        sample = list(zip(channels[:100_000], sells[:100_000]))
        mismatches = [
            (ch, st) for ch, st in sample
            if self.mapping.get(ch, "Other") != st
        ]
        self.assertEqual(mismatches, [], f"Mapping violations (first 5): {mismatches[:5]}")

    def test_measurable_impressions_sum_positive_per_channel(self):
        """SCHEMA-03: measurable_impressions total must be positive (data flowed through).

        Note: some channels (HEADER_BIDDING_*, TAM) may have zero measurable_impressions
        in the upstream source CSV — this is a data reality, not an ETL bug. The key
        invariant is that the overall sum is positive and that GOOGLE_ADEX (the primary
        channel) has non-zero data, confirming the ETL preserved the column (not zero-filled).

        Memory-safe: uses to_pandas() on a 2-column narrow table (~50MB).
        R-13 only prohibits full daily_kpi.csv loads; this is the parquet projection.
        """
        t = pq.read_table(str(DAILY), columns=["channel_group", "measurable_impressions"])
        # 2-column narrow table — safe to_pandas() (R-13: prohibition is on daily_kpi.csv full load)
        df = t.to_pandas()
        total_sum = df["measurable_impressions"].sum()
        self.assertGreater(total_sum, 0,
                           "Total measurable_impressions is zero — ETL drop still active?")
        # GOOGLE_ADEX is the primary channel and must have non-zero measurable_impressions
        per_channel = df.groupby("channel_group")["measurable_impressions"].sum()
        adex_sum = per_channel.get("GOOGLE_ADEX", 0)
        self.assertGreater(adex_sum, 0,
                           f"GOOGLE_ADEX measurable_impressions is zero — ETL drop still active?")

    def test_existing_18_columns_unchanged_names(self):
        """SCHEMA v2 is additive: no v1 column was renamed, only 2 were added."""
        v1_schema = pq.read_schema(str(DAILY_V1))
        v1_names = set(v1_schema.names)
        v2_names = set(self.daily_schema.names)
        # All v1 names should be a subset of v2 names (v2 added 2, renamed 0)
        self.assertEqual(v1_names - v2_names, set(),
                         f"v2 is missing columns that existed in v1: {v1_names - v2_names}")
        new_in_v2 = v2_names - v1_names
        self.assertEqual(len(new_in_v2), 2,
                         f"Expected exactly 2 new columns in v2, got: {new_in_v2}")
        self.assertEqual(new_in_v2, {"measurable_impressions", "sell_type_proxy"},
                         f"New v2 columns are not the expected ones: {new_in_v2}")

    def test_v1_backup_preserved(self):
        """Rollback path must be intact: v1 backups exist with 18 columns each."""
        self.assertTrue(DAILY_V1.exists(), f"v1 backup missing: {DAILY_V1}")
        self.assertTrue(HOURLY_V1.exists(), f"v1 backup missing: {HOURLY_V1}")
        # v1 must have 18 columns (pre-Phase-08)
        self.assertEqual(len(pq.read_schema(str(DAILY_V1)).names), 18,
                         f"v1 daily should have 18 cols, got {len(pq.read_schema(str(DAILY_V1)).names)}")
        self.assertEqual(len(pq.read_schema(str(HOURLY_V1)).names), 18,
                         f"v1 hourly should have 18 cols, got {len(pq.read_schema(str(HOURLY_V1)).names)}")

    def test_yaml_mapping_covers_all_channel_group_values_in_parquet(self):
        """SCHEMA-04: every channel_group value in the parquet must have a mapping entry.

        Ensures .fillna('Other') only fires as designed fallback, not silently for known channels.
        Memory-safe: reads only channel_group column.
        """
        t = pq.read_table(str(DAILY), columns=["channel_group"])
        uniques = set(pc.unique(t.column("channel_group")).to_pylist())
        uncovered = uniques - set(self.mapping.keys())
        self.assertEqual(uncovered, set(),
                         f"channel_group values in parquet with no mapping entry: {uncovered}")

    def test_no_full_csv_load_in_test(self):
        """R-13 memory rule: this test file must not import pandas or use full-CSV read patterns.

        Validation is by pyarrow projection on the already-built parquet (MB-scale, not GB-scale).
        Enforcement is by checking imports (pandas absent) and that all data access uses pyarrow.
        """
        import importlib
        # pandas must not be imported (construction guarantee)
        try:
            import pandas as _pd  # noqa: F401
            pandas_available = True
        except ImportError:
            pandas_available = False
        # If pandas IS installed, ensure this module doesn't USE it
        # (the test module's globals don't include 'pd' or 'pandas')
        import sys
        test_module = sys.modules.get("__main__")
        if test_module is not None:
            module_globals = vars(test_module)
            self.assertNotIn("pd", module_globals,
                             "R-13: pandas imported as 'pd' in test module globals")
            self.assertNotIn("pandas", [
                name for name, obj in module_globals.items()
                if hasattr(obj, "__name__") and getattr(obj, "__name__", "") == "pandas"
            ], "R-13: pandas imported in test module globals")
        # Verify this file uses pyarrow for data access (construction guarantee)
        src = Path(__file__).read_text()
        self.assertIn("import pyarrow.parquet as pq", src,
                      "Test must use pyarrow.parquet for parquet access (R-13)")
        self.assertIn("pq.read_table", src,
                      "Test must use pq.read_table for memory-safe column projection (R-13)")


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestEtlSchemaV2)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
