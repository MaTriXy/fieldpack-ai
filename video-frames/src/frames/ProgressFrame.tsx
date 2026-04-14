import { useEffect, useRef, useState } from 'react'

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

// ---- Main frame ----

export default function ProgressFrame() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-bg px-20" style={{ position: 'relative', overflow: 'hidden' }}>
      {/* Background photo -- woman planting in Sierra Leone */}
      <img
        src="/photos/persona_planting.jpg"
        alt=""
        aria-hidden="true"
        className="photo-bg"
      />
      {/* Dark overlay -- heavy, progress data needs to dominate */}
      <div
        aria-hidden="true"
        style={{ position: 'absolute', inset: 0, background: 'rgba(15, 26, 20, 0.85)', pointerEvents: 'none' }}
      />
      <div className="w-full max-w-[680px]" style={{ position: 'relative' }}>

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


      </div>
    </div>
  )
}
