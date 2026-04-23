import { useState, useEffect, useCallback, useRef } from 'react'
import { isNative, autoScanForServer, getServerUrl, apiUrl } from '../lib/config'

export interface ServerInfo {
  ip: string
  model: string
  pack: string
  ollama: string
}

export type ConnectionStatus = 'scanning' | 'connected' | 'disconnected'

export interface ServerConnectionState {
  status: ConnectionStatus
  serverInfo: ServerInfo | null
  scanProgress: string | null
  /** True when laptop itself has internet reachability (from /health.internet). */
  laptopHasInternet: boolean
  /** Convenience: same as status === 'connected'. */
  reachable: boolean
  retry: () => void
}

function parseHealth(data: Record<string, unknown>): ServerInfo {
  const model = data.model as Record<string, unknown> | null
  const pack = data.pack as Record<string, unknown> | null
  const serverUrl = getServerUrl()
  let ip = serverUrl
  try {
    ip = new URL(serverUrl).hostname
  } catch {
    // Fallback to full URL
  }
  return {
    ip,
    model: (model?.name as string) || 'FieldStation',
    pack: (pack?.pack_name as string) || (pack?.name as string) || (pack?.pack_id as string) || 'Unknown Pack',
    ollama: (data.ollama_version as string) || (data.ollama as string) || 'unknown',
  }
}

function parseInternet(data: Record<string, unknown>): boolean {
  const internet = data.internet as Record<string, unknown> | undefined
  return Boolean(internet?.online)
}

const POLL_INTERVAL_MS = 5_000
const HEALTH_TIMEOUT_MS = 3_000
// Backoff for native LAN rescan on disconnect: 0.5s → 2s → 5s → 15s (cap).
// Prevents unbounded radio hammering when the laptop is gone for a while.
const RESCAN_BACKOFF_MS = [500, 2_000, 5_000, 15_000]
// Browser-mode: require 2 consecutive failures before flipping to disconnected.
// Single 3s timeouts on congested WiFi are not a real outage.
const FAILURE_THRESHOLD = 2
// Frozen at module load — the app does not switch between web and native at runtime.
const native = isNative()

export function useServerConnection(): ServerConnectionState {
  const [status, setStatus] = useState<ConnectionStatus>(native ? 'scanning' : 'connected')
  const [serverInfo, setServerInfo] = useState<ServerInfo | null>(null)
  const [scanProgress, setScanProgress] = useState<string | null>(null)
  const [laptopHasInternet, setLaptopHasInternet] = useState(false)
  const [scanTrigger, setScanTrigger] = useState(0)
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const consecutiveFailuresRef = useRef(0)
  const rescanAttemptsRef = useRef(0)

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current !== null) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
    if (retryTimerRef.current !== null) {
      clearTimeout(retryTimerRef.current)
      retryTimerRef.current = null
    }
  }, [])

  const startPolling = useCallback(() => {
    stopPolling()
    consecutiveFailuresRef.current = 0
    rescanAttemptsRef.current = 0
    pollTimerRef.current = setInterval(async () => {
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS)
      try {
        const res = await fetch(apiUrl('/health'), { signal: controller.signal })
        clearTimeout(timer)
        if (!res.ok) throw new Error('not ok')
        const data = (await res.json()) as Record<string, unknown>
        consecutiveFailuresRef.current = 0
        setServerInfo(parseHealth(data))
        setLaptopHasInternet(parseInternet(data))
        setStatus('connected')
      } catch {
        clearTimeout(timer)
        consecutiveFailuresRef.current += 1
        if (consecutiveFailuresRef.current < FAILURE_THRESHOLD) return
        setStatus('disconnected')
        setLaptopHasInternet(false)
        // Stop the poll loop; schedule a LAN rescan with capped backoff.
        if (pollTimerRef.current !== null) {
          clearInterval(pollTimerRef.current)
          pollTimerRef.current = null
        }
        const idx = Math.min(rescanAttemptsRef.current, RESCAN_BACKOFF_MS.length - 1)
        rescanAttemptsRef.current += 1
        retryTimerRef.current = setTimeout(() => {
          setScanTrigger((n) => n + 1)
        }, RESCAN_BACKOFF_MS[idx])
      }
    }, POLL_INTERVAL_MS)
  }, [stopPolling])

  // Browser mode: try to get real server info from proxy, then poll for internet state.
  useEffect(() => {
    if (native) return
    let cancelled = false

    const fetchHealth = async () => {
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS)
      try {
        const res = await fetch(apiUrl('/health'), { signal: controller.signal })
        clearTimeout(timer)
        if (!res.ok) throw new Error('not ok')
        const data = (await res.json()) as Record<string, unknown>
        if (cancelled) return
        consecutiveFailuresRef.current = 0
        setServerInfo(parseHealth(data))
        setLaptopHasInternet(parseInternet(data))
        setStatus('connected')
      } catch {
        clearTimeout(timer)
        if (cancelled) return
        consecutiveFailuresRef.current += 1
        if (consecutiveFailuresRef.current < FAILURE_THRESHOLD) return
        setStatus('disconnected')
        setLaptopHasInternet(false)
      }
    }

    // Force an immediate re-check when the network or tab wakes up.
    const wakeCheck = () => {
      consecutiveFailuresRef.current = 0
      fetchHealth()
    }
    const onVisibility = () => {
      if (document.visibilityState === 'visible') wakeCheck()
    }

    fetchHealth()
    const interval = setInterval(fetchHealth, POLL_INTERVAL_MS)
    window.addEventListener('online', wakeCheck)
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      cancelled = true
      clearInterval(interval)
      window.removeEventListener('online', wakeCheck)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [])

  useEffect(() => {
    if (!native) return

    let cancelled = false

    const run = async () => {
      console.log('[conn] scan starting')
      setStatus('scanning')
      setServerInfo(null)
      setScanProgress('Starting scan…')
      stopPolling()

      const found = await autoScanForServer((msg) => {
        if (!cancelled) setScanProgress(msg)
      })
      console.log('[conn] scan result:', found)
      if (cancelled) return

      if (!found) {
        console.log('[conn] no server found, disconnected')
        setScanProgress(null)
        setStatus('disconnected')
        const idx = Math.min(rescanAttemptsRef.current, RESCAN_BACKOFF_MS.length - 1)
        rescanAttemptsRef.current += 1
        retryTimerRef.current = setTimeout(() => {
          if (!cancelled) setScanTrigger((n) => n + 1)
        }, RESCAN_BACKOFF_MS[idx])
        return
      }

      const ctrl = new AbortController()
      const tmr = setTimeout(() => ctrl.abort(), HEALTH_TIMEOUT_MS)
      try {
        const res = await fetch(`${found}/health`, { signal: ctrl.signal })
        clearTimeout(tmr)
        if (!res.ok) throw new Error('not ok')
        const data = (await res.json()) as Record<string, unknown>
        if (cancelled) return
        setServerInfo(parseHealth(data))
        setLaptopHasInternet(parseInternet(data))
        setScanProgress(null)
        setStatus('connected')
        startPolling()
      } catch {
        clearTimeout(tmr)
        if (!cancelled) {
          setScanProgress(null)
          setStatus('disconnected')
          const idx = Math.min(rescanAttemptsRef.current, RESCAN_BACKOFF_MS.length - 1)
          rescanAttemptsRef.current += 1
          retryTimerRef.current = setTimeout(() => {
            if (!cancelled) setScanTrigger((n) => n + 1)
          }, RESCAN_BACKOFF_MS[idx])
        }
      }
    }

    run()

    return () => {
      cancelled = true
      stopPolling()
    }
  }, [scanTrigger, startPolling, stopPolling])

  const retry = useCallback(() => {
    if (native) setScanTrigger((n) => n + 1)
  }, [])

  return {
    status,
    serverInfo,
    scanProgress,
    laptopHasInternet,
    reachable: status === 'connected',
    retry,
  }
}
