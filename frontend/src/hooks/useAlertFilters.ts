import { useSearchParams } from 'react-router-dom'
import { useMemo, useCallback } from 'react'
import type { AlertFilters } from '../api/client'

const FILTER_KEYS = ['severity', 'status', 'channel_group', 'from_date', 'to_date', 'assigned_to'] as const

export function useAlertFilters() {
  const [searchParams, setSearchParams] = useSearchParams()

  const filters: AlertFilters = useMemo(() => {
    const f: AlertFilters = {}
    for (const key of FILTER_KEYS) {
      const val = searchParams.get(key)
      if (val) {
        (f as Record<string, string>)[key] = val
      }
    }
    return f
  }, [searchParams])

  const setFilter = useCallback(
    (key: string, value: string) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        if (value) {
          next.set(key, value)
        } else {
          next.delete(key)
        }
        return next
      })
    },
    [setSearchParams]
  )

  const clearFilters = useCallback(() => {
    setSearchParams({})
  }, [setSearchParams])

  const hasActiveFilters = FILTER_KEYS.some((k) => searchParams.has(k))

  return { filters, setFilter, clearFilters, hasActiveFilters }
}
