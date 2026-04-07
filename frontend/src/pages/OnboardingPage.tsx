import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Leaf,
  FileText,
  WifiOff,
  Wifi,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  Camera,
  Search,
  Database,
  Globe,
  Cloud,
  CloudOff,
} from 'lucide-react'
import { useConnection } from '../hooks/ServerConnectionContext'
import { getServerUrl, setServerUrl, isNative } from '../lib/config'

const TOTAL_SLIDES = 5

const haptic = (style: string = 'Medium') =>
  isNative() && import('@capacitor/haptics').then(m =>
    m.Haptics.impact({ style: m.ImpactStyle[style as keyof typeof m.ImpactStyle] })
  ).catch(() => {})

// ── Slide 1: Welcome ───────────────────────────────────────────────────────────

function WelcomeSlide() {
  return (
    <div className="flex flex-col items-center justify-center flex-1 px-8 text-center">
      {/* Pulsing glow icon */}
      <div className="relative mb-8">
        <span className="absolute inset-0 rounded-full bg-secondary/25 animate-ping" style={{ animationDuration: '2.6s' }} />
        <span className="absolute inset-0 rounded-full bg-secondary/10 scale-150 animate-ping" style={{ animationDuration: '3.2s', animationDelay: '0.4s' }} />
        <div className="relative bg-white/10 rounded-full p-5 ring-1 ring-white/20 backdrop-blur-sm">
          <Leaf className="text-secondary" size={36} />
        </div>
      </div>

      <h1 className="font-heading text-4xl font-extrabold text-white tracking-tight leading-none mb-3">
        FieldPack <span className="text-secondary">AI</span>
      </h1>
      <p className="text-white/80 text-base font-medium mb-6">
        Offline intelligence for field workers
      </p>

      <p className="text-white/75 text-sm leading-relaxed max-w-xs mb-8">
        Point your phone at a sick plant. Get a diagnosis and treatment plan &mdash; no internet, no signal required.
      </p>

      <p className="text-white/75 text-xs tracking-widest uppercase">
        Powered by Gemma&nbsp;4 &middot; Built for the field
      </p>
    </div>
  )
}

// ── Slide 2: Hero Workflow ──────────────────────────────────────────────────────

function HeroWorkflowSlide() {
  return (
    <div className="flex flex-col items-center justify-center flex-1 px-6 text-center">
      <h2 className="font-heading text-2xl font-bold text-white mb-8">
        Photo to diagnosis in seconds
      </h2>

      {/* 3-step flow */}
      <div className="flex items-start justify-center gap-3 mb-8 w-full max-w-sm">
        {/* Step 1 */}
        <div className="flex-1 animate-slideUp" style={{ animationDelay: '0.1s' }}>
          <div className="bg-white/10 border border-white/15 rounded-xl p-4 flex flex-col items-center gap-2 mb-2">
            <div className="bg-secondary/20 rounded-full p-2.5">
              <Camera size={20} className="text-secondary" />
            </div>
            <span className="text-white font-semibold text-xs">Take Photo</span>
          </div>
          <p className="text-white/65 text-[11px] leading-tight">Point at affected leaves or stems</p>
        </div>

        {/* Arrow */}
        <div className="pt-7 text-secondary/50"><ChevronRight size={16} /></div>

        {/* Step 2 */}
        <div className="flex-1 animate-slideUp" style={{ animationDelay: '0.2s' }}>
          <div className="bg-white/10 border border-white/15 rounded-xl p-4 flex flex-col items-center gap-2 mb-2">
            <div className="bg-secondary/20 rounded-full p-2.5">
              <Search size={20} className="text-secondary" />
            </div>
            <span className="text-white font-semibold text-xs">AI Diagnoses</span>
          </div>
          <p className="text-white/65 text-[11px] leading-tight">Identifies disease from knowledge base</p>
        </div>

        {/* Arrow */}
        <div className="pt-7 text-secondary/50"><ChevronRight size={16} /></div>

        {/* Step 3 */}
        <div className="flex-1 animate-slideUp" style={{ animationDelay: '0.3s' }}>
          <div className="bg-white/10 border border-white/15 rounded-xl p-4 flex flex-col items-center gap-2 mb-2">
            <div className="bg-secondary/20 rounded-full p-2.5">
              <FileText size={20} className="text-secondary" />
            </div>
            <span className="text-white font-semibold text-xs">Treatment</span>
          </div>
          <p className="text-white/65 text-[11px] leading-tight">Step-by-step plan with local materials</p>
        </div>
      </div>

      {/* Tip callout */}
      <div className="w-full max-w-sm bg-white/8 border border-white/12 rounded-xl p-4 text-left">
        <div className="flex items-start gap-3">
          <Camera size={16} className="text-secondary flex-shrink-0 mt-0.5" />
          <p className="text-white/75 text-xs leading-relaxed">
            Just attach a photo in Field Chat &mdash; no special commands needed. You can also describe symptoms in text.
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Slide 3: Online vs Offline ──────────────────────────────────────────────────

function OnlineOfflineSlide() {
  return (
    <div className="flex flex-col items-center justify-center flex-1 px-6 text-center">
      <h2 className="font-heading text-2xl font-bold text-white mb-2">
        Two modes, one app
      </h2>
      <p className="text-white/70 text-sm mb-8 max-w-xs">
        FieldPack works in the office and in the field
      </p>

      <div className="w-full max-w-sm space-y-3">
        {/* Online card */}
        <div className="bg-white/8 border border-white/12 rounded-xl p-4 text-left animate-slideUp" style={{ animationDelay: '0.1s' }}>
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-blue-500/20 rounded-full p-2">
              <Globe size={18} className="text-blue-400" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-sm">Online Mode</h3>
              <p className="text-white/65 text-xs">Requires internet</p>
            </div>
            <Cloud size={14} className="text-white/40 ml-auto" />
          </div>
          <ul className="space-y-1.5 ml-1">
            <li className="flex items-center gap-2 text-white/75 text-xs">
              <span className="w-1 h-1 rounded-full bg-blue-400 flex-shrink-0" />
              Create Knowledge Packs for your region
            </li>
            <li className="flex items-center gap-2 text-white/75 text-xs">
              <span className="w-1 h-1 rounded-full bg-blue-400 flex-shrink-0" />
              AI agents research crops, diseases, treatments
            </li>
            <li className="flex items-center gap-2 text-white/75 text-xs">
              <span className="w-1 h-1 rounded-full bg-blue-400 flex-shrink-0" />
              Done once at the office before field deployment
            </li>
          </ul>
        </div>

        {/* Offline card */}
        <div className="bg-white/8 border border-secondary/25 rounded-xl p-4 text-left animate-slideUp" style={{ animationDelay: '0.2s' }}>
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-secondary/20 rounded-full p-2">
              <WifiOff size={18} className="text-secondary" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-sm">Offline Mode</h3>
              <p className="text-secondary text-xs">No internet needed</p>
            </div>
            <CloudOff size={14} className="text-white/40 ml-auto" />
          </div>
          <ul className="space-y-1.5 ml-1">
            <li className="flex items-center gap-2 text-white/75 text-xs">
              <span className="w-1 h-1 rounded-full bg-secondary flex-shrink-0" />
              Diagnose diseases from photos
            </li>
            <li className="flex items-center gap-2 text-white/75 text-xs">
              <span className="w-1 h-1 rounded-full bg-secondary flex-shrink-0" />
              Get treatment plans with local materials
            </li>
            <li className="flex items-center gap-2 text-white/75 text-xs">
              <span className="w-1 h-1 rounded-full bg-secondary flex-shrink-0" />
              Works anywhere &mdash; no signal, no cloud
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}

// ── Slide 4: Knowledge Packs ────────────────────────────────────────────────────

function KnowledgePackSlide() {
  return (
    <div className="flex flex-col items-center justify-center flex-1 px-6 text-center">
      <h2 className="font-heading text-2xl font-bold text-white mb-2">
        Pre-loaded crop knowledge
      </h2>
      <p className="text-white/70 text-sm mb-8 max-w-xs">
        A Knowledge Pack contains everything the AI needs &mdash; stored locally, not in the cloud
      </p>

      {/* Mock pack card */}
      <div className="w-full max-w-sm rounded-xl overflow-hidden border border-white/15 mb-6 animate-slideUp" style={{ animationDelay: '0.15s' }}>
        {/* Shimmer top bar */}
        <div className="h-0.5 w-full animate-shimmer" style={{ background: 'linear-gradient(90deg, transparent 0%, #F5A623 30%, #FFD180 50%, #F5A623 70%, transparent 100%)', backgroundSize: '200% 100%' }} />

        <div className="bg-white/8 p-4">
          <div className="flex items-center gap-3 mb-3">
            <div className="bg-secondary/20 rounded-lg p-2.5 ring-1 ring-secondary/30">
              <Database size={20} className="text-secondary" />
            </div>
            <div className="text-left flex-1 min-w-0">
              <h3 className="text-white font-semibold text-sm">Casamance, Senegal &mdash; Agriculture</h3>
              <p className="text-white/65 text-xs">Southern Region</p>
            </div>
            <span className="flex items-center gap-1 text-[10px] font-bold text-green-400 bg-green-500/15 border border-green-500/25 rounded-full px-2 py-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
              Loaded
            </span>
          </div>

          {/* Pack stats */}
          <div className="bg-white/6 rounded-lg divide-y divide-white/8">
            <div className="flex items-center justify-between px-3 py-2">
              <span className="text-white/65 text-xs">Crops</span>
              <span className="text-white/80 text-xs font-medium">Cassava, Rice, Millet, Groundnut</span>
            </div>
            <div className="flex items-center justify-between px-3 py-2">
              <span className="text-white/65 text-xs">Diseases</span>
              <span className="text-white/80 text-xs font-medium">47 disease profiles</span>
            </div>
            <div className="flex items-center justify-between px-3 py-2">
              <span className="text-white/65 text-xs">Records</span>
              <span className="text-white/80 text-xs font-medium">847 entries &middot; 4 search indexes</span>
            </div>
          </div>
        </div>
      </div>

      {/* Note */}
      <div className="w-full max-w-sm bg-white/8 border border-white/12 rounded-xl p-4 text-left">
        <div className="flex items-start gap-3">
          <Leaf size={16} className="text-secondary flex-shrink-0 mt-0.5" />
          <p className="text-white/75 text-xs leading-relaxed">
            The FieldStation laptop pre-loads a pack before deploying to the field. You just connect and go.
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Slide 5: Connect ────────────────────────────────────────────────────────────

function ConnectSlide({ onComplete }: { onComplete: () => void }) {
  const { status, serverInfo, retry } = useConnection()
  const [showManualInput, setShowManualInput] = useState(false)
  const [manualUrl, setManualUrl] = useState(() => getServerUrl() || 'http://192.168.137.1:8000')
  const [connectState, setConnectState] = useState<'idle' | 'testing' | 'ok' | 'error'>('idle')

  const handleManualConnect = async () => {
    const cleaned = manualUrl.replace(/\/+$/, '')
    if (!cleaned.startsWith('http://') && !cleaned.startsWith('https://')) {
      setConnectState('error')
      return
    }
    setConnectState('testing')
    try {
      const res = await fetch(`${cleaned}/health`, { signal: AbortSignal.timeout(5000) })
      if (res.ok) {
        setServerUrl(cleaned)
        setConnectState('ok')
        setTimeout(() => retry(), 300)
      } else {
        setConnectState('error')
      }
    } catch {
      setConnectState('error')
    }
  }

  const handleManualUrlChange = (v: string) => {
    setManualUrl(v)
    if (connectState === 'error') setConnectState('idle')
  }

  // Instructions shown during scanning and disconnected states
  const instructionSteps = [
    'On the laptop, start the FieldPack backend',
    'Create a WiFi hotspot from the laptop',
    'Connect this phone to that WiFi hotspot',
  ]

  // ── Scanning ──
  if (status === 'scanning') {
    return (
      <div className="flex flex-col items-center justify-center flex-1 px-6 text-center">
        <h2 className="font-heading text-xl font-bold text-white mb-6">
          Connect to FieldStation
        </h2>

        {/* Radar animation */}
        <div className="relative flex items-center justify-center mb-6" style={{ width: 100, height: 100 }}>
          <span className="absolute rounded-full border border-secondary/20 animate-ping" style={{ width: 100, height: 100, animationDuration: '2.4s' }} />
          <span className="absolute rounded-full border border-secondary/35 animate-ping" style={{ width: 66, height: 66, animationDuration: '2.4s', animationDelay: '0.5s' }} />
          <span className="absolute rounded-full border border-secondary/55 animate-ping" style={{ width: 36, height: 36, animationDuration: '2.4s', animationDelay: '1s' }} />
          <span className="absolute rounded-full border border-secondary/15" style={{ width: 100, height: 100 }} />
          <div className="relative z-10 bg-white/10 rounded-full p-2.5 ring-1 ring-white/20">
            <Wifi size={20} className="text-secondary" />
          </div>
        </div>

        <p className="font-heading text-base font-semibold text-white mb-1 animate-dotPulse">
          Searching for FieldStation...
        </p>
        <p className="text-white/65 text-xs mb-6">
          The AI runs on a nearby laptop over WiFi
        </p>

        {/* Proactive instructions */}
        <div className="w-full max-w-sm bg-white/6 border border-white/10 rounded-xl p-3.5 mb-5">
          <ol className="space-y-2">
            {instructionSteps.map((tip, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-secondary/20 border border-secondary/30 text-secondary text-[10px] font-bold flex items-center justify-center mt-0.5">
                  {i + 1}
                </span>
                <span className="text-white/75 text-xs leading-relaxed">{tip}</span>
              </li>
            ))}
          </ol>
        </div>

        {!showManualInput ? (
          <button
            onClick={() => setShowManualInput(true)}
            className="text-secondary text-xs underline underline-offset-2"
          >
            Enter IP manually
          </button>
        ) : (
          <div className="w-full max-w-sm">
            <ManualIpInput url={manualUrl} onChange={handleManualUrlChange} onConnect={handleManualConnect} state={connectState} />
          </div>
        )}
      </div>
    )
  }

  // ── Connected ──
  if (status === 'connected') {
    return (
      <div className="flex flex-col items-center justify-center flex-1 px-6 text-center">
        <div className="relative mb-6">
          <div className="absolute inset-0 rounded-full bg-green-500/20 scale-150 blur-xl" />
          <CheckCircle2 size={56} className="relative text-green-400" />
        </div>

        <h2 className="font-heading text-2xl font-bold text-white mb-6">
          FieldStation Found!
        </h2>

        {serverInfo && (
          <div className="w-full max-w-sm bg-white/8 border border-white/12 rounded-xl divide-y divide-white/8 mb-8 text-left">
            <div className="flex items-center justify-between px-4 py-3">
              <span className="text-white/65 text-xs">Server</span>
              <span className="text-white text-xs font-mono">{serverInfo.ip}</span>
            </div>
            <div className="flex items-center justify-between px-4 py-3">
              <span className="text-white/65 text-xs">Model</span>
              <span className="text-white text-xs font-medium truncate ml-4 text-right max-w-[150px]">{serverInfo.model}</span>
            </div>
            <div className="flex items-center justify-between px-4 py-3">
              <span className="text-white/65 text-xs">Knowledge Pack</span>
              <span className="text-secondary text-xs font-medium truncate ml-4 text-right max-w-[150px]">{serverInfo.pack}</span>
            </div>
          </div>
        )}

        <button
          onClick={() => { haptic('Medium'); onComplete() }}
          className="w-full max-w-sm flex items-center justify-center gap-2 bg-secondary text-white font-heading font-bold rounded-xl px-6 py-4 text-base active:scale-95 transition-transform"
        >
          Get Started
          <ChevronRight size={18} />
        </button>
      </div>
    )
  }

  // ── Disconnected ──
  return (
    <div className="flex flex-col items-center justify-center flex-1 px-6 text-center">
      <div className="relative mb-4">
        <div className="absolute inset-0 rounded-full bg-amber-500/15 scale-150 blur-lg" />
        <AlertTriangle size={48} className="relative text-amber-400" />
      </div>

      <h2 className="font-heading text-xl font-bold text-white mb-5">
        Couldn&apos;t find a FieldStation
      </h2>

      <div className="w-full max-w-sm bg-white/6 border border-white/10 rounded-xl p-3.5 mb-5">
        <ol className="space-y-2">
          {instructionSteps.map((tip, i) => (
            <li key={i} className="flex items-start gap-2.5">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-secondary/20 border border-secondary/30 text-secondary text-[10px] font-bold flex items-center justify-center mt-0.5">
                {i + 1}
              </span>
              <span className="text-white/75 text-xs leading-relaxed">{tip}</span>
            </li>
          ))}
        </ol>
      </div>

      <div className="w-full max-w-sm mb-4">
        <ManualIpInput url={manualUrl} onChange={handleManualUrlChange} onConnect={handleManualConnect} state={connectState} />
      </div>

      <button
        onClick={retry}
        className="w-full max-w-sm flex items-center justify-center gap-2 border border-white/25 text-white/80 font-heading font-semibold rounded-xl px-6 py-3 text-sm active:scale-95 transition-transform"
      >
        Try Again
      </button>
    </div>
  )
}

// ── Manual IP input ─────────────────────────────────────────────────────────────

function ManualIpInput({ url, onChange, onConnect, state }: {
  url: string
  onChange: (v: string) => void
  onConnect: () => void
  state: 'idle' | 'testing' | 'ok' | 'error'
}) {
  return (
    <div className="space-y-2">
      <label className="text-white/65 text-xs text-left block mb-1">Server address</label>
      <input
        type="url"
        inputMode="url"
        value={url}
        onChange={(e) => onChange(e.target.value)}
        placeholder="http://192.168.137.1:8000"
        className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-3 text-sm text-white placeholder-white/30 outline-none focus:border-secondary/60 focus:ring-1 focus:ring-secondary/30 transition-colors"
        aria-label="Server URL"
      />
      <button
        type="button"
        onClick={onConnect}
        disabled={state === 'testing'}
        className="w-full flex items-center justify-center gap-2 bg-secondary/90 text-white font-semibold rounded-lg px-4 py-3 text-sm disabled:opacity-50 active:scale-95 transition-transform"
      >
        {state === 'testing' ? (
          <span className="animate-dotPulse">Connecting...</span>
        ) : state === 'ok' ? (
          <><Wifi size={14} className="text-green-300" /><span className="text-green-200">Connected!</span></>
        ) : state === 'error' ? (
          <><WifiOff size={14} /><span>Cannot reach server &mdash; check address</span></>
        ) : (
          'Connect'
        )}
      </button>
    </div>
  )
}

// ── Dot indicators ──────────────────────────────────────────────────────────────

function DotIndicators({ total, active, onDotClick }: { total: number; active: number; onDotClick: (i: number) => void }) {
  return (
    <div className="flex items-center justify-center gap-2.5" role="tablist" aria-label="Onboarding slides">
      {Array.from({ length: total }).map((_, i) => (
        <button
          key={i}
          role="tab"
          aria-selected={i === active}
          aria-label={`Slide ${i + 1}`}
          onClick={() => onDotClick(i)}
          className="p-2"
        >
          <span className={`block transition-all duration-300 rounded-full ${
            i === active
              ? 'w-6 h-2.5 bg-secondary'
              : 'w-2.5 h-2.5 bg-white/35 hover:bg-white/50'
          }`} />
        </button>
      ))}
    </div>
  )
}

// ── Slide labels ────────────────────────────────────────────────────────────────

const SLIDE_BUTTON_LABELS: Record<number, string> = {
  0: 'Get Started',
  1: 'How it works',
  2: 'Got it',
  3: 'Connect',
}

// ── Main OnboardingPage ─────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const navigate = useNavigate()
  const [slide, setSlide] = useState(0)
  const [slideDirection, setSlideDirection] = useState<'left' | 'right'>('right')

  const touchStartX = useRef<number | null>(null)
  const touchStartY = useRef<number | null>(null)

  const handleComplete = useCallback(() => {
    localStorage.setItem('fieldpack_onboarded', 'true')
    navigate('/', { replace: true })
  }, [navigate])

  const goTo = useCallback((target: number) => {
    if (target < 0 || target >= TOTAL_SLIDES) return
    setSlide((prev) => {
      setSlideDirection(target > prev ? 'right' : 'left')
      return target
    })
  }, [])

  const goNext = () => goTo(slide + 1)

  const goSkip = () => handleComplete()

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX
    touchStartY.current = e.touches[0].clientY
  }

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null || touchStartY.current === null) {
      return
    }
    const dx = e.changedTouches[0].clientX - touchStartX.current
    const dy = e.changedTouches[0].clientY - touchStartY.current
    // Always clean up refs regardless of swipe outcome
    touchStartX.current = null
    touchStartY.current = null
    if (Math.abs(dx) < 40 || Math.abs(dx) < Math.abs(dy)) return
    if (dx < 0 && slide < TOTAL_SLIDES - 1) goTo(slide + 1)
    if (dx > 0 && slide > 0) goTo(slide - 1)
  }

  const slideAnimation = slideDirection === 'right' ? 'animate-slideInRight' : 'animate-slideInLeft'

  return (
    <div
      className="min-h-[100dvh] flex flex-col overflow-hidden relative"
      style={{ background: 'linear-gradient(160deg, #2D6A4F 0%, #1B4332 55%, #143d29 100%)' }}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Decorative textures */}
      <div className="absolute inset-0 opacity-[0.05] pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle, white 1.5px, transparent 1.5px)', backgroundSize: '28px 28px' }} aria-hidden="true" />
      <div className="absolute inset-0 opacity-25 pointer-events-none" style={{ background: 'radial-gradient(ellipse 70% 45% at 50% 0%, #40916C, transparent)' }} aria-hidden="true" />
      <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ background: 'radial-gradient(ellipse 50% 35% at 10% 100%, #F5A62340, transparent)' }} aria-hidden="true" />

      {/* Skip button — visible on slides 0-3, hidden on last slide */}
      <div className="relative z-10 flex justify-end px-5 pt-4 min-h-[48px]">
        {slide < TOTAL_SLIDES - 1 && (
          <button
            onClick={goSkip}
            className="inline-flex items-center gap-1 text-white/80 text-sm font-medium bg-white/15 border border-white/20 rounded-full px-4 py-2 active:bg-white/25 transition-colors min-h-[44px]"
          >
            Skip setup
            <ChevronRight size={14} className="opacity-60" />
          </button>
        )}
      </div>

      {/* Slide content */}
      <div key={slide} className={`relative z-10 flex flex-col flex-1 overflow-hidden ${slideAnimation}`}>
        {slide === 0 && <WelcomeSlide />}
        {slide === 1 && <HeroWorkflowSlide />}
        {slide === 2 && <OnlineOfflineSlide />}
        {slide === 3 && <KnowledgePackSlide />}
        {slide === 4 && <ConnectSlide onComplete={handleComplete} />}
      </div>

      {/* Bottom nav */}
      <div className="relative z-10 px-6 pt-4 space-y-4" style={{ paddingBottom: 'calc(2.5rem + env(safe-area-inset-bottom, 0px))' }}>
        <DotIndicators total={TOTAL_SLIDES} active={slide} onDotClick={goTo} />

        {slide < TOTAL_SLIDES - 1 && (
          <button
            onClick={() => { haptic('Medium'); goNext() }}
            className="w-full flex items-center justify-center gap-2 bg-secondary text-white font-heading font-bold rounded-xl px-6 py-4 text-base active:scale-95 transition-transform"
          >
            {SLIDE_BUTTON_LABELS[slide] ?? 'Next'}
            <ChevronRight size={18} />
          </button>
        )}
      </div>
    </div>
  )
}
