import { useState } from 'react'
import { Wifi, WifiOff, Settings, X } from 'lucide-react'
import { getServerUrl, setServerUrl, isNative } from '../lib/config'

interface ServerSettingsProps {
  onClose: () => void
}

export default function ServerSettings({ onClose }: ServerSettingsProps) {
  const [url, setUrl] = useState(getServerUrl() || 'http://192.168.1.100:8000')
  const [testing, setTesting] = useState(false)
  const [status, setStatus] = useState<'idle' | 'ok' | 'error'>('idle')

  const testConnection = async () => {
    setTesting(true)
    setStatus('idle')
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 5000)
    try {
      const res = await fetch(`${url.replace(/\/+$/, '')}/health`, { signal: controller.signal })
      clearTimeout(timer)
      setStatus(res.ok ? 'ok' : 'error')
    } catch {
      clearTimeout(timer)
      setStatus('error')
    }
    setTesting(false)
  }

  const handleSave = () => {
    setServerUrl(url)
    onClose()
    // Reload to pick up new URL
    window.location.reload()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-card rounded-2xl w-full max-w-sm shadow-xl">
        <div className="flex items-center justify-between p-4 border-b border-surface-dark">
          <div className="flex items-center gap-2">
            <Settings size={20} className="text-primary" />
            <h2 className="font-heading font-bold text-lg">Server Connection</h2>
          </div>
          <button onClick={onClose} className="text-text-muted p-1">
            <X size={20} />
          </button>
        </div>

        <div className="p-4 space-y-4">
          <p className="text-sm text-text-muted">
            Enter the IP address of the laptop running the FieldPack backend.
          </p>

          <div>
            <label className="text-xs font-medium text-text-muted mb-1 block">Server URL</label>
            <input
              type="text"
              value={url}
              onChange={(e) => { setUrl(e.target.value); setStatus('idle') }}
              placeholder="http://192.168.1.100:8000"
              className="w-full bg-surface rounded-lg px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>

          <button
            onClick={testConnection}
            disabled={testing}
            className="w-full flex items-center justify-center gap-2 bg-surface rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-surface-dark transition-colors disabled:opacity-50"
          >
            {testing ? (
              <span className="animate-pulse">Testing...</span>
            ) : status === 'ok' ? (
              <>
                <Wifi size={16} className="text-green-500" />
                <span className="text-green-600">Connected</span>
              </>
            ) : status === 'error' ? (
              <>
                <WifiOff size={16} className="text-tertiary" />
                <span className="text-tertiary">Cannot reach server</span>
              </>
            ) : (
              'Test Connection'
            )}
          </button>

          <button
            onClick={handleSave}
            className="w-full bg-primary text-white rounded-lg px-4 py-2.5 text-sm font-semibold hover:bg-primary-light transition-colors"
          >
            Save & Connect
          </button>
        </div>
      </div>
    </div>
  )
}

/** Small button to open server settings. Only shows in native mode. */
export function ServerSettingsButton({ onClick }: { onClick: () => void }) {
  if (!isNative()) return null

  return (
    <button
      onClick={onClick}
      className="text-white/80 p-1 hover:text-white transition-colors"
      aria-label="Server settings"
    >
      <Settings size={18} />
    </button>
  )
}
