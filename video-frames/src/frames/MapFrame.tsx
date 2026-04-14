import { AlertTriangle } from 'lucide-react'

/**
 * Scene 5 (0:28-0:35): Senegal map - Casamance isolation
 * Narration: "Casamance is 450 km from Dakar. Once she's there - no reliable
 * internet. No cloud AI. No expert database to fall back on."
 *
 * SVG coordinate space: 0 0 400 520
 * Geography:
 *   Top border (Senegal River / Mauritania): y ~ 22, x 68-368
 *   Cap-Vert peninsula (Dakar): western jut, tip at x~22 y~200
 *   Gambia notch: y 310-348, x 48-300 (the critical separator)
 *   Casamance (below Gambia): bottom of country, y 348-476
 */
export default function MapFrame() {
  const DAKAR_X = 32
  const DAKAR_Y = 200

  const CAS_X = 170
  const CAS_Y = 422

  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-bg gap-6" style={{ position: 'relative', overflow: 'hidden' }}>

      {/* Background photo — Casamance landscape with baobab */}
      <img
        src="/photos/landscape_casamance.jpg"
        alt=""
        aria-hidden="true"
        className="photo-bg"
        style={{ objectPosition: 'center 50%' }}
      />
      {/* Dark overlay — map SVG needs to stay legible */}
      <div
        aria-hidden="true"
        style={{ position: 'absolute', inset: 0, background: 'rgba(15, 26, 20, 0.82)', pointerEvents: 'none' }}
      />

      <div className="animate-fade delay-1" style={{ position: 'relative' }}>
        <svg
          viewBox="0 0 400 520"
          width="480"
          height="624"
          xmlns="http://www.w3.org/2000/svg"
          aria-label="Map of Senegal showing Casamance isolated by The Gambia"
          style={{ overflow: 'visible' }}
        >
          <defs>
            {/* Subtle Atlantic blue tint on the left */}
            <linearGradient id="ocean" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#0D2535" stopOpacity="0.55" />
              <stop offset="28%" stopColor="#0F1A14" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Ocean tint wash */}
          <rect x="0" y="0" width="400" height="520" fill="url(#ocean)" />

          {/* ══════════════════════════════════════════════════════════════
            NORTHERN SENEGAL BODY (everything above the Gambia)

            Polygon runs clockwise from NW corner:
              Top edge: left to right along Senegal River / Mauritania border
              Eastern edge: angled SW along Mali/Guinea border
              Southern edge: runs west along Gambia's north bank (y~310)
              Western edge (Atlantic coast): back north, including the
                Cap-Vert peninsula jut that is handled separately below

            Bottom of this shape closes at x=48 y=312 (Atlantic mouth of Gambia)
          ══════════════════════════════════════════════════════════════ */}
          <polygon
            points="
              68,22   148,18  212,16  272,18  332,22
              368,36  374,58  370,90  362,122 356,152
              360,178 354,202 340,220 318,230 294,234
              270,240 246,252 224,264 202,274 180,280
              160,282 138,284 116,292 94,302  72,308
              52,312  48,312
            "
            fill="#162920"
            stroke="#2D6A4F"
            strokeWidth="2"
            strokeLinejoin="miter"
          />

          {/* ── Cap-Vert peninsula ──
            A sharp westward jut on the Atlantic coast, roughly at y=185-215.
            The real peninsula is narrow at the neck (~10km) then broadens.
          ── */}
          <polygon
            points="72,184  54,188  34,192  22,198  24,208  34,216  50,218  66,214  74,204  78,194"
            fill="#162920"
            stroke="#2D6A4F"
            strokeWidth="2"
            strokeLinejoin="miter"
          />

          {/* ══════════════════════════════════════════════════════════════
            GAMBIA NOTCH

            A bg-colored band that visually separates Casamance from the north.
            Tapers slightly: narrower at the Atlantic mouth, wider inland.
            Top (north bank): y=310 rising to y=308 at east end
            Bottom (south bank): y=348 flat
          ══════════════════════════════════════════════════════════════ */}
          <polygon
            points="48,312  296,308  300,320  300,348  48,348"
            fill="#0F1A14"
          />
          {/* North bank dashed border */}
          <polyline
            points="48,312 296,308 300,320"
            fill="none"
            stroke="#2D6A4F"
            strokeWidth="1.5"
            strokeDasharray="5 4"
          />
          {/* South bank dashed border */}
          <polyline
            points="48,348 300,348 300,320"
            fill="none"
            stroke="#2D6A4F"
            strokeWidth="1.5"
            strokeDasharray="5 4"
          />
          {/* Gambia text label */}
          <text
            x="168"
            y="334"
            textAnchor="middle"
            fontFamily="Inter, system-ui, sans-serif"
            fontSize="13"
            fontWeight="600"
            fill="#2D6A4F"
            letterSpacing="2.5"
          >
            THE GAMBIA
          </text>

          {/* ══════════════════════════════════════════════════════════════
            CASAMANCE - the visual hero

            Below Gambia south bank. Angular shape, amber fill + layered glow.
          ══════════════════════════════════════════════════════════════ */}
          <polygon
            points="
              48,348
              300,348
              304,365
              306,388
              302,410
              290,432
              270,452
              244,466
              214,474
              182,476
              154,472
              126,460
              102,442
              80,418
              62,392
              50,368
              48,354
            "
            fill="#D4A017"
            fillOpacity="0.25"
            stroke="#D4A017"
            strokeWidth="2.5"
            strokeLinejoin="miter"
            style={{
              filter:
                'drop-shadow(0 0 18px #D4A017) drop-shadow(0 0 40px rgba(212,160,23,0.5))',
            }}
            className="animate-pop delay-3"
          />

          {/* ── Dakar: two concentric pulse rings + solid dot ── */}
          <circle
            cx={DAKAR_X}
            cy={DAKAR_Y}
            r="18"
            fill="none"
            stroke="#F5F1EB"
            strokeWidth="1"
            strokeOpacity="0.18"
            className="animate-fade delay-2"
          />
          <circle
            cx={DAKAR_X}
            cy={DAKAR_Y}
            r="12"
            fill="none"
            stroke="#F5F1EB"
            strokeWidth="1"
            strokeOpacity="0.40"
            className="animate-fade delay-2"
          />
          <circle
            cx={DAKAR_X}
            cy={DAKAR_Y}
            r="6"
            fill="#F5F1EB"
            stroke="#0F1A14"
            strokeWidth="2"
            className="animate-pop delay-2"
          />

          {/* ── Dakar label ── */}
          <text
            x={DAKAR_X + 14}
            y={DAKAR_Y - 6}
            fontFamily="Inter, system-ui, sans-serif"
            fontSize="16"
            fontWeight="700"
            fill="#F5F1EB"
            className="animate-fade delay-2"
          >
            Dakar
          </text>

          {/* ── Dashed gold arc: Dakar to Casamance ──
            Bezier curves right of centre, hugging the coast line.
          ── */}
          <path
            d={`M ${DAKAR_X},${DAKAR_Y} Q 90,308 ${CAS_X},${CAS_Y - 22}`}
            fill="none"
            stroke="#D4A017"
            strokeWidth="2.5"
            strokeDasharray="22 22"
            strokeLinecap="round"
            className="delay-3"
            style={{ animation: 'fadeInOnly 0.6s ease-out 0.9s both, routeTravel 2s linear 1.5s infinite' }}
          />

          {/* ── 450 km pill label ── */}
          <g className="animate-fade delay-4">
            <rect
              x="96"
              y="252"
              width="80"
              height="28"
              rx="7"
              fill="#0F1A14"
              fillOpacity="0.85"
              stroke="#D4A017"
              strokeWidth="1"
              strokeOpacity="0.45"
            />
            <text
              x="136"
              y="271"
              textAnchor="middle"
              fontFamily="Inter, system-ui, sans-serif"
              fontSize="16"
              fontWeight="600"
              fill="#D4A017"
            >
              450 km
            </text>
          </g>

          {/* ── CASAMANCE label ── */}
          <text
            x={CAS_X}
            y={CAS_Y}
            textAnchor="middle"
            fontFamily="'Plus Jakarta Sans', system-ui, sans-serif"
            fontSize="22"
            fontWeight="800"
            fill="#D4A017"
            letterSpacing="4"
            style={{
              filter: 'drop-shadow(0 0 10px rgba(212,160,23,0.95))',
            }}
            className="animate-fade delay-4"
          >
            CASAMANCE
          </text>

        </svg>
      </div>

      {/* ── Warning labels ─────────────────────────────────────────────── */}
      <div className="flex flex-col items-center gap-4" style={{ position: 'relative' }}>

        <div
          className="flex items-center gap-3 px-6 py-3 rounded-xl animate-slide-up delay-5"
          style={{
            background: 'rgba(196,69,54,0.08)',
            border: '1px solid rgba(196,69,54,0.22)',
          }}
        >
          <AlertTriangle className="text-red shrink-0" size={28} strokeWidth={2.5} />
          <span
            className="font-body text-cream tracking-wide"
            style={{ fontSize: '1.5rem', fontWeight: 700 }}
          >
            No reliable internet
          </span>
        </div>

        <div
          className="flex items-center gap-3 px-6 py-3 rounded-xl animate-slide-up delay-6"
          style={{
            background: 'rgba(212,160,23,0.07)',
            border: '1px solid rgba(212,160,23,0.2)',
          }}
        >
          <AlertTriangle className="text-gold shrink-0" size={28} strokeWidth={2.5} />
          <span
            className="font-body text-cream tracking-wide"
            style={{ fontSize: '1.5rem', fontWeight: 700 }}
          >
            No cloud AI. No expert database.
          </span>
        </div>

      </div>

    </div>
  )
}
