#!/usr/bin/env python3
"""Phase 17.4 D2CLOSE-02 — Athena connector unwhitelist + graceful fallback contract.

Tests that:
  (a) ALLOWED_CHANNEL_GROUPS now has 8 values matching the v1.2 canonical schema;
  (b) _validate_inputs accepts each of the 6 newly whitelisted channels;
  (c) _get_athena_client returns None gracefully when AWS creds are missing (mock);
  (d) data_fetcher_real propagates data_source='synthetic_no_athena' when
      active_source=athena AND Athena returns None in BACKTEST mode;
  (e) Plan 02 regression: GOOGLE_ADEX BACKTEST still emits data_source='real_csv'.

Run:  .venv/bin/python scripts/test_athena_unwhitelist.py
Exit: 0 = all 5 tests GREEN; non-zero = failure.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class TestAthenaUnwhitelist(unittest.TestCase):
    """Phase 17.4 D2CLOSE-02 — ALLOWED_CHANNEL_GROUPS expansion + synthetic_no_athena fallback."""

    def test_allowed_channel_groups_has_8_values(self):
        """ALLOWED_CHANNEL_GROUPS must equal the 8-value v1.2 canonical set."""
        from backend.connectors.athena import ALLOWED_CHANNEL_GROUPS

        self.assertEqual(len(ALLOWED_CHANNEL_GROUPS), 8)
        expected = {
            "GOOGLE",
            "GOOGLE_ADEX",
            "OPEN_BIDDING",
            "HEADER_BIDDING_MAGNITE",
            "HEADER_BIDDING_PUBMATIC",
            "TAM",
            "DIRECT",
            "DEAL",
        }
        self.assertEqual(ALLOWED_CHANNEL_GROUPS, expected)

    def test_validate_inputs_accepts_new_channels(self):
        """Each of the 6 newly whitelisted channels must pass _validate_inputs."""
        from backend.connectors.athena import _validate_inputs

        new_channels = (
            "GOOGLE_ADEX",
            "HEADER_BIDDING_MAGNITE",
            "HEADER_BIDDING_PUBMATIC",
            "TAM",
            "DIRECT",
            "DEAL",
        )
        for ch in new_channels:
            with self.subTest(channel=ch):
                try:
                    _validate_inputs(
                        ch,
                        "2026-03-22 01:00:00",
                        "2026-03-22 02:00:00",
                        "test_db",
                        "test_table",
                    )
                except ValueError as e:
                    self.fail(f"{ch} should be accepted but raised ValueError: {e}")

        # Negative case: truly unknown channel must still raise ValueError.
        with self.assertRaises(ValueError):
            _validate_inputs(
                "BOGUS_CHANNEL",
                "2026-03-22 01:00:00",
                "2026-03-22 02:00:00",
                "test_db",
                "test_table",
            )

    def test_get_athena_client_returns_none_without_creds(self):
        """_get_athena_client must return None gracefully when AWS creds are missing."""
        try:
            from botocore.exceptions import NoCredentialsError
        except ImportError:
            self.skipTest("botocore not installed in test environment")

        from backend.connectors import athena as athena_mod

        mock_boto = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = NoCredentialsError()
        mock_boto.client.side_effect = lambda svc, **kw: (
            mock_sts if svc == "sts" else MagicMock()
        )

        with patch.dict("sys.modules", {"boto3": mock_boto}):
            result = athena_mod._get_athena_client("us-east-1")

        self.assertIsNone(result)

    def test_data_fetcher_real_propagates_synthetic_no_athena_for_hbm(self):
        """When active_source=athena and Athena returns None, BACKTEST must tag
        data_source='synthetic_no_athena' (NOT the generic 'synthetic')."""
        from backend.agents import data_fetcher_real as dfr

        with (
            patch.object(dfr, "_get_active_source", return_value="athena"),
            patch.object(dfr, "_try_athena_fetch", return_value=None),
            patch.object(dfr, "_try_gam_fetch", return_value=None),
            patch.object(dfr, "_load_hourly_data", return_value=None),
        ):
            state = {
                "trigger_type": "A2",
                "channel_group": "HEADER_BIDDING_MAGNITE",
                "mode": "BACKTEST",
                "timestamp": "2026-03-20T07:00:00+00:00",
                "execution_errors": [],
            }
            result = dfr.data_fetcher_agent(state)

        self.assertEqual(
            result["data_source"],
            "synthetic_no_athena",
            f"expected 'synthetic_no_athena', got {result['data_source']!r}",
        )

    def test_data_fetcher_real_real_csv_unchanged_for_google_adex(self):
        """Regression: Plan 02 Path A path must still emit data_source='real_csv'
        for GOOGLE_ADEX BACKTEST (no mocking — exercises live hour_kpi.csv)."""
        from backend.agents.data_fetcher_real import data_fetcher_agent

        state = {
            "trigger_type": "A2",
            "channel_group": "GOOGLE_ADEX",
            "mode": "BACKTEST",
            "timestamp": "2026-03-22T01:00:00+00:00",
            "execution_errors": [],
        }
        result = data_fetcher_agent(state)

        self.assertEqual(
            result["data_source"],
            "real_csv",
            f"Plan 02 Path A regression: got {result['data_source']!r}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
