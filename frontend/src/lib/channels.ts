import type { ChannelGroup } from '../types/alert'

export const CHANNEL_COLORS: Record<string, string> = {
  GOOGLE_ADEX: '#4285F4',
  OPEN_BIDDING: '#34A853',
  HEADER_BIDDING_MAGNITE: '#FF6D01',
  HEADER_BIDDING_PUBMATIC: '#9C27B0',
  TAM: '#00BCD4',
  DIRECT: '#FF5722',
  DEAL: '#795548',
  // Legacy fallback
  GOOGLE: '#4285F4',
}

export const CHANNEL_LABELS: Record<string, string> = {
  GOOGLE_ADEX: 'Google AdX',
  OPEN_BIDDING: 'Open Bidding',
  HEADER_BIDDING_MAGNITE: 'HB Magnite',
  HEADER_BIDDING_PUBMATIC: 'HB PubMatic',
  TAM: 'TAM',
  DIRECT: 'Direct',
  DEAL: 'Deal',
  GOOGLE: 'Google',
}

export const ALL_CHANNELS: ChannelGroup[] = [
  'GOOGLE_ADEX',
  'OPEN_BIDDING',
  'HEADER_BIDDING_MAGNITE',
  'HEADER_BIDDING_PUBMATIC',
  'TAM',
  'DIRECT',
  'DEAL',
]
