import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Rocket, Leaf, Database, Moon, Sun, ChevronRight, WifiOff, Cpu, Globe, BarChart2 } from 'lucide-react'
import { apiUrl } from '../lib/config'

export default function HomePage() {
  const [packStatus, setPackStatus] = useState<'none' | 'loading' | 'loaded'>('none')
  const [packName, setPackName] = useState('')
  const [isDark, setIsDark] = useState(() =>
    document.documentElement.classList.contains('dark')
  )

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
      .then((packs: { pack_id: string; name: string; loaded?: boolean }[]) => {
        if (packs.length === 0) return
        const alreadyLoaded = packs.find(p => p.loaded)
        if (alreadyLoaded) {
          setPackStatus('loaded')
          setPackName(alreadyLoaded.name)
          return
        }
        setPackStatus('loading')
        fetch(apiUrl(`/packs/load/${packs[0].pack_id}`), { method: 'POST', signal: controller.signal })
          .then(r => { if (r.ok) { setPackStatus('loaded'); setPackName(packs[0].name) } else { setPackStatus('none') } })
          .catch(() => { if (!controller.signal.aborted) setPackStatus('none') })
      })
      .catch(() => {})
    return () => controller.abort()
  }, [])

  return (
    <div className="bg-surface animate-fadeIn min-h-screen">

      {/* ── Hero ── */}
      <div className="relative">
        <div className="bg-gradient-to-br from-primary via-primary-dark to-[#071910] px-6 pt-14 pb-24 text-center relative overflow-hidden">

          {/* dot grid */}
          <div
            className="absolute inset-0 opacity-[0.06]"
            style={{ backgroundImage: 'radial-gradient(circle, white 1.5px, transparent 1.5px)', backgroundSize: '28px 28px' }}
          />

          {/* radial spotlight from top */}
          <div className="absolute inset-0 opacity-30" style={{ background: 'radial-gradient(ellipse 70% 55% at 50% 0%, #2D6A4F, transparent)' }} />

          {/* second ambient glow — bottom left */}
          <div className="absolute inset-0 opacity-15" style={{ background: 'radial-gradient(ellipse 50% 40% at 10% 100%, #D4A01740, transparent)' }} />

          {/* decorative leaf cluster — bottom right */}
          <div className="absolute bottom-6 right-3 opacity-[0.08] pointer-events-none select-none" aria-hidden="true">
            <svg width="110" height="110" viewBox="0 0 110 110" fill="none">
              <ellipse cx="68" cy="55" rx="36" ry="17" transform="rotate(-30 68 55)" fill="white" />
              <ellipse cx="46" cy="68" rx="26" ry="12" transform="rotate(20 46 68)" fill="white" />
              <ellipse cx="76" cy="35" rx="22" ry="10" transform="rotate(-50 76 35)" fill="white" />
              <ellipse cx="30" cy="42" rx="18" ry="8" transform="rotate(10 30 42)" fill="white" />
            </svg>
          </div>

          {/* decorative leaf cluster — top left */}
          <div className="absolute top-8 left-3 opacity-[0.05] pointer-events-none select-none" aria-hidden="true">
            <svg width="70" height="70" viewBox="0 0 70 70" fill="none">
              <ellipse cx="38" cy="35" rx="24" ry="11" transform="rotate(40 38 35)" fill="white" />
              <ellipse cx="22" cy="45" rx="16" ry="7" transform="rotate(-15 22 45)" fill="white" />
            </svg>
          </div>

          {/* theme toggle */}
          <button
            onClick={toggleTheme}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            className="absolute top-4 right-4 w-9 h-9 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 transition-colors text-white"
          >
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          {/* wordmark */}
          <div className="relative">

            {/* pulsing glow ring behind icon */}
            <div className="flex items-center justify-center mb-5">
              <div className="relative">
                <span className="absolute inset-0 rounded-full bg-secondary/25 animate-ping" style={{ animationDuration: '2.6s' }} />
                <span className="absolute inset-0 rounded-full bg-secondary/10 scale-150 animate-ping" style={{ animationDuration: '3.2s', animationDelay: '0.4s' }} />
                <div className="relative bg-white/10 rounded-full p-4 ring-1 ring-white/20 backdrop-blur-sm">
                  <Leaf className="text-secondary" size={32} />
                </div>
              </div>
            </div>

            <h1 className="font-heading text-5xl font-extrabold text-white tracking-tight leading-none">
              FieldPack <span className="text-secondary">AI</span>
            </h1>
            <p className="text-white/80 text-base font-medium mt-3 tracking-wide">
              Offline intelligence for field workers
            </p>
            <p className="text-white/45 text-xs mt-1.5 tracking-widest uppercase">
              Powered by Gemma&nbsp;4 &middot; Built for humanitarian workers
            </p>

            {/* tech badge row */}
            <div className="mt-5 flex items-center justify-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-white/60 bg-white/8 border border-white/12 rounded-full px-2.5 py-1">
                <Cpu size={10} className="text-secondary/80" />
                Gemma 4 E2B
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-white/60 bg-white/8 border border-white/12 rounded-full px-2.5 py-1">
                <BarChart2 size={10} className="text-secondary/80" />
                Agentic RAG
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-white/60 bg-white/8 border border-white/12 rounded-full px-2.5 py-1">
                <WifiOff size={10} className="text-secondary/80" />
                100% Offline
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-white/60 bg-white/8 border border-white/12 rounded-full px-2.5 py-1">
                <Globe size={10} className="text-secondary/80" />
                LangGraph
              </span>
            </div>
          </div>
        </div>

        {/* SVG wave — creates a clean curved transition into the card area */}
        <div className="absolute bottom-0 left-0 right-0 overflow-hidden leading-none" style={{ height: '40px' }}>
          <svg
            viewBox="0 0 390 40"
            xmlns="http://www.w3.org/2000/svg"
            preserveAspectRatio="none"
            className="block w-full h-full"
            aria-hidden="true"
          >
            <path
              d="M0,20 C80,40 160,0 220,18 C280,36 340,10 390,20 L390,40 L0,40 Z"
              className="fill-surface"
            />
          </svg>
        </div>
      </div>

      {/* ── CTA Cards ── */}
      <div className="px-4 -mt-2 pb-2 space-y-3 max-w-lg mx-auto">

        {/* Phase 2: Field Session — PRIMARY card */}
        <Link
          to="/field"
          className="block rounded-2xl overflow-hidden shadow-2xl active:scale-[0.98] transition-transform"
          style={{
            background: 'linear-gradient(135deg, #2D6A4F 0%, #1B4332 55%, #0f2d1e 100%)',
            animationDelay: '0.1s',
          }}
        >
          {/* shimmer stripe — animated sweep on load */}
          <div
            className="h-0.5 w-full animate-shimmer"
            style={{
              background: 'linear-gradient(90deg, transparent 0%, #D4A017 30%, #E3B634 50%, #D4A017 70%, transparent 100%)',
              backgroundSize: '200% 100%',
            }}
          />

          <div className="p-5">
            {/* subtle inner glow top-left */}
            <div className="absolute top-0 left-0 w-32 h-32 opacity-10 pointer-events-none" style={{ background: 'radial-gradient(circle, #D4A017, transparent)' }} />

            <div className="flex items-start gap-4">
              <div className="bg-secondary/20 rounded-xl p-3 ring-1 ring-secondary/30 flex-shrink-0">
                <Leaf className="text-secondary" size={26} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h2 className="font-heading font-bold text-xl text-white leading-tight">
                    Start Field Session
                  </h2>
                  <span className="text-[10px] font-bold uppercase tracking-widest bg-secondary/25 text-secondary px-1.5 py-0.5 rounded-md border border-secondary/30">
                    Hero
                  </span>
                </div>
                <p className="text-white/65 text-sm leading-snug">
                  Photo to diagnosis to treatment plan &mdash; entirely offline
                </p>
                <div className="mt-4 flex items-center gap-1.5 text-secondary font-semibold text-sm">
                  <span>Open Field Chat</span>
                  <ChevronRight size={15} />
                </div>
              </div>
            </div>
          </div>
        </Link>

        {/* Phase 1: Create Pack — secondary card */}
        <Link
          to="/mission"
          className="block bg-card rounded-2xl shadow-lg border border-surface-dark active:scale-[0.98] transition-transform overflow-hidden"
          style={{ animationDelay: '0.2s' }}
        >
          {/* left accent bar */}
          <div className="flex">
            <div className="w-1 flex-shrink-0 bg-gradient-to-b from-primary-light via-primary to-primary-dark rounded-l-2xl" />
            <div className="flex-1 p-5">
              <div className="flex items-start gap-4">
                <div className="bg-primary/10 dark:bg-primary/25 rounded-xl p-3 ring-1 ring-primary/20 flex-shrink-0">
                  <Rocket className="text-primary dark:text-primary-light" size={24} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="font-heading font-bold text-base text-text leading-tight">
                      Create Knowledge Pack
                    </h2>
                    <span className="text-[10px] font-bold uppercase tracking-widest bg-primary/10 dark:bg-primary/30 text-primary-light px-1.5 py-0.5 rounded-md">
                      Online
                    </span>
                  </div>
                  <p className="text-text-muted text-sm leading-snug">
                    Dispatch AI agents to curate crop knowledge for your region
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
      </div>

      {/* ── Status bar ── */}
      <div className="px-4 mt-4 pb-6 max-w-lg mx-auto space-y-2">
        <div className="bg-card border border-surface-dark rounded-xl px-4 py-3 flex items-center justify-between shadow-sm">
          {/* offline ready indicator */}
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-60" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500" />
            </span>
            <span className="text-xs font-medium text-text-muted flex items-center gap-1">
              <WifiOff size={11} />
              Offline Ready
            </span>
          </div>

          <div className="h-4 w-px bg-surface-dark" />

          {/* active pack */}
          <div className="flex items-center gap-1.5 text-xs text-text-muted min-w-0">
            <Database size={12} className="text-secondary flex-shrink-0" />
            <span className="truncate max-w-[130px]">
              {packStatus === 'loaded' ? packName : packStatus === 'loading' ? 'Loading pack...' : 'No pack loaded'}
            </span>
            {packStatus === 'loaded' && (
              <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-secondary" />
            )}
          </div>

          <div className="h-4 w-px bg-surface-dark" />

          <span className="text-[10px] text-text-muted/50 font-mono flex-shrink-0">v1.0.0</span>
        </div>

        {/* demo context line */}
        <p className="text-center text-[11px] text-text-muted/40 tracking-wide">
          Kaggle Gemma 4 Good Hackathon &mdash; Offline AI Demo
        </p>
      </div>

    </div>
  )
}
