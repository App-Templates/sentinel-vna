import { useEffect, useRef, useState, useCallback } from 'react'

interface UseAutoRefreshOptions {
  intervalMs?: number
  enabled?: boolean
  onRefresh: () => void
}

export function useAutoRefresh({
  intervalMs = 30_000,
  enabled = true,
  onRefresh,
}: UseAutoRefreshOptions) {
  const [isActive, setIsActive] = useState(enabled)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const pause = useCallback(() => setIsActive(false), [])
  const resume = useCallback(() => setIsActive(true), [])

  useEffect(() => {
    if (!isActive) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    intervalRef.current = setInterval(() => {
      if (document.visibilityState === 'visible') {
        onRefresh()
        setLastRefresh(new Date())
      }
    }, intervalMs)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [isActive, intervalMs, onRefresh])

  // Pause when tab is not visible
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'hidden') {
        pause()
      } else if (enabled) {
        resume()
        // Refresh immediately when tab becomes visible again
        onRefresh()
        setLastRefresh(new Date())
      }
    }

    document.addEventListener('visibilitychange', handleVisibility)
    return () => document.removeEventListener('visibilitychange', handleVisibility)
  }, [enabled, pause, resume, onRefresh])

  return { isActive, lastRefresh, pause, resume }
}
