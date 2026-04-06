import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Leaf, Bug, Pill, Shield, FileText, Database, MapPin, Loader2, AlertCircle } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import { listPacks, browseKnowledge, type PackSummary } from '../lib/api'

const MODELS = [
  { name: 'Research', model: 'Gemma 4 26B MoE', provider: 'Google AI Studio' },
  { name: 'Compiler', model: 'Gemma 4 31B', provider: 'Google AI Studio' },
  { name: 'Embeddings', model: 'all-MiniLM-L6-v2', provider: 'Local' },
  { name: 'Edge Model', model: 'Gemma 4 E2B Q4', provider: 'Ollama' },
]

interface PackStats {
  crops: number
  diseases: number
  treatments: number
  pests: number
  practices: number
  climate: number
}

export default function PackInfoPage() {
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pack, setPack] = useState<PackSummary | null>(null)
  const [stats, setStats] = useState<PackStats | null>(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      setLoading(true)
      setError(null)
      try {
        const packs = await listPacks()
        const loaded = packs.find((p) => p.loaded) ?? null
        if (cancelled) return
        if (!loaded) {
          setPack(null)
          setLoading(false)
          return
        }
        setPack(loaded)

        const [diseases, treatments, pests, practices, climate] = await Promise.all([
          browseKnowledge('disease', '', 200),
          browseKnowledge('treatment', '', 200),
          browseKnowledge('pest', '', 200),
          browseKnowledge('practice', '', 200),
          browseKnowledge('climate', '', 200),
        ])
        if (cancelled) return
        setStats({
          crops: loaded.crops.length,
          diseases: diseases.count,
          treatments: treatments.count,
          pests: pests.count,
          practices: practices.count,
          climate: climate.count,
        })
      } catch (err) {
        if (!cancelled) setError('Could not reach the backend. Is the server running?')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => { cancelled = true }
  }, [])

  const buildStats = stats
    ? [
        { label: `${stats.crops} Crop${stats.crops !== 1 ? 's' : ''}`, icon: Leaf, color: 'text-primary' },
        { label: `${stats.diseases} Disease${stats.diseases !== 1 ? 's' : ''}`, icon: Bug, color: 'text-tertiary' },
        { label: `${stats.treatments} Treatment${stats.treatments !== 1 ? 's' : ''}`, icon: Pill, color: 'text-primary' },
        { label: `${stats.pests} Pest${stats.pests !== 1 ? 's' : ''}`, icon: Shield, color: 'text-secondary' },
        { label: `${stats.practices} Practice${stats.practices !== 1 ? 's' : ''}`, icon: FileText, color: 'text-text-muted' },
        { label: `${stats.climate} Climate`, icon: MapPin, color: 'text-text-muted' },
      ]
    : []

  return (
    <div className="flex flex-col animate-fadeIn">
      <TopBar title="Pack Details" back backTo="/" />

      <div className="flex-1 overflow-y-auto px-4 py-4 bg-surface">
        <div className="max-w-lg mx-auto space-y-4">

          {/* Loading state */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-text-muted">
              <Loader2 size={32} className="animate-spin text-primary" />
              <p className="text-sm">Loading pack info...</p>
            </div>
          )}

          {/* Error state */}
          {!loading && error && (
            <div className="bg-card rounded-xl p-6 shadow-sm border border-surface-dark text-center space-y-3">
              <AlertCircle size={32} className="mx-auto text-tertiary" />
              <p className="text-sm font-semibold text-text">Connection Error</p>
              <p className="text-xs text-text-muted">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="text-xs text-primary font-medium hover:underline"
              >
                Retry
              </button>
            </div>
          )}

          {/* No pack loaded */}
          {!loading && !error && !pack && (
            <div className="bg-card rounded-xl p-6 shadow-sm border border-surface-dark text-center space-y-3">
              <Database size={32} className="mx-auto text-text-muted" />
              <p className="text-sm font-semibold text-text">No pack loaded</p>
              <p className="text-xs text-text-muted">Go to the home screen to load a Knowledge Pack first.</p>
              <button
                onClick={() => navigate('/')}
                className="text-xs text-primary font-medium hover:underline"
              >
                Go to Home
              </button>
            </div>
          )}

          {/* Main content — only shown when pack is loaded */}
          {!loading && !error && pack && (
            <>
              {/* Pack identity */}
              <div className="bg-card rounded-xl p-4 shadow-sm border border-surface-dark text-center">
                <div className="w-14 h-14 bg-primary/10 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <Database className="text-primary" size={28} />
                </div>
                <h2 className="font-heading text-xl font-extrabold">{pack.name}</h2>
                <p className="text-xs text-text-muted mt-1">Pack ID: {pack.pack_id}</p>
                <div className="flex items-center justify-center gap-1.5 mt-2">
                  <MapPin size={12} className="text-text-muted" />
                  <span className="text-xs text-text-muted">{pack.region}</span>
                </div>
                <span className="inline-block mt-2 text-xs font-semibold bg-primary/10 text-primary px-3 py-1 rounded-full">
                  Loaded
                </span>
              </div>

              {/* Stats grid */}
              {stats ? (
                <div className="grid grid-cols-3 gap-2">
                  {buildStats.map((s) => (
                    <div key={s.label} className="bg-card rounded-lg p-3 text-center shadow-sm border border-surface-dark">
                      <s.icon size={18} className={`mx-auto mb-1 ${s.color}`} />
                      <p className="text-xs font-semibold text-text">{s.label}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-2">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="bg-card rounded-lg p-3 text-center shadow-sm border border-surface-dark animate-pulse h-16" />
                  ))}
                </div>
              )}

              {/* Crops */}
              {pack.crops.length > 0 && (
                <div className="bg-card rounded-xl p-4 shadow-sm border border-surface-dark">
                  <h3 className="font-heading font-bold text-sm mb-3">Crops Covered</h3>
                  <div className="flex flex-wrap gap-2">
                    {pack.crops.map((crop) => (
                      <span
                        key={crop}
                        className="text-xs bg-primary/10 text-primary font-medium px-2.5 py-1 rounded-full capitalize"
                      >
                        {crop}
                      </span>
                    ))}
                  </div>
                </div>
              )}

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
                  Open in Knowledge Explorer
                </button>
                <button className="w-full border-2 border-secondary text-secondary font-semibold text-sm py-2.5 rounded-lg hover:bg-secondary/5 transition-colors">
                  Rebuild Pack
                </button>
                <button className="w-full text-tertiary text-xs font-medium py-2 hover:underline">
                  Unload Pack
                </button>
              </div>
            </>
          )}

        </div>
      </div>
    </div>
  )
}
