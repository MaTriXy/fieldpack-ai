import { useState, useEffect, useCallback, useRef } from 'react'
import { apiUrl } from '../lib/config'

export function useBackendReachable(intervalMs: number = 15000): {
  reachable: boolean
  checking: boolean
} {
  const [reachable, setReachable] = useState(false)
  const [checking, setChecking] = useState(true)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const check = useCallback(async () => {
    setChecking(true)
    try {
      const res = await fetch(apiUrl('/health'), {
        signal: AbortSignal.timeout(5000),
      })
      setReachable(res.ok)
    } catch {
      setReachable(false)
    } finally {
      setChecking(false)
    }
  }, [])

  useEffect(() => {
    check()
    intervalRef.current = setInterval(check, intervalMs)

    const handleOnline = () => { check() }
    const handleOffline = () => { setReachable(false) }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [check, intervalMs])

  return { reachable, checking }
}
