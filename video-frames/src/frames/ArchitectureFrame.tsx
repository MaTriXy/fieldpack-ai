import { Cloud, Package, Smartphone, ChevronDown } from 'lucide-react'

/**
 * SCENE 7 (0:45-0:55): Architecture flow diagram
 * Three-box vertical pipeline: Cloud AI -> Knowledge Pack -> Edge AI.
 * Phase 1 (online) brackets Box 1. Phase 2 (offline) brackets Box 3.
 * Knowledge Pack box uses amber border + double-layer glow for key innovation.
 */
export default function ArchitectureFrame() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-bg px-16">
      <div className="w-full max-w-[620px] flex flex-col items-center">

        {/* Phase 1 label — gold to signal online/cloud */}
        <p
          className="font-body font-semibold text-gold tracking-[0.2em] uppercase mb-3 self-start animate-in delay-0"
          style={{ fontSize: '16px' }}
        >
          PHASE 1 &middot; ONLINE
        </p>

        {/* Box 1 — Cloud AI Agents */}
        <div
          className="w-full max-w-[620px] bg-bg-card border border-green/30 rounded-2xl p-8 animate-in delay-1"
        >
          <div className="flex items-center gap-4 mb-2">
            <Cloud className="w-7 h-7 text-gold shrink-0" />
            <span className="font-heading font-bold text-cream" style={{ fontSize: '28px' }}>
              Cloud AI Agents
            </span>
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span
              className="font-body text-cream-muted"
              style={{ fontSize: '22px', marginRight: '4px' }}
            >
              Models:
            </span>
            <span
              className="font-body font-semibold text-cream"
              style={{
                fontSize: '16px',
                padding: '3px 10px',
                borderRadius: '999px',
                background: 'rgba(15,26,20,0.8)',
                border: '1px solid rgba(45,106,79,0.45)',
              }}
            >
              Gemma 4 31B
            </span>
            <span
              className="font-body font-semibold text-cream"
              style={{
                fontSize: '16px',
                padding: '3px 10px',
                borderRadius: '999px',
                background: 'rgba(15,26,20,0.8)',
                border: '1px solid rgba(45,106,79,0.45)',
              }}
            >
              Gemma 4 26B
            </span>
          </div>
          <p className="font-body text-gold mt-2" style={{ fontSize: '20px' }}>
            Research &middot; Compile &middot; Verify
          </p>
        </div>

        {/* Arrow 1 — bright, visible */}
        <div className="flex flex-col items-center my-2 animate-fade delay-2">
          <div className="w-[3px] h-12 bg-green-light" />
          <ChevronDown className="w-6 h-6 text-green-light -mt-1" />
        </div>

        {/* Box 2 — Knowledge Pack (key innovation: double-layer amber glow) */}
        <div
          className="w-full max-w-[620px] bg-bg-card border-2 border-gold/50 rounded-2xl p-8 animate-in delay-3"
          style={{ boxShadow: '0 0 30px rgba(212,160,23,0.25), 0 0 60px rgba(212,160,23,0.1)' }}
        >
          <div className="flex items-center gap-4 mb-2">
            <Package className="w-7 h-7 text-gold shrink-0" />
            <span className="font-heading font-bold text-cream" style={{ fontSize: '28px' }}>
              Knowledge Pack
            </span>
          </div>
          <p className="font-body text-cream-muted mt-1" style={{ fontSize: '22px' }}>
            Portable &middot; 200 MB
          </p>
          <p className="font-body text-gold mt-1" style={{ fontSize: '20px' }}>
            Domain-specific &middot; Verified
          </p>
        </div>

        {/* Divider between Phase 1 and Phase 2 — must be visible */}
        <div className="w-full flex items-center gap-3 my-3">
          <div style={{ flex: 1, height: '1px', background: 'rgba(200,194,184,0.25)' }} />
          <span
            className="font-body font-semibold text-cream-muted tracking-[0.15em] uppercase shrink-0"
            style={{ fontSize: '11px', opacity: 0.6 }}
          >
            KNOWLEDGE PACK TRANSFER
          </span>
          <div style={{ flex: 1, height: '1px', background: 'rgba(200,194,184,0.25)' }} />
        </div>

        {/* Arrow 2 — bright, visible */}
        <div className="flex flex-col items-center mb-2 animate-fade delay-4">
          <div className="w-[3px] h-12 bg-green-light" />
          <ChevronDown className="w-6 h-6 text-green-light -mt-1" />
        </div>

        {/* Phase 2 label — green-light to signal offline/edge */}
        <p
          className="font-body font-semibold text-green-light tracking-[0.2em] uppercase mb-3 self-start animate-in delay-5"
          style={{ fontSize: '16px' }}
        >
          PHASE 2 &middot; OFFLINE
        </p>

        {/* Box 3 — Edge AI Agent */}
        <div
          className="w-full max-w-[620px] bg-bg-card border border-green/30 rounded-2xl p-8 animate-in delay-6"
        >
          <div className="flex items-center gap-4 mb-2">
            <Smartphone className="w-7 h-7 text-green-light shrink-0" />
            <span className="font-heading font-bold text-cream" style={{ fontSize: '28px' }}>
              Edge AI Agent
            </span>
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span
              className="font-body font-semibold text-cream"
              style={{
                fontSize: '16px',
                padding: '3px 10px',
                borderRadius: '999px',
                background: 'rgba(15,26,20,0.8)',
                border: '1px solid rgba(45,106,79,0.45)',
              }}
            >
              Gemma 4 E2B
            </span>
            <span className="font-body text-green-light" style={{ fontSize: '22px' }}>
              on Ollama
            </span>
          </div>
          <p className="font-body text-gold mt-2" style={{ fontSize: '20px' }}>
            Search &middot; Diagnose &middot; Advise
          </p>
        </div>

      </div>
    </div>
  )
}
