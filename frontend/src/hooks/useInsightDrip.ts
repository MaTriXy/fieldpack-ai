import { useState, useRef, useCallback, useEffect } from 'react'

/**
 * Queue-based drip feed for pipeline insights.
 * Insights are enqueued instantly but displayed one at a time
 * at the given interval, preventing a wall of text.
 */
export function useInsightDrip(intervalMs = 1500) {
  const [insights, setInsights] = useState<string[]>([])
  const queueRef = useRef<string[]>([])
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [])

  const enqueueInsight = useCallback((text: string) => {
    queueRef.current.push(text)
    // Start drip if not already running
    if (!timerRef.current) {
      const drip = () => {
        const next = queueRef.current.shift()
        if (next) {
          setInsights((prev) => [...prev.slice(-4), next])
          timerRef.current = setTimeout(drip, intervalMs)
        } else {
          timerRef.current = null
        }
      }
      drip()
    }
  }, [intervalMs])

  const clearInsights = useCallback(() => {
    queueRef.current = []
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
    setInsights([])
  }, [])

  return { insights, enqueueInsight, clearInsights }
}
