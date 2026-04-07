import { createContext, useContext } from 'react'
import { useServerConnection, type ServerConnectionState } from './useServerConnection'

const ServerConnectionCtx = createContext<ServerConnectionState>({
  status: 'connected',
  serverInfo: null,
  retry: () => {},
})

export function ServerConnectionProvider({ children }: { children: React.ReactNode }) {
  const state = useServerConnection()
  return (
    <ServerConnectionCtx.Provider value={state}>
      {children}
    </ServerConnectionCtx.Provider>
  )
}

export function useConnection(): ServerConnectionState {
  return useContext(ServerConnectionCtx)
}
