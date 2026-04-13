import { useState, useRef, useEffect, useCallback } from 'react'
import { Loader2, Check, Circle, Play, RotateCcw, Copy, CopyCheck } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import { apiUrl } from '../lib/config'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type NodeStatus = 'completed' | 'in_progress' | 'pending'

interface PipelineNode {
  id: string
  name: string
  status: NodeStatus
  detail: string
  latency_ms: number | null
  insight: string | null
}

type RunState = 'idle' | 'running' | 'done' | 'error'

interface SummaryStats {
  total_latency_ms: number
  llm_calls: number
  provider: string
  mode: string | null
}

// ---------------------------------------------------------------------------
// WebSocket event shapes (minimal -- only what we read)
// ---------------------------------------------------------------------------

interface WsStatus       { type: 'status';           step: string; detail?: string }
interface WsNodeStats    { type: 'node_stats';        node: string; latency_ms: number; model?: string }
interface WsNodeComplete { type: 'node_complete';     node: string }
interface WsPipelineMode { type: 'pipeline_mode';     mode: string }
interface WsPipelineInsight { type: 'pipeline_insight'; node: string; insight: string }
interface WsDone         { type: 'done';              final_answer: string; model?: string }
type WsEvent = WsStatus | WsNodeStats | WsNodeComplete | WsPipelineMode | WsPipelineInsight | WsDone | { type: string }

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DEFAULT_QUERY = "What's wrong with my cassava?"

/** Friendly display name from raw node identifier or status step string. */
function labelFromStep(step: string): string {
  return step
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/** Format a millisecond value for display. */
function formatMs(ms: number | null): string {
  if (ms === null) return '...'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

/** Tailwind color class based on latency. */
function latencyColor(ms: number | null): string {
  if (ms === null) return 'text-white/40'
  if (ms < 100) return 'text-green-400'
  if (ms < 2000) return 'text-secondary'
  return 'text-tertiary-light'
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const StatusIcon = ({ status }: { status: NodeStatus }) => {
  if (status === 'completed')   return <Check   size={14} className="text-green-400" />
  if (status === 'in_progress') return <Loader2 size={14} className="text-secondary animate-spin" />
  return <Circle size={14} className="text-white/30" />
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function PipelineDebugPage() {
  const [query, setQuery]       = useState(DEFAULT_QUERY)
  const [runState, setRunState] = useState<RunState>('idle')
  const [nodes, setNodes]       = useState<PipelineNode[]>([])
  const [stats, setStats]       = useState<SummaryStats>({
    total_latency_ms: 0,
    llm_calls: 0,
    provider: '--',
    mode: null,
  })
  const [error, setError]       = useState<string | null>(null)
  const [copied, setCopied]     = useState(false)

  const wsRef       = useRef<WebSocket | null>(null)
  const nodesRef    = useRef<PipelineNode[]>([])
  const llmCallsRef = useRef(0)
  const bottomRef   = useRef<HTMLDivElement>(null)

  // Keep ref in sync so WS callbacks always see latest nodes.
  useEffect(() => { nodesRef.current = nodes }, [nodes])

  // Auto-scroll to bottom as nodes arrive.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [nodes.length])

  // ---------------------------------------------------------------------------
  // WebSocket orchestration
  // ---------------------------------------------------------------------------

  const closeWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const upsertNode = useCallback((
    id: string,
    patch: Partial<Omit<PipelineNode, 'id'>>,
  ) => {
    setNodes((prev) => {
      const idx = prev.findIndex((n) => n.id === id)
      if (idx === -1) {
        return [
          ...prev,
          {
            id,
            name: patch.name ?? labelFromStep(id),
            status: patch.status ?? 'in_progress',
            detail: patch.detail ?? '',
            latency_ms: patch.latency_ms ?? null,
            insight: patch.insight ?? null,
          },
        ]
      }
      const updated = [...prev]
      updated[idx] = { ...updated[idx], ...patch }
      return updated
    })
  }, [])

  const handleMessage = useCallback((raw: string) => {
    let event: WsEvent
    try { event = JSON.parse(raw) } catch { return }

    switch (event.type) {
      case 'status': {
        const e = event as WsStatus
        upsertNode(e.step, {
          name: labelFromStep(e.step),
          status: 'in_progress',
          detail: e.detail ?? '',
        })
        break
      }

      case 'node_stats': {
        const e = event as WsNodeStats
        if (e.model) llmCallsRef.current += 1
        upsertNode(e.node, {
          status: 'completed',
          latency_ms: e.latency_ms,
        })
        setStats((prev) => ({
          ...prev,
          total_latency_ms: prev.total_latency_ms + e.latency_ms,
          llm_calls: llmCallsRef.current,
          provider: e.model ?? prev.provider,
        }))
        break
      }

      case 'node_complete': {
        const e = event as WsNodeComplete
        upsertNode(e.node, { status: 'completed' })
        break
      }

      case 'pipeline_mode': {
        const e = event as WsPipelineMode
        setStats((prev) => ({ ...prev, mode: e.mode }))
        break
      }

      case 'pipeline_insight': {
        const e = event as WsPipelineInsight
        upsertNode(e.node, { insight: e.insight })
        break
      }

      case 'token':
        upsertNode('generate_answer', {
          name: 'Generate Answer',
          status: 'in_progress',
          detail: 'Streaming tokens...',
        })
        break

      case 'done': {
        const e = event as WsDone
        upsertNode('generate_answer', { status: 'completed' })
        setStats((prev) => ({
          ...prev,
          provider: e.model ?? prev.provider,
        }))
        setRunState('done')
        closeWs()
        break
      }

      case 'error': {
        const e = event as { type: string; detail?: string }
        setError((e as { detail?: string }).detail ?? 'Pipeline error')
        setRunState('error')
        closeWs()
        break
      }

      default:
        break
    }
  }, [upsertNode, closeWs])

  const runPipeline = useCallback(() => {
    if (runState === 'running') return
    closeWs()

    setNodes([])
    setError(null)
    llmCallsRef.current = 0
    setStats({ total_latency_ms: 0, llm_calls: 0, provider: '--', mode: null })
    setRunState('running')

    const wsUrl = apiUrl('/chat/ws').replace(/^http/, 'ws')
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify({ message: query, conversation_id: 'debug' }))
    }

    ws.onmessage = (evt) => handleMessage(evt.data)

    ws.onerror = () => {
      setError('WebSocket connection failed. Is the backend running?')
      setRunState('error')
    }

    ws.onclose = (evt) => {
      if (evt.code !== 1000 && evt.code !== 1005) {
        setRunState((prev) => {
          if (prev === 'running') {
            setError(`Connection closed unexpectedly (code ${evt.code}).`)
            return 'error'
          }
          return prev
        })
      }
    }
  }, [runState, query, handleMessage, closeWs])

  // Cleanup on unmount
  useEffect(() => () => closeWs(), [closeWs])

  // ---------------------------------------------------------------------------
  // Copy debug log
  // ---------------------------------------------------------------------------

  const copyLog = useCallback(() => {
    const lines = nodesRef.current.map((n) =>
      `${n.name.padEnd(28)} ${n.status.padEnd(12)} ${formatMs(n.latency_ms).padStart(8)}${n.insight ? '  // ' + n.insight : ''}`
    )
    const text = [
      `Query: ${query}`,
      `Mode: ${stats.mode ?? 'unknown'}`,
      `Provider: ${stats.provider}`,
      `Total: ${formatMs(stats.total_latency_ms)}  LLM calls: ${stats.llm_calls}`,
      '',
      ...lines,
    ].join('\n')

    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [query, stats])

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const isRunning = runState === 'running'

  const resetAll = useCallback(() => {
    setRunState('idle')
    setNodes([])
    setError(null)
    setStats({ total_latency_ms: 0, llm_calls: 0, provider: '--', mode: null })
  }, [])

  return (
    <div className="flex flex-col min-h-[calc(100dvh-4rem)] bg-debug-bg animate-fadeIn">
      <TopBar title="Pipeline Debug" dark badge={{ label: 'Dev', variant: 'live' }} back backTo="/field" />

      {/* Query input */}
      <div className="bg-debug-card px-4 py-3 border-b border-white/5">
        <div className="max-w-lg mx-auto flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !isRunning) runPipeline() }}
            placeholder="Test query..."
            disabled={isRunning}
            aria-label="Test query"
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/90
                       placeholder:text-white/30 focus:outline-none focus:border-secondary/60
                       disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            onClick={!isRunning ? runPipeline : undefined}
            disabled={isRunning || query.trim() === ''}
            aria-label="Run pipeline"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-secondary text-white text-xs font-semibold
                       disabled:opacity-40 disabled:cursor-not-allowed active:opacity-80 transition-opacity"
          >
            {isRunning
              ? <Loader2 size={14} className="animate-spin" />
              : <Play size={14} />}
            Run
          </button>
          {(runState === 'done' || runState === 'error') && (
            <button
              onClick={resetAll}
              aria-label="Reset"
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/10 text-white/60
                         hover:text-white/90 hover:border-white/20 text-xs transition-colors"
            >
              <RotateCcw size={14} />
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Provider / mode bar */}
      <div className="bg-debug-card/50 px-4 py-2 border-b border-white/5">
        <div className="max-w-lg mx-auto flex items-center justify-between">
          <span className="text-xs text-white/70 font-mono truncate max-w-[60%]">
            {stats.provider === '--' ? 'Awaiting connection...' : stats.provider}
            {stats.mode && (
              <span className="ml-2 text-white/40">({stats.mode} mode)</span>
            )}
          </span>
          <div className="flex items-center gap-1.5 shrink-0">
            {isRunning && (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                <span className="text-xs text-green-400">Live</span>
              </>
            )}
            {runState === 'done' && (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                <span className="text-xs text-green-400">Done</span>
              </>
            )}
            {runState === 'error' && (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                <span className="text-xs text-red-400">Error</span>
              </>
            )}
            {runState === 'idle' && (
              <span className="text-xs text-white/40">Ready</span>
            )}
          </div>
        </div>
      </div>

      {/* Pipeline nodes */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="max-w-lg mx-auto space-y-2">

          {/* Idle / empty state */}
          {runState === 'idle' && nodes.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Play size={32} className="text-white/20 mb-3" />
              <p className="text-white/40 text-sm">Type a query and press Run</p>
              <p className="text-white/25 text-xs mt-1">to trace the live pipeline</p>
            </div>
          )}

          {/* Error state */}
          {runState === 'error' && error && (
            <div className="bg-red-900/30 border border-red-500/30 rounded-lg p-4 text-sm text-red-300">
              {error}
            </div>
          )}

          {/* Node list */}
          {nodes.map((node, idx) => (
            <div key={node.id} className="flex gap-3">
              {/* Timeline */}
              <div className="flex flex-col items-center pt-3 shrink-0">
                <StatusIcon status={node.status} />
                {idx < nodes.length - 1 && (
                  <div
                    className={`w-px flex-1 mt-1 ${node.status === 'completed' ? 'bg-green-400/20' : 'bg-white/10'}`}
                  />
                )}
              </div>

              {/* Card */}
              <div className="flex-1 bg-debug-card rounded-lg p-3 border border-white/5 mb-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-xs font-mono font-semibold text-white/90 truncate">
                    {node.name}
                  </span>
                  <span className={`text-xs font-mono shrink-0 ${latencyColor(node.latency_ms)}`}>
                    {formatMs(node.latency_ms)}
                  </span>
                </div>
                {node.detail && (
                  <p className="text-xs text-white/60 break-words">{node.detail}</p>
                )}
                {node.insight && (
                  <p className="text-xs text-secondary/80 mt-0.5 italic break-words">{node.insight}</p>
                )}
                {node.status === 'in_progress' && (
                  <div className="mt-1.5 h-0.5 rounded-full bg-white/10 overflow-hidden">
                    <div className="h-full w-1/3 bg-secondary/60 rounded-full" style={{ animation: 'shimmer 1.2s ease-in-out infinite' }} />
                  </div>
                )}
              </div>
            </div>
          ))}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Summary bar */}
      <div className="bg-debug-card border-t border-white/5 px-4 py-3">
        <div className="max-w-lg mx-auto">
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-white/50">Total latency:</span>
              <span className={`font-mono ${latencyColor(stats.total_latency_ms || null)}`}>
                {stats.total_latency_ms ? formatMs(stats.total_latency_ms) : '--'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/50">LLM calls:</span>
              <span className="text-white/80 font-mono">{stats.llm_calls || '--'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/50">Nodes run:</span>
              <span className="text-white/80 font-mono">
                {nodes.length
                  ? `${nodes.filter((n) => n.status === 'completed').length}/${nodes.length}`
                  : '--'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/50">Mode:</span>
              <span className="text-green-400 font-mono">{stats.mode ?? '--'}</span>
            </div>
          </div>

          <div className="flex items-center justify-between mt-3">
            <button
              onClick={copyLog}
              disabled={nodes.length === 0}
              className="flex items-center gap-1.5 text-xs text-white/50 hover:text-white/80
                         border border-white/10 px-3 py-1.5 rounded-md transition-colors
                         disabled:opacity-30 disabled:cursor-not-allowed"
            >
              {copied ? <CopyCheck size={12} className="text-green-400" /> : <Copy size={12} />}
              {copied ? 'Copied' : 'Copy Debug Log'}
            </button>
            <span className="text-xs text-white/30 font-mono">
              {nodes.length} node{nodes.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
