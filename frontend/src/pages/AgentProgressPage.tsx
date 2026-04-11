import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, Loader2, Circle } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import { listPacks, type PackSummary } from '../lib/api'

interface AgentStep {
  name: string
  status: 'completed' | 'in_progress' | 'pending'
  detail: string
  latency?: string
  findings?: string[]
  progress?: number
}

function buildSteps(pack: PackSummary | null): AgentStep[] {
  const cropCount = pack?.crops.length ?? 0
  const entryCount = pack?.knowledge_entries ?? 0
  const sourceCount = (pack?.sources ?? []).length
  return [
    {
      name: 'Mission Planner',
      status: 'completed',
      detail: `Identified ${cropCount} crops, ${entryCount} knowledge entries, ${sourceCount} expert sources`,
      latency: '2.3s',
    },
    {
      name: 'Research Agents',
      status: 'in_progress',
      detail: `3 of ${cropCount} agents complete`,
      progress: 60,
      findings: [
        'Found 12 cassava diseases',
        'Found 8 rice blast treatments',
        'Gathering pest data...',
      ],
    },
    {
      name: 'Knowledge Compiler',
      status: 'pending',
      detail: 'Waiting for research...',
    },
    {
      name: 'Pack Builder',
      status: 'pending',
      detail: 'Will create database and vector store',
    },
  ]
}

function buildLogEntries(pack: PackSummary | null): string[] {
  const sources = pack?.sources ?? []
  return [
    `[Agent 2] Researching rice blast treatments from ${sources[2] ?? 'PlantVillage'}...`,
    `[Agent 1] Found cassava mosaic data from ${sources[1] ?? 'IITA'}`,
    `[Agent 3] Querying ${sources[0] ?? 'FAO'} disease database...`,
    `[Agent 4] Gathering ${pack?.region ?? 'target region'} climate data...`,
    '[Agent 2] Found 3 organic treatments for rice blast',
    '[Agent 5] Collecting pest management protocols...',
  ]
}

export default function AgentProgressPage() {
  const [activePack, setActivePack] = useState<PackSummary | null>(null)
  const [steps, setSteps] = useState<AgentStep[]>(buildSteps(null))
  const [logs, setLogs] = useState<string[]>([])
  const [overallProgress] = useState(47)
  const navigate = useNavigate()

  useEffect(() => {
    listPacks()
      .then((packs) => {
        const loaded = packs.find((p) => p.loaded) ?? packs[0] ?? null
        setActivePack(loaded)
        setSteps(buildSteps(loaded))
        const entries = buildLogEntries(loaded)
        setLogs([entries[0]])
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    const entries = buildLogEntries(activePack)
    let i = 1
    const interval = setInterval(() => {
      if (i < entries.length) {
        setLogs((prev) => [...prev, entries[i]])
        i++
      } else {
        clearInterval(interval)
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [activePack])

  const StatusIcon = ({ status }: { status: AgentStep['status'] }) => {
    if (status === 'completed') return <Check size={18} className="text-white" />
    if (status === 'in_progress') return <Loader2 size={18} className="text-white animate-spin" />
    return <Circle size={18} className="text-white/50" />
  }

  const statusBg = (status: AgentStep['status']) => {
    if (status === 'completed') return 'bg-primary'
    if (status === 'in_progress') return 'bg-secondary'
    return 'bg-text-muted/30'
  }

  return (
    <div className="flex flex-col h-[calc(100dvh-4rem)] animate-fadeIn">
      <TopBar title="Building Pack" back backTo="/mission" badge={{ label: 'Live', variant: 'live' }} />

      {/* Mission summary */}
      <div className="bg-primary/5 px-4 py-3 border-b border-surface-dark">
        <div className="max-w-lg mx-auto">
          <p className="font-heading font-bold text-sm text-text">{activePack?.name ?? 'Loading pack...'}</p>
          <p className="text-xs text-text-muted">{activePack?.crops.map(c => c.charAt(0).toUpperCase() + c.slice(1)).join(', ') ?? ''}</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-surface">
        <div className="max-w-lg mx-auto space-y-3">
          {/* Timeline */}
          {steps.map((step, idx) => (
            <div key={step.name} className="flex gap-3">
              {/* Vertical line + icon */}
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${statusBg(step.status)}`}>
                  <StatusIcon status={step.status} />
                </div>
                {idx < steps.length - 1 && (
                  <div className={`w-0.5 flex-1 mt-1 ${step.status === 'completed' ? 'bg-primary/30' : 'bg-text-muted/15'}`} />
                )}
              </div>

              {/* Card */}
              <div className={`flex-1 bg-card rounded-xl p-3 shadow-sm border border-surface-dark mb-1 border-l-4 ${
                step.status === 'completed'
                  ? 'border-l-primary'
                  : step.status === 'in_progress'
                  ? 'border-l-secondary'
                  : 'border-l-text-muted/30'
              }`}>
                <div className="flex items-center justify-between">
                  <h3 className="font-heading font-bold text-sm">{step.name}</h3>
                  {step.latency && (
                    <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-mono">
                      {step.latency}
                    </span>
                  )}
                </div>
                <p className="text-xs text-text-muted mt-1">{step.detail}</p>

                {step.progress !== undefined && (
                  <div className="mt-2 h-1.5 bg-surface-dark rounded-full overflow-hidden">
                    <div
                      className="h-full bg-secondary rounded-full transition-all"
                      style={{ width: `${step.progress}%` }}
                    />
                  </div>
                )}

                {step.findings && (
                  <ul className="mt-2 space-y-0.5">
                    {step.findings.map((f) => (
                      <li key={f} className="text-xs text-text-muted flex items-center gap-1.5">
                        <span className="w-1 h-1 rounded-full bg-secondary shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          ))}

          {/* Activity log */}
          <div className="bg-debug-bg rounded-xl p-3 mt-4">
            <p className="text-xs font-mono text-white/60 mb-2 uppercase tracking-wider">Activity Feed</p>
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {logs.map((log) => (
                <p key={log} className="text-sm font-mono text-green-400/90 leading-snug">{log}</p>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom progress */}
      <div className="bg-card border-t border-surface-dark px-4 py-3">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="font-semibold text-text">{overallProgress}% complete</span>
            <button
              onClick={() => navigate('/packs')}
              className="text-tertiary font-medium hover:underline"
            >
              Cancel
            </button>
          </div>
          <div className="h-2 bg-surface-dark rounded-full overflow-hidden">
            <div
              className="h-full bg-secondary rounded-full transition-all"
              style={{ width: `${overallProgress}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
