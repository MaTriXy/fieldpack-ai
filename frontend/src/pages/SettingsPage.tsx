import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Wifi, WifiOff, Globe, Camera, Type, Moon, Sun,
  RefreshCw, RotateCcw, Info, Cpu, Database, HardDrive, Package,
} from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import { useConnection } from '../hooks/ServerConnectionContext'
import { isNative, getServerUrl, setServerUrl, apiUrl } from '../lib/config'
import {
  getLanguage, setLanguage, LANGUAGE_LABELS, LANGUAGE_OPTIONS,
  getCameraPreset, setCameraPreset, CAMERA_LABELS, CAMERA_OPTIONS,
  getTextSize, setTextSize, applyTextSize, TEXT_SIZE_LABELS, TEXT_SIZE_OPTIONS,
} from '../lib/settings'
import type { Language, CameraPreset, TextSize } from '../lib/settings'
import { getQueuedObservationCount, flushObservationQueue } from '../lib/offline-queue'


// ── Reusable setting row ───────────────────────────────────

function SettingRow({ icon, label, description, children }: {
  icon: React.ReactNode
  label: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between px-4 py-3.5 gap-3">
      <div className="flex items-center gap-3 min-w-0">
        <span className="text-text-muted flex-shrink-0">{icon}</span>
        <div className="min-w-0">
          <p className="text-sm font-medium text-text">{label}</p>
          {description && <p className="text-xs text-text-muted mt-0.5">{description}</p>}
        </div>
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  )
}


// ── Segmented control ──────────────────────────────────────

function SegmentedControl<T extends string>({ options, value, onChange, labels }: {
  options: T[]
  value: T
  onChange: (v: T) => void
  labels: Record<T, string>
}) {
  return (
    <div className="flex rounded-lg bg-surface overflow-hidden border border-surface-dark w-full">
      {options.map(opt => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className={`flex-1 px-3 py-1.5 text-xs font-medium transition-colors min-w-[44px] ${
            value === opt
              ? 'bg-primary text-white'
              : 'text-text-muted hover:bg-surface-dark'
          }`}
        >
          {labels[opt]}
        </button>
      ))}
    </div>
  )
}


// ── Section wrapper ────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2 px-1">
        {title}
      </h2>
      <div className="bg-card rounded-2xl shadow-sm border border-surface-dark divide-y divide-surface-dark overflow-hidden">
        {children}
      </div>
    </section>
  )
}


// ── Info row (read-only) ───────────────────────────────────

function InfoRow({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between px-4 py-3">
      <div className="flex items-center gap-2.5">
        {icon && <span className="text-text-muted">{icon}</span>}
        <span className="text-xs text-text-muted">{label}</span>
      </div>
      <span className="text-xs font-medium text-text max-w-[60%] text-right truncate">{value}</span>
    </div>
  )
}


// ============================================================
// Main settings page
// ============================================================

export default function SettingsPage() {
  const navigate = useNavigate()
  const { status: liveStatus, serverInfo, retry } = useConnection()

  // ── Connection state ───────────────────────────────────
  const [serverUrl, setUrl] = useState(getServerUrl() || 'http://192.168.1.100:8000')
  const [connStatus, setConnStatus] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle')

  // ── Settings state ─────────────────────────────────────
  const [language, setLang] = useState<Language>(getLanguage)
  const [cameraPreset, setCamPreset] = useState<CameraPreset>(getCameraPreset)
  const [textSize, setTxtSize] = useState<TextSize>(getTextSize)
  const [isDark, setIsDark] = useState(() => document.documentElement.classList.contains('dark'))

  // ── Offline queue ──────────────────────────────────────
  const [queueCount, setQueueCount] = useState(getQueuedObservationCount)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<string | null>(null)

  // ── System info from /health ───────────────────────────
  const [health, setHealth] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch(apiUrl('/health'), { signal: controller.signal })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setHealth(data) })
      .catch(() => {})
    return () => controller.abort()
  }, [])

  // Keep queue count fresh
  useEffect(() => {
    const update = () => setQueueCount(getQueuedObservationCount())
    window.addEventListener('storage', update)
    return () => window.removeEventListener('storage', update)
  }, [])

  // ── Handlers ───────────────────────────────────────────

  const testConnection = async () => {
    setConnStatus('testing')
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 5000)
    try {
      const res = await fetch(`${serverUrl.replace(/\/+$/, '')}/health`, { signal: controller.signal })
      clearTimeout(timer)
      setConnStatus(res.ok ? 'ok' : 'error')
    } catch {
      clearTimeout(timer)
      setConnStatus('error')
    }
  }

  const saveConnection = () => {
    setServerUrl(serverUrl)
    window.location.reload()
  }

  const handleLanguage = (lang: Language) => {
    setLang(lang)
    setLanguage(lang)
  }

  const handleCameraPreset = (preset: CameraPreset) => {
    setCamPreset(preset)
    setCameraPreset(preset)
  }

  const handleTextSize = (size: TextSize) => {
    setTxtSize(size)
    setTextSize(size)
    applyTextSize(size)
  }

  const toggleTheme = () => {
    const next = !isDark
    setIsDark(next)
    if (next) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }

  const handleSync = useCallback(async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const result = await flushObservationQueue((synced, total) => {
        setSyncResult(`Syncing ${synced}/${total}...`)
      })
      setSyncResult(`Synced ${result.synced}${result.failed ? `, ${result.failed} failed` : ''}`)
      setTimeout(() => setSyncResult(null), 3000)
    } catch {
      setSyncResult('Sync failed')
      setTimeout(() => setSyncResult(null), 3000)
    } finally {
      setSyncing(false)
    }
  }, [])

  const resetOnboarding = () => {
    localStorage.removeItem('fieldpack_onboarded')
    navigate('/onboarding')
  }

  // ── Derived health data ────────────────────────────────
  const model = health?.model as Record<string, unknown> | undefined
  const pack = health?.pack as Record<string, unknown> | undefined

  return (
    <div className="bg-surface min-h-screen">
      <TopBar title="Settings" back backTo="/" />

      <div className="px-4 py-5 space-y-5 max-w-lg mx-auto pb-28">

        {/* ── Connection (native only) ── */}
        {isNative() ? (
          <Section title="Connection">
            {/* Live status banner */}
            <div className="px-4 py-3 flex items-center gap-3">
              <span className={`relative flex h-2.5 w-2.5 flex-shrink-0 ${liveStatus === 'scanning' ? '' : ''}`}>
                {liveStatus === 'scanning' && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                )}
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                  liveStatus === 'connected' ? 'bg-green-500' :
                  liveStatus === 'scanning'  ? 'bg-amber-400' :
                                               'bg-red-400'
                }`} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-text">
                  {liveStatus === 'connected' ? 'Connected' :
                   liveStatus === 'scanning'  ? 'Scanning...' :
                                                'Disconnected'}
                </p>
                {liveStatus === 'connected' && serverInfo && (
                  <p className="text-xs text-text-muted truncate">
                    {serverInfo.ip} · {serverInfo.pack}
                  </p>
                )}
                {liveStatus === 'disconnected' && (
                  <p className="text-xs text-text-muted">No FieldStation found on the network</p>
                )}
              </div>
              {liveStatus === 'disconnected' && (
                <button
                  onClick={retry}
                  className="px-3 py-1.5 text-xs font-medium bg-surface rounded-lg border border-surface-dark hover:bg-surface-dark transition-colors"
                >
                  Retry
                </button>
              )}
            </div>

            <div className="px-4 py-4 space-y-3">
              <label className="text-xs font-medium text-text-muted block">Server URL</label>
              <input
                type="url"
                inputMode="url"
                value={serverUrl}
                onChange={e => { setUrl(e.target.value); setConnStatus('idle') }}
                placeholder="http://192.168.1.100:8000"
                className="w-full bg-surface rounded-lg px-4 py-2.5 text-sm outline-none border border-surface-dark focus:ring-2 focus:ring-primary/30 transition-colors"
              />
              <div className="flex gap-2">
                <button
                  onClick={testConnection}
                  disabled={connStatus === 'testing'}
                  className="flex-1 flex items-center justify-center gap-2 bg-surface rounded-lg px-3 py-2.5 text-xs font-medium border border-surface-dark hover:bg-surface-dark transition-colors disabled:opacity-50"
                >
                  {connStatus === 'testing' ? (
                    <span className="animate-pulse">Testing...</span>
                  ) : connStatus === 'ok' ? (
                    <><Wifi size={14} className="text-green-500" /><span className="text-green-600">Connected</span></>
                  ) : connStatus === 'error' ? (
                    <><WifiOff size={14} className="text-tertiary" /><span className="text-tertiary">Unreachable</span></>
                  ) : 'Test'}
                </button>
                <button
                  onClick={saveConnection}
                  className="flex-1 bg-primary text-white rounded-lg px-3 py-2.5 text-xs font-semibold hover:bg-primary-light transition-colors"
                >
                  Save & Reconnect
                </button>
              </div>
            </div>
          </Section>
        ) : (
          <Section title="Connection">
            <div className="px-4 py-3">
              <p className="text-xs text-text-muted">Using development proxy (Vite)</p>
            </div>
          </Section>
        )}

        {/* ── Language & Display ── */}
        <Section title="Language & Display">
          {/* Language needs full-width layout — 4 options don't fit in a side-by-side row */}
          <div className="px-4 py-3.5 space-y-2.5">
            <div className="flex items-center gap-3">
              <span className="text-text-muted flex-shrink-0"><Globe size={18} /></span>
              <div>
                <p className="text-sm font-medium text-text">Response Language</p>
                <p className="text-xs text-text-muted mt-0.5">AI responses will use this language</p>
              </div>
            </div>
            <SegmentedControl
              options={LANGUAGE_OPTIONS}
              value={language}
              onChange={handleLanguage}
              labels={LANGUAGE_LABELS}
            />
          </div>

          <SettingRow
            icon={<Type size={18} />}
            label="Text Size"
          >
            <SegmentedControl
              options={TEXT_SIZE_OPTIONS}
              value={textSize}
              onChange={handleTextSize}
              labels={TEXT_SIZE_LABELS}
            />
          </SettingRow>

          <SettingRow
            icon={isDark ? <Moon size={18} /> : <Sun size={18} />}
            label="Dark Mode"
          >
            <button
              onClick={toggleTheme}
              className={`relative w-11 h-6 rounded-full transition-colors ${isDark ? 'bg-primary' : 'bg-surface-dark'}`}
              aria-label="Toggle dark mode"
            >
              <span
                className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${isDark ? 'translate-x-5' : ''}`}
              />
            </button>
          </SettingRow>
        </Section>

        {/* ── Camera ── */}
        <Section title="Camera">
          <SettingRow
            icon={<Camera size={18} />}
            label="Photo Quality"
            description={CAMERA_LABELS[cameraPreset].desc}
          >
            <SegmentedControl
              options={CAMERA_OPTIONS}
              value={cameraPreset}
              onChange={handleCameraPreset}
              labels={Object.fromEntries(CAMERA_OPTIONS.map(k => [k, CAMERA_LABELS[k].label])) as Record<CameraPreset, string>}
            />
          </SettingRow>
        </Section>

        {/* ── Data ── */}
        <Section title="Data">
          <SettingRow
            icon={<RefreshCw size={18} className={syncing ? 'animate-spin' : ''} />}
            label="Offline Queue"
            description={
              syncResult
                ? syncResult
                : queueCount > 0
                  ? `${queueCount} observation${queueCount > 1 ? 's' : ''} pending sync`
                  : 'All synced'
            }
          >
            <button
              onClick={handleSync}
              disabled={queueCount === 0 || syncing}
              className="px-3 py-1.5 text-xs font-medium bg-surface rounded-lg border border-surface-dark hover:bg-surface-dark transition-colors disabled:opacity-40"
            >
              Sync Now
            </button>
          </SettingRow>

          <SettingRow
            icon={<RotateCcw size={18} />}
            label="Reset Onboarding"
            description="Re-run the welcome tutorial"
          >
            <button
              onClick={resetOnboarding}
              className="px-3 py-1.5 text-xs font-medium text-tertiary bg-surface rounded-lg border border-surface-dark hover:bg-tertiary/10 transition-colors"
            >
              Reset
            </button>
          </SettingRow>
        </Section>

        {/* ── About ── */}
        <Section title="About">
          <InfoRow icon={<Info size={14} />} label="App" value="FieldPack AI v1.0" />
          <InfoRow
            icon={<Cpu size={14} />}
            label="Model"
            value={model?.name as string || 'Not connected'}
          />
          <InfoRow
            icon={<HardDrive size={14} />}
            label="Quantization"
            value="4-bit weights · 8-bit KV cache"
          />
          <InfoRow
            icon={<Cpu size={14} />}
            label="Parameters"
            value={model?.parameters as string || '\u2014'}
          />
          {model?.memory_mb ? (
            <InfoRow
              icon={<HardDrive size={14} />}
              label="VRAM"
              value={`${model.memory_mb} MB`}
            />
          ) : null}
          <InfoRow
            icon={<Package size={14} />}
            label="Ollama"
            value={(health?.ollama_version as string) || '\u2014'}
          />
          <InfoRow
            icon={<Database size={14} />}
            label="Knowledge Pack"
            value={(pack?.pack_name as string) || (pack?.name as string) || (pack?.pack_id as string) || 'None loaded'}
          />

          {/* Hackathon badge */}
          <div className="px-4 py-3 text-center">
            <p className="text-[10px] text-text-muted/60 tracking-widest uppercase">
              Kaggle Gemma 4 Good Hackathon
            </p>
          </div>
        </Section>

      </div>
    </div>
  )
}
