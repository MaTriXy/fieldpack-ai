import { useState, useEffect } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { Rocket, Leaf, Database, Moon, Sun, ChevronRight, WifiOff, Layers, Package, BarChart2, Wifi, Terminal, Settings, Laptop, Cpu, Globe } from 'lucide-react'
import { apiUrl } from '../lib/config'
import { useConnection } from '../hooks/ServerConnectionContext'

interface OllamaHealth {
  ollama: string
  ollama_version?: string
  model?: {
    name?: string
    exists?: boolean
    loaded?: boolean
    parameters?: string
    quantization?: string
    family?: string
    memory_mb?: number
  }
}

export default function HomePage() {
  const { reachable: backendUp, laptopHasInternet } = useConnection()
  const [packStatus, setPackStatus] = useState<'none' | 'loading' | 'loaded'>('none')
  const [packName, setPackName] = useState('')
  const [packMeta, setPackMeta] = useState<{ crops: string[]; knowledgeEntries: number; sources: number }>({ crops: [], knowledgeEntries: 0, sources: 0 })
  const [isDark, setIsDark] = useState(() =>
    document.documentElement.classList.contains('dark')
  )
  const [ollamaStatus, setOllamaStatus] = useState<OllamaHealth | null>(null)

  function toggleTheme() {
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

  useEffect(() => {
    const controller = new AbortController()
    fetch(apiUrl('/packs/'), { signal: controller.signal })
      .then(r => r.ok ? r.json() : [])
      .then((packs: { pack_id: string; name: string; region?: string; crops?: string[]; diseases_count?: number; knowledge_entries?: number; sources?: string[]; loaded?: boolean }[]) => {
        if (packs.length === 0) return
        const alreadyLoaded = packs.find(p => p.loaded)
        const setMeta = (p: typeof packs[0]) => setPackMeta({ crops: p.crops || [], knowledgeEntries: p.knowledge_entries || 0, sources: (p.sources || []).length })
        if (alreadyLoaded) {
          setPackStatus('loaded')
          setPackName(alreadyLoaded.name)
          setMeta(alreadyLoaded)
          return
        }
        setPackStatus('loading')
        fetch(apiUrl(`/packs/load/${packs[0].pack_id}`), { method: 'POST', signal: controller.signal })
          .then(r => { if (r.ok) { setPackStatus('loaded'); setPackName(packs[0].name); setMeta(packs[0]) } else { setPackStatus('none') } })
          .catch(() => { if (!controller.signal.aborted) setPackStatus('none') })
      })
      .catch(() => {})
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    fetch(apiUrl('/health'), { signal: controller.signal })
      .then(r => r.ok ? r.json() : null)
      .then((data: OllamaHealth | null) => {
        if (data) setOllamaStatus(data)
      })
      .catch(() => {})
    return () => controller.abort()
  }, [])

  if (!localStorage.getItem('fieldpack_onboarded')) {
    return <Navigate to="/onboarding" replace />
  }

  const ollamaIndicator = (() => {
    if (!ollamaStatus) return { dot: 'bg-gray-400', label: 'Offline' }
    const m = ollamaStatus.model
    if (m?.loaded) return { dot: 'bg-green-500', label: 'Ready' }
    if (m?.exists) return { dot: 'bg-amber-400', label: 'Available' }
    return { dot: 'bg-red-500', label: 'Not Found' }
  })()

  return (
    <div className="bg-surface animate-fadeIn min-h-screen">

      {/* -- Hero -- */}
      <div className="relative">
        <div className="px-6 pt-10 pb-16 text-center relative overflow-hidden">

          {/* hero background photo */}
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: "url('/images/packs/default-2.jpg')" }}
            aria-hidden="true"
          />
          {/* dark overlay for text readability */}
          <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-black/40 to-black/60" aria-hidden="true" />

          {/* settings + theme toggle + debug link */}
          <div className="absolute top-4 right-4 flex items-center gap-2">
            {import.meta.env.DEV && (
              <Link
                to="/debug"
                className="w-9 h-9 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 transition-colors text-white"
                aria-label="Debug pipeline"
              >
                <Terminal size={18} />
              </Link>
            )}
            <Link
              to="/settings"
              className="w-9 h-9 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 transition-colors text-white"
              aria-label="Settings"
            >
              <Settings size={18} />
            </Link>
            <button
              onClick={toggleTheme}
              aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              className="w-9 h-9 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 transition-colors text-white"
            >
              {isDark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>

          {/* wordmark */}
          <div className="relative">

            <h1
              className="font-heading text-5xl font-extrabold text-white tracking-tight leading-none"
              style={{ textShadow: '0 2px 12px rgba(0,0,0,0.7), 0 1px 3px rgba(0,0,0,0.9)' }}
            >
              FieldPack <span className="text-secondary">AI</span>
            </h1>
            <p
              className="text-white/80 text-base font-medium mt-3 tracking-wide"
              style={{ textShadow: '0 1px 6px rgba(0,0,0,0.8)' }}
            >
              Offline intelligence for field workers
            </p>
            <p
              className="text-white/75 text-[13px] mt-3 leading-relaxed max-w-xs mx-auto"
              style={{ textShadow: '0 1px 5px rgba(0,0,0,0.85)' }}
            >
              3.7 billion people lack internet. The field workers who serve them deserve AI that works without it.
            </p>
            <p
              className="text-white/60 text-xs mt-2 tracking-widest uppercase"
              style={{ textShadow: '0 1px 4px rgba(0,0,0,0.9)' }}
            >
              Powered by Gemma&nbsp;4 &middot; Built for humanitarian missions
            </p>

            {/* tech badge row */}
            <div className="mt-5 flex items-center justify-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-white/80 bg-white/12 border border-white/18 rounded-full px-2.5 py-1">
                <Layers size={10} className="text-secondary" />
                Gemma 4 Family
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-white/80 bg-white/12 border border-white/18 rounded-full px-2.5 py-1">
                <BarChart2 size={10} className="text-secondary" />
                Agentic RAG
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-white/90 bg-white/15 border border-secondary/30 rounded-full px-2.5 py-1">
                <WifiOff size={10} className="text-secondary" />
                Works Offline
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-white/80 bg-white/12 border border-white/18 rounded-full px-2.5 py-1">
                <Package size={10} className="text-secondary" />
                Knowledge Packs
              </span>
            </div>
          </div>
        </div>

        {/* SVG wave -- double-wave organic transition into the card area */}
        <div className="absolute bottom-0 left-0 right-0 overflow-hidden leading-none" style={{ height: '56px' }}>
          <svg
            viewBox="0 0 390 56"
            xmlns="http://www.w3.org/2000/svg"
            preserveAspectRatio="none"
            className="block w-full h-full"
            aria-hidden="true"
          >
            {/* back wave -- slightly transparent for depth */}
            <path
              d="M0,34 C55,18 110,46 170,30 C230,14 290,44 390,28 L390,56 L0,56 Z"
              className="fill-surface opacity-40"
            />
            {/* front wave -- solid fill */}
            <path
              d="M0,42 C60,26 120,54 190,38 C250,24 320,50 390,36 L390,56 L0,56 Z"
              className="fill-surface"
            />
          </svg>
        </div>
      </div>

      {/* -- CTA Cards -- */}
      <div className="px-4 -mt-2 pb-2 space-y-3 max-w-lg mx-auto">

        {/* Phase 1: Create Pack -- pipeline step 1 */}
        <Link
          to="/mission"
          className="block bg-card rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.08)] border border-surface-dark active:scale-[0.98] transition-transform overflow-hidden"
          style={{ animationDelay: '0.1s' }}
        >
          <div className="flex">
            <div className="w-1 flex-shrink-0 bg-gradient-to-b from-primary-light via-primary to-primary-dark rounded-l-2xl opacity-80" />
            <div className="flex-1 p-5">
              <div className="flex items-start gap-4">
                <div className="relative bg-primary/10 dark:bg-primary/25 rounded-xl p-3 ring-1 ring-primary/20 flex-shrink-0">
                  <Rocket className="text-primary dark:text-primary-light" size={24} />
                  <span className="absolute -top-1.5 -left-1.5 w-5 h-5 rounded-full bg-primary text-white text-[10px] font-bold flex items-center justify-center ring-2 ring-card">1</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="font-heading font-bold text-base text-text leading-tight">
                      Create Knowledge Pack
                    </h2>
                    <span className="text-[10px] font-bold uppercase tracking-widest bg-primary/10 dark:bg-primary/30 text-primary-light px-1.5 py-0.5 rounded-md flex items-center gap-1">
                      <Wifi size={8} />
                      Online
                    </span>
                  </div>
                  <p className="text-text-muted text-sm leading-snug">
                    Gemma 4 31B + 26B agents curate crop knowledge for your region
                  </p>
                  <div className="mt-3 flex items-center gap-1 text-primary dark:text-primary-light font-semibold text-sm">
                    <span>Start Mission</span>
                    <ChevronRight size={14} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Link>

        {/* pipeline connector */}
        <div className="flex items-center justify-center gap-2 -my-1 py-0.5 text-text-muted/40">
          <div className="h-px flex-1 bg-surface-dark" />
          <span className="text-[10px] tracking-widest uppercase font-medium">then deploy to the field</span>
          <div className="h-px flex-1 bg-surface-dark" />
        </div>

        {/* Phase 2: Field Session -- PRIMARY card, pipeline step 2 */}
        <Link
          to="/field"
          className="block rounded-2xl overflow-hidden shadow-[0_8px_32px_rgba(27,67,50,0.3)] active:scale-[0.98] transition-transform"
          style={{
            background: 'linear-gradient(135deg, #40916C 0%, #2D6A4F 55%, #1B4332 100%)',
            animationDelay: '0.2s',
          }}
        >
          {/* shimmer stripe */}
          <div
            className="h-0.5 w-full animate-shimmer"
            style={{
              background: 'linear-gradient(90deg, transparent 0%, #F5A623 30%, #FFD180 50%, #F5A623 70%, transparent 100%)',
              backgroundSize: '200% 100%',
            }}
          />

          <div className="p-5">
            <div className="absolute top-0 left-0 w-32 h-32 opacity-10 pointer-events-none" style={{ background: 'radial-gradient(circle, #F5A623, transparent)' }} />

            <div className="flex items-start gap-4">
              <div className="relative bg-secondary/20 rounded-xl p-3 ring-1 ring-secondary/30 flex-shrink-0">
                <Leaf className="text-secondary" size={26} />
                <span className="absolute -top-1.5 -left-1.5 w-5 h-5 rounded-full bg-secondary text-white text-[10px] font-bold flex items-center justify-center ring-2 ring-[#2D6A4F]">2</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h2 className="font-heading font-bold text-xl text-white leading-tight">
                    Start Field Session
                  </h2>
                  <span className="text-[10px] font-bold uppercase tracking-widest bg-secondary/25 text-secondary px-1.5 py-0.5 rounded-md border border-secondary/30 flex items-center gap-1">
                    {laptopHasInternet ? <Wifi size={8} /> : <WifiOff size={8} />}
                    {laptopHasInternet ? 'Works Online' : 'Works Offline'}
                  </span>
                </div>
                <p className="text-white/80 text-sm leading-snug">
                  Photo to diagnosis to treatment plan &mdash; Gemma 4 E2B on your device
                </p>
                <div className="mt-4 flex items-center gap-1.5 text-secondary font-semibold text-sm">
                  <span>Open Field Chat</span>
                  <ChevronRight size={15} />
                </div>
              </div>
            </div>
          </div>
        </Link>
      </div>

      {/* -- Status bar -- */}
      <div className="px-4 mt-3 pb-6 max-w-lg mx-auto space-y-2">
        <Link to="/packs" className="bg-card border border-surface-dark rounded-xl px-4 py-3 shadow-sm active:scale-[0.98] transition-transform block">
          {/* connectivity mode */}
          <div className="flex items-center gap-2.5 mb-2">
            <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
              {backendUp && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-60" />
              )}
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${backendUp ? 'bg-green-500' : 'bg-amber-400'}`} />
            </span>
            <span className="text-xs font-semibold text-text flex items-center gap-1.5">
              {backendUp ? (
                <>
                  <Laptop size={12} />
                  Laptop Connected &middot; {laptopHasInternet ? 'Online' : 'Offline'} &middot; LLM local
                  {laptopHasInternet && <Globe size={10} className="text-text-muted" />}
                </>
              ) : (
                <><WifiOff size={12} /> Phone Only &mdash; Logging Mode</>
              )}
            </span>
          </div>
          <p className="text-[11px] text-text-muted leading-snug mb-2.5">
            {backendUp
              ? `Take a photo in Field Chat to get instant diagnosis and treatment plans.${laptopHasInternet ? ' Inference stays on your device.' : ''}`
              : 'No laptop found. You can log observations \u2014 they\u2019ll sync when you reconnect.'}
          </p>
          {/* active pack row */}
          <div className="flex items-center justify-between pt-2 border-t border-surface-dark">
            <div className="flex items-center gap-1.5 text-xs text-text-muted min-w-0">
              <Database size={12} className="text-secondary flex-shrink-0" />
              <span className="truncate max-w-[180px]">
                {packStatus === 'loaded' ? packName : packStatus === 'loading' ? 'Loading pack...' : 'No pack loaded'}
              </span>
              {packStatus === 'loaded' && (
                <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-secondary" />
              )}
            </div>
            <span className="text-[10px] text-text-muted/60 flex-shrink-0">
              {packStatus === 'loaded' && packMeta.knowledgeEntries > 0
                ? `${packMeta.crops.length} crops · ${packMeta.knowledgeEntries} entries · ${packMeta.sources} sources`
                : packStatus === 'loading' ? 'Loading...' : 'v1.0'}
            </span>
          </div>
        </Link>

        {/* Ollama model status card */}
        <div className="bg-card border border-surface-dark rounded-xl px-4 py-3 shadow-sm">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-start gap-2 min-w-0">
              <Cpu size={14} className="text-text-muted flex-shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-xs font-semibold text-text leading-tight">
                  {ollamaStatus?.model?.family
                    ? `${ollamaStatus.model.family.charAt(0).toUpperCase()}${ollamaStatus.model.family.slice(1)}`
                    : 'Gemma 4'}{' '}
                  {ollamaStatus?.model?.parameters ?? 'E2B'}
                  {ollamaStatus?.model?.quantization
                    ? <span className="text-text-muted font-normal"> &middot; {ollamaStatus.model.quantization}</span>
                    : null}
                </p>
                <p className="text-[11px] text-text-muted truncate mt-0.5">
                  {ollamaStatus?.model?.name ?? 'fieldpack-assistant-lite'}
                </p>
                <p className="text-[10px] text-text-muted/60 mt-0.5">
                  {ollamaStatus?.model?.memory_mb != null
                    ? `${ollamaStatus.model.memory_mb.toLocaleString()} MB`
                    : '--'}{' '}
                  &middot; Ollama {ollamaStatus?.ollama_version ?? '--'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <span className={`w-2 h-2 rounded-full ${ollamaIndicator.dot}`} />
              <span className="text-[11px] font-semibold text-text-muted">{ollamaIndicator.label}</span>
            </div>
          </div>
        </div>

        {/* demo context line */}
        <p className="text-center text-[11px] text-text-muted/70 tracking-wide">
          Kaggle Gemma 4 Good Hackathon &mdash; Offline AI Demo
        </p>
      </div>

    </div>
  )
}
