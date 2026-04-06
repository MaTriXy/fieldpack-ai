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
