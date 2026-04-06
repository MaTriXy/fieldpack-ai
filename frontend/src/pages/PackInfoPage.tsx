import { useNavigate } from 'react-router-dom'
import { Leaf, Bug, Pill, Shield, FileText, Search, Database, MapPin } from 'lucide-react'
import TopBar from '../components/layout/TopBar'

const STATS = [
  { label: '5 Crops', icon: Leaf, color: 'text-primary' },
  { label: '15 Diseases', icon: Bug, color: 'text-tertiary' },
  { label: '31 Treatments', icon: Pill, color: 'text-primary' },
  { label: '12 Pests', icon: Shield, color: 'text-secondary' },
  { label: '190 Chunks', icon: FileText, color: 'text-text-muted' },
  { label: '7 FTS Tables', icon: Search, color: 'text-text-muted' },
]

const COLLECTIONS = [
  { name: 'disease_knowledge', chunks: 45 },
  { name: 'treatment_guides', chunks: 38 },
  { name: 'farming_practices', chunks: 62 },
  { name: 'regional_context', chunks: 45 },
]

const SOURCES = [
  'PlantVillage Database',
  'IITA Research Papers',
  'FAO Crop Manuals',
  'AfricaRice Center',
  'ISRA Senegal',
  'Local Extension Services',
]

const MODELS = [
  { name: 'Research', model: 'Gemma 4 26B MoE', provider: 'Google AI Studio' },
  { name: 'Compiler', model: 'Gemma 4 31B', provider: 'Google AI Studio' },
  { name: 'Embeddings', model: 'all-MiniLM-L6-v2', provider: 'Local' },
  { name: 'Edge Model', model: 'Gemma 4 E2B Q4', provider: 'Ollama' },
]

export default function PackInfoPage() {
  const navigate = useNavigate()

  return (
    <div className="flex flex-col">
      <TopBar title="Pack Details" back backTo="/" />

      <div className="flex-1 overflow-y-auto px-4 py-4 bg-surface">
        <div className="max-w-lg mx-auto space-y-4">
          {/* Pack identity */}
          <div className="bg-card rounded-xl p-4 shadow-sm border border-surface-dark text-center">
            <div className="w-14 h-14 bg-primary/10 rounded-xl flex items-center justify-center mx-auto mb-3">
              <Database className="text-primary" size={28} />
            </div>
            <h2 className="font-heading text-xl font-extrabold">Casamance Agriculture</h2>
            <p className="text-xs text-text-muted mt-1">v1.0 &mdash; Built {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
            <div className="flex items-center justify-center gap-1.5 mt-2">
              <MapPin size={12} className="text-text-muted" />
              <span className="text-xs text-text-muted">Casamance, Senegal</span>
            </div>
            <span className="inline-block mt-2 text-xs font-semibold bg-primary/10 text-primary px-3 py-1 rounded-full">
              Loaded \u2713
            </span>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-3 gap-2">
            {STATS.map((s) => (
              <div key={s.label} className="bg-card rounded-lg p-3 text-center shadow-sm border border-surface-dark">
                <s.icon size={18} className={`mx-auto mb-1 ${s.color}`} />
                <p className="text-xs font-semibold text-text">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Collections */}
          <div className="bg-card rounded-xl p-4 shadow-sm border border-surface-dark">
            <h3 className="font-heading font-bold text-sm mb-3">Vector Collections</h3>
            <div className="space-y-2">
              {COLLECTIONS.map((c) => (
                <div key={c.name} className="flex items-center justify-between py-1.5 border-b border-surface-dark last:border-0">
                  <span className="text-xs font-mono text-text">{c.name}</span>
                  <span className="text-xs bg-surface text-text-muted px-2 py-0.5 rounded-full">{c.chunks} chunks</span>
                </div>
              ))}
            </div>
          </div>

          {/* Sources */}
          <div className="bg-card rounded-xl p-4 shadow-sm border border-surface-dark">
            <h3 className="font-heading font-bold text-sm mb-3">Data Sources</h3>
            <ul className="space-y-1.5">
              {SOURCES.map((s) => (
                <li key={s} className="flex items-center gap-2 text-xs text-text-muted">
                  <span className="w-1.5 h-1.5 bg-primary rounded-full shrink-0" />
                  {s}
                </li>
              ))}
            </ul>
          </div>

          {/* Models */}
          <div className="bg-card rounded-xl p-4 shadow-sm border border-surface-dark">
            <h3 className="font-heading font-bold text-sm mb-3">Models Used</h3>
            <div className="space-y-2">
              {MODELS.map((m) => (
                <div key={m.name} className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-text">{m.name}: </span>
                    <span className="text-xs text-text-muted">{m.model}</span>
                  </div>
                  <span className="text-xs bg-surface text-text-muted px-2 py-0.5 rounded-full">{m.provider}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-2">
            <button
              onClick={() => navigate('/packs/explorer')}
              className="w-full border-2 border-primary text-primary font-semibold text-sm py-2.5 rounded-lg hover:bg-primary/5 transition-colors"
            >
              Open in Knowledge Explorer \u2192
            </button>
            <button className="w-full border-2 border-secondary text-secondary font-semibold text-sm py-2.5 rounded-lg hover:bg-secondary/5 transition-colors">
              Rebuild Pack
            </button>
            <button className="w-full text-tertiary text-xs font-medium py-2 hover:underline">
              Unload Pack
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
