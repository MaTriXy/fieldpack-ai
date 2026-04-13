import { useState, useEffect } from 'react'
import { FIELD_FACTS, type FieldFact } from '../lib/field-facts'

/** Default step labels for the field chat RAG pipeline. */
export const STEP_LABELS: Record<string, string> = {
  classifying: 'Understanding your question',
  evaluating: 'Checking what I know',
  routing: 'Planning search strategy',
  crafting: 'Building search queries',
  searching: 'Searching knowledge base',
  reranking: 'Picking the best results',
  expanding: 'Widening the search',
  generating: 'Writing your answer',
  saving: 'Saving observation',
}

interface ThinkingBubbleProps {
  step: string | null
  mode: 'quick' | 'rag' | null
  insights: string[]
  stepLabels?: Record<string, string>
  facts?: FieldFact[]
}

export default function ThinkingBubble({
  step,
  mode,
  insights,
  stepLabels = STEP_LABELS,
  facts = FIELD_FACTS,
}: ThinkingBubbleProps) {
  const [factIndex, setFactIndex] = useState(() => Math.floor(Math.random() * facts.length))
  const [fadeKey, setFadeKey] = useState(0)

  useEffect(() => {
    if (mode !== 'rag') return
    const id = setInterval(() => {
      setFactIndex((i) => (i + 1) % facts.length)
      setFadeKey((k) => k + 1)
    }, 15000)
    return () => clearInterval(id)
  }, [mode, facts.length])

  const fact = facts[factIndex]
  const stepLabel = step ? (stepLabels[step] || step) : null

  if (mode === 'quick' || mode === null) {
    // Show step label with spinner if a step is active, otherwise bouncing dots
    if (stepLabel) {
      return (
        <div className="flex items-center gap-2.5">
          <div className="w-4.5 h-4.5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-primary font-semibold">{stepLabel}...</span>
        </div>
      )
    }
    return (
      <div className="flex gap-1.5 items-center h-5">
        <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounceTyping" />
        <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounceTyping [animation-delay:0.15s]" />
        <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounceTyping [animation-delay:0.3s]" />
      </div>
    )
  }

  // RAG pipeline — show live insights one by one + step + fact
  return (
    <div className="space-y-2">
      {/* Current step spinner — always on top */}
      {stepLabel && (
        <div className="flex items-center gap-2.5">
          <div className="w-4.5 h-4.5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-primary font-semibold">{stepLabel}...</span>
        </div>
      )}
      {/* Pipeline activity feed — completed steps appear below */}
      {insights.length > 0 && (
        <div className="space-y-1 border-l-2 border-primary/25 pl-3 ml-[7px] mt-1">
          {insights.map((text, i) => {
            const isLatest = i === insights.length - 1
            return (
              <div
                key={`${i}-${text}`}
                className={`flex items-center gap-2 ${isLatest ? 'animate-fadeIn' : ''}`}
              >
                <span className={`text-xs leading-none ${isLatest ? 'text-primary' : 'text-text-muted/50'}`}>✓</span>
                <span className={`text-[13px] leading-snug ${isLatest ? 'text-text-secondary' : 'text-text-muted/50'}`}>
                  {text}
                </span>
              </div>
            )
          })}
        </div>
      )}
      {/* Field fact — only before any insights arrive */}
      {insights.length === 0 && (
        <div key={fadeKey} className="flex items-start gap-2.5 animate-fadeIn">
          <span className="text-lg leading-none mt-0.5">{fact.icon}</span>
          <p className="text-xs text-text-muted italic leading-relaxed">{fact.text}</p>
        </div>
      )}
    </div>
  )
}
