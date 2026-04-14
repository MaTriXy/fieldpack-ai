import { useEffect, useRef, useState } from 'react'

/**
 * SCENE 6 (0:35-0:45): Impact statistics
 * Three massive numbers that count up, staggered.
 * No cards, no chrome — just numbers carved into the darkness.
 */

interface StatConfig {
  /** Target numeric value (float) */
  target: number
  /** Suffix appended after the count: "M", "%", "B" */
  suffix: string
  /** Decimal places to display during count */
  decimals: number
  /** Delay before this stat starts counting (ms) */
  delay: number
  /** Duration of the count-up animation (ms) */
  duration: number
}

const STATS: StatConfig[] = [
  { target: 800,  suffix: 'M', decimals: 0, delay: 0,    duration: 800 },
  { target: 50,   suffix: '%', decimals: 0, delay: 800,  duration: 800 },
  { target: 3.7,  suffix: 'B', decimals: 1, delay: 1600, duration: 800 },
]

// Number font size in px — the anchor of every sizing decision
const NUM_SIZE   = 148
// Percent suffix is 60% of the number size for superscript treatment
const PCT_SIZE   = 88
// Suffix for non-percent (M, B) matches the number
const SUFF_SIZE  = 148

function useCountUp(config: StatConfig): { value: string; done: boolean } {
  const [raw, setRaw]   = useState(0)
  const [done, setDone] = useState(false)
  const rafRef          = useRef<number | null>(null)

  useEffect(() => {
    let startTime: number | null = null

    const tick = (timestamp: number) => {
      if (startTime === null) startTime = timestamp
      const elapsed  = timestamp - startTime
      const progress = Math.min(elapsed / config.duration, 1)
      // Ease-out cubic
      const eased    = 1 - Math.pow(1 - progress, 3)
      setRaw(eased * config.target)

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick)
      } else {
        setRaw(config.target)
        setDone(true)
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

  const value = raw.toFixed(config.decimals)
  return { value, done }
}

interface StatBlockProps {
  config: StatConfig
  label: string
  animateClass: string
}

function StatBlock({ config, label, animateClass }: StatBlockProps) {
  const { value, done } = useCountUp(config)

  const isPercent    = config.suffix === '%'
  const suffixSize   = isPercent ? PCT_SIZE : SUFF_SIZE

  return (
    <div className={animateClass}>
      {/* Number row — items-baseline so % sits flush at number base */}
      <div className="flex items-baseline" style={{ lineHeight: 1 }}>
        <span
          className="font-heading font-extrabold text-gold"
          style={{
            fontSize: `${NUM_SIZE}px`,
            lineHeight: 1,
            letterSpacing: '-0.03em',
            animation: done ? 'countPulse 0.4s ease-out' : undefined,
          }}
        >
          {value}
        </span>
        <span
          className="font-heading font-extrabold text-gold"
          style={{
            fontSize: `${suffixSize}px`,
            lineHeight: 1,
            letterSpacing: '-0.02em',
            // Nudge % up slightly so it reads as superscript without float tricks
            marginBottom: isPercent ? `${(NUM_SIZE - PCT_SIZE) * 0.35}px` : undefined,
          }}
        >
          {config.suffix}
        </span>
      </div>

      {/* Label — single line, no wrapping */}
      <p
        className="font-body text-cream-muted"
        style={{
          fontSize: '28px',
          marginTop: '16px',
          whiteSpace: 'nowrap',
          letterSpacing: '0.01em',
        }}
      >
        {label}
      </p>
    </div>
  )
}

export default function StatsFrame() {
  return (
    // Outer shell: full canvas, true vertical + horizontal center
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
        background: 'var(--color-bg)',
      }}
    >
      {/* Background photo — Senegal marketplace, conveys digital divide */}
      <img
        src="/photos/community_marketplace.jpg"
        alt=""
        aria-hidden="true"
        className="photo-bg"
        style={{ objectPosition: 'center 40%' }}
      />
      {/* Dark overlay — stats need high contrast */}
      <div
        aria-hidden="true"
        style={{ position: 'absolute', inset: 0, background: 'rgba(15, 26, 20, 0.75)', pointerEvents: 'none' }}
      />
      {/* Content block: generous max-width so numbers have room to breathe */}
      <div style={{ position: 'relative', width: '100%', maxWidth: '800px', paddingLeft: '80px', paddingRight: '80px', margin: '0 auto' }}>

        {/* Stat 1: 800M */}
        <StatBlock
          config={STATS[0]}
          animateClass="animate-in delay-0"
          label="people depend on cassava"
        />

        {/* Spacer + divider between stat 1 and 2 */}
        <div
          className="animate-in delay-1"
          style={{
            marginTop: '48px',
            marginBottom: '48px',
            height: '2px',
            background: 'rgba(45, 106, 79, 0.35)',
          }}
        />

        {/* Stat 2: 50% */}
        <StatBlock
          config={STATS[1]}
          animateClass="animate-in delay-3"
          label="crop yield lost to disease"
        />

        {/* Spacer + divider between stat 2 and 3 */}
        <div
          className="animate-in delay-4"
          style={{
            marginTop: '48px',
            marginBottom: '48px',
            height: '2px',
            background: 'rgba(45, 106, 79, 0.35)',
          }}
        />

        {/* Stat 3: 3.7B */}
        <StatBlock
          config={STATS[2]}
          animateClass="animate-in delay-6"
          label="people without reliable internet"
        />

      </div>
    </div>
  )
}
