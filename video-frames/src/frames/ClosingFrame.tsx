/**
 * SCENE 15 (2:50-3:00): Closing card
 * Project name, tagline, tech credits, logo placeholders.
 * The last frame before credits. Resolved. Cinematic.
 * Canvas: 1152x1080px
 */

export default function ClosingFrame() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-bg relative" style={{ overflow: 'hidden' }}>

      {/* Background photo — bookend with title frame */}
      <img
        src="/photos/community_children.jpg"
        alt=""
        aria-hidden="true"
        className="photo-bg"
        style={{ objectPosition: 'center 30%' }}
      />
      {/* Dark overlay — heavier than title for gravitas */}
      <div
        aria-hidden="true"
        style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at center, rgba(15,26,20,0.72) 0%, rgba(15,26,20,0.90) 100%)', pointerEvents: 'none' }}
      />

      {/* Content stack — true vertical + horizontal center */}
      <div
        className="relative flex flex-col items-center text-center"
        style={{ gap: '2.75rem' }}
      >

        {/* Title — dominant, must fill the frame with presence */}
        <h1
          className="font-heading text-cream animate-in delay-0"
          style={{
            fontSize: '108px',
            fontWeight: 800,
            letterSpacing: '0.17em',
            lineHeight: 1,
            textShadow: '0 0 80px rgba(212,160,23,0.12)',
            margin: 0,
          }}
        >
          FIELDPACK AI
        </h1>

        {/* Gold rule — solid 3px, matches TitleFrame exactly, signals resolution */}
        <div
          className="animate-fade delay-1"
          style={{
            height: '3px',
            width: '160px',
            background: '#D4A017',
            borderRadius: '2px',
          }}
        />

        {/* Tagline — italic, two lines, second line in warm gold, boosted to 34px */}
        <div
          className="flex flex-col items-center animate-in delay-2"
          style={{ gap: '0.5rem' }}
        >
          <p
            className="font-body text-cream-muted"
            style={{ fontSize: '38px', fontWeight: 400, fontStyle: 'italic', margin: 0 }}
          >
            The people who need AI most
          </p>
          <p
            className="font-body"
            style={{
              fontSize: '38px',
              fontWeight: 400,
              fontStyle: 'italic',
              color: '#D4A017',
              margin: 0,
            }}
          >
            are the ones furthest from the cloud.
          </p>
        </div>

        {/* Secondary headline — subordinate to tagline, lighter weight */}
        <p
          className="font-body text-cream-muted animate-in delay-3"
          style={{
            fontSize: '18px',
            fontWeight: 400,
            letterSpacing: '0.02em',
            margin: 0,
          }}
        >
          Built with Gemma 4 on Ollama
        </p>

        {/* Logo pills — Gemma 4 gets gold border tint, Ollama keeps green */}
        <div
          className="flex items-center animate-in delay-4"
          style={{ gap: '1.25rem' }}
        >
          <div
            style={{
              padding: '0.75rem 2rem',
              borderRadius: '9999px',
              background: '#1a3328',
              border: '1px solid rgba(212,160,23,0.35)',
            }}
          >
            <span
              className="font-heading"
              style={{ fontSize: '18px', fontWeight: 600, letterSpacing: '0.04em', color: '#E8C55A' }}
            >
              Gemma 4
            </span>
          </div>
          <div
            style={{
              padding: '0.75rem 2rem',
              borderRadius: '9999px',
              background: '#1a3328',
              border: '1px solid rgba(82,183,136,0.4)',
            }}
          >
            <span
              className="font-heading text-green-light"
              style={{ fontSize: '18px', fontWeight: 600, letterSpacing: '0.04em' }}
            >
              Ollama
            </span>
          </div>
        </div>

        {/* Competition callout — between pills and GitHub URL */}
        <p
          className="font-body animate-fade delay-5"
          style={{
            fontSize: '15px',
            fontWeight: 400,
            color: 'rgba(200,194,184,0.40)',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            margin: 0,
          }}
        >
          Kaggle Gemma 4 Good Hackathon 2026
        </p>

        {/* GitHub — watermark treatment only, cream-muted at 30% */}
        <p
          className="font-body animate-fade delay-6"
          style={{
            fontSize: '13px',
            fontWeight: 400,
            color: 'rgba(200,194,184,0.30)',
            letterSpacing: '0.03em',
            margin: 0,
          }}
        >
          github.com/or-kol/fieldpack-ai
        </p>

      </div>
    </div>
  )
}
