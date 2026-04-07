/**
 * Backend connection configuration.
 *
 * In browser dev mode, relative paths go through the Vite proxy.
 * In a Capacitor APK, we need the full LAN URL to the edge server.
 */

const STORAGE_KEY = 'fieldpack_server_url'
const DEFAULT_SERVER = 'http://192.168.1.100:8000'

/** True when running inside a Capacitor native shell (APK). */
export function isNative(): boolean {
  // Capacitor injects this on the window object
  return !!(window as unknown as Record<string, unknown>).Capacitor
}

/** Get the saved server URL, or the default. */
export function getServerUrl(): string {
  if (!isNative()) return '' // browser dev mode uses relative paths + proxy
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_SERVER
}

/** Save a new server URL. */
export function setServerUrl(url: string): void {
  localStorage.setItem(STORAGE_KEY, url.replace(/\/+$/, ''))
}

/** Base URL for REST API calls. Empty string = relative (browser dev). */
export function getApiBase(): string {
  const server = getServerUrl()
  return server ? server : '/api'
}

/** Full WebSocket URL for the chat endpoint. */
export function getWsUrl(): string {
  const server = getServerUrl()
  if (server) {
    // Native: build full ws:// URL from server address
    const wsBase = server.replace(/^http/, 'ws')
    return `${wsBase}/chat/ws`
  }
  // Browser dev: use window.location (Vite proxy handles /ws)
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/chat/ws`
}

/** Build a full API endpoint URL. */
export function apiUrl(path: string): string {
  return `${getApiBase()}${path}`
}

/** Probe a single candidate URL; resolves to the base URL on success, rejects otherwise. */
async function probeHealth(baseUrl: string, timeoutMs: number): Promise<string> {
  const res = await fetch(`${baseUrl}/health`, { signal: AbortSignal.timeout(timeoutMs) })
  if (!res.ok) throw new Error('not ok')
  return baseUrl
}

/**
 * Scan the local network for the FieldPack backend.
 *
 * Probing order:
 *   1. Saved server URL (if any) — skip scan when it still responds.
 *   2. Windows hotspot default: 192.168.137.1:8000
 *   3. Common gateway IPs: 192.168.1.1, 192.168.0.1, 192.168.43.1, 10.0.0.1
 *   4. .1–.5 on 192.168.137.x subnet (parallel, 2 s timeout each)
 *
 * Returns the first URL that responds with HTTP 200, or null if none found.
 * Automatically saves the found URL via setServerUrl().
 */
export async function autoScanForServer(): Promise<string | null> {
  if (!isNative()) return null

  const TIMEOUT = 2000

  // 1. Saved URL still alive — no scan needed
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    try {
      const found = await probeHealth(saved, TIMEOUT)
      return found
    } catch {
      // Saved URL is dead — fall through to scan
    }
  }

  // 2. Parallel scan: Windows hotspot default, common gateways, subnet .2-.5
  //    Uses Promise.any — first to respond wins (no wrong-order issue).
  const allCandidates = [
    'http://192.168.137.1:8000',  // Windows hotspot default (most likely)
    'http://192.168.1.1:8000',
    'http://192.168.0.1:8000',
    'http://192.168.43.1:8000',   // Android hotspot
    'http://10.0.0.1:8000',
    // .2-.5 on Windows hotspot subnet (skip .1, already above)
    'http://192.168.137.2:8000',
    'http://192.168.137.3:8000',
    'http://192.168.137.4:8000',
    'http://192.168.137.5:8000',
  ]

  try {
    const found = await Promise.any(
      allCandidates.map((url) => probeHealth(url, TIMEOUT))
    )
    setServerUrl(found)
    return found
  } catch {
    // All candidates failed
  }

  return null
}
