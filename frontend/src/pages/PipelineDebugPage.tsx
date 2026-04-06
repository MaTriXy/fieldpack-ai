import { Loader2, Check, Circle } from 'lucide-react'
import TopBar from '../components/layout/TopBar'

interface PipelineNode {
  name: string
  status: 'completed' | 'in_progress' | 'pending'
  detail: string
  latency: string
  tokens?: string
  extra?: string
}

const NODES: PipelineNode[] = [
  {
    name: 'classify_and_extract',
    status: 'completed',
    detail: 'Intent: diagnose_disease, Crop: cassava, Confidence: 0.95',
    latency: '4,200ms',
    tokens: 'in:380 out:128',
  },
  {
    name: 'route_intent',
    status: 'completed',
    detail: 'Route: disease_knowledge + treatment_guides',
    latency: '2ms',
    extra: 'Engines: chroma_embedding, fts_keyword',
  },
  {
    name: 'craft_search_query',
    status: 'completed',
    detail: 'Template query (no LLM)',
    latency: '1ms',
    extra: 'cassava mosaic yellow leaves curling Casamance',
  },
  {
    name: 'execute_searches',
    status: 'completed',
    detail: 'Chroma: 8 results, FTS: 5 results, SQLite: 3 results',
    latency: '120ms',
  },
  {
    name: 'rerank_results',
    status: 'completed',
    detail: 'Heuristic rerank (no LLM needed)',
    latency: '5ms',
    extra: 'Top score: 0.92, Sufficient: yes',
  },
  {
    name: 'generate_answer',
    status: 'in_progress',
    detail: 'Streaming tokens...',
    latency: '8,400ms',
    tokens: '347/1024',
  },
]

const StatusIcon = ({ status }: { status: PipelineNode['status'] }) => {
  if (status === 'completed') return <Check size={14} className="text-green-400" />
  if (status === 'in_progress') return <Loader2 size={14} className="text-secondary animate-spin" />
  return <Circle size={14} className="text-white/30" />
}

const latencyColor = (latency: string) => {
  const ms = parseInt(latency.replace(/[^0-9]/g, ''))
  if (ms < 100) return 'text-green-400'
  if (ms < 2000) return 'text-secondary'
  return 'text-tertiary-light'
}

export default function PipelineDebugPage() {
  return (
    <div className="flex flex-col min-h-[calc(100dvh-4rem)] bg-debug-bg">
      <TopBar title="Pipeline Debug" dark badge={{ label: 'Live', variant: 'live' }} back backTo="/field" />

      {/* Query */}
      <div className="bg-debug-card px-4 py-2 border-b border-white/5">
        <p className="text-xs text-white/50 max-w-lg mx-auto">
          Query: <span className="text-white/80 italic">"What's wrong with my cassava?"</span>
        </p>
      </div>

      {/* Provider */}
      <div className="bg-debug-card/50 px-4 py-2 border-b border-white/5">
        <div className="max-w-lg mx-auto flex items-center justify-between">
          <span className="text-xs text-white/70">Gemma 4 E2B Q4 via Ollama (local)</span>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
            <span className="text-xs text-green-400">Connected</span>
          </div>
        </div>
      </div>

      {/* Pipeline nodes */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="max-w-lg mx-auto space-y-2">
          {NODES.map((node, idx) => (
            <div key={node.name} className="flex gap-3">
              {/* Timeline */}
              <div className="flex flex-col items-center pt-3">
                <StatusIcon status={node.status} />
                {idx < NODES.length - 1 && (
                  <div className={`w-px flex-1 mt-1 ${node.status === 'completed' ? 'bg-green-400/20' : 'bg-white/10'}`} />
                )}
              </div>

              {/* Card */}
              <div className="flex-1 bg-debug-card rounded-lg p-3 border border-white/5 mb-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono font-semibold text-white/90">{node.name}</span>
                  <span className={`text-xs font-mono ${latencyColor(node.latency)}`}>{node.latency}</span>
                </div>
                <p className="text-xs text-white/60">{node.detail}</p>
                {node.tokens && (
                  <p className="text-xs text-white/40 font-mono mt-0.5">Tokens: {node.tokens}</p>
                )}
                {node.extra && (
                  <p className="text-xs text-white/40 mt-0.5">{node.extra}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Summary */}
      <div className="bg-debug-card border-t border-white/5 px-4 py-3">
        <div className="max-w-lg mx-auto">
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-white/50">Total latency:</span>
              <span className="text-secondary font-mono">12,728ms</span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/50">LLM calls:</span>
              <span className="text-white/80 font-mono">2</span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/50">Search results:</span>
              <span className="text-white/80 font-mono">16 \u2192 5</span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/50">Provider:</span>
              <span className="text-green-400 font-mono">Ollama local</span>
            </div>
          </div>
          <div className="flex items-center justify-between mt-3">
            <button className="text-xs text-white/50 hover:text-white/80 border border-white/10 px-3 py-1.5 rounded-md">
              Copy Debug Log
            </button>
            <label className="flex items-center gap-1.5 text-xs text-white/50">
              <input type="checkbox" defaultChecked className="accent-secondary" />
              Auto-scroll
            </label>
          </div>
        </div>
      </div>
    </div>
  )
}
