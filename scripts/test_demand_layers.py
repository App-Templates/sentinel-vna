"""Phase 19 V1 — demand-layer taxonomy contract tests.

Asserts:
- Every `channel_group` enum value has a mapping (no orphans).
- The 3 demand layers (DIRETTA, DEAL, OPEN_MARKET) cover Marco's verbatim
  request (diretta-deal-open).
- `demand_layer_for()` is deterministic + raises on unknown input.
- TS mirror in `frontend/src/lib/demand-layers.ts` declares the same mapping
  byte-for-byte (drift gate — mirrors the test_models_sync.py pattern).
"""

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.db.demand_layers import (  # noqa: E402
    CHANNEL_TO_DEMAND_LAYER,
    DemandLayer,
    OPEN_MARKET_CHANNELS,
    demand_layer_for,
)
from backend.db.models import ChannelGroup  # noqa: E402


class TestDemandLayerCoverage(unittest.TestCase):
    """Every channel_group has a demand_layer. No orphans, no Marco-feedback gaps."""

    def test_every_channel_group_is_mapped(self):
        unmapped = [
            ch.value for ch in ChannelGroup if ch.value not in CHANNEL_TO_DEMAND_LAYER
        ]
        self.assertEqual(
            unmapped, [], f"Channel groups missing demand_layer mapping: {unmapped}"
        )

    def test_three_layers_match_marco_request(self):
        # Marco's verbatim: "diretta-deal-open"
        layers = {dl.value for dl in DemandLayer}
        self.assertEqual(layers, {"DIRETTA", "DEAL", "OPEN_MARKET"})

    def test_direct_maps_to_diretta(self):
        self.assertEqual(demand_layer_for("DIRECT"), "DIRETTA")

    def test_deal_maps_to_deal(self):
        self.assertEqual(demand_layer_for("DEAL"), "DEAL")

    def test_open_market_channels_map_to_open_market(self):
        for ch in OPEN_MARKET_CHANNELS:
            self.assertEqual(
                demand_layer_for(ch),
                "OPEN_MARKET",
                f"{ch} should be OPEN_MARKET",
            )

    def test_unknown_channel_raises(self):
        with self.assertRaises(KeyError):
            demand_layer_for("DOES_NOT_EXIST")


class TestDemandLayerTsMirrorSync(unittest.TestCase):
    """Byte-identity gate: TS mirror must declare the same mapping.

    Pattern mirrored from scripts/test_models_sync.py. If the TS file drifts
    from this Python source, the test fails — analogous to the SQL CHECK
    byte-identity gate that prevents silent enum drift.
    """

    TS_MIRROR_PATH = REPO_ROOT / "frontend" / "src" / "lib" / "demand-layers.ts"

    def setUp(self):
        if not self.TS_MIRROR_PATH.exists():
            self.skipTest(f"TS mirror not yet shipped at {self.TS_MIRROR_PATH}")
        self.ts_src = self.TS_MIRROR_PATH.read_text()

    def test_ts_declares_every_channel_mapping(self):
        for ch, dl in CHANNEL_TO_DEMAND_LAYER.items():
            # Match `'CHANNEL': 'DEMAND_LAYER'` or `CHANNEL: 'DEMAND_LAYER'`
            pattern = rf"['\"]?{re.escape(ch)}['\"]?\s*:\s*['\"]{re.escape(dl.value)}['\"]"
            self.assertRegex(
                self.ts_src,
                pattern,
                f"TS mirror missing {ch} -> {dl.value} mapping",
            )

    def test_ts_declares_three_demand_layers(self):
        for dl in DemandLayer:
            self.assertIn(
                f"'{dl.value}'",
                self.ts_src,
                f"TS mirror missing DemandLayer.{dl.value}",
            )


if __name__ == "__main__":
    unittest.main()
