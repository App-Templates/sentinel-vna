#!/usr/bin/env python3
"""Phase 11 API-02 — Nyquist Wave 0 RED test for sell_type filter on /api/publishers/top.

Authored before implementation per VALIDATION contract. Expected RED until Plan 03
wires the param. Wave 1 implementation (plan 11-03) will turn it GREEN.

Truth source: `config/sell_type_proxy.yaml` (canonical 5-value mapping). The parquet
column `sell_type_proxy` is already present (verified RESEARCH §5+§7); Plan 03 only
adds the FastAPI Query param + filter on `df_year` + `sell_type_filter` echo in
the response payload for transparency.

Run:  .venv/bin/python scripts/test_sell_type_filter.py
Exit: 0 = sell_type filter live + transparent (Wave 1 GREEN);
      non-zero = param ignored / sell_type_filter missing (Wave 0 RED — expected today).
"""
import os
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
# Constants — verbatim from config/sell_type_proxy.yaml
# ---------------------------------------------------------------------------

ENDPOINT_PATH = "/api/publishers/top"
VALID_SELL_TYPES = ["Open_Market", "Header_Bidding", "Direct", "Deal", "Other"]
# Year present in current parquet (verified RESEARCH §7 — max_date=2026-03-23).
QUERY_YEAR = 2026


class TestSellTypeFilter(unittest.TestCase):
    """API-02 sell_type filter assertion + input validation contract."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # -------------------------------------------------------------------------
    # Test 1: Open_Market filter returns rows + transparency contract
    # -------------------------------------------------------------------------
    def test_open_market_filter_returns_only_open_market(self):
        """RED today: param `sell_type` not yet accepted; payload has no sell_type_filter key.

        GREEN after Plan 03: response contains `sell_type_filter='Open_Market'` and a
        non-empty publishers list (Open_Market is the dominant sell_type in parquet).
        """
        resp = self.client.get(
            f"{ENDPOINT_PATH}?year={QUERY_YEAR}&sell_type=Open_Market"
        )
        self.assertEqual(
            resp.status_code,
            200,
            f"expected 200, got {resp.status_code}; body: {resp.text}",
        )
        body = resp.json()
        self.assertEqual(
            body.get("sell_type_filter"),
            "Open_Market",
            f"sell_type_filter must echo 'Open_Market' (transparency contract); body: {body!r}",
        )
        self.assertIn(
            "publishers",
            body,
            f"response must include 'publishers' list; body keys: {list(body.keys())}",
        )
        self.assertGreater(
            len(body["publishers"]),
            0,
            "Open_Market is the dominant sell_type — must return at least 1 publisher",
        )
        self.assertEqual(
            body.get("year"),
            QUERY_YEAR,
            f"year must echo {QUERY_YEAR}; got {body.get('year')!r}",
        )

    # -------------------------------------------------------------------------
    # Test 2: invalid sell_type → HTTP 400
    # -------------------------------------------------------------------------
    def test_invalid_sell_type_returns_400(self):
        """Invalid sell_type literal (`Programmatic_Direct`) must yield 400 with detail.

        The 5-value whitelist is fixed by `config/sell_type_proxy.yaml` — anything
        outside is rejected at the validation layer.
        """
        resp = self.client.get(
            f"{ENDPOINT_PATH}?year={QUERY_YEAR}&sell_type=Programmatic_Direct"
        )
        self.assertEqual(
            resp.status_code,
            400,
            f"invalid sell_type must yield 400; got {resp.status_code}; body: {resp.text}",
        )
        detail = resp.json().get("detail", "")
        # Detail may be string or list[dict] depending on FastAPI raising path.
        detail_text = detail if isinstance(detail, str) else str(detail)
        self.assertTrue(
            "sell_type" in detail_text or any(st in detail_text for st in VALID_SELL_TYPES),
            f"detail must reference 'sell_type' or list valid values; got: {detail_text!r}",
        )

    # -------------------------------------------------------------------------
    # Test 3: no filter → unchanged behavior (Phase 12 backwards-compat)
    # -------------------------------------------------------------------------
    def test_no_filter_unchanged_behavior(self):
        """Omitted `sell_type` → 200 + publishers list + sell_type_filter is None/empty.

        Backwards compat for Phase 12 frontend that does not yet pass the param.
        """
        resp = self.client.get(f"{ENDPOINT_PATH}?year={QUERY_YEAR}")
        self.assertEqual(
            resp.status_code,
            200,
            f"unfiltered call must yield 200; got {resp.status_code}; body: {resp.text}",
        )
        body = resp.json()
        self.assertIn(
            "publishers",
            body,
            f"response must include 'publishers' list; body keys: {list(body.keys())}",
        )
        self.assertIn(
            body.get("sell_type_filter"),
            (None, ""),
            f"sell_type_filter must be None/empty when no filter; got {body.get('sell_type_filter')!r}",
        )

    # -------------------------------------------------------------------------
    # Test 4: each valid sell_type → 200 (or 503 if zero rows in parquet)
    # -------------------------------------------------------------------------
    def test_each_valid_sell_type_returns_200(self):
        """All 5 valid whitelist values must be accepted by the endpoint.

        503 also acceptable for sell_types with zero rows in current parquet
        (e.g. `Other`/`TAM` may have no top-50 publishers). The contract is
        whitelist acceptance, not data presence.
        """
        for st in VALID_SELL_TYPES:
            with self.subTest(sell_type=st):
                resp = self.client.get(
                    f"{ENDPOINT_PATH}?year={QUERY_YEAR}&sell_type={st}"
                )
                self.assertIn(
                    resp.status_code,
                    (200, 503),
                    f"sell_type={st!r} must yield 200 or 503; got {resp.status_code}; "
                    f"body: {resp.text}",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
