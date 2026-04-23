import { useState, useRef } from 'react'
import { ArrowLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { isNative } from '../../lib/config'
import { useConnection } from '../../hooks/ServerConnectionContext'
import type { ConnectionStatus, ServerInfo } from '../../hooks/useServerConnection'

interface TopBarProps {
  title: string
  subtitle?: string
  back?: boolean
  backTo?: string
  badge?: { label: string; variant: 'online' | 'offline' | 'live' }
  leftAction?: React.ReactNode
  rightAction?: React.ReactNode
  dark?: boolean
}

// Connection status pill rendered inside TopBar — only in native mode.
// Status is passed from outside so the hook is called once at the layout level.
function ConnectionPill({
  status,
  serverInfo,
  scanProgress,
  onRetry,
}: {
  status: ConnectionStatus
  serverInfo: ServerInfo | null
  scanProgress: string | null
  onRetry: () => void
}) {
  const [popoverOpen, setPopoverOpen] = useState(false)
  const pillRef = useRef<HTMLButtonElement>(null)

  if (status === 'scanning') {
    const label = scanProgress ?? 'Scanning…'
    return (
      <div
        className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-white/10 max-w-[200px]"
        title={label}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-dotPulse shrink-0" />
        <span className="text-white/80 leading-none truncate" style={{ fontSize: '11px' }}>{label}</span>
      </div>
    )
  }

  if (status === 'disconnected') {
    return (
      <button
        onClick={onRetry}
        className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-white/10 active:bg-white/20 transition-colors"
        aria-label="Offline - tap to retry"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
        <span className="text-white/80 leading-none" style={{ fontSize: '11px' }}>Offline</span>
      </button>
    )
  }

  // Connected
  const label = serverInfo?.model
    ? serverInfo.model.replace('fieldpack-assistant', 'FieldStation').replace('fieldpack-', '')
    : 'FieldStation'

  return (
    <div className="relative">
      <button
        ref={pillRef}
        onClick={() => setPopoverOpen((v) => !v)}
        className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-white/10 active:bg-white/20 transition-colors"
        aria-label={`Connected to ${label}`}
        aria-expanded={popoverOpen}
      >
        <span className="relative flex w-1.5 h-1.5 shrink-0">
          <span className="absolute inline-flex h-full w-full rounded-full bg-green-400 animate-dotPing" />
          <span className="relative inline-flex rounded-full w-1.5 h-1.5 bg-green-400" />
        </span>
        <span className="text-white/90 leading-none max-w-[80px] truncate" style={{ fontSize: '11px' }}>
          {label}
        </span>
      </button>

      {popoverOpen && serverInfo && (
        <>
          {/* Backdrop — close on tap outside */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setPopoverOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute right-0 top-full mt-2 z-50 bg-card rounded-xl shadow-xl border border-surface-dark p-3 min-w-[180px] animate-slideUp">
            <p className="text-xs font-semibold text-text mb-2">Connection</p>
            <div className="space-y-1.5">
              <div className="flex justify-between gap-3">
                <span className="text-xs text-text-muted">Server</span>
                <span className="text-xs text-text font-medium truncate max-w-[100px]">{serverInfo.ip}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-xs text-text-muted">Model</span>
                <span className="text-xs text-text font-medium truncate max-w-[100px]">{serverInfo.model}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-xs text-text-muted">Pack</span>
                <span className="text-xs text-text font-medium truncate max-w-[100px]">{serverInfo.pack}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span className="text-xs text-text-muted">Ollama</span>
                <span className="text-xs text-text font-medium">{serverInfo.ollama}</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default function TopBar({
  title,
  subtitle,
  back,
  backTo,
  badge,
  leftAction,
  rightAction,
  dark,
}: TopBarProps) {
  const navigate = useNavigate()
  const connection = useConnection()

  const badgeColors = {
    online: 'bg-secondary text-white',
    offline: 'bg-primary-light text-white',
    live: 'bg-green-500 text-white',
  }

  const handleBack = () => {
    if (backTo) {
      navigate(backTo)
    } else {
      navigate(-1)
    }
  }

  const showConnectionPill = isNative()

  return (
    <header role="banner" className={`sticky top-0 z-40 px-4 py-3 relative overflow-hidden ${dark ? 'bg-debug-bg' : ''}`} style={{ paddingTop: 'calc(0.75rem + env(safe-area-inset-top, 0px))' }}>
      {!dark && (
        <>
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: "url('/images/packs/default-2.jpg')" }}
            aria-hidden="true"
          />
          <div className="absolute inset-0 bg-black/50" aria-hidden="true" />
        </>
      )}
      <div className="max-w-lg mx-auto flex items-center gap-3 relative min-h-[44px]">
        {back && (
          <button onClick={handleBack} className="text-white p-2.5 -ml-2.5" aria-label="Go back">
            <ArrowLeft size={22} />
          </button>
        )}
        {leftAction}
        <div className="flex-1 min-w-0">
          <h1 className="text-white font-heading font-bold text-lg leading-tight truncate">
            {title}
          </h1>
          {subtitle && (
            <p className="text-white/70 text-xs truncate">{subtitle}</p>
          )}
        </div>
        {badge && (
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${badgeColors[badge.variant]}`}>
            {badge.label}
          </span>
        )}
        {showConnectionPill && (
          <ConnectionPill
            status={connection.status}
            serverInfo={connection.serverInfo}
            scanProgress={connection.scanProgress}
            onRetry={connection.retry}
          />
        )}
        {rightAction}
      </div>
    </header>
  )
}
