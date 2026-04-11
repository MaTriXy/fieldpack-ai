import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Leaf, Bug, Pill, Shield, FileText, Database, MapPin, Loader2, AlertCircle, CheckCircle2, BookOpen, Globe } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import { listPacks, loadPack, unloadPack, browseKnowledge, type PackSummary } from '../lib/api'
import { getPackHeroImage } from '../lib/pack-images'

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
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pack, setPack] = useState<PackSummary | null>(null)
  const [stats, setStats] = useState<PackStats | null>(null)
  const [loadingPack, setLoadingPack] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  async function fetchBrowseStats(p: PackSummary) {
    const [diseases, treatments, pests, practices, climate] = await Promise.all([
      browseKnowledge('disease', '', 1),
      browseKnowledge('treatment', '', 1),
      browseKnowledge('pest', '', 1),
      browseKnowledge('practice', '', 1),
      browseKnowledge('climate', '', 1),
    ])
    setStats({
      crops: p.crops.length,
      diseases: diseases.count,
      treatments: treatments.count,
      pests: pests.count,
      practices: practices.count,
      climate: climate.count,
    })
  }

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      setLoading(true)
      setError(null)
      try {
        const packs = await listPacks()
        const thisPack = packs.find((p) => p.pack_id === id) ?? null
        if (cancelled) return
        if (!thisPack) {
          setPack(null)
          setLoading(false)
          return
        }
        setPack(thisPack)
        if (thisPack.loaded) {
          await fetchBrowseStats(thisPack)
          if (cancelled) return
        }
      } catch (err) {
        if (!cancelled) setError('Could not reach the backend. Is the server running?')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => { cancelled = true }
  }, [id])

  async function handleLoadPack() {
    if (!id) return
    setLoadingPack(true)
    setLoadError(null)
    try {
      const ok = await loadPack(id)
      if (!ok) {
        setLoadError('Failed to load the pack. Check server logs.')
        return
      }
      const packs = await listPacks()
      const updated = packs.find((p) => p.pack_id === id) ?? null
      setPack(updated)
      if (updated?.loaded) await fetchBrowseStats(updated)
    } catch {
      setLoadError('Could not reach the backend.')
    } finally {
      setLoadingPack(false)
    }
  }

  // When browse stats are loaded, show full breakdown. Otherwise fall back to pack metadata.
  const buildStats = stats
    ? [
        { label: `${stats.crops} Crop${stats.crops !== 1 ? 's' : ''}`, icon: Leaf, color: 'text-primary' },
        { label: `${stats.diseases} Disease${stats.diseases !== 1 ? 's' : ''}`, icon: Bug, color: 'text-tertiary' },
        { label: `${stats.treatments} Treatment${stats.treatments !== 1 ? 's' : ''}`, icon: Pill, color: 'text-primary' },
        { label: `${stats.pests} Pest${stats.pests !== 1 ? 's' : ''}`, icon: Shield, color: 'text-secondary' },
        { label: `${stats.practices} Practice${stats.practices !== 1 ? 's' : ''}`, icon: FileText, color: 'text-text-muted' },
        { label: `${stats.climate} Climate`, icon: MapPin, color: 'text-text-muted' },
      ]
    : pack
      ? [
          { label: `${pack.crops.length} Crop${pack.crops.length !== 1 ? 's' : ''}`, icon: Leaf, color: 'text-primary' },
          { label: `${pack.knowledge_entries} Knowledge Entries`, icon: BookOpen, color: 'text-secondary' },
          { label: `${(pack.sources || []).length} Expert Source${(pack.sources || []).length !== 1 ? 's' : ''}`, icon: Globe, color: 'text-primary' },
        ]
      : []

  return (
    <div className="flex flex-col animate-fadeIn">
      <TopBar title="Pack Details" back backTo="/packs" />

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

          {/* Pack not found */}
          {!loading && !error && !pack && (
            <div className="bg-card rounded-xl p-6 shadow-sm border border-surface-dark text-center space-y-3">
              <Database size={32} className="mx-auto text-text-muted" />
              <p className="text-sm font-semibold text-text">Pack not found</p>
              <p className="text-xs text-text-muted">The pack "{id}" does not exist or the server is not running.</p>
              <button
                onClick={() => navigate('/packs')}
                className="text-xs text-primary font-medium hover:underline"
              >
                Back to Packs
              </button>
            </div>
          )}

          {/* Main content — only shown when pack is loaded */}
          {!loading && !error && pack && (
            <>
              {/* Pack identity — hero banner */}
              <div className="bg-card rounded-xl shadow-sm border border-surface-dark overflow-hidden">
                <div className="h-40 relative overflow-hidden">
                  <img
                    src={getPackHeroImage(pack.pack_id)}
                    alt={`${pack.name} landscape`}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent" />
                  {pack.loaded ? (
                    <span className="absolute top-2.5 right-2.5 inline-flex items-center gap-1 text-[11px] font-bold bg-primary/90 text-white px-2.5 py-1 rounded-full shadow-sm">
                      <CheckCircle2 size={12} />
                      Active
                    </span>
                  ) : (
                    <span className="absolute top-2.5 right-2.5 text-[11px] font-bold bg-black/40 text-white/80 px-2.5 py-1 rounded-full backdrop-blur-sm">
                      Not Loaded
                    </span>
                  )}
                  <div className="absolute bottom-3 left-4 right-4">
                    <h2 className="font-heading text-xl font-extrabold text-white drop-shadow-md">{pack.name}</h2>
                    <div className="flex items-center gap-1.5 mt-1">
                      <MapPin size={12} className="text-white/80" />
                      <span className="text-xs text-white/80">{pack.region}</span>
                      <span className="text-white/40 mx-1">&middot;</span>
                      <span className="text-xs text-white/60 font-mono">{pack.pack_id}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Load error */}
              {loadError && (
                <div className="bg-card rounded-xl p-3 shadow-sm border border-surface-dark flex items-center gap-2">
                  <AlertCircle size={16} className="text-tertiary shrink-0" />
                  <p className="text-xs text-tertiary">{loadError}</p>
                </div>
              )}

              {/* Load this Pack button — only shown if not currently loaded */}
              {!pack.loaded && (
                <button
                  onClick={handleLoadPack}
                  disabled={loadingPack}
                  className="w-full bg-primary text-white font-semibold text-sm py-3 rounded-lg hover:bg-primary/90 active:scale-[0.98] transition-all disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loadingPack ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      Loading Pack...
                    </>
                  ) : (
                    'Load this Pack'
                  )}
                </button>
              )}

              {/* Stats grid */}
              {pack.loaded && !stats ? (
                // Loading skeleton while browse stats are being fetched for the active pack
                <div className="grid grid-cols-3 gap-2">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="bg-card rounded-lg p-3 text-center shadow-sm border border-surface-dark animate-pulse h-16" />
                  ))}
                </div>
              ) : buildStats.length > 0 ? (
                <div className={`grid gap-2 ${buildStats.length === 2 ? 'grid-cols-2' : 'grid-cols-3'}`}>
                  {buildStats.map((s) => (
                    <div key={s.label} className="bg-card rounded-lg p-3 text-center shadow-sm border border-surface-dark">
                      <s.icon size={18} className={`mx-auto mb-1 ${s.color}`} />
                      <p className="text-xs font-semibold text-text">{s.label}</p>
                    </div>
                  ))}
                </div>
              ) : null}

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
                  disabled={!pack.loaded}
                  className={`w-full border-2 font-semibold text-sm py-2.5 rounded-lg transition-colors ${
                    pack.loaded
                      ? 'border-primary text-primary hover:bg-primary/5'
                      : 'border-surface-dark text-text-muted cursor-not-allowed opacity-50'
                  }`}
                >
                  {pack.loaded ? 'Open in Knowledge Explorer' : 'Load pack to explore knowledge'}
                </button>
                <button
                  onClick={handleLoadPack}
                  disabled={loadingPack}
                  className="w-full flex items-center justify-center gap-2 border-2 border-secondary text-secondary font-semibold text-sm py-2.5 rounded-lg hover:bg-secondary/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loadingPack && <Loader2 size={14} className="animate-spin" />}
                  {loadingPack ? 'Reloading...' : 'Reload Pack'}
                </button>
                {loadError && (
                  <p className="text-xs text-tertiary text-center">{loadError}</p>
                )}
                <button
                  onClick={async () => {
                    const ok = await unloadPack()
                    if (ok) {
                      setPack(prev => prev ? { ...prev, loaded: false } : null)
                      setStats(null)
                    }
                  }}
                  className="w-full text-tertiary text-xs font-medium py-2 hover:underline"
                >
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
