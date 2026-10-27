#!/usr/bin/env python3
"""Phase 11 API-01 — Nyquist Wave 0 RED test for /api/metrics/network-totals PBI parity.

Authored before implementation per VALIDATION contract. Expected RED until Plan 02
lands the endpoint. Wave 1 implementation (plan 11-02) will turn it GREEN.

Truth source: email Vito 2026-04-22 — Jan 12 2026 GOOGLE_ADEX revenue_gross PBI €27.2k.
Verified live (RESEARCH §4): raw `data/sentinel_db/daily_kpi.csv` Jan 12 GOOGLE_ADEX
revenue_gross = €27,245.63 → +0.17% from PBI target = within ±2% tolerance.

Run:  .venv/bin/python scripts/test_network_totals_pbi_parity.py
Exit: 0 = endpoint live + within PBI bounds (Wave 1 GREEN);
      non-zero = endpoint missing or out of bounds (Wave 0 RED — expected today).
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
# PBI parity constants — verbatim from email Vito 2026-04-22 + RESEARCH §4
# ---------------------------------------------------------------------------

PBI_TARGET_GROSS = 27200.0          # email Vito 2026-04-22, Jan 12 GOOGLE_ADEX
PBI_TOLERANCE_PCT = 0.02            # ±2% per ROADMAP Phase 11 SC#1
LOWER_BOUND = PBI_TARGET_GROSS * (1 - PBI_TOLERANCE_PCT)  # 26,656.00
UPPER_BOUND = PBI_TARGET_GROSS * (1 + PBI_TOLERANCE_PCT)  # 27,744.00

ENDPOINT_PATH = "/api/metrics/network-totals"
TARGET_DATE = "2026-01-12"
TARGET_CHANNEL = "GOOGLE_ADEX"


class TestNetworkTotalsPbiParity(unittest.TestCase):
    """API-01 PBI-parity assertion + input validation contract."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # -------------------------------------------------------------------------
    # Test 1: PBI parity — Jan 12 GOOGLE_ADEX revenue_gross within ±2% of €27,200
    # -------------------------------------------------------------------------
    def test_pbi_parity_jan12_google_adex(self):
        """RED today: endpoint /api/metrics/network-totals does not exist (Plan 02 lands it).

        GREEN after Plan 02: revenue_gross within [26656.00, 27744.00] for Jan 12 GOOGLE_ADEX,
        currency=EUR, channel echoed verbatim, date echoed verbatim.
        """
        resp = self.client.get(
            f"{ENDPOINT_PATH}?date={TARGET_DATE}&channel={TARGET_CHANNEL}"
        )
        self.assertEqual(
            resp.status_code,
            200,
            f"expected 200, got {resp.status_code}; body: {resp.text}",
        )
        body = resp.json()
        self.assertIn(
            "revenue_gross",
            body,
            f"response must include revenue_gross; body: {body!r}",
        )
        rg = body["revenue_gross"]
        self.assertGreaterEqual(
            rg,
            LOWER_BOUND,
            f"revenue_gross {rg:,.2f} < {LOWER_BOUND:,.2f} (PBI €27,200 -2%)",
        )
        self.assertLessEqual(
            rg,
            UPPER_BOUND,
            f"revenue_gross {rg:,.2f} > {UPPER_BOUND:,.2f} (PBI €27,200 +2%)",
        )
        self.assertEqual(
            body.get("currency"),
            "EUR",
            f"currency must be EUR; got {body.get('currency')!r}",
        )
        self.assertEqual(
            body.get("channel"),
            TARGET_CHANNEL,
            f"channel must echo {TARGET_CHANNEL!r}; got {body.get('channel')!r}",
        )
        self.assertEqual(
            body.get("date"),
            TARGET_DATE,
            f"date must echo {TARGET_DATE!r}; got {body.get('date')!r}",
        )

    # -------------------------------------------------------------------------
    # Test 2: missing date param → 400 or 422 (FastAPI default vs custom validator)
    # -------------------------------------------------------------------------
    def test_missing_date_returns_400(self):
        """Missing required `date` param must surface a client error.

        Accepts 400 (custom Query validator) OR 422 (FastAPI default for missing
        required Query). Either is a valid implementation per RESEARCH §10.
        """
        resp = self.client.get(f"{ENDPOINT_PATH}?channel={TARGET_CHANNEL}")
        self.assertIn(
            resp.status_code,
            (400, 422),
            f"missing date must yield 400/422; got {resp.status_code}; body: {resp.text}",
        )

    # -------------------------------------------------------------------------
    # Test 3: malformed date → 400 or 422 with detail body
    # -------------------------------------------------------------------------
    def test_malformed_date_returns_400(self):
        """Malformed date string (`not-a-date`) must yield 400 or 422 with detail."""
        resp = self.client.get(
            f"{ENDPOINT_PATH}?date=not-a-date&channel={TARGET_CHANNEL}"
        )
        self.assertIn(
            resp.status_code,
            (400, 422),
            f"malformed date must yield 400/422; got {resp.status_code}; body: {resp.text}",
        )
        body = resp.json()
        self.assertIn(
            "detail",
            body,
            f"4xx response must include 'detail' key; body: {body!r}",
        )

    # -------------------------------------------------------------------------
    # Test 4: date outside CSV range → 404
    # -------------------------------------------------------------------------
    def test_date_out_of_csv_range_returns_404(self):
        """Date well beyond `daily_kpi.csv` max_date must yield 404 (no data)."""
        resp = self.client.get(
            f"{ENDPOINT_PATH}?date=2099-01-01&channel={TARGET_CHANNEL}"
        )
        self.assertEqual(
            resp.status_code,
            404,
            f"out-of-range date must yield 404; got {resp.status_code}; body: {resp.text}",
        )


    # -------------------------------------------------------------------------
    # Phase 17.4 D2CLOSE-01 — bypass_top50 param tests
    # -------------------------------------------------------------------------

    def test_bypass_top50_default_false_backward_compatible(self):
        """Phase 17.4 D-01: omitting bypass_top50 yields byte-identical response."""
        r1 = self.client.get(
            f"{ENDPOINT_PATH}?date={TARGET_DATE}&channel={TARGET_CHANNEL}"
        )
        r2 = self.client.get(
            f"{ENDPOINT_PATH}?date={TARGET_DATE}&channel={TARGET_CHANNEL}&bypass_top50=false"
        )
        self.assertEqual(r1.status_code, 200,
                         f"expected 200, got {r1.status_code}; body: {r1.text}")
        self.assertEqual(r2.status_code, 200,
                         f"expected 200, got {r2.status_code}; body: {r2.text}")
        self.assertEqual(
            r1.json()["revenue_gross"],
            r2.json()["revenue_gross"],
            "revenue_gross must be identical when bypass_top50 omitted vs explicit false",
        )
        # Phase 11 baseline preserved: Jan 12 GOOGLE_ADEX ≈ €27,245.63
        self.assertAlmostEqual(
            r1.json()["revenue_gross"],
            27245.63,
            delta=27245.63 * 0.02,
            msg="Phase 11 PBI baseline must be preserved (±2%)",
        )

    def test_bypass_top50_accepted_for_google_adex(self):
        """Phase 17.4 D-01 + D-03: bypass_top50=true accepted for GOOGLE_ADEX."""
        r = self.client.get(
            f"{ENDPOINT_PATH}?date={TARGET_DATE}&channel={TARGET_CHANNEL}&bypass_top50=true"
        )
        self.assertEqual(
            r.status_code,
            200,
            f"expected 200 for GOOGLE_ADEX bypass_top50=true; got {r.status_code}; body: {r.text}",
        )
        gross = r.json()["revenue_gross"]
        self.assertGreater(gross, 26700.66,
                           f"revenue_gross {gross} below lower bound 26700.66 (27245.63 - 2%)")
        self.assertLess(gross, 27789.94,
                        f"revenue_gross {gross} above upper bound 27789.94 (27245.63 + 2%)")

    def test_bypass_top50_rejected_for_other_channels(self):
        """Phase 17.4 D-03: bypass_top50=true is GOOGLE_ADEX-only whitelist."""
        for forbidden_channel in (
            "OPEN_BIDDING",
            "HEADER_BIDDING_MAGNITE",
            "TAM",
            "DIRECT",
            "DEAL",
        ):
            r = self.client.get(
                f"{ENDPOINT_PATH}?date={TARGET_DATE}&channel={forbidden_channel}&bypass_top50=true"
            )
            self.assertEqual(
                r.status_code,
                400,
                f"bypass_top50=true must be rejected for {forbidden_channel}; "
                f"got {r.status_code}; body: {r.text}",
            )
            detail = r.json().get("detail", "")
            self.assertIn(
                "bypass_top50",
                detail,
                f"error detail must mention 'bypass_top50'; got: {detail!r}",
            )
            self.assertIn(
                "GOOGLE_ADEX",
                detail,
                f"error detail must mention 'GOOGLE_ADEX'; got: {detail!r}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
