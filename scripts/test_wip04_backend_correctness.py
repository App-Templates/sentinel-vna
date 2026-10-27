#!/usr/bin/env python3
"""Phase 12 Plan 03 (WIP-04 Commit C) — TDD RED-then-GREEN scaffold for backend correctness.

Authored BEFORE the WIP-04 cherry-pick is applied (RED gate). Wave 1 application
(`git apply --3way` of commit `7ea4a74`) flips these GREEN.

Four behaviors locked by this scaffold (mapped 1-to-1 onto plan 12-03 <behavior> block):

1. Bacino dedup: get_top_publishers returns total_bacino bounded by
   (naive_sum / max_n_channels) < corrected <= naive_sum for any publisher
   whose data spans >1 channel_group on any (date, environment, geo_cluster)
   cell. Concretely verified for `publisher_id='Mondadori'`.

2. revenue_status_24h response payload contains key `available_dates` whose
   value is `[str, ...]` with length <= 7 and each entry matches
   `^\\d{4}-\\d{2}-\\d{2}$`.

3. revenue_status_24h prev_year block: `weeks_averaged` is int in [1, 7];
   `hours` is array of 24 floats; sum(hours) ≈ total_revenue ±0.5%.

4. Path-based variant: `/api/metrics/revenue-status-24h/2026-03-23` returns
   the SAME body shape as `?date=2026-03-23` (field-by-field equality except
   for keys that may differ by floating-point rounding in `prev_year.hours`).

Run:  .venv/bin/python scripts/test_wip04_backend_correctness.py -v
Exit: 0 = WIP-04 applied + 4/4 tests pass (Wave 1 GREEN);
      non-zero = WIP-04 not applied / contract drift (Wave 0 RED — expected pre-cherry-pick).

Truth source: `git show 7ea4a74` (WIP commit on `wip/pre-10.2-rescue`).
"""
import os
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Bypass auth for tests (require_auth is a no-op outside production).
os.environ["ENVIRONMENT"] = "development"

from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

PUB_ENDPOINT = "/api/publishers/top"
REV24H_ENDPOINT = "/api/metrics/revenue-status-24h"

# Last complete day in the hourly parquet (verified live 2026-04-30).
PROBE_DATE = "2026-03-23"

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class TestWip04BacinoDedup(unittest.TestCase):
    """Behavior 1 — bacino dedup in get_top_publishers."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_mondadori_total_bacino_dedup(self):
        """RED today: total_bacino computed as naive `bacino.sum()` (no dedup).

        GREEN after WIP-04: total_bacino is corrected by dividing the per-cell
        bacino_per_cell by n_channels (channels per publisher×date×env×geo cell)
        before per-publisher aggregation.

        Bound: corrected total_bacino <= naive sum (equality only when every
        cell has n_channels=1). For Mondadori in current parquet (5+ channels
        per cell), corrected ~ naive / n_channels.
        """
        # Compute naive sum + corrected sum directly from the parquet for
        # comparison reference (the API already loads + caches it).
        from backend.api.publisher_routes import _load_adrequests

        df = _load_adrequests()
        self.assertIsNotNone(df, "ad_requests parquet must be loadable")
        df_year = df[df["date"].dt.year == 2026]
        df_pub = df_year[df_year["publisher_id"] == "Mondadori"]
        if df_pub.empty:
            self.skipTest("Mondadori not present in 2026 parquet slice")

        naive_sum = float(df_pub["bacino"].sum())

        # Reference corrected computation (mirrors WIP hunk).
        n_channels = df_year.groupby(
            ["publisher_id", "date", "environment", "geo_cluster"]
        )["channel_group"].nunique()
        bacino_per_cell = df_year.groupby(
            ["publisher_id", "date", "environment", "geo_cluster"]
        )["bacino"].sum()
        bacino_corrected = (bacino_per_cell / n_channels).groupby("publisher_id").sum()
        ref_corrected = float(bacino_corrected.get("Mondadori", 0.0))

        # Sanity: parquet IS over-counted (otherwise the WIP hunk is a no-op).
        max_n_channels = float(
            n_channels.loc["Mondadori"].max() if ("Mondadori" in n_channels.index.get_level_values(0)) else 1.0
        )
        if max_n_channels <= 1:
            self.skipTest(
                "Mondadori has n_channels<=1 across all cells — dedup invariant trivially holds"
            )

        # API call (the surface under test).
        resp = self.client.get(f"{PUB_ENDPOINT}?year=2026&limit=200")
        self.assertEqual(
            resp.status_code, 200, f"top publishers must yield 200; body: {resp.text[:200]}"
        )
        body = resp.json()
        rows = body.get("publishers", [])
        match = next((p for p in rows if p["publisher_id"] == "Mondadori"), None)
        self.assertIsNotNone(
            match,
            "Mondadori must appear in top publishers list (it's a top-5 publisher in the parquet)",
        )
        api_total_bacino = float(match["total_bacino"])

        # Bound 1: api total_bacino strictly less than naive_sum (since n_channels > 1).
        self.assertLess(
            api_total_bacino,
            naive_sum,
            f"BACINO DEDUP REGRESSION: api total_bacino ({api_total_bacino}) must be "
            f"strictly less than naive parquet sum ({naive_sum}) since max_n_channels="
            f"{max_n_channels} > 1. Equality means dedup logic is missing.",
        )

        # Bound 2: api total_bacino strictly greater than naive_sum / max_n_channels.
        # (The corrected value lies between 'all cells share max_n_channels' and 'all cells have 1 channel'.)
        lower_bound = naive_sum / max_n_channels
        self.assertGreater(
            api_total_bacino,
            lower_bound,
            f"BACINO DEDUP UNDER-BOUND: api total_bacino ({api_total_bacino}) must be "
            f">{lower_bound} (naive/{max_n_channels}). Excessive dedup detected.",
        )

        # Bound 3: api total_bacino matches reference computation within rounding.
        self.assertAlmostEqual(
            api_total_bacino,
            ref_corrected,
            delta=max(1.0, ref_corrected * 0.001),
            msg=f"api total_bacino ({api_total_bacino}) does NOT match reference "
            f"corrected computation ({ref_corrected}). WIP hunk arithmetic drift.",
        )


class TestWip04AvailableDates(unittest.TestCase):
    """Behavior 2 — available_dates field in revenue_status_24h."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_response_contains_available_dates_array(self):
        """RED today: response payload has no `available_dates` key.

        GREEN after WIP-04: array of last-7 complete-day date strings.
        """
        resp = self.client.get(REV24H_ENDPOINT)
        self.assertEqual(
            resp.status_code,
            200,
            f"revenue-status-24h must yield 200; body: {resp.text[:200]}",
        )
        body = resp.json()
        self.assertIn(
            "available_dates",
            body,
            f"response MUST contain 'available_dates'; got keys: {sorted(body.keys())}",
        )
        avail = body["available_dates"]
        self.assertIsInstance(avail, list, "available_dates must be a JSON array")
        self.assertLessEqual(
            len(avail),
            7,
            f"available_dates length must be <=7; got {len(avail)}",
        )
        self.assertGreater(
            len(avail),
            0,
            "available_dates must be non-empty (parquet has 60+ days of complete data)",
        )
        for entry in avail:
            self.assertIsInstance(entry, str, f"available_dates entry must be str; got {type(entry).__name__}")
            self.assertRegex(
                entry,
                DATE_PATTERN,
                f"available_dates entry {entry!r} does not match YYYY-MM-DD",
            )


class TestWip04PrevYearRolling(unittest.TestCase):
    """Behavior 3 — prev_year 7-week rolling YoY block."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_prev_year_has_weeks_averaged_and_hours(self):
        """RED today: prev_year has `hourly_avg` (single scalar), no `weeks_averaged`,
        no `hours` array.

        GREEN after WIP-04: prev_year.weeks_averaged is int [1,7], prev_year.hours
        is array of 24 floats summing to ~total_revenue (±0.5%).
        """
        resp = self.client.get(f"{REV24H_ENDPOINT}?date={PROBE_DATE}")
        self.assertEqual(resp.status_code, 200, f"body: {resp.text[:200]}")
        body = resp.json()
        prev_year = body.get("prev_year")
        if prev_year is None:
            self.skipTest(
                f"prev_year is None for {PROBE_DATE} (no prev-year same-weekday data) — "
                "cannot exercise rolling-YoY contract"
            )

        self.assertIn(
            "weeks_averaged",
            prev_year,
            f"prev_year MUST contain 'weeks_averaged'; got keys: {sorted(prev_year.keys())}",
        )
        weeks_averaged = prev_year["weeks_averaged"]
        self.assertIsInstance(weeks_averaged, int)
        self.assertGreaterEqual(weeks_averaged, 1)
        self.assertLessEqual(weeks_averaged, 7)

        self.assertIn("hours", prev_year, "prev_year MUST contain 'hours' array")
        hours = prev_year["hours"]
        self.assertIsInstance(hours, list)
        self.assertEqual(len(hours), 24, f"prev_year.hours must have 24 entries; got {len(hours)}")
        for h in hours:
            self.assertIsInstance(h, (int, float), f"prev_year.hours entry must be number; got {type(h).__name__}")

        prev_total = float(prev_year["total_revenue"])
        hours_sum = float(sum(hours))
        # Synthetic curve is weighted by baseline_hourly distribution; the
        # weighting is normalized so the sum equals py_rev within rounding.
        if prev_total > 0:
            tolerance = max(0.5, prev_total * 0.005)  # 0.5% or 0.5 EUR (small-value floor)
            self.assertAlmostEqual(
                hours_sum,
                prev_total,
                delta=tolerance,
                msg=f"sum(prev_year.hours)={hours_sum} must approximate prev_year.total_revenue="
                f"{prev_total} within ±{tolerance} (0.5%)",
            )


class TestWip04PathVariant(unittest.TestCase):
    """Behavior 4 — path-based variant /metrics/revenue-status-24h/{date_path}."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_path_variant_matches_query_variant(self):
        """RED today: path-based variant route does not exist (404).

        GREEN after WIP-04: GET /metrics/revenue-status-24h/{date_path} yields
        the same body shape as /metrics/revenue-status-24h?date={date_path}.
        """
        resp_path = self.client.get(f"{REV24H_ENDPOINT}/{PROBE_DATE}")
        self.assertEqual(
            resp_path.status_code,
            200,
            f"path variant {PROBE_DATE} must yield 200; got {resp_path.status_code}; body: {resp_path.text[:200]}",
        )
        resp_query = self.client.get(f"{REV24H_ENDPOINT}?date={PROBE_DATE}")
        self.assertEqual(resp_query.status_code, 200, f"body: {resp_query.text[:200]}")

        body_path = resp_path.json()
        body_query = resp_query.json()

        # Top-level keys must match exactly.
        self.assertEqual(
            sorted(body_path.keys()),
            sorted(body_query.keys()),
            f"path-variant keys {sorted(body_path.keys())} != query-variant keys {sorted(body_query.keys())}",
        )

        # Scalar/array fields that should match byte-for-byte (no recomputation between calls).
        for k in ("date", "day_of_week", "total_revenue", "total_baseline", "total_delta_pct", "available_dates"):
            if k in body_path and k in body_query:
                self.assertEqual(
                    body_path[k],
                    body_query[k],
                    f"field {k!r} differs between path and query variants: "
                    f"path={body_path[k]!r} vs query={body_query[k]!r}",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
