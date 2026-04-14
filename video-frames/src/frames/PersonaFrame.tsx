import { MapPin, Target, AlertTriangle } from 'lucide-react'

/**
 * SCENE 4 (0:18-0:28): Amina's profile card
 * THE most important scene. This is who we built for.
 * Elements fade in top-to-bottom over 3 seconds.
 *
 * BACKGROUND PHOTO NOTE:
 * Replace the radial gradient layer below with a real stock photo of Senegal farmland.
 * Suggested: Unsplash search "Senegal farm field worker" or "Casamance agriculture".
 * Use: <img src="YOUR_STOCK_PHOTO_URL" style={{ position:'absolute', inset:0, width:'100%', height:'100%', objectFit:'cover', opacity:0.07, filter:'blur(8px) saturate(1.4)' }} />
 * Then remove or reduce the CSS gradient simulation below.
 */
export default function PersonaFrame() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-bg px-16" style={{ position: 'relative', overflow: 'hidden' }}>

      {/* Background photo — woman harvesting cassava in West Africa */}
      <img
        src="/photos/persona_smiling.jpg"
        alt=""
        aria-hidden="true"
        className="photo-bg"
      />
      {/* Dark overlay for text readability */}
      <div
        aria-hidden="true"
        style={{ position: 'absolute', inset: 0, background: 'rgba(15, 26, 20, 0.70)', pointerEvents: 'none' }}
      />

      <div className="w-full max-w-[680px]" style={{ position: 'relative' }}>
        {/* Section label */}
        <p
          className="font-body text-green-light uppercase mb-8 animate-fade delay-0"
          style={{ fontSize: '20px', letterSpacing: '0.25em' }}
        >
          Meet Amina
        </p>

        {/* Main card — gold left border for warmth */}
        <div className="bg-bg-card rounded-2xl border border-green/30 border-l-[3px] border-l-gold overflow-hidden">
          {/* Header */}
          <div className="px-10 pt-10 pb-6 border-b border-green/20 flex items-center gap-6 animate-in delay-1">
            {/* Photo avatar — cropped from background photo */}
            <div
              className="w-20 h-20 rounded-full shrink-0 overflow-hidden"
              style={{ border: '2px solid rgba(212, 160, 23, 0.4)' }}
            >
              <img
                src="/photos/persona_smiling.jpg"
                alt="Amina Diallo"
                className="w-full h-full object-cover"
                style={{ objectPosition: 'center 20%' }}
              />
            </div>
            <div>
              <h2 className="font-heading font-bold text-5xl text-cream tracking-tight">
                Amina Diallo
              </h2>
              <p className="font-body text-xl text-gold mt-1">
                Agronomist
              </p>
            </div>
          </div>

          {/* Details */}
          <div className="px-10 py-8 space-y-7">
            {/* Organization */}
            <div className="animate-in delay-2">
              <p
                className="font-body text-cream-muted tracking-[0.2em] uppercase mb-1.5"
                style={{ fontSize: '16px' }}
              >
                Organization
              </p>
              <p
                className="font-body font-semibold text-cream"
                style={{ fontSize: '28px' }}
              >
                Action Against Hunger
              </p>
            </div>

            {/* Mission */}
            <div className="animate-in delay-3">
              <div className="flex items-center gap-2 mb-1.5">
                <MapPin className="w-4 h-4 text-gold shrink-0" />
                <p
                  className="font-body text-cream-muted tracking-[0.2em] uppercase"
                  style={{ fontSize: '16px' }}
                >
                  Mission
                </p>
              </div>
              <p
                className="font-body font-semibold text-cream"
                style={{ fontSize: '28px' }}
              >
                3-week field deployment
              </p>
              <p
                className="font-body text-cream-muted mt-0.5"
                style={{ fontSize: '22px' }}
              >
                Casamance, Senegal
              </p>
            </div>

            {/* Focus */}
            <div className="animate-in delay-4">
              <div className="flex items-center gap-2 mb-1.5">
                <Target className="w-4 h-4 text-gold shrink-0" />
                <p
                  className="font-body text-cream-muted tracking-[0.2em] uppercase"
                  style={{ fontSize: '16px' }}
                >
                  Focus
                </p>
              </div>
              <p
                className="font-body font-semibold text-cream"
                style={{ fontSize: '28px' }}
              >
                Cassava &amp; rice disease response
              </p>
              <p
                className="font-body text-cream-muted mt-0.5"
                style={{ fontSize: '22px' }}
              >
                Drought-season survival strategy
              </p>
            </div>

            {/* Challenge — visually isolated with red tint */}
            <div className="animate-in delay-5">
              <div
                className="rounded-lg p-4 border-l-[3px] border-red"
                style={{ background: 'rgba(196, 69, 54, 0.07)' }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-red shrink-0" />
                  <p
                    className="font-body text-cream-muted tracking-[0.2em] uppercase"
                    style={{ fontSize: '16px' }}
                  >
                    Challenge
                  </p>
                </div>
                <p
                  className="font-body font-semibold text-red-light"
                  style={{ fontSize: '28px' }}
                >
                  No reliable internet access
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
