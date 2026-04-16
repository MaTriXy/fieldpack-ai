import { useEffect, useState } from 'react'
import { Search, Brain, GitBranch, FileSearch, Database, BarChart3, MessageSquare } from 'lucide-react'

/**
 * SCENE 12b (1:50-2:20): RAG Pipeline Visualization
 * Shows the agentic pipeline processing Amina's cassava question in real-time.
 * Nodes light up sequentially: classify → route → needs_search → craft_query
 * → execute_search → rerank → generate_answer.
 *
 * The cassava disease photo (disease_cmd_figure.jpg) anchors the "what is
 * being processed" context. A query bar at top shows the user's question.
 *
 * 30-second frame — pipeline animation takes ~18s, then result holds.
 * Canvas: 1152x1080px dark cinematic.
 */

interface PipelineNode {
  id: string
  label: string
  subtitle: string
  icon: React.FC<{ className?: string; style?: React.CSSProperties }>
  activateAt: number   // ms after mount
  durationMs: number   // how long the "processing" pulse lasts
}

const PIPELINE: PipelineNode[] = [
  {
    id: 'classify',
    label: 'Classify',
    subtitle: 'Plant disease query detected',
    icon: GitBranch,
    activateAt: 1200,
    durationMs: 1800,
  },
  {
    id: 'route',
    label: 'Route',
    subtitle: 'Agriculture knowledge pack',
    icon: GitBranch,
    activateAt: 3200,
    durationMs: 1500,
  },
  {
    id: 'needs_search',
    label: 'Needs Search',
    subtitle: 'RAG retrieval required',
    icon: Search,
    activateAt: 5000,
    durationMs: 1400,
  },
  {
    id: 'craft_query',
    label: 'Craft Query',
    subtitle: '"cassava mosaic disease treatment Casamance"',
    icon: Brain,
    activateAt: 6700,
    durationMs: 1800,
  },
  {
    id: 'execute_search',
    label: 'Execute Search',
    subtitle: '3 chunks retrieved · relevance 0.94',
    icon: Database,
    activateAt: 8800,
    durationMs: 2200,
  },
  {
    id: 'rerank',
    label: 'Rerank',
    subtitle: 'LLM reranking · top 3 verified',
    icon: BarChart3,
    activateAt: 11300,
    durationMs: 1800,
  },
  {
    id: 'generate_answer',
    label: 'Generate Answer',
    subtitle: 'Streaming response with citations',
    icon: MessageSquare,
    activateAt: 13400,
    durationMs: 2500,
  },
]

type NodeState = 'waiting' | 'active' | 'done'

function useNodeStates(): Record<string, NodeState> {
  const [states, setStates] = useState<Record<string, NodeState>>(() => {
    const init: Record<string, NodeState> = {}
    for (const node of PIPELINE) init[node.id] = 'waiting'
    return init
  })

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = []

    for (const node of PIPELINE) {
      // Activate
      timers.push(
        setTimeout(() => {
          setStates(prev => ({ ...prev, [node.id]: 'active' }))
        }, node.activateAt),
      )
      // Complete
      timers.push(
        setTimeout(() => {
          setStates(prev => ({ ...prev, [node.id]: 'done' }))
        }, node.activateAt + node.durationMs),
      )
    }

    return () => timers.forEach(clearTimeout)
  }, [])

  return states
}

function NodeRow({
  node,
  state,
  isLast,
}: {
  node: PipelineNode
  state: NodeState
  isLast: boolean
}) {
  const Icon = node.icon

  const borderColor =
    state === 'active'
      ? 'rgba(212, 160, 23, 0.7)'
      : state === 'done'
        ? 'rgba(82, 183, 136, 0.5)'
        : 'rgba(45, 106, 79, 0.25)'

  const bgColor =
    state === 'active'
      ? 'rgba(212, 160, 23, 0.08)'
      : state === 'done'
        ? 'rgba(82, 183, 136, 0.06)'
        : 'rgba(22, 41, 32, 0.6)'

  const shadow =
    state === 'active'
      ? '0 0 20px rgba(212, 160, 23, 0.25), 0 0 40px rgba(212, 160, 23, 0.1)'
      : 'none'

  const iconColor =
    state === 'active'
      ? '#D4A017'
      : state === 'done'
        ? '#52B788'
        : 'rgba(200, 194, 184, 0.35)'

  const labelColor =
    state === 'waiting'
      ? 'rgba(200, 194, 184, 0.45)'
      : '#F5F1EB'

  const subtitleColor =
    state === 'active'
      ? 'rgba(212, 160, 23, 0.75)'
      : state === 'done'
        ? 'rgba(82, 183, 136, 0.65)'
        : 'rgba(200, 194, 184, 0.25)'

  return (
    <>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          padding: '14px 20px',
          borderRadius: '12px',
          border: `1px solid ${borderColor}`,
          background: bgColor,
          boxShadow: shadow,
          transition: 'all 0.5s ease-out',
        }}
      >
        {/* Status indicator */}
        <div
          style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background:
              state === 'active'
                ? '#D4A017'
                : state === 'done'
                  ? '#52B788'
                  : 'rgba(45, 106, 79, 0.3)',
            boxShadow:
              state === 'active'
                ? '0 0 8px rgba(212, 160, 23, 0.6)'
                : 'none',
            transition: 'all 0.4s ease-out',
            animation: state === 'active' ? 'dotPulse 1.2s ease-in-out infinite' : 'none',
            flexShrink: 0,
          }}
        />

        {/* Icon */}
        <Icon
          className="shrink-0"
          style={{
            width: '22px',
            height: '22px',
            color: iconColor,
            transition: 'color 0.4s ease-out',
          }}
        />

        {/* Label + subtitle */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <p
            className="font-heading font-bold"
            style={{
              fontSize: '20px',
              color: labelColor,
              transition: 'color 0.4s ease-out',
            }}
          >
            {node.label}
          </p>
          <p
            className="font-body"
            style={{
              fontSize: '14px',
              color: subtitleColor,
              transition: 'color 0.5s ease-out',
              marginTop: '2px',
            }}
          >
            {node.subtitle}
          </p>
        </div>

        {/* Status badge */}
        {state === 'done' && (
          <span
            className="font-body font-semibold uppercase"
            style={{
              fontSize: '11px',
              letterSpacing: '0.12em',
              color: '#52B788',
              padding: '3px 10px',
              borderRadius: '999px',
              background: 'rgba(82, 183, 136, 0.12)',
              border: '1px solid rgba(82, 183, 136, 0.3)',
              animation: 'fadeInOnly 0.3s ease-out both',
            }}
          >
            DONE
          </span>
        )}
        {state === 'active' && (
          <span
            className="font-body font-semibold uppercase"
            style={{
              fontSize: '11px',
              letterSpacing: '0.12em',
              color: '#D4A017',
              padding: '3px 10px',
              borderRadius: '999px',
              background: 'rgba(212, 160, 23, 0.1)',
              border: '1px solid rgba(212, 160, 23, 0.3)',
            }}
          >
            RUNNING
          </span>
        )}
      </div>

      {/* Connector line between nodes */}
      {!isLast && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-start',
            paddingLeft: '29px',
          }}
        >
          <div
            style={{
              width: '2px',
              height: '8px',
              background:
                state === 'done'
                  ? 'rgba(82, 183, 136, 0.4)'
                  : 'rgba(45, 106, 79, 0.2)',
              transition: 'background 0.4s ease-out',
            }}
          />
        </div>
      )}
    </>
  )
}

export default function PipelineFrame() {
  const nodeStates = useNodeStates()

  return (
    <div
      className="w-full h-full flex bg-bg"
      style={{ position: 'relative', overflow: 'hidden' }}
    >
      {/* Background photo — cassava disease reference */}
      <img
        src="/photos/disease_cmd_field.jpg"
        alt=""
        aria-hidden="true"
        className="photo-bg"
        style={{ objectPosition: 'center center' }}
      />
      {/* Dark overlay — very heavy, pipeline data must dominate */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(15, 26, 20, 0.92)',
          pointerEvents: 'none',
        }}
      />

      {/* Content — two-column layout: pipeline left, context right */}
      <div
        style={{
          position: 'relative',
          display: 'flex',
          width: '100%',
          height: '100%',
          padding: '48px 48px 48px 56px',
          gap: '40px',
        }}
      >
        {/* Left column — pipeline nodes */}
        <div style={{ flex: '1 1 0', display: 'flex', flexDirection: 'column' }}>
          {/* Header */}
          <div className="animate-in delay-0" style={{ marginBottom: '24px' }}>
            <p
              className="font-body font-bold text-green-light uppercase"
              style={{ fontSize: '16px', letterSpacing: '0.2em' }}
            >
              AGENTIC RAG PIPELINE
            </p>
            <div
              style={{
                marginTop: '10px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              <div
                className="w-full h-[3px] rounded-full"
                style={{ background: 'rgba(82, 183, 136, 0.55)' }}
              />
              <div
                className="w-full h-[3px] rounded-full"
                style={{ background: 'rgba(82, 183, 136, 0.25)' }}
              />
            </div>
          </div>

          {/* Pipeline nodes */}
          <div
            className="animate-fade delay-1"
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              flex: 1,
            }}
          >
            {PIPELINE.map((node, i) => (
              <NodeRow
                key={node.id}
                node={node}
                state={nodeStates[node.id]}
                isLast={i === PIPELINE.length - 1}
              />
            ))}
          </div>
        </div>

        {/* Right column — query context + cassava image + output preview */}
        <div
          style={{
            width: '380px',
            flexShrink: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: '20px',
          }}
        >
          {/* User query card */}
          <div
            className="animate-in delay-0"
            style={{
              background: 'rgba(22, 41, 32, 0.8)',
              border: '1px solid rgba(212, 160, 23, 0.3)',
              borderRadius: '12px',
              padding: '20px',
            }}
          >
            <p
              className="font-body font-semibold uppercase text-gold"
              style={{ fontSize: '12px', letterSpacing: '0.15em', marginBottom: '8px' }}
            >
              AMINA&apos;S QUESTION
            </p>
            <p
              className="font-body text-cream"
              style={{ fontSize: '18px', lineHeight: 1.5 }}
            >
              &ldquo;My cassava leaves are curling and have yellow patches. What disease is this and how do I treat it?&rdquo;
            </p>
          </div>

          {/* Cassava disease reference image */}
          <div
            className="animate-in delay-1"
            style={{
              borderRadius: '12px',
              overflow: 'hidden',
              border: '1px solid rgba(45, 106, 79, 0.3)',
            }}
          >
            <img
              src="/photos/disease_cmd_field.jpg"
              alt="Cassava mosaic disease — healthy vs infected leaves"
              style={{
                width: '100%',
                height: 'auto',
                display: 'block',
              }}
            />
            <div
              style={{
                background: 'rgba(22, 41, 32, 0.9)',
                padding: '10px 16px',
                borderTop: '1px solid rgba(45, 106, 79, 0.25)',
              }}
            >
              <p
                className="font-body text-cream-muted"
                style={{ fontSize: '13px' }}
              >
                Cassava Mosaic Disease — healthy (B) vs. infected (C, E)
              </p>
            </div>
          </div>

          {/* Retrieved sources — appear after execute_search completes */}
          <div
            style={{
              background: 'rgba(22, 41, 32, 0.7)',
              border: '1px solid rgba(45, 106, 79, 0.25)',
              borderRadius: '12px',
              padding: '16px 20px',
              opacity: nodeStates['execute_search'] === 'done' || nodeStates['rerank'] !== 'waiting' ? 1 : 0,
              pointerEvents: nodeStates['execute_search'] === 'done' || nodeStates['rerank'] !== 'waiting' ? 'auto' : 'none',
              transition: 'opacity 0.6s ease-out',
            }}
          >
            <p
              className="font-body font-semibold uppercase text-green-light"
              style={{ fontSize: '12px', letterSpacing: '0.15em', marginBottom: '12px' }}
            >
              RETRIEVED SOURCES
            </p>
            {[
              { name: 'PlantVillage — CMD Identification', score: '0.94' },
              { name: 'FAO Treatment Protocols', score: '0.89' },
              { name: 'IITA Resistant Varieties', score: '0.82' },
            ].map((src) => (
              <div
                key={src.name}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '6px 0',
                  borderBottom: '1px solid rgba(45, 106, 79, 0.15)',
                }}
              >
                <FileSearch
                  style={{
                    width: '14px',
                    height: '14px',
                    color: 'rgba(82, 183, 136, 0.6)',
                    marginRight: '8px',
                    flexShrink: 0,
                  }}
                />
                <span
                  className="font-body text-cream"
                  style={{ fontSize: '14px', flex: 1 }}
                >
                  {src.name}
                </span>
                <span
                  className="font-body font-semibold text-gold"
                  style={{ fontSize: '14px', marginLeft: '12px' }}
                >
                  {src.score}
                </span>
              </div>
            ))}
          </div>

          {/* Streaming output preview — appears after generate_answer starts */}
          <div
            style={{
              background: 'rgba(22, 41, 32, 0.7)',
              border: '1px solid rgba(45, 106, 79, 0.25)',
              borderLeft: '3px solid rgba(212, 160, 23, 0.5)',
              borderRadius: '8px',
              padding: '14px 16px',
              opacity: nodeStates['generate_answer'] !== 'waiting' ? 1 : 0,
              pointerEvents: nodeStates['generate_answer'] !== 'waiting' ? 'auto' : 'none',
              transition: 'opacity 0.6s ease-out',
              flex: 1,
              minHeight: 0,
            }}
          >
            <p
              className="font-body font-semibold uppercase text-gold"
              style={{ fontSize: '12px', letterSpacing: '0.15em', marginBottom: '10px' }}
            >
              GENERATING RESPONSE
            </p>
            <p
              className="font-body text-cream-muted"
              style={{ fontSize: '15px', lineHeight: 1.65 }}
            >
              The symptoms you describe — leaf curling with yellow mosaic patterns — are consistent with{' '}
              <span className="text-cream font-semibold">Cassava Mosaic Disease (CMD)</span>, caused by
              geminiviruses transmitted by whiteflies...
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
