import { FileText } from 'lucide-react'

/**
 * SCENE 13 (2:20-2:35): Grounded AI
 * Verified sources panel. Four source entries in a card, then three
 * closing manifesto punches -- the amber punchline lands hardest.
 */

interface SourceEntry {
  name: string
  animateDelay: string
}

const SOURCES: SourceEntry[] = [
  {
    name: 'PlantVillage Database',
    animateDelay: 'delay-3',
  },
  {
    name: 'FAO Treatment Protocols',
    animateDelay: 'delay-4',
  },
  {
    name: 'IITA Variety Catalog',
    animateDelay: 'delay-5',
  },
  {
    name: 'Senegal Extension Service Records',
    animateDelay: 'delay-6',
  },
]

export default function GroundedFrame() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-bg px-16" style={{ position: 'relative', overflow: 'hidden' }}>

      {/* Background photo — mother harvesting, emotional warmth */}
      <img
        src="/photos/persona_mother.jpg"
        alt=""
        aria-hidden="true"
        className="photo-bg"
        style={{ objectPosition: 'center 35%' }}
      />
      {/* Dark overlay — sources card and text need high readability */}
      <div
        aria-hidden="true"
        style={{ position: 'absolute', inset: 0, background: 'rgba(15, 26, 20, 0.80)', pointerEvents: 'none' }}
      />
      <div className="w-full max-w-[640px]" style={{ position: 'relative' }}>

        {/* Title */}
        <h1
          className="font-heading font-extrabold text-cream tracking-[0.04em] animate-in delay-0"
          style={{ fontSize: '84px' }}
        >
          GROUNDED AI
        </h1>

        {/* Gold underline accent */}
        <div
          className="mt-3 animate-fade delay-0"
          style={{ height: '4px', width: '200px', background: 'rgba(212,160,23,0.8)', borderRadius: '2px' }}
        />

        {/* Subtitle */}
        <p
          className="mt-6 font-body text-cream animate-in delay-1"
          style={{ fontSize: '24px' }}
        >
          Every answer traces to a verified source:
        </p>

        {/* Sources card */}
        <div
          className="mt-6 rounded-2xl p-7 animate-in delay-2"
          style={{ background: '#1A3228', border: '1px solid rgba(45,106,79,0.35)' }}
        >
          <div className="flex flex-col gap-5">
            {SOURCES.map((source) => (
              <div
                key={source.name}
                className={`flex items-center gap-3 animate-in ${source.animateDelay}`}
                style={{ borderLeft: '3px solid rgba(82,183,136,0.5)', paddingLeft: '16px' }}
              >
                <FileText className="w-5 h-5 text-green-light shrink-0" />
                <p
                  className="font-heading font-semibold text-cream leading-snug"
                  style={{ fontSize: '24px' }}
                >
                  {source.name}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* RAG retrieval evidence */}
        <div
          className="animate-in delay-7 mt-5"
          style={{
            borderLeft: '3px solid rgba(82,183,136,0.6)',
            background: '#162920',
            borderRadius: '6px',
            padding: '12px 16px',
          }}
        >
          <p
            className="text-cream-muted"
            style={{ fontFamily: 'monospace', fontSize: '16px', lineHeight: 1.6 }}
          >
            <span style={{ color: 'rgba(82,183,136,0.8)' }}>query:</span> cassava mosaic disease treatment
          </p>
          <p
            className="text-cream-muted"
            style={{ fontFamily: 'monospace', fontSize: '16px', lineHeight: 1.6 }}
          >
            <span style={{ color: 'rgba(82,183,136,0.8)' }}>matches:</span> 3 chunks retrieved &nbsp;&middot;&nbsp; relevance <span style={{ color: '#F5F1EB' }}>0.94</span> / <span style={{ color: '#F5F1EB' }}>0.89</span> / <span style={{ color: '#F5F1EB' }}>0.82</span>
          </p>
        </div>

        {/* Closing manifesto */}
        <div className="mt-6 flex flex-col gap-5">
          <p
            className="font-heading font-bold text-cream animate-in delay-8"
            style={{ fontSize: '44px' }}
          >
            No hallucination.
          </p>
          <p
            className="font-heading font-bold text-cream animate-in delay-9"
            style={{ fontSize: '44px' }}
          >
            No guessing.
          </p>
          <p
            className="mt-6 font-heading font-extrabold text-gold animate-in delay-10"
            style={{ fontSize: '56px' }}
          >
            Verified, curated knowledge.
          </p>
        </div>

      </div>
    </div>
  )
}
