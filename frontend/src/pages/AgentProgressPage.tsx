import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Check, Loader2, Circle, AlertTriangle, CheckCircle } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import { getMissionWsUrl } from '../lib/config'

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
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${ms}ms`
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusIcon({ status }: { status: StepStatus }) {
  if (status === 'completed') return <Check size={18} className="text-white" />
  if (status === 'in_progress') return <Loader2 size={18} className="text-white animate-spin" />
  return <Circle size={18} className="text-white/50" />
}

function statusBg(status: StepStatus): string {
  if (status === 'completed') return 'bg-primary'
  if (status === 'in_progress') return 'bg-secondary'
  return 'bg-text-muted/30'
}

function statusBorderL(status: StepStatus): string {
  if (status === 'completed') return 'border-l-primary'
  if (status === 'in_progress') return 'border-l-secondary'
  return 'border-l-text-muted/30'
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
        setLogs((prev) => [...prev, `[${displayName}] ${detail}`])
      } else if (type === 'phase_complete') {
        const phase = data.phase as string
        const latencyMs = data.latency_ms as number
        const displayName = PHASE_DISPLAY[phase] ?? phase
        const latencyStr = formatLatency(latencyMs)

        setSteps((prev) =>
          prev.map((s) =>
            s.phase === phase
              ? { ...s, status: 'completed', latency: latencyStr }
              : s
          )
        )
        setLogs((prev) => [...prev, `[${displayName}] Complete (${latencyStr})`])

        setOverallProgress((prev) => {
          const completedCount = prev / (100 / 6) + 1
          return Math.round(Math.min(completedCount * (100 / 6), 100))
        })
      } else if (type === 'done') {
        isDoneRef.current = true
        const summary = data.summary as Record<string, unknown>
        const totalMs = summary?.total_latency_ms as number | undefined
        const findings = summary?.findings as number | undefined
        const chunks = summary?.chunks as number | undefined
        const images = summary?.images as number | undefined

        const parts: string[] = []
        if (findings !== undefined) parts.push(`${findings} findings`)
        if (chunks !== undefined) parts.push(`${chunks} chunks`)
        if (images !== undefined) parts.push(`${images} images`)
        if (totalMs !== undefined) parts.push(`total ${formatLatency(totalMs)}`)

        const summaryLine = parts.length > 0
          ? `Pack built: ${parts.join(', ')}`
          : 'Pack built successfully'

        setCompleteSummary(summaryLine)
        setLogs((prev) => [...prev, `[Done] ${summaryLine}`])
        setOverallProgress(100)
        setIsComplete(true)
      } else if (type === 'error') {
        const message = (data.message as string) ?? 'An unknown error occurred'
        isErrorRef.current = true
        setErrorMessage(message)
        setLogs((prev) => [...prev, `[Error] ${message}`])
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

  return (
    <div className="flex flex-col h-[calc(100dvh-4rem)] animate-fadeIn">
      <TopBar title="Building Pack" back backTo="/mission" badge={topBarBadge} />

      {/* Mission summary */}
      <div className="bg-primary/5 px-4 py-3 border-b border-surface-dark">
        <div className="max-w-lg mx-auto">
          <p className="font-heading font-bold text-sm text-text">{missionCard.region}</p>
          <p className="text-xs text-text-muted">{cropLabel}</p>
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
            <div key={step.phase} className="flex gap-3">
              {/* Vertical line + icon */}
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${statusBg(step.status)}`}>
                  <StatusIcon status={step.status} />
                </div>
                {idx < steps.length - 1 && (
                  <div
                    className={`w-0.5 flex-1 mt-1 ${
                      step.status === 'completed' ? 'bg-primary/30' : 'bg-text-muted/15'
                    }`}
                  />
                )}
              </div>

              {/* Card */}
              <div
                className={`flex-1 bg-card rounded-xl p-3 shadow-sm border border-surface-dark mb-1 border-l-4 ${statusBorderL(step.status)}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-heading font-bold text-sm">{step.name}</h3>
                  {step.latency && (
                    <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-mono shrink-0">
                      {step.latency}
                    </span>
                  )}
                </div>
                <p className="text-xs text-text-muted mt-1 leading-relaxed">{step.detail}</p>
              </div>
            </div>
          ))}

          {/* Activity feed */}
          <div className="bg-debug-bg rounded-xl p-3 mt-4">
            <p className="text-xs font-mono text-white/60 mb-2 uppercase tracking-wider">
              Activity Feed
            </p>
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {logs.length === 0 && (
                <p className="text-xs font-mono text-white/30 italic">Waiting for pipeline to start...</p>
              )}
              {logs.map((log, i) => (
                <p
                  key={i}
                  className="text-sm font-mono text-green-400/90 leading-snug break-words"
                >
                  {log}
                </p>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>

          {/* Success banner */}
          {isComplete && completeSummary && (
            <div className="flex items-start gap-3 bg-primary/10 border border-primary/20 rounded-xl px-4 py-3 animate-fadeIn">
              <CheckCircle size={18} className="text-primary shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-primary">Pack Ready</p>
                <p className="text-xs text-text-muted mt-0.5">{completeSummary}</p>
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
              <div className="h-2 bg-surface-dark rounded-full overflow-hidden">
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
