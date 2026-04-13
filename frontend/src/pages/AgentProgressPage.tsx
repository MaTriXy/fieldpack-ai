import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Check, Loader2, Circle, AlertTriangle, CheckCircle, Search, Database, Image, Clock, Layers } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import { getMissionWsUrl } from '../lib/config'
import { FIELD_FACTS } from '../lib/field-facts'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MissionCard {
  region: string
  crops: string[]
  season: string
  focusAreas: string[]
  scaleEstimate?: string
  description: string
}

type StepStatus = 'pending' | 'in_progress' | 'completed'

interface AgentStep {
  phase: string
  name: string
  status: StepStatus
  detail: string
  latency?: string
  justCompleted?: boolean
}

interface LiveStats {
  findings: number
  tables: Record<string, number>
  chunks: number
  images: number
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PHASE_DISPLAY: Record<string, string> = {
  gathering: 'Source Gathering',
  extracting: 'Knowledge Extraction',
  gap_analysis: 'Gap Analysis',
  compiling: 'Compilation',
  chunks: 'Chunk Generation',
  images: 'Image Download',
}

const PHASE_ORDER = ['gathering', 'extracting', 'gap_analysis', 'compiling', 'chunks', 'images']

const PHASE_INIT_DETAIL: Record<string, string> = {
  gathering: 'Waiting to fetch HTML pages, PDFs, and climate data...',
  extracting: 'Waiting to parse and extract structured knowledge entries...',
  gap_analysis: 'Waiting to identify coverage gaps and missing topics...',
  compiling: 'Waiting to compile all sources into a unified knowledge base...',
  chunks: 'Waiting to split and embed knowledge chunks for retrieval...',
  images: 'Waiting to download and validate diagnostic images...',
}

function buildInitialSteps(): AgentStep[] {
  return PHASE_ORDER.map((phase) => ({
    phase,
    name: PHASE_DISPLAY[phase] ?? phase,
    status: 'pending',
    detail: PHASE_INIT_DETAIL[phase] ?? 'Waiting...',
  }))
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatLatency(ms: number): string {
  if (ms >= 60000) return `${(ms / 60000).toFixed(1)}min`
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${ms}ms`
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusIcon({ status }: { status: StepStatus }) {
  if (status === 'completed') return <Check size={16} className="text-white" />
  if (status === 'in_progress') return <Loader2 size={16} className="text-white animate-spin" />
  return <Circle size={16} className="text-text-muted/40" />
}

function statusBg(status: StepStatus): string {
  if (status === 'completed') return 'bg-primary'
  if (status === 'in_progress') return 'bg-secondary'
  return 'bg-surface-dark'
}

function statusBorderL(status: StepStatus): string {
  if (status === 'completed') return 'border-l-primary'
  if (status === 'in_progress') return 'border-l-secondary'
  return 'border-l-surface-dark'
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="bg-card rounded-xl p-3 shadow-sm border border-surface-dark text-center flex-1 min-w-0">
      <div className="flex items-center justify-center gap-1.5 mb-1">
        {icon}
        <span className="text-[10px] text-text-muted uppercase tracking-wider font-semibold">{label}</span>
      </div>
      <p className="font-heading font-bold text-xl text-primary transition-all duration-500">
        {value.toLocaleString()}
      </p>
    </div>
  )
}

function FieldFactCard() {
  const [factIndex, setFactIndex] = useState(() => Math.floor(Math.random() * FIELD_FACTS.length))
  const [fadeKey, setFadeKey] = useState(0)

  useEffect(() => {
    const id = setInterval(() => {
      setFactIndex((i) => (i + 1) % FIELD_FACTS.length)
      setFadeKey((k) => k + 1)
    }, 15000)
    return () => clearInterval(id)
  }, [])

  const fact = FIELD_FACTS[factIndex]

  return (
    <div key={fadeKey} className="bg-primary/5 rounded-xl p-3 animate-fadeIn">
      <div className="flex items-start gap-2.5">
        <span className="text-lg leading-none mt-0.5">{fact.icon}</span>
        <div>
          <p className="text-[10px] text-primary/60 font-semibold uppercase tracking-wider mb-0.5">Did you know?</p>
          <p className="text-xs text-text-muted italic leading-relaxed">{fact.text}</p>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function AgentProgressPage() {
  const location = useLocation()
  const navigate = useNavigate()

  const missionCard = (location.state as { missionCard?: MissionCard } | null)?.missionCard

  const [steps, setSteps] = useState<AgentStep[]>(buildInitialSteps())
  const [logs, setLogs] = useState<string[]>([])
  const [overallProgress, setOverallProgress] = useState(0)
  const [isComplete, setIsComplete] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [completeSummary, setCompleteSummary] = useState<string | null>(null)
  const [liveStats, setLiveStats] = useState<LiveStats>({ findings: 0, tables: {}, chunks: 0, images: 0 })
  const [totalLatency, setTotalLatency] = useState<number | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const isDoneRef = useRef(false)
  const isErrorRef = useRef(false)
  const logEndRef = useRef<HTMLDivElement>(null)

  // Redirect if no mission card was passed
  useEffect(() => {
    if (!missionCard) {
      navigate('/mission', { replace: true })
    }
  }, [missionCard, navigate])

  // Auto-scroll activity log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // Clear justCompleted flag after animation
  useEffect(() => {
    const hasJustCompleted = steps.some((s) => s.justCompleted)
    if (!hasJustCompleted) return
    const timer = setTimeout(() => {
      setSteps((prev) => prev.map((s) =>
        s.justCompleted ? { ...s, justCompleted: false } : s
      ))
    }, 600)
    return () => clearTimeout(timer)
  }, [steps])

  // WebSocket connection
  useEffect(() => {
    if (!missionCard) return

    // Reset state on (re-)mount (React Strict Mode double-mounts in dev)
    isDoneRef.current = false
    isErrorRef.current = false
    setErrorMessage(null)
    setIsComplete(false)
    setSteps(buildInitialSteps())
    setLogs([])
    setOverallProgress(0)
    setCompleteSummary(null)
    setLiveStats({ findings: 0, tables: {}, chunks: 0, images: 0 })
    setTotalLatency(null)

    let cleanedUp = false
    const ws = new WebSocket(getMissionWsUrl())
    wsRef.current = ws

    ws.onopen = () => {
      if (cleanedUp) return
      ws.send(
        JSON.stringify({
          region: missionCard.region,
          crops: missionCard.crops,
          description: missionCard.description,
          season: missionCard.season,
          focus_areas: missionCard.focusAreas,
        })
      )
    }

    ws.onmessage = (event: MessageEvent) => {
      if (cleanedUp) return
      let data: Record<string, unknown>
      try {
        data = JSON.parse(event.data as string) as Record<string, unknown>
      } catch {
        return
      }

      const type = data.type as string

      if (type === 'status') {
        const phase = data.phase as string
        const detail = data.detail as string
        const displayName = PHASE_DISPLAY[phase] ?? phase

        setSteps((prev) =>
          prev.map((s) =>
            s.phase === phase ? { ...s, status: 'in_progress', detail } : s
          )
        )
        setLogs((prev) => [...prev.slice(-19), `[${displayName}] ${detail}`])
      } else if (type === 'phase_complete') {
        const phase = data.phase as string
        const latencyMs = data.latency_ms as number
        const displayName = PHASE_DISPLAY[phase] ?? phase
        const latencyStr = formatLatency(latencyMs)

        setSteps((prev) =>
          prev.map((s) =>
            s.phase === phase
              ? { ...s, status: 'completed', latency: latencyStr, justCompleted: true }
              : s
          )
        )
        setLogs((prev) => [...prev.slice(-19), `[${displayName}] Complete (${latencyStr})`])

        setOverallProgress((prev) => {
          const completedCount = prev / (100 / 6) + 1
          return Math.round(Math.min(completedCount * (100 / 6), 100))
        })
      } else if (type === 'stats') {
        setLiveStats({
          findings: (data.findings as number) || 0,
          tables: (data.tables as Record<string, number>) || {},
          chunks: (data.chunks as number) || 0,
          images: (data.images as number) || 0,
        })
      } else if (type === 'done') {
        isDoneRef.current = true
        const summary = data.summary as Record<string, unknown>
        const totalMs = summary?.total_latency_ms as number | undefined
        const findings = summary?.findings as number | undefined
        const chunks = summary?.chunks as number | undefined
        const images = summary?.images as number | undefined
        const tables = summary?.tables as Record<string, number> | undefined

        // Update final stats
        setLiveStats({
          findings: findings ?? 0,
          tables: tables ?? {},
          chunks: chunks ?? 0,
          images: images ?? 0,
        })
        if (totalMs !== undefined) setTotalLatency(totalMs)

        const parts: string[] = []
        if (findings !== undefined) parts.push(`${findings} findings`)
        if (chunks !== undefined) parts.push(`${chunks} chunks`)
        if (images !== undefined) parts.push(`${images} images`)
        if (totalMs !== undefined) parts.push(`total ${formatLatency(totalMs)}`)

        const summaryLine = parts.length > 0
          ? `Pack built: ${parts.join(', ')}`
          : 'Pack built successfully'

        setCompleteSummary(summaryLine)
        setLogs((prev) => [...prev.slice(-19), `[Done] ${summaryLine}`])
        setOverallProgress(100)
        setIsComplete(true)
      } else if (type === 'error') {
        const message = (data.message as string) ?? 'An unknown error occurred'
        isErrorRef.current = true
        setErrorMessage(message)
        setLogs((prev) => [...prev.slice(-19), `[Error] ${message}`])
      }
    }

    ws.onclose = () => {
      if (cleanedUp) return
      if (!isDoneRef.current && !isErrorRef.current) {
        setErrorMessage('Connection closed unexpectedly. The pipeline may still be running.')
      }
    }

    ws.onerror = () => {
      if (cleanedUp) return
      if (!isDoneRef.current) {
        isErrorRef.current = true
        setErrorMessage('WebSocket connection failed. Check that the server is reachable.')
      }
    }

    return () => {
      cleanedUp = true
      ws.close()
      wsRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (!missionCard) return null

  const cropLabel = missionCard.crops
    .map((c) => c.charAt(0).toUpperCase() + c.slice(1))
    .join(', ')

  const topBarBadge = isComplete
    ? ({ label: 'Done', variant: 'online' } as const)
    : errorMessage
    ? ({ label: 'Error', variant: 'offline' } as const)
    : ({ label: 'Live', variant: 'live' } as const)

  const hasStats = liveStats.findings > 0 || liveStats.chunks > 0 || liveStats.images > 0
  const tableCount = Object.values(liveStats.tables).reduce((a, b) => a + b, 0)

  return (
    <div className="flex flex-col h-[calc(100dvh-4rem)] animate-fadeIn">
      <TopBar title="Building Pack" back backTo="/mission" badge={topBarBadge} />

      {/* Mission summary */}
      <div className="bg-primary/5 px-4 py-3 border-b border-surface-dark">
        <div className="max-w-lg mx-auto flex items-center justify-between">
          <div>
            <p className="font-heading font-bold text-sm text-text">{missionCard.region}</p>
            <p className="text-xs text-text-muted">{cropLabel}</p>
          </div>
          {!isComplete && !errorMessage && (
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-secondary rounded-full animate-dotPulse" />
              <span className="text-[10px] text-secondary font-semibold">Building</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-surface">
        <div className="max-w-lg mx-auto space-y-3">

          {/* Error banner */}
          {errorMessage && (
            <div className="flex items-start gap-3 bg-tertiary/10 border border-tertiary/20 rounded-xl px-4 py-3 animate-fadeIn">
              <AlertTriangle size={18} className="text-tertiary shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-tertiary">Pipeline Error</p>
                <p className="text-xs text-tertiary/80 mt-0.5 leading-relaxed">{errorMessage}</p>
              </div>
            </div>
          )}

          {/* Timeline */}
          {steps.map((step, idx) => (
            <div key={step.phase} className={`flex gap-3 ${step.justCompleted ? 'animate-scaleUp' : ''}`}>
              {/* Vertical line + icon */}
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-colors duration-300 ${statusBg(step.status)}`}>
                  <StatusIcon status={step.status} />
                </div>
                {idx < steps.length - 1 && (
                  <div
                    className={`w-0.5 flex-1 mt-1 transition-colors duration-300 ${
                      step.status === 'completed' ? 'bg-primary/30' : 'bg-surface-dark'
                    }`}
                  />
                )}
              </div>

              {/* Card */}
              <div
                className={`flex-1 bg-card rounded-xl p-3 shadow-sm border border-surface-dark mb-1 border-l-4 transition-all duration-300 ${statusBorderL(step.status)} ${
                  step.justCompleted ? 'bg-primary/5' : ''
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-heading font-bold text-sm">{step.name}</h3>
                  {step.latency && (
                    <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-mono shrink-0 animate-fadeIn">
                      {step.latency}
                    </span>
                  )}
                </div>
                <p className="text-xs text-text-muted mt-1 leading-relaxed">{step.detail}</p>
                {step.status === 'in_progress' && (
                  <div className="mt-2 h-[2px] bg-surface-dark rounded-full overflow-hidden">
                    <div className="h-full bg-secondary rounded-full animate-shimmer" style={{ width: '60%' }} />
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Live stat counters */}
          {hasStats && (
            <div className="flex gap-2 animate-slideUp">
              <StatCard
                icon={<Search size={10} className="text-primary" />}
                label="Findings"
                value={liveStats.findings}
              />
              <StatCard
                icon={<Layers size={10} className="text-primary" />}
                label="Chunks"
                value={liveStats.chunks}
              />
              <StatCard
                icon={<Image size={10} className="text-primary" />}
                label="Images"
                value={liveStats.images}
              />
            </div>
          )}

          {/* Field fact — only during build */}
          {!isComplete && !errorMessage && <FieldFactCard />}

          {/* Activity feed — warm styled */}
          <div className="bg-card rounded-xl p-3 border border-surface-dark shadow-sm">
            <p className="text-[10px] text-text-muted font-semibold uppercase tracking-wider mb-2">
              Activity Feed
            </p>
            <div className="space-y-1 max-h-36 overflow-y-auto">
              {logs.length === 0 && (
                <p className="text-xs text-text-muted/40 italic">Waiting for pipeline to start...</p>
              )}
              {logs.map((log, i) => {
                const isLatest = i === logs.length - 1
                const isComplete = log.includes('Complete') || log.includes('Done')
                return (
                  <div
                    key={i}
                    className={`flex items-start gap-2 text-xs leading-relaxed ${
                      isLatest ? 'animate-fadeIn' : ''
                    }`}
                  >
                    <span className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${
                      isComplete ? 'bg-primary' : 'bg-secondary'
                    }`} />
                    <span className={`${isLatest ? 'text-text' : 'text-text-muted/70'} break-words`}>
                      {log}
                    </span>
                  </div>
                )
              })}
              <div ref={logEndRef} />
            </div>
          </div>

          {/* Pack preview card on completion */}
          {isComplete && completeSummary && (
            <div className="bg-card rounded-xl p-4 shadow-sm border border-primary/20 animate-slideUp">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <CheckCircle size={20} className="text-primary" />
                </div>
                <div>
                  <p className="font-heading font-bold text-sm">Knowledge Pack Ready</p>
                  <p className="text-xs text-text-muted">{missionCard.region}</p>
                </div>
              </div>

              {/* Stats grid */}
              <div className="grid grid-cols-2 gap-2 mb-3">
                <div className="bg-surface rounded-lg p-2.5 text-center">
                  <div className="flex items-center justify-center gap-1 mb-0.5">
                    <Search size={10} className="text-primary" />
                    <span className="text-[10px] text-text-muted uppercase tracking-wider">Findings</span>
                  </div>
                  <p className="font-heading font-bold text-lg text-primary">{liveStats.findings.toLocaleString()}</p>
                </div>
                <div className="bg-surface rounded-lg p-2.5 text-center">
                  <div className="flex items-center justify-center gap-1 mb-0.5">
                    <Layers size={10} className="text-primary" />
                    <span className="text-[10px] text-text-muted uppercase tracking-wider">Chunks</span>
                  </div>
                  <p className="font-heading font-bold text-lg text-primary">{liveStats.chunks.toLocaleString()}</p>
                </div>
                <div className="bg-surface rounded-lg p-2.5 text-center">
                  <div className="flex items-center justify-center gap-1 mb-0.5">
                    <Image size={10} className="text-primary" />
                    <span className="text-[10px] text-text-muted uppercase tracking-wider">Images</span>
                  </div>
                  <p className="font-heading font-bold text-lg text-primary">{liveStats.images.toLocaleString()}</p>
                </div>
                <div className="bg-surface rounded-lg p-2.5 text-center">
                  <div className="flex items-center justify-center gap-1 mb-0.5">
                    <Clock size={10} className="text-primary" />
                    <span className="text-[10px] text-text-muted uppercase tracking-wider">Time</span>
                  </div>
                  <p className="font-heading font-bold text-lg text-primary">
                    {totalLatency ? formatLatency(totalLatency) : '--'}
                  </p>
                </div>
              </div>

              {/* Table breakdown */}
              {tableCount > 0 && (
                <div className="flex items-center gap-1.5 mb-3">
                  <Database size={10} className="text-text-muted" />
                  <span className="text-[10px] text-text-muted">
                    {tableCount} records across {Object.keys(liveStats.tables).length} tables
                  </span>
                </div>
              )}

              {/* Crop pills */}
              <div className="flex flex-wrap gap-1.5">
                {missionCard.crops.map((c) => (
                  <span key={c} className="bg-primary/10 text-primary px-2.5 py-0.5 rounded-full text-xs font-medium">
                    {c.charAt(0).toUpperCase() + c.slice(1)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Bottom bar */}
      <div className="bg-card border-t border-surface-dark px-4 py-3">
        <div className="max-w-lg mx-auto">
          {isComplete ? (
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-text-muted font-medium">Build complete</p>
              <button
                onClick={() => navigate('/packs')}
                className="bg-primary text-white text-sm font-semibold px-5 py-2 rounded-lg hover:bg-primary-light transition-colors min-h-[44px]"
              >
                View Pack
              </button>
            </div>
          ) : errorMessage ? (
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-tertiary font-medium">Pipeline stopped</p>
              <button
                onClick={() => navigate('/mission')}
                className="bg-tertiary text-white text-sm font-semibold px-5 py-2 rounded-lg hover:opacity-90 transition-opacity min-h-[44px]"
              >
                Try Again
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between text-xs mb-1.5">
                <span className="font-semibold text-text">{overallProgress}% complete</span>
                <button
                  onClick={() => {
                    wsRef.current?.close()
                    navigate('/mission')
                  }}
                  className="text-tertiary font-medium hover:underline"
                >
                  Cancel
                </button>
              </div>
              <div className="h-2 bg-primary/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-secondary rounded-full transition-all duration-500"
                  style={{ width: `${overallProgress}%` }}
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
