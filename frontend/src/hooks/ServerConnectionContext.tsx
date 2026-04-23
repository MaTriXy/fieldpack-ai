import { createContext, useContext, useMemo } from 'react'
import { useServerConnection, type ServerConnectionState } from './useServerConnection'

const ServerConnectionCtx = createContext<ServerConnectionState>({
  status: 'connected',
  serverInfo: null,
  scanProgress: null,
  laptopHasInternet: false,
  reachable: true,
  retry: () => {},
})

export function ServerConnectionProvider({ children }: { children: React.ReactNode }) {
  const state = useServerConnection()
  const serverInfoKey = state.serverInfo
    ? `${state.serverInfo.ip}|${state.serverInfo.model}|${state.serverInfo.pack}|${state.serverInfo.ollama}`
    : null
  // Memo deps are intentionally the *fields* of state (primitives + stable
  // refs), not `state` itself. `state` is a fresh object every poll tick, but
  // its fields only change when the poll result actually differs. `retry` is
  // stable (useCallback([])). serverInfoKey flattens the ServerInfo object to
  // a string so identical polls don't invalidate the memo. This keeps every
  // consumer of useConnection() from re-rendering on every 5s tick.
  const value = useMemo(
    () => state,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [state.status, state.scanProgress, state.laptopHasInternet, state.reachable, state.retry, serverInfoKey],
  )
  return (
    <ServerConnectionCtx.Provider value={value}>
      {children}
    </ServerConnectionCtx.Provider>
  )
}

export function useConnection(): ServerConnectionState {
  return useContext(ServerConnectionCtx)
}
