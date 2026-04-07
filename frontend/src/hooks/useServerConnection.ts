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

const POLL_INTERVAL_MS = 10_000
const RETRY_DELAY_MS = 3_000
const native = isNative()

export function useServerConnection(): ServerConnectionState {
  const [status, setStatus] = useState<ConnectionStatus>(native ? 'scanning' : 'connected')
  const [serverInfo, setServerInfo] = useState<ServerInfo | null>(null)
  const [scanTrigger, setScanTrigger] = useState(0)
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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
    pollTimerRef.current = setInterval(async () => {
      try {
        const res = await fetch(apiUrl('/health'), { signal: AbortSignal.timeout(5000) })
        if (!res.ok) throw new Error('not ok')
        const data = (await res.json()) as Record<string, unknown>
        setServerInfo(parseHealth(data))
        setStatus('connected')
      } catch {
        setStatus('disconnected')
        // Stop polling but schedule an auto-retry scan
        if (pollTimerRef.current !== null) {
          clearInterval(pollTimerRef.current)
          pollTimerRef.current = null
        }
        retryTimerRef.current = setTimeout(() => {
          setScanTrigger((n) => n + 1)
        }, RETRY_DELAY_MS)
      }
    }, POLL_INTERVAL_MS)
  }, [stopPolling])

  // Browser mode: try to get real server info from proxy
  useEffect(() => {
    if (native) return
    const controller = new AbortController()
    fetch(apiUrl('/health'), { signal: controller.signal })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setServerInfo(parseHealth(data as Record<string, unknown>))
      })
      .catch(() => {})
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!native) return

    let cancelled = false

    const run = async () => {
      setStatus('scanning')
      setServerInfo(null)
      stopPolling()

      const found = await autoScanForServer()
      if (cancelled) return

      if (!found) {
        setStatus('disconnected')
        // Auto-retry after delay
        retryTimerRef.current = setTimeout(() => {
          if (!cancelled) setScanTrigger((n) => n + 1)
        }, RETRY_DELAY_MS)
        return
      }

      try {
        const res = await fetch(`${found}/health`, { signal: AbortSignal.timeout(5000) })
        if (!res.ok) throw new Error('not ok')
        const data = (await res.json()) as Record<string, unknown>
        if (cancelled) return
        setServerInfo(parseHealth(data))
        setStatus('connected')
        startPolling()
      } catch {
        if (!cancelled) {
          setStatus('disconnected')
          retryTimerRef.current = setTimeout(() => {
            if (!cancelled) setScanTrigger((n) => n + 1)
          }, RETRY_DELAY_MS)
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

  return { status, serverInfo, retry }
}
