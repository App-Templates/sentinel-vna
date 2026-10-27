import { useSearchParams } from 'react-router-dom'
import { useMemo, useCallback, useEffect } from 'react'
import {
  MONTH_LABELS,
  GEO_LABELS,
  PUBLISHER_TIER_LABELS,
  ENVIRONMENT_LABELS,
  SELL_TYPE_LABELS,
  type SellTypeKey,
} from '../lib/i18n-keys'
/**
 * Phase 14 — URL-state hook for PublishersPage (CORR-06).
 *
 * Mirrors useAlertFilters.ts line-by-line (UI-SPEC §CORR-06 line 514) but
 * upgrades to a typed filter shape per UI-SPEC §Type Contract Updates
 * lines 760-773. Six filters: year, month, sell_type_proxy,
 * publisher_tier, geo_cluster, gross_net.
 *
 * Whitelist enforcement: invalid URL values fall back to defaults silently
 * (no error UI, no console.warn) — mitigates URL-state injection per
 * ASVS V5.1.4 (UI-SPEC §threat model).
 *
 * Default-omission: setting a filter to its default removes the URL param,
 * keeping the default URL clean (`/publishers` not `?month=all&...`).
 *
 * Backwards-compat: legacy Phase 12 `?sell_type=` is read as
 * `sell_type_proxy`; on next setFilter the legacy param is deleted.
 *
 * UI-SPEC §"CORR-06 — URL State Migration" lines 506-543.
 */

// Re-exported from GrossNetToggle.tsx (Plan 14-02) for consumers of this hook.
export type GrossNetMode = 'gross' | 'net'

export type PublisherTier = 'A' | 'B' | 'C' | 'all'

export type MonthKey =
  | 'all' | '01' | '02' | '03' | '04' | '05' | '06'
  | '07' | '08' | '09' | '10' | '11' | '12'

export type GeoKey = 'all' | 'ITA' | 'ES' | 'LATAM' | 'PT' | 'OTHER'

// W-1 iter-1 — mirrors Environment union from frontend/src/types/alert.ts line 6.
export type EnvironmentKey = 'all' | 'WEB' | 'AMP' | 'APP' | 'UNKNOWN'

export interface PublishersFilters {
  year: number
  month: MonthKey
  sell_type_proxy: SellTypeKey
  publisher_tier: PublisherTier
  geo_cluster: GeoKey
  environment: EnvironmentKey   // W-1 iter-1
  gross_net: GrossNetMode
}

// Whitelists derived from i18n-keys.ts (Plan 14-01 SSoT). Kept private to
// this module — consumers use the typed unions, not the runtime arrays.
const MONTH_KEYS = Object.keys(MONTH_LABELS) as MonthKey[]
const GEO_KEYS = Object.keys(GEO_LABELS) as GeoKey[]
const TIER_KEYS = Object.keys(PUBLISHER_TIER_LABELS) as PublisherTier[]
const ENV_KEYS = Object.keys(ENVIRONMENT_LABELS) as EnvironmentKey[]
const SELL_TYPE_KEYS = Object.keys(SELL_TYPE_LABELS) as SellTypeKey[]
const GROSS_NET_KEYS: GrossNetMode[] = ['gross', 'net']

const DEFAULT_YEAR = 2025
const DEFAULTS: PublishersFilters = {
  year: DEFAULT_YEAR,
  month: 'all',
  sell_type_proxy: 'all',
  publisher_tier: 'all',
  geo_cluster: 'all',
  environment: 'all',
  gross_net: 'gross',
}

function parseYear(raw: string | null): number {
  if (!raw) return DEFAULT_YEAR
  const n = Number(raw)
  // Whitelist range: integer between 2000 and 2100 (defensive). Out of
  // range falls back to default.
  if (!Number.isInteger(n) || n < 2000 || n > 2100) return DEFAULT_YEAR
  return n
}

function parseFromWhitelist<T extends string>(
  raw: string | null,
  whitelist: T[],
  fallback: T,
): T {
  if (!raw) return fallback
  return (whitelist as string[]).includes(raw) ? (raw as T) : fallback
}

export function useTopPublishersFilters(): {
  filters: PublishersFilters
  setFilter: <K extends keyof PublishersFilters>(key: K, value: PublishersFilters[K]) => void
  clearFilters: () => void
  hasActiveFilters: boolean
} {
  const [searchParams, setSearchParams] = useSearchParams()

  // Phase 12 backward-compat: legacy `?sell_type=` is read as
  // `sell_type_proxy` if the new key is absent. UI-SPEC line 541.
  const legacySellType = searchParams.get('sell_type')
  const newSellType = searchParams.get('sell_type_proxy')
  const effectiveSellTypeRaw = newSellType ?? legacySellType

  const filters: PublishersFilters = useMemo(() => ({
    year: parseYear(searchParams.get('year')),
    month: parseFromWhitelist<MonthKey>(searchParams.get('month'), MONTH_KEYS, 'all'),
    sell_type_proxy: parseFromWhitelist<SellTypeKey>(effectiveSellTypeRaw, SELL_TYPE_KEYS, 'all'),
    publisher_tier: parseFromWhitelist<PublisherTier>(searchParams.get('publisher_tier'), TIER_KEYS, 'all'),
    geo_cluster: parseFromWhitelist<GeoKey>(searchParams.get('geo_cluster'), GEO_KEYS, 'all'),
    environment: parseFromWhitelist<EnvironmentKey>(searchParams.get('environment'), ENV_KEYS, 'all'),
    gross_net: parseFromWhitelist<GrossNetMode>(searchParams.get('gross_net'), GROSS_NET_KEYS, 'gross'),
  }), [searchParams, effectiveSellTypeRaw])

  // Side-effect: silently migrate legacy `?sell_type=` to
  // `?sell_type_proxy=` on next render. One-shot, no infinite loop because
  // useEffect dependency captures only when legacy is present and new is
  // absent. After migration, both reads return the same value.
  useEffect(() => {
    if (legacySellType && !newSellType) {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        // Whitelist-validate before writing forward.
        if ((SELL_TYPE_KEYS as string[]).includes(legacySellType)) {
          next.set('sell_type_proxy', legacySellType)
        }
        next.delete('sell_type')
        return next
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [legacySellType, newSellType])

  const setFilter = useCallback(
    <K extends keyof PublishersFilters>(key: K, value: PublishersFilters[K]) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        const defaultValue = DEFAULTS[key]
        if (value === defaultValue) {
          // Default-omission rule: setting back to default removes the
          // URL param. UI-SPEC line 539.
          next.delete(key as string)
        } else {
          next.set(key as string, String(value))
        }
        // Always cleanup legacy `sell_type` on any setFilter touching
        // sell_type_proxy. UI-SPEC line 541 'On next setFilter ... DELETE
        // sell_type'.
        if (key === 'sell_type_proxy') {
          next.delete('sell_type')
        }
        return next
      })
    },
    [setSearchParams],
  )

  const clearFilters = useCallback(() => {
    setSearchParams({})
  }, [setSearchParams])

  const hasActiveFilters =
    searchParams.has('year') ||
    searchParams.has('month') ||
    searchParams.has('sell_type_proxy') ||
    searchParams.has('sell_type') ||
    searchParams.has('publisher_tier') ||
    searchParams.has('geo_cluster') ||
    searchParams.has('environment') ||
    searchParams.has('gross_net')

  return { filters, setFilter, clearFilters, hasActiveFilters }
}
