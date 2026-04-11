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
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 5000)
    try {
      const res = await fetch(apiUrl('/health'), { signal: controller.signal })
      clearTimeout(timer)
      setReachable(res.ok)
    } catch {
      clearTimeout(timer)
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
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') check()
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [check, intervalMs])

  return { reachable, checking }
}
