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

/** Full WebSocket URL for the mission pipeline endpoint. */
export function getMissionWsUrl(): string {
  const server = getServerUrl()
  if (server) {
    const wsBase = server.replace(/^http/, 'ws')
    return `${wsBase}/mission/ws`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/mission/ws`
}

/** Build a full API endpoint URL. */
export function apiUrl(path: string): string {
  return `${getApiBase()}${path}`
}

/** Probe a single candidate URL; resolves to the base URL on success, rejects otherwise. */
async function probeHealth(baseUrl: string, timeoutMs: number): Promise<string> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(`${baseUrl}/health`, { signal: controller.signal })
    clearTimeout(timer)
    if (!res.ok) throw new Error('not ok')
    return baseUrl
  } catch (err) {
    clearTimeout(timer)
    throw err
  }
}

/**
 * Get the device's local IP via WebRTC (works in Android WebView, no plugins).
 * Returns e.g. "192.168.0.42" or null if detection fails.
 */
async function getLocalIp(): Promise<string | null> {
  try {
    const pc = new RTCPeerConnection({ iceServers: [] })
    pc.createDataChannel('')
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    return await new Promise<string | null>((resolve) => {
      const timeout = setTimeout(() => { pc.close(); resolve(null) }, 2000)
      pc.onicecandidate = (e) => {
        if (!e.candidate) return
        // ICE candidate line contains the local IP, e.g. "... 192.168.0.42 ..."
        const match = e.candidate.candidate.match(/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/)
        if (match && !match[1].startsWith('0.') && match[1] !== '0.0.0.0') {
          clearTimeout(timeout)
          pc.close()
          resolve(match[1])
        }
      }
    })
  } catch {
    return null
  }
}

/** Build candidate URLs for a /24 subnet: all 254 hosts. */
function subnetCandidates(localIp: string, port: number): string[] {
  const parts = localIp.split('.')
  const prefix = `${parts[0]}.${parts[1]}.${parts[2]}`
  const self = parseInt(parts[3], 10)
  const urls: string[] = []
  for (let i = 1; i <= 254; i++) {
    if (i === self) continue // skip own IP
    urls.push(`http://${prefix}.${i}:${port}`)
  }
  return urls
}

/**
 * Scan the local network for the FieldPack backend.
 *
 * Strategy:
 *   1. Saved server URL — skip scan if still alive.
 *   2. Priority IPs: Windows hotspot + common gateways (fast, 1.5 s).
 *   3. Smart subnet scan: detect phone's own IP via WebRTC, scan its /24.
 *      All 253 probes fire in parallel with 2 s timeout — Promise.any
 *      resolves as soon as the first one hits, typically <500 ms.
 *
 * Returns the first URL that responds with HTTP 200, or null.
 * Automatically saves the found URL via setServerUrl().
 *
 * Security note: auto-discovery trusts the first /health responder on the LAN.
 * This is acceptable for our deployment model (closed WiFi hotspot, single
 * laptop server). In a hostile network, an attacker could impersonate the
 * server — but FieldPack is designed for isolated field deployments, not
 * public WiFi. TLS certificate pinning would mitigate this if needed.
 */
export async function autoScanForServer(): Promise<string | null> {
  if (!isNative()) return null
  console.log('[scan] starting, native=true')

  const TIMEOUT = 2000

  // 1. Saved URL still alive — no scan needed
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    console.log('[scan] probing saved URL:', saved)
    try {
      const result = await probeHealth(saved, TIMEOUT)
      console.log('[scan] saved URL alive:', result)
      return result
    } catch (e) {
      console.log('[scan] saved URL dead:', (e as Error).message)
    }
  }

  // 2. Priority: hotspot & gateway IPs (field scenario)
  const priorityIps = [
    'http://10.0.2.2:8000',       // Android emulator → host loopback
    'http://192.168.137.1:8000',  // Windows hotspot
    'http://192.168.43.1:8000',   // Android hotspot
    'http://192.168.1.1:8000',
    'http://192.168.0.1:8000',
    'http://10.0.0.1:8000',
  ]

  console.log('[scan] probing priority IPs...')
  try {
    const found = await Promise.any(
      priorityIps.map((url) => probeHealth(url, 1500))
    )
    console.log('[scan] priority hit:', found)
    setServerUrl(found)
    return found
  } catch (e) {
    console.log('[scan] all priority IPs failed:', (e as Error).message)
  }

  // 3. Smart subnet scan: detect own IP, scan the /24
  const localIp = await getLocalIp()
  console.log('[scan] local IP:', localIp)
  if (localIp) {
    const candidates = subnetCandidates(localIp, 8000)
    console.log('[scan] scanning', candidates.length, 'subnet candidates in batches')
    const BATCH_SIZE = 30
    for (let i = 0; i < candidates.length; i += BATCH_SIZE) {
      const batch = candidates.slice(i, i + BATCH_SIZE)
      try {
        const found = await Promise.any(
          batch.map((url) => probeHealth(url, TIMEOUT))
        )
        console.log('[scan] subnet hit:', found)
        setServerUrl(found)
        return found
      } catch {
        // batch had no hits — continue to next batch
      }
    }
    console.log('[scan] subnet scan failed')
  }

  console.log('[scan] no server found')
  return null
}
