"""Demand-layer taxonomy — Phase 19 V1 closure (Marco feedback 2026-05-19).

Marco's verbatim feedback:
  "Alert per Channel a livello Demand (diretta-deal-open). All'interno dell'open
   ci puo' essere uno shift di revenue tra Channel quindi il calo di una puo'
   essere compensato da altro."

Maps the 8 `channel_group` values to 3 Demand layers so the UI can aggregate
alerts at the Demand level and surface intra-Open-Market shifts separately.

This is a PURE computed mapping. No DB schema change — the layer is derived
from `channel_group` on every read. Single source of truth lives here; backend
exposes it in `/api/alerts` + `/api/alerts/{id}` responses, frontend mirrors
the same mapping in `frontend/src/lib/demand-layers.ts`.

Byte-identity between this Python mapping and the TS mirror is asserted by
`scripts/test_demand_layers_sync.py`.
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class DemandLayer(str, Enum):
    DIRETTA = "DIRETTA"          # Direct sold by sales team (DIRECT)
    DEAL = "DEAL"                # Private marketplace / PMP deals (DEAL)
    OPEN_MARKET = "OPEN_MARKET"  # Programmatic open auction (AdEx, OB, HBM, HBP, TAM, legacy GOOGLE)


# Authoritative mapping. Update test_demand_layers_sync.py + the TS mirror
# in lockstep — otherwise the API + UI render diverge silently.
CHANNEL_TO_DEMAND_LAYER: Final[dict[str, DemandLayer]] = {
    "DIRECT": DemandLayer.DIRETTA,
    "DEAL": DemandLayer.DEAL,
    "GOOGLE_ADEX": DemandLayer.OPEN_MARKET,
    "OPEN_BIDDING": DemandLayer.OPEN_MARKET,
    "HEADER_BIDDING_MAGNITE": DemandLayer.OPEN_MARKET,
    "HEADER_BIDDING_PUBMATIC": DemandLayer.OPEN_MARKET,
    "TAM": DemandLayer.OPEN_MARKET,
    # Legacy alias of pre-Phase-09 schema. Same demand semantics as GOOGLE_ADEX.
    "GOOGLE": DemandLayer.OPEN_MARKET,
}


# OM sub-channels — used by the frontend OpenMarketDistributionPanel (V2)
# to enumerate which sub-channels to render in the intra-OM breakdown.
OPEN_MARKET_CHANNELS: Final[tuple[str, ...]] = (
    "GOOGLE_ADEX",
    "OPEN_BIDDING",
    "HEADER_BIDDING_MAGNITE",
    "HEADER_BIDDING_PUBMATIC",
    "TAM",
    "GOOGLE",
)


def demand_layer_for(channel_group: str) -> str:
    """Resolve `channel_group` -> demand layer string.

    Unknown channel groups raise KeyError. Callers that read from SQLite
    can rely on the CHECK constraint in alerts.channel_group to enforce
    membership upstream; an unknown value here is a data integrity bug.
    """
    return CHANNEL_TO_DEMAND_LAYER[channel_group].value
