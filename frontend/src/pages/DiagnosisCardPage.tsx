import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, Share2, Check, X } from 'lucide-react'

function ConfidenceArc({ value }: { value: number }) {
  const radius = 45
  const circumference = 2 * Math.PI * radius
  const arcLength = circumference * 0.75 // 270 degree arc
  const offset = arcLength - (arcLength * value) / 100

  return (
    <div className="relative w-24 h-24 flex items-center justify-center">
      <svg className="w-24 h-24 -rotate-[135deg]" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="currentColor" strokeWidth="8" className="text-surface-dark" strokeDasharray={`${arcLength} ${circumference}`} strokeLinecap="round" />
        <circle cx="50" cy="50" r={radius} fill="none" stroke="currentColor" strokeWidth="8" className="text-primary-light animate-confidenceArc" strokeDasharray={`${arcLength} ${circumference}`} strokeLinecap="round"
          style={{ '--arc-length': String(arcLength), '--arc-target': String(offset), strokeDashoffset: offset } as React.CSSProperties}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-heading font-extrabold text-2xl text-text">{value}%</span>
        <span className="text-[10px] text-text-muted -mt-0.5">confidence</span>
      </div>
    </div>
  )
}

export default function DiagnosisCardPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const imageUrl = (location.state as { image?: string })?.image

  return (
    <div className="flex flex-col h-[calc(100dvh-4rem-env(safe-area-inset-bottom,0px))] bg-surface">
      {/* Header */}
      <header className="bg-primary px-4 py-3 flex items-center justify-between">
        <button onClick={() => navigate('/field')} className="text-white flex items-center gap-1.5 text-sm p-2.5 -ml-2.5" aria-label="Back to chat">
          <ArrowLeft size={18} />
          Back to Chat
        </button>
        <h1 className="text-white font-heading font-bold text-base">Diagnosis Result</h1>
        <button className="text-white p-2.5" aria-label="Share diagnosis">
          <Share2 size={18} />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto overscroll-none">
        {/* Photo hero */}
        <div className="h-56 relative overflow-hidden">
          {imageUrl ? (
            <img src={imageUrl} alt="Analyzed plant" className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center"
              style={{ background: 'linear-gradient(160deg, #2D6A4F 0%, #40916C 45%, #52B788 100%)' }}>
              {/* SVG cassava leaf illustration */}
              <svg viewBox="0 0 120 120" className="w-28 h-28 drop-shadow-lg" aria-hidden="true">
                {/* Main leaf body */}
                <ellipse cx="60" cy="62" rx="22" ry="44" fill="#74C69D" transform="rotate(-10 60 62)" />
                {/* Secondary leaflets */}
                <ellipse cx="38" cy="58" rx="14" ry="30" fill="#52B788" transform="rotate(-35 38 58)" />
                <ellipse cx="82" cy="55" rx="14" ry="30" fill="#52B788" transform="rotate(25 82 55)" />
                <ellipse cx="26" cy="72" rx="10" ry="22" fill="#40916C" transform="rotate(-55 26 72)" />
                <ellipse cx="93" cy="68" rx="10" ry="22" fill="#40916C" transform="rotate(45 93 68)" />
                {/* Stem */}
                <path d="M60 106 Q58 90 56 75" stroke="#2D6A4F" strokeWidth="3" fill="none" strokeLinecap="round" />
                {/* Leaf veins */}
                <path d="M60 20 Q61 50 62 106" stroke="#40916C" strokeWidth="1.5" fill="none" strokeLinecap="round" opacity="0.6" />
                <path d="M60 45 Q48 52 36 56" stroke="#40916C" strokeWidth="1" fill="none" opacity="0.5" />
                <path d="M60 45 Q72 52 84 54" stroke="#40916C" strokeWidth="1" fill="none" opacity="0.5" />
                <path d="M60 60 Q46 66 32 70" stroke="#40916C" strokeWidth="1" fill="none" opacity="0.5" />
                <path d="M60 60 Q74 66 88 68" stroke="#40916C" strokeWidth="1" fill="none" opacity="0.5" />
                {/* Disease spots (yellow mosaic) */}
                <ellipse cx="50" cy="42" rx="5" ry="3.5" fill="#D4A017" opacity="0.75" transform="rotate(-15 50 42)" />
                <ellipse cx="70" cy="50" rx="4" ry="2.5" fill="#E3B634" opacity="0.7" transform="rotate(10 70 50)" />
                <ellipse cx="44" cy="62" rx="3.5" ry="2.5" fill="#D4A017" opacity="0.65" transform="rotate(-5 44 62)" />
                <ellipse cx="76" cy="58" rx="3" ry="2" fill="#E3B634" opacity="0.65" transform="rotate(20 76 58)" />
                <ellipse cx="58" cy="70" rx="4" ry="2.5" fill="#D4A017" opacity="0.6" />
              </svg>
              <p className="text-white/70 text-xs mt-3 font-medium tracking-wide">Sample diagnosis — no photo provided</p>
            </div>
          )}
          {/* Gradient scrim at bottom for legibility */}
          <div className="absolute inset-x-0 bottom-0 h-16 pointer-events-none"
            style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.45) 0%, transparent 100%)' }} />
          <span className="absolute bottom-2 right-2 bg-primary/80 text-white text-xs px-2 py-1 rounded-md backdrop-blur-sm">
            Photo analyzed
          </span>
        </div>

        <div className="px-4 py-4 max-w-lg mx-auto space-y-4">
          {/* Disease title + confidence arc */}
          <div className="flex items-start gap-4 animate-slideUp bg-card rounded-2xl p-4 shadow-sm border border-surface-dark"
            style={{ background: 'linear-gradient(135deg, rgba(27,67,50,0.07) 0%, rgba(212,160,23,0.06) 100%)' }}>
            <div className="flex-1">
              <h2 className="font-heading text-xl font-extrabold text-text leading-tight">
                Cassava Mosaic Disease
                <span className="block text-base font-semibold text-text-muted">(CMD)</span>
              </h2>
              <div className="flex gap-2 flex-wrap mt-3">
                <span className="text-sm font-bold bg-tertiary text-white px-3.5 py-1.5 rounded-full shadow-md">
                  High Severity
                </span>
                <span className="text-sm font-bold bg-secondary text-white px-3.5 py-1.5 rounded-full shadow-sm">
                  Viral
                </span>
              </div>
              <p className="text-xs text-text-muted mt-2 italic">
                Begomovirus (family Geminiviridae)
              </p>
            </div>
            <ConfidenceArc value={92} />
          </div>

          {/* Symptoms */}
          <div className="animate-slideUp [animation-delay:0.1s] bg-card rounded-xl p-4 border border-surface-dark shadow-sm"
            style={{ background: 'linear-gradient(135deg, rgba(27,67,50,0.04) 0%, rgba(255,255,255,1) 60%)' }}>
            <h3 className="font-heading font-bold text-sm mb-3 text-text">Symptoms Matched</h3>
            <ul className="space-y-2">
              {[
                { text: 'Yellow mosaic patterns on leaves', matched: true },
                { text: 'Leaf curling and distortion', matched: true },
                { text: 'Stunted plant growth', matched: true },
                { text: 'Leaf drop (not observed)', matched: false },
              ].map((s, i) => (
                <li key={s.text} className={`flex items-center gap-2.5 text-sm animate-slideUp ${s.matched ? 'text-text' : 'text-text-muted/60'}`} style={{ animationDelay: `${0.2 + i * 0.1}s` }}>
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${s.matched ? 'bg-primary/10' : 'bg-surface-dark'}`}>
                    {s.matched ? (
                      <Check size={12} className="text-primary" />
                    ) : (
                      <X size={12} className="text-text-muted/40" />
                    )}
                  </span>
                  {s.text}
                </li>
              ))}
            </ul>
          </div>

          {/* Treatment */}
          <div className="bg-card rounded-xl border border-secondary/30 shadow-sm overflow-hidden animate-slideUp [animation-delay:0.3s]">
            <div className="bg-secondary/10 border-b border-secondary/20 px-4 py-2.5 flex items-center justify-between">
              <h3 className="font-heading font-bold text-sm text-text">Recommended Treatment</h3>
              <div className="flex gap-1.5">
                <span className="text-xs bg-secondary/20 text-secondary px-2 py-0.5 rounded-full font-semibold">Easy</span>
                <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-semibold">Organic</span>
              </div>
            </div>
            <ol className="px-4 py-3 space-y-3">
              {[
                { step: 'Remove infected plants', detail: 'Uproot and burn all visibly infected plants immediately to stop spread.' },
                { step: 'Control whitefly vectors', detail: 'Mix neem leaves with water and a drop of soap. Spray on remaining plants every 7 days.' },
                { step: 'Replant with resistant varieties', detail: 'Source TME 419 or IITA-approved stem cuttings from a certified nursery.' },
              ].map((item, i) => (
                <li key={item.step} className="flex gap-3">
                  <span className="w-5 h-5 rounded-full bg-secondary text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                    {i + 1}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-text">{item.step}</p>
                    <p className="text-xs text-text-muted mt-0.5 leading-relaxed">{item.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
            <div className="px-4 pb-3">
              <div className="bg-surface rounded-lg px-3 py-2 flex items-start gap-2">
                <span className="text-xs font-semibold text-text-muted shrink-0 pt-0.5">Materials:</span>
                <span className="text-xs text-text">Neem leaves, water, soap, resistant stem cuttings</span>
              </div>
            </div>
          </div>

          {/* Prevention */}
          <div className="bg-card rounded-xl p-4 border border-surface-dark shadow-sm animate-slideUp [animation-delay:0.4s]">
            <h3 className="font-heading font-bold text-sm mb-3 text-text">Prevention</h3>
            <ul className="space-y-3">
              {[
                'Use certified clean planting material',
                'Control whitefly populations early in the season',
                'Plant resistant varieties whenever available',
                'Maintain field hygiene — remove crop debris',
              ].map((p) => (
                <li key={p} className="flex items-center gap-3 text-sm text-text">
                  <span className="w-3 h-3 bg-primary rounded-full shrink-0" />
                  {p}
                </li>
              ))}
            </ul>
          </div>

          {/* Bottom spacer so last card clears the action bar */}
          <div className="h-4" aria-hidden="true" />
        </div>
      </div>

      {/* Bottom actions */}
      <div className="bg-card border-t border-surface-dark px-4 py-3">
        <div className="max-w-lg mx-auto space-y-2">
          <button
            onClick={() => navigate('/field')}
            className="w-full bg-primary text-white font-semibold text-sm py-2.5 rounded-lg hover:bg-primary-light transition-all active:scale-95"
          >
            Ask Follow-up Question &rarr;
          </button>
          <div className="flex gap-1.5 justify-center flex-wrap">
            {['Treatment details', 'Resistant varieties', 'Whitefly control'].map((s) => (
              <button
                key={s}
                onClick={() => navigate('/field', { state: { prefill: s } })}
                className="text-xs bg-surface text-text px-3 py-2.5 rounded-full border border-surface-dark hover:bg-surface-dark min-h-[44px]"
              >
                {s}
              </button>
            ))}
          </div>
          <p className="text-center">
            <button className="text-xs text-text-muted hover:underline">Save as PDF</button>
          </p>
        </div>
      </div>
    </div>
  )
}
