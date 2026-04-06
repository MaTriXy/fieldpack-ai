import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Share2, Check, X, Camera } from 'lucide-react'

export default function DiagnosisCardPage() {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col h-dvh bg-surface">
      {/* Header */}
      <header className="bg-primary px-4 py-3 flex items-center justify-between">
        <button onClick={() => navigate('/field')} className="text-white flex items-center gap-1.5 text-sm" aria-label="Back to chat">
          <ArrowLeft size={18} />
          Back to Chat
        </button>
        <h1 className="text-white font-heading font-bold text-base">Diagnosis Result</h1>
        <button className="text-white p-1" aria-label="Share diagnosis">
          <Share2 size={18} />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto">
        {/* Photo hero */}
        <div className="bg-surface-dark h-48 flex items-center justify-center relative">
          <Camera size={40} className="text-text-muted/30" />
          <span className="absolute bottom-2 right-2 bg-primary/80 text-white text-xs px-2 py-1 rounded-md">
            Photo analyzed
          </span>
        </div>

        <div className="px-4 py-4 max-w-lg mx-auto space-y-4">
          {/* Disease title */}
          <div>
            <h2 className="font-heading text-xl font-extrabold text-text">
              Cassava Mosaic Disease (CMD)
            </h2>
            <div className="flex gap-1.5 flex-wrap mt-2">
              <span className="text-xs font-semibold bg-primary/10 text-primary px-2.5 py-1 rounded-full">
                92% Confidence
              </span>
              <span className="text-xs font-semibold bg-tertiary/10 text-tertiary px-2.5 py-1 rounded-full">
                High Severity
              </span>
              <span className="text-xs font-medium bg-text-muted/10 text-text-muted px-2.5 py-1 rounded-full">
                Viral
              </span>
            </div>
            <p className="text-xs text-text-muted mt-2 italic">
              Begomovirus (family Geminiviridae)
            </p>
          </div>

          <hr className="border-surface-dark" />

          {/* Symptoms */}
          <div>
            <h3 className="font-heading font-bold text-sm mb-2">Symptoms Matched</h3>
            <ul className="space-y-1.5">
              {[
                { text: 'Yellow mosaic patterns on leaves', matched: true },
                { text: 'Leaf curling and distortion', matched: true },
                { text: 'Stunted plant growth', matched: true },
                { text: 'Leaf drop (not observed)', matched: false },
              ].map((s) => (
                <li key={s.text} className={`flex items-center gap-2 text-sm ${s.matched ? 'text-text' : 'text-text-muted'}`}>
                  {s.matched ? (
                    <Check size={16} className="text-primary shrink-0" />
                  ) : (
                    <X size={16} className="text-text-muted/40 shrink-0" />
                  )}
                  {s.text}
                </li>
              ))}
            </ul>
          </div>

          <hr className="border-surface-dark" />

          {/* Treatment */}
          <div className="border-l-4 border-secondary pl-4">
            <h3 className="font-heading font-bold text-sm mb-2">Recommended Treatment</h3>
            <p className="text-sm text-text leading-relaxed">
              Remove and burn infected plants. Plant resistant varieties (TME 419, IITA varieties).
              Control whitefly vectors using neem oil spray.
            </p>
            <div className="mt-3 space-y-1.5">
              <div className="flex items-center gap-2 text-xs">
                <span className="font-semibold text-text-muted">Materials:</span>
                <span className="text-text">Neem leaves, water, soap, resistant stem cuttings</span>
              </div>
              <div className="flex gap-1.5">
                <span className="text-xs bg-secondary/10 text-secondary px-2 py-0.5 rounded-full font-medium">
                  Easy
                </span>
                <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-medium">
                  Organic
                </span>
              </div>
            </div>
          </div>

          <hr className="border-surface-dark" />

          {/* Prevention */}
          <div>
            <h3 className="font-heading font-bold text-sm mb-2">Prevention</h3>
            <ul className="space-y-1 text-sm text-text-muted">
              {[
                'Use certified clean planting material',
                'Control whitefly populations',
                'Plant resistant varieties',
                'Maintain field hygiene',
              ].map((p) => (
                <li key={p} className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-primary rounded-full shrink-0" />
                  {p}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Bottom actions */}
      <div className="bg-card border-t border-surface-dark px-4 py-3">
        <div className="max-w-lg mx-auto space-y-2">
          <button
            onClick={() => navigate('/field')}
            className="w-full bg-primary text-white font-semibold text-sm py-2.5 rounded-lg hover:bg-primary-light transition-colors"
          >
            Ask Follow-up Question &rarr;
          </button>
          <div className="flex gap-1.5 justify-center flex-wrap">
            {['Treatment details', 'Resistant varieties', 'Whitefly control'].map((s) => (
              <button
                key={s}
                onClick={() => navigate('/field', { state: { prefill: s } })}
                className="text-xs bg-surface text-text px-3 py-1.5 rounded-full border border-surface-dark hover:bg-surface-dark"
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
