import { useState, useEffect, useCallback, useRef } from 'react'
import { apiUrl } from '../lib/config'

// Back-off schedule (seconds): 15 → 30 → 60 → 300 (cap)
const BACKOFF_STEPS = [15000, 30000, 60000, 300000]

export function useBackendReachable(): {
  reachable: boolean
  checking: boolean
} {
  const [reachable, setReachable] = useState(false)
  const [checking, setChecking] = useState(true)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const failuresRef = useRef(0)

  /** Return current back-off delay based on consecutive failure count. */
  const currentDelay = useCallback((): number => {
    const idx = Math.min(failuresRef.current, BACKOFF_STEPS.length - 1)
    return BACKOFF_STEPS[idx]
  }, [])

  /** Clear any running interval and start a new one with the given delay. */
  const reschedule = useCallback(
    (delay: number, checkFn: () => void) => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      intervalRef.current = setInterval(checkFn, delay)
    },
    []
  )

  const check = useCallback(async () => {
    setChecking(true)
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 5000)
    try {
      const res = await fetch(apiUrl('/health'), { signal: controller.signal })
      clearTimeout(timer)
      const ok = res.ok
      setReachable(ok)
      if (ok) {
        // Success: reset back-off to base interval
        failuresRef.current = 0
      } else {
        failuresRef.current += 1
      }
    } catch {
      clearTimeout(timer)
      setReachable(false)
      failuresRef.current += 1
    } finally {
      setChecking(false)
    }
  }, [])

  // Separate effect so reschedule fires after each check completes.
  // We re-schedule inside check's finally via a wrapper that knows reschedule.
  useEffect(() => {
    let cancelled = false

    async function runCheck() {
      await check()
      if (!cancelled) {
        reschedule(currentDelay(), runCheck)
      }
    }

    // Initial probe
    runCheck()

    const handleOnline = () => {
      // Network came back — reset failures and probe immediately
      failuresRef.current = 0
      if (intervalRef.current) clearInterval(intervalRef.current)
      runCheck()
    }
    const handleOffline = () => { setReachable(false) }
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        failuresRef.current = 0
        if (intervalRef.current) clearInterval(intervalRef.current)
        runCheck()
      }
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      cancelled = true
      if (intervalRef.current) clearInterval(intervalRef.current)
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [check, reschedule, currentDelay])

  return { reachable, checking }
}
