// Phase 19 V1 — Demand-layer taxonomy (Marco feedback 2026-05-19).
//
// Mirrors backend/db/demand_layers.py byte-for-byte. scripts/test_demand_layers.py
// asserts sync via TestDemandLayerTsMirrorSync; if you change a key here, change
// the Python source first, run the test, then update this file.

import type { ChannelGroup } from '../types/alert'

export type DemandLayer = 'DIRETTA' | 'DEAL' | 'OPEN_MARKET'

/**
 * channel_group -> demand_layer. Byte-identical with backend/db/demand_layers.py
 * CHANNEL_TO_DEMAND_LAYER. Marco verbatim: "diretta-deal-open".
 */
export const CHANNEL_TO_DEMAND_LAYER: Record<ChannelGroup, DemandLayer> = {
  'DIRECT': 'DIRETTA',
  'DEAL': 'DEAL',
  'GOOGLE_ADEX': 'OPEN_MARKET',
  'OPEN_BIDDING': 'OPEN_MARKET',
  'HEADER_BIDDING_MAGNITE': 'OPEN_MARKET',
  'HEADER_BIDDING_PUBMATIC': 'OPEN_MARKET',
  'TAM': 'OPEN_MARKET',
  // Legacy alias of pre-Phase-09 schema. Same semantics as GOOGLE_ADEX.
  'GOOGLE': 'OPEN_MARKET',
}

/**
 * OM sub-channels — used by OpenMarketDistributionPanel (V2) to render the
 * intra-OM breakdown when alert.demand_layer === 'OPEN_MARKET'.
 */
export const OPEN_MARKET_CHANNELS: ChannelGroup[] = [
  'GOOGLE_ADEX',
  'OPEN_BIDDING',
  'HEADER_BIDDING_MAGNITE',
  'HEADER_BIDDING_PUBMATIC',
  'TAM',
  'GOOGLE',
]

export const DEMAND_LAYER_LABELS: Record<DemandLayer, string> = {
  DIRETTA: 'Diretta',
  DEAL: 'Deal',
  OPEN_MARKET: 'Open Market',
}

export const DEMAND_LAYER_COLORS: Record<DemandLayer, string> = {
  DIRETTA: '#FF5722', // matches CHANNEL_COLORS.DIRECT
  DEAL: '#795548',    // matches CHANNEL_COLORS.DEAL
  OPEN_MARKET: '#4285F4', // GOOGLE_ADEX blue, representative of the OM bucket
}

/**
 * Resolve a channel_group to its demand_layer. Returns 'OPEN_MARKET' as a
 * defensive fallback for unknown values — backend CHECK constraint should
 * make this impossible, but the UI must not crash if the API ever drifts.
 */
export function demandLayerFor(channel: ChannelGroup | string): DemandLayer {
  return CHANNEL_TO_DEMAND_LAYER[channel as ChannelGroup] ?? 'OPEN_MARKET'
}
