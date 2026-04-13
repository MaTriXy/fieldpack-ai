import { Zap } from 'lucide-react'

/**
 * SCENE 11 (1:40-1:55): Field session status panel
 * Offline mode card with pack details, model info, and pack stats.
 * Canvas: 1152x1080px dark cinematic.
 */

export default function FieldSessionFrame() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-bg px-20">
      {/* marginTop nudges content below true center for optical centering */}
      <div className="w-full max-w-[640px]" style={{ marginTop: '20px' }}>

        {/* Header */}
        <div className="animate-in delay-0">
          <p
            className="font-body font-semibold text-green-light uppercase"
            style={{ fontSize: '16px', letterSpacing: '0.3em' }}
          >
            FIELD SESSION
          </p>
          <h1 className="font-heading font-bold text-5xl text-cream mt-2">
            <span style={{ color: 'var(--color-cream)' }}>Day 3</span>
            <span style={{ color: 'var(--color-gold)' }}> · </span>
            <span style={{ color: 'var(--color-cream)' }}>Casamance</span>
          </h1>
          <div
            className="w-full mt-4 mb-10"
            style={{ height: '1px', background: 'rgba(82, 183, 136, 0.35)' }}
          />
        </div>

        {/* Offline Mode Card */}
        <div
          className="animate-in delay-1 rounded-2xl p-10"
          style={{
            background: 'var(--color-bg-card)',
            border: '1px solid rgba(82, 183, 136, 0.25)',
            boxShadow: '0 8px 40px rgba(0,0,0,0.4)',
          }}
        >

          {/* Row 1 — OFFLINE MODE badge */}
          <div className="animate-pop delay-2">
            <span
              className="inline-flex items-center gap-2.5 rounded-xl px-5 py-2.5"
              style={{
                background: 'rgba(212, 160, 23, 0.20)',
                border: '1.5px solid rgba(212, 160, 23, 0.50)',
                boxShadow: '0 0 20px rgba(212, 160, 23, 0.20)',
              }}
            >
              <Zap
                style={{
                  width: '24px',
                  height: '24px',
                  color: 'var(--color-gold)',
                  fill: 'rgba(212,160,23,0.25)',
                }}
              />
              <span
                className="font-body font-bold"
                style={{
                  fontSize: '18px',
                  color: 'var(--color-gold)',
                  letterSpacing: '0.15em',
                  textTransform: 'uppercase',
                }}
              >
                OFFLINE MODE
              </span>
            </span>
          </div>

          {/* Row 2 — Active Pack */}
          <div className="animate-in delay-3" style={{ marginTop: '2rem' }}>
            <p
              className="font-body font-semibold"
              style={{
                fontSize: '16px',
                color: 'var(--color-cream-muted)',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              Active Pack
            </p>
            <p
              className="font-heading font-bold mt-1.5"
              style={{ fontSize: '44px', lineHeight: 1.15, color: 'var(--color-cream)' }}
            >
              Casamance Agriculture
            </p>
          </div>

          {/* Divider */}
          <div
            className="animate-fade delay-4 w-full"
            style={{ height: '1px', background: 'rgba(82, 183, 136, 0.30)', marginTop: '1.75rem' }}
          />

          {/* Row 3 — Pack Stats: horizontal 3-column */}
          <div
            className="animate-in delay-4"
            style={{ marginTop: '1.75rem', display: 'flex', alignItems: 'stretch' }}
          >
            {/* Stat 1 */}
            <div style={{ flex: 1, textAlign: 'center' }}>
              <p
                className="font-heading font-bold"
                style={{ fontSize: '44px', lineHeight: 1, color: 'var(--color-gold)' }}
              >
                156
              </p>
              <p
                className="font-body mt-1.5"
                style={{ fontSize: '16px', color: 'var(--color-cream-muted)', lineHeight: 1.3 }}
              >
                knowledge<br />entries
              </p>
            </div>

            {/* Vertical divider */}
            <div style={{ width: '1px', background: 'rgba(82, 183, 136, 0.30)', margin: '0 0.5rem' }} />

            {/* Stat 2 */}
            <div style={{ flex: 1, textAlign: 'center' }}>
              <p
                className="font-heading font-bold"
                style={{ fontSize: '44px', lineHeight: 1, color: 'var(--color-gold)' }}
              >
                23
              </p>
              <p
                className="font-body mt-1.5"
                style={{ fontSize: '16px', color: 'var(--color-cream-muted)', lineHeight: 1.3 }}
              >
                reference<br />images
              </p>
            </div>

            {/* Vertical divider */}
            <div style={{ width: '1px', background: 'rgba(82, 183, 136, 0.30)', margin: '0 0.5rem' }} />

            {/* Stat 3 */}
            <div style={{ flex: 1, textAlign: 'center' }}>
              <p
                className="font-heading font-bold"
                style={{ fontSize: '44px', lineHeight: 1, color: 'var(--color-gold)' }}
              >
                47
              </p>
              <p
                className="font-body mt-1.5"
                style={{ fontSize: '16px', color: 'var(--color-cream-muted)', lineHeight: 1.3 }}
              >
                verified<br />sources
              </p>
            </div>
          </div>

          {/* Divider */}
          <div
            className="animate-fade delay-5 w-full"
            style={{ height: '1px', background: 'rgba(82, 183, 136, 0.30)', marginTop: '1.75rem' }}
          />

          {/* Row 4 — Model pill badge */}
          <div className="animate-in delay-5" style={{ marginTop: '1.75rem' }}>
            <p
              className="font-body font-semibold"
              style={{
                fontSize: '16px',
                color: 'var(--color-cream-muted)',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                marginBottom: '0.75rem',
              }}
            >
              AI Model
            </p>
            <span
              className="inline-flex items-center gap-2 rounded-lg px-4 py-2"
              style={{
                background: 'var(--color-bg)',
                border: '1px solid rgba(82, 183, 136, 0.30)',
              }}
            >
              <span
                className="font-body text-base"
                style={{ color: 'var(--color-cream)' }}
              >
                Gemma 4 E2B
              </span>
              <span style={{ color: 'rgba(82, 183, 136, 0.4)', fontSize: '1rem' }}>·</span>
              <span
                className="font-body text-base font-semibold"
                style={{ color: 'var(--color-green-light)' }}
              >
                Ollama
              </span>
              <span
                className="font-body text-base"
                style={{ color: 'var(--color-cream-muted)' }}
              >
                (local)
              </span>
            </span>
          </div>

          {/* Row 5 — Performance metrics */}
          <div
            className="animate-fade delay-6"
            style={{
              marginTop: '1.25rem',
              paddingTop: '1rem',
              borderTop: '1px solid rgba(82, 183, 136, 0.18)',
              display: 'flex',
              alignItems: 'center',
              gap: '1.5rem',
            }}
          >
            <span
              className="font-body"
              style={{ fontSize: '15px', color: 'var(--color-cream-muted)' }}
            >
              avg response
              <span style={{ color: 'rgba(82, 183, 136, 0.5)', margin: '0 0.35rem' }}>·</span>
              <span style={{ color: 'var(--color-cream)', fontWeight: 600 }}>4.2s</span>
            </span>
            <span
              style={{ width: '1px', height: '14px', background: 'rgba(82, 183, 136, 0.25)', display: 'inline-block' }}
            />
            <span
              className="font-body"
              style={{ fontSize: '15px', color: 'var(--color-cream-muted)' }}
            >
              throughput
              <span style={{ color: 'rgba(82, 183, 136, 0.5)', margin: '0 0.35rem' }}>·</span>
              <span style={{ color: 'var(--color-cream)', fontWeight: 600 }}>12 tok/s</span>
            </span>
          </div>

        </div>
      </div>
    </div>
  )
}
