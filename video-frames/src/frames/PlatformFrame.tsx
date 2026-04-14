import { Wheat, Stethoscope, BookOpen, Binoculars, Building2, ShieldAlert } from 'lucide-react'

/**
 * SCENE 14 (2:35-2:50): Platform vision — Knowledge Pack grid
 * Agriculture card is active/built (green glow, solid BUILT badge, lighter bg).
 * Five vision cards are clearly dimmed — 50% opacity text, 20% border.
 * Clean 3x2 grid with Disaster Response as the 6th card.
 */
export default function PlatformFrame() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-bg px-20" style={{ position: 'relative', overflow: 'hidden' }}>
      {/* Background photo — marketplace, platform = many domains */}
      <img
        src="/photos/community_marketplace.jpg"
        alt=""
        aria-hidden="true"
        className="photo-bg"
      />
      {/* Dark overlay — very heavy, 6-card grid needs max readability */}
      <div
        aria-hidden="true"
        style={{ position: 'absolute', inset: 0, background: 'rgba(15, 26, 20, 0.88)', pointerEvents: 'none' }}
      />
      <div className="flex flex-col items-start w-full max-w-[640px]" style={{ position: 'relative' }}>

        {/* Headline */}
        <div className="animate-in delay-0">
          <p className="font-heading font-extrabold leading-tight text-cream tracking-[0.03em]" style={{ fontSize: '56px' }}>
            ONE ARCHITECTURE.
          </p>
          <p className="font-heading font-extrabold leading-tight text-gold tracking-[0.03em] mt-1" style={{ fontSize: '56px' }}>
            ANY MISSION.
          </p>
          {/* Double divider */}
          <div className="mt-4 mb-1 h-0.5 w-[220px] bg-green-light/60" />
          <div className="mt-1 mb-7 h-0.5 w-[220px] bg-green-light/20" />
        </div>

        {/* Card grid — 3 columns, 2 rows = clean 6-card layout */}
        <div className="grid grid-cols-3 gap-4 w-full">

          {/* Card 1 — Agriculture (ACTIVE / BUILT) */}
          <div
            className="rounded-2xl border-2 border-green-light p-7 relative animate-pop delay-2"
            style={{
              background: '#1D3C2E',
              boxShadow: '0 0 30px 6px rgba(82,183,136,0.35)',
            }}
          >
            {/* BUILT badge — solid fill, clearly different from VISION */}
            <span
              className="absolute top-3 right-3 px-3 py-1 rounded font-bold tracking-[0.1em] uppercase"
              style={{ background: '#52B788', color: '#fff', fontSize: '12px' }}
            >
              BUILT
            </span>
            <Wheat className="w-9 h-9 text-green-light" />
            <p className="font-heading font-bold text-cream mt-3 leading-snug" style={{ fontSize: '22px' }}>
              Agriculture
            </p>
          </div>

          {/* Card 2 — Medical Triage (VISION) */}
          <div className="bg-bg-card/60 rounded-2xl border border-green/20 p-7 relative animate-pop delay-3">
            <span className="absolute top-3 right-3 bg-cream-muted/10 rounded px-2 py-0.5 font-normal tracking-[0.12em] uppercase" style={{ fontSize: '12px', color: 'rgba(200,194,184,0.55)' }}>
              VISION
            </span>
            <Stethoscope className="w-8 h-8" style={{ color: 'rgba(200,194,184,0.55)' }} />
            <p className="font-heading font-semibold mt-3 leading-snug" style={{ fontSize: '20px', color: 'rgba(200,194,184,0.65)' }}>
              Medical Triage
            </p>
          </div>

          {/* Card 3 — Education (VISION) */}
          <div className="bg-bg-card/60 rounded-2xl border border-green/20 p-7 relative animate-pop delay-4">
            <span className="absolute top-3 right-3 bg-cream-muted/10 rounded px-2 py-0.5 font-normal tracking-[0.12em] uppercase" style={{ fontSize: '12px', color: 'rgba(200,194,184,0.55)' }}>
              VISION
            </span>
            <BookOpen className="w-8 h-8" style={{ color: 'rgba(200,194,184,0.55)' }} />
            <p className="font-heading font-semibold mt-3 leading-snug" style={{ fontSize: '20px', color: 'rgba(200,194,184,0.65)' }}>
              Education
            </p>
          </div>

          {/* Card 4 — Wildlife Conservation (VISION) */}
          <div className="bg-bg-card/60 rounded-2xl border border-green/20 p-7 relative animate-pop delay-5">
            <span className="absolute top-3 right-3 bg-cream-muted/10 rounded px-2 py-0.5 font-normal tracking-[0.12em] uppercase" style={{ fontSize: '12px', color: 'rgba(200,194,184,0.55)' }}>
              VISION
            </span>
            <Binoculars className="w-8 h-8" style={{ color: 'rgba(200,194,184,0.55)' }} />
            <p className="font-heading font-semibold mt-3 leading-snug" style={{ fontSize: '20px', color: 'rgba(200,194,184,0.65)' }}>
              Wildlife Conservation
            </p>
          </div>

          {/* Card 5 — Infra Assessment (VISION) */}
          <div className="bg-bg-card/60 rounded-2xl border border-green/20 p-7 relative animate-pop delay-6">
            <span className="absolute top-3 right-3 bg-cream-muted/10 rounded px-2 py-0.5 font-normal tracking-[0.12em] uppercase" style={{ fontSize: '12px', color: 'rgba(200,194,184,0.55)' }}>
              VISION
            </span>
            <Building2 className="w-8 h-8" style={{ color: 'rgba(200,194,184,0.55)' }} />
            <p className="font-heading font-semibold mt-3 leading-snug" style={{ fontSize: '20px', color: 'rgba(200,194,184,0.65)' }}>
              Infra Assessment
            </p>
          </div>

          {/* Card 6 — Disaster Response (VISION) — completes the 3x2 grid */}
          <div className="bg-bg-card/60 rounded-2xl border border-green/20 p-7 relative animate-pop delay-7">
            <span className="absolute top-3 right-3 bg-cream-muted/10 rounded px-2 py-0.5 font-normal tracking-[0.12em] uppercase" style={{ fontSize: '12px', color: 'rgba(200,194,184,0.55)' }}>
              VISION
            </span>
            <ShieldAlert className="w-8 h-8" style={{ color: 'rgba(200,194,184,0.55)' }} />
            <p className="font-heading font-semibold mt-3 leading-snug" style={{ fontSize: '20px', color: 'rgba(200,194,184,0.65)' }}>
              Disaster Response
            </p>
          </div>

        </div>

        {/* Subtitle — manifesto line, not a footnote */}
        <p className="mt-8 font-body text-xl font-medium text-cream animate-fade delay-8">
          Same system. Different pack. Any mission.
        </p>

      </div>
    </div>
  )
}
