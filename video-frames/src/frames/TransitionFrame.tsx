/**
 * SCENE 10 (1:30-1:40): The emotional pivot — departure into the field
 * Narration: "Amina flies to Ziguinchor. No WiFi. No data. No cloud.
 *             [pause] Just her and her Knowledge Pack."
 *
 * Design intent: silence before the storm, then the storm, then calm.
 * Three title-card lines slam in one at a time. The map ghost recedes.
 * The closing whisper is the emotional release.
 *
 * Layout logic:
 *   pt-[15%] gives ~162px of dark sky above — the isolation is the message.
 *   Content sits at ~55-60% vertical, not dead-center, for cinematic weight.
 *   Map shrinks to 320x200 and dims to 0.28 opacity — atmosphere, not info.
 *   Three NO lines at 108px with mb-3 gaps = wall-of-words, not a list.
 *   Whisper in warm diluted gold — not cool grey, not silent white.
 */
export default function TransitionFrame() {
  return (
    <div className="w-full h-full flex flex-col items-center bg-bg px-20 pt-[15%]">

      {/* ── Ghost map — Dakar to Casamance journey ─────────────────────
          Opacity 0.28 so it is felt, not read. The map is atmosphere,
          not information. It recedes behind the words.
          Scaled from 400x260 viewBox to 320x200 render size.
      ─────────────────────────────────────────────────────────────────── */}
      <div className="animate-fade delay-0 mb-12" style={{ opacity: 0.28 }}>
        <svg
          viewBox="0 0 400 260"
          width="320"
          height="200"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          {/* ── Senegal outline — simplified westward silhouette ──
              Coordinates hand-tuned to read as "West Africa coast"
              at a glance. Not geographically precise; emotionally true.

              Key points in viewBox (0 0 400 260):
                Top-left coast:         x ~30,  y ~20
                Northern border (flat): x ~370, y ~20
                Eastern border:         x ~370, y ~180
                Southern tip:           x ~110, y ~240
                Dakar peninsula:        x ~30,  y ~120
          ── */}
          <path
            d="
              M 42,20
              L 370,20
              L 370,80
              L 355,110
              L 340,140
              L 335,165
              L 310,175
              L 280,178
              L 260,182
              L 240,188
              L 230,200
              L 220,215
              L 200,230
              L 175,240
              L 150,243
              L 125,238
              L 110,225
              L 100,208
              L 95,190
              L 90,175
              L 75,162
              L 60,158
              L 42,148
              L 30,138
              L 30,110
              L 22,95
              L 20,75
              L 28,48
              Z
            "
            fill="#162920"
            fillOpacity="0.30"
            stroke="#2D6A4F"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />

          {/* ── Gambia notch — thin horizontal gap in southern third ── */}
          <rect
            x="90"
            y="175"
            width="200"
            height="14"
            fill="#0F1A14"
            fillOpacity="0.70"
          />

          {/* ── Casamance region — south of Gambia notch ── */}
          <path
            d="
              M 90,189
              L 290,189
              L 295,200
              L 290,215
              L 270,230
              L 240,240
              L 210,245
              L 175,243
              L 145,237
              L 118,226
              L 100,210
              L 90,198
              Z
            "
            fill="#D4A017"
            fillOpacity="0.12"
            stroke="#D4A017"
            strokeWidth="1"
            strokeLinejoin="round"
          />

          {/* ── Dakar peninsula nub ── */}
          <polygon
            points="30,110 18,118 22,130 36,128 42,118"
            fill="#162920"
            fillOpacity="0.50"
            stroke="#2D6A4F"
            strokeWidth="1"
          />

          {/* ── Dashed arc: Dakar -> Casamance ──
              Dakar approx (26, 120), Casamance centre approx (185, 218).
              Quadratic curve bows gently east for visual flow.
          ── */}
          <path
            d="M 26,120 Q 80,185 185,218"
            fill="none"
            stroke="#C8C2B8"
            strokeWidth="1.5"
            strokeDasharray="6 5"
            strokeLinecap="round"
            strokeOpacity="0.30"
          />

          {/* ── Dakar dot — dimmed, supporting role ── */}
          <circle
            cx="26"
            cy="120"
            r="5"
            fill="#F5F1EB"
            fillOpacity="0.50"
          />

          {/* ── Casamance dot — gold but subordinate to text ── */}
          <circle
            cx="185"
            cy="218"
            r="5"
            fill="#D4A017"
            fillOpacity="0.20"
          />
        </svg>
      </div>

      {/* ── Three title-card lines — slam in one at a time ──────────────
          delay-3, delay-5, delay-7 = 0.9s, 1.5s, 2.1s
          Each line feels like a fist hitting the screen.
          108px + letterSpacing 0.10em + mb-3 = wall of words, not a list.
          Double-space between NO and the word creates visual breath.
      ─────────────────────────────────────────────────────────────────── */}
      <div className="flex flex-col items-center">

        <h2
          className="animate-in delay-3 font-heading font-extrabold text-cream leading-none"
          style={{ fontSize: '108px', fontWeight: 800, letterSpacing: '0.10em' }}
        >
          NO&nbsp;&nbsp;WIFI.
        </h2>

        <div className="mb-3" />

        <h2
          className="animate-in delay-5 font-heading font-extrabold text-cream leading-none"
          style={{ fontSize: '108px', fontWeight: 800, letterSpacing: '0.10em' }}
        >
          NO&nbsp;&nbsp;DATA.
        </h2>

        <div className="mb-3" />

        <h2
          className="animate-in delay-7 font-heading font-extrabold text-cream leading-none"
          style={{ fontSize: '108px', fontWeight: 800, letterSpacing: '0.10em' }}
        >
          NO&nbsp;&nbsp;CLOUD.
        </h2>

      </div>

      {/* ── Divider — visible green rule, not a ghost ── */}
      <div
        className="animate-fade delay-8 mt-12 mb-6"
        style={{
          width: '320px',
          height: '1px',
          background: 'rgba(200, 194, 184, 0.20)',
        }}
      />

      {/* ── Closing whisper — emotional release after the shout ──────────
          Warm diluted gold — not cool grey, not silence white.
          It glows against the dark; it is the answer, not an afterthought.
      ─────────────────────────────────────────────────────────────────── */}
      <p
        className="animate-fade delay-9 font-body italic text-2xl"
        style={{ color: 'rgba(212, 160, 23, 0.50)' }}
      >
        Just her and her Knowledge Pack.
      </p>

    </div>
  )
}
