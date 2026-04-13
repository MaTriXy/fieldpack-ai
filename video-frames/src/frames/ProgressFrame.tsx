import { useEffect, useRef, useState } from 'react'
import { Check } from 'lucide-react'

/**
 * SCENE 9 (1:10-1:30): Knowledge pack compilation dashboard
 * Three animated progress bars, summary stats, and a 5-step phase checklist.
 * Canvas: 1152x1080px dark cinematic.
 */

// ---- Count-up hook (integer only, ease-out cubic) ----

interface CountUpConfig {
  target: number
  delay: number
  duration: number
}

function useCountUp(config: CountUpConfig): number {
  const [value, setValue] = useState(0)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    let startTime: number | null = null

    const tick = (timestamp: number) => {
      if (startTime === null) startTime = timestamp
      const elapsed  = timestamp - startTime
      const progress = Math.min(elapsed / config.duration, 1)
      const eased    = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(eased * config.target))

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick)
      } else {
        setValue(config.target)
      }
    }

    const timer = setTimeout(() => {
      rafRef.current = requestAnimationFrame(tick)
    }, config.delay)

    return () => {
      clearTimeout(timer)
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [config.delay, config.duration, config.target])

  return value
}

// ---- Individual progress bar ----

interface BarProps {
  label: string
  fillPercent: number
  target: number
  delayClass: string
  countDelay: number
}

function ProgressBar({ label, fillPercent, target, delayClass, countDelay }: BarProps) {
  const count = useCountUp({ target, delay: countDelay, duration: 1400 })

  return (
    <div className={`animate-in ${delayClass}`}>
      <p className="font-body text-cream-muted mb-2" style={{ fontSize: '20px' }}>{label}</p>
      <div className="flex items-center gap-4">
        {/* Track — explicit dark-green so it reads against card bg */}
        <div
          className="flex-1 h-5 rounded-full overflow-hidden"
          style={{ background: '#1E3A28' }}
        >
          {/* Fill — barFill keyframe animates width from 0% */}
          <div
            className="h-full rounded-full"
            style={{
              width: `${fillPercent}%`,
              background: 'linear-gradient(to right, var(--color-green), var(--color-green-light))',
              animation: 'barFill 1.5s ease-out both',
              animationDelay: `${countDelay / 1000}s`,
            }}
          />
        </div>
        {/* Animated count — text-3xl, gold, consistent across all bars */}
        <span
          className="font-heading font-bold text-3xl text-gold"
          style={{ minWidth: '72px', textAlign: 'right' }}
        >
          {count}
        </span>
      </div>
    </div>
  )
}

// ---- Checklist item variants ----

interface ChecklistItemProps {
  state: 'done' | 'active' | 'pending'
  label: string
  delayClass: string
}

function ChecklistItem({ state, label, delayClass }: ChecklistItemProps) {
  let indicator: React.ReactNode
  let textClass: string

  if (state === 'done') {
    indicator = (
      <div
        className="w-6 h-6 rounded-full flex items-center justify-center shrink-0"
        style={{ background: 'var(--color-green-light)' }}
      >
        <Check className="w-3.5 h-3.5" style={{ color: '#fff' }} />
      </div>
    )
    textClass = 'font-body text-cream font-semibold'
  } else if (state === 'active') {
    indicator = (
      <div
        className="w-6 h-6 rounded-full shrink-0"
        style={{
          background: 'var(--color-gold)',
          animation: 'glowPulse 2s infinite',
        }}
      />
    )
    textClass = 'font-body text-gold font-bold'
  } else {
    indicator = (
      <div
        className="w-6 h-6 rounded-full shrink-0"
        style={{ border: '2px solid rgba(200, 194, 184, 0.30)' }}
      />
    )
    textClass = 'font-body font-normal'
  }

  if (state === 'active') {
    return (
      <div
        className={`flex items-center gap-3 animate-in ${delayClass} rounded-lg px-3 py-3`}
        style={{
          background: 'rgba(212, 160, 23, 0.08)',
          borderLeft: '3px solid var(--color-gold)',
        }}
      >
        {indicator}
        <span className={textClass} style={{ fontSize: '18px' }}>{label}</span>
      </div>
    )
  }

  return (
    <div
      className={`flex items-center gap-3 animate-in ${delayClass} px-3 py-1`}
    >
      {indicator}
      <span
        className={textClass}
        style={state === 'pending' ? { fontSize: '18px', color: 'rgba(200, 194, 184, 0.65)' } : { fontSize: '18px' }}
      >
        {label}
      </span>
    </div>
  )
}

// ---- Main frame ----

export default function ProgressFrame() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-bg px-20">
      <div className="w-full max-w-[680px]">

        {/* Header — clear anchor, text-base with strong letter-spacing */}
        <div className="animate-in delay-0 mb-6">
          <p
            className="font-body font-bold text-green-light uppercase"
            style={{ fontSize: '18px', letterSpacing: '0.2em' }}
          >
            COMPILING KNOWLEDGE PACK
          </p>
          {/* Double-line divider — h-[3px] each, clearly visible */}
          <div className="w-full mt-3" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div className="w-full h-[3px] rounded-full" style={{ background: 'rgba(82, 183, 136, 0.55)' }} />
            <div className="w-full h-[3px] rounded-full" style={{ background: 'rgba(82, 183, 136, 0.25)' }} />
          </div>
        </div>

        {/* Progress bars */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
          <ProgressBar
            label="Sources Gathered"
            fillPercent={78}
            target={47}
            delayClass="delay-1"
            countDelay={300}
          />
          <ProgressBar
            label="Knowledge Entries"
            fillPercent={87}
            target={156}
            delayClass="delay-2"
            countDelay={600}
          />
          <ProgressBar
            label="Reference Images"
            fillPercent={46}
            target={23}
            delayClass="delay-3"
            countDelay={900}
          />
        </div>

        {/* Summary stats — anchored in a card so they don't float */}
        <div className="animate-in delay-4 mt-8">
          <div
            className="rounded-lg p-4"
            style={{
              background: 'var(--color-bg-card)',
              border: '1px solid rgba(45, 106, 79, 0.20)',
              borderLeft: '3px solid rgba(212,160,23,0.5)',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div className="flex justify-between items-center">
                <span className="font-body text-cream-muted" style={{ fontSize: '18px' }}>Estimated Pack Size</span>
                <span className="font-heading font-bold text-3xl text-gold">~200 MB</span>
              </div>
              <div
                className="w-full"
                style={{ height: '1px', background: 'rgba(45, 106, 79, 0.25)' }}
              />
              <div className="flex justify-between items-center">
                <span className="font-body text-cream-muted" style={{ fontSize: '18px' }}>Processing Time</span>
                <span className="font-heading font-bold text-3xl text-gold">~8 min</span>
              </div>
            </div>
          </div>
        </div>

        {/* Checklist card */}
        <div
          className="animate-in delay-5 rounded-xl mt-6"
          style={{
            background: 'var(--color-bg-card)',
            border: '1px solid rgba(45, 106, 79, 0.30)',
            padding: '1.25rem 1rem',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <ChecklistItem state="done"    label="Source Gathering"      delayClass="delay-6"  />
            <ChecklistItem state="done"    label="Knowledge Extraction"  delayClass="delay-7"  />
            <ChecklistItem state="active"  label="Compilation..."        delayClass="delay-8"  />
            <ChecklistItem state="pending" label="Chunk Generation"      delayClass="delay-9"  />
            <ChecklistItem state="pending" label="Image Download"        delayClass="delay-10" />
          </div>
        </div>

      </div>
    </div>
  )
}
