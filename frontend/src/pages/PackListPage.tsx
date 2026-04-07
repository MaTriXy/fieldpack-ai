import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { MapPin, Leaf, Bug, Check, Database, Plus, Loader2 } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import { listPacks, type PackSummary } from '../lib/api'
import { getPackCardImage } from '../lib/pack-images'

export default function PackListPage() {
  const [packs, setPacks] = useState<PackSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(false)
    listPacks()
      .then((data) => {
        if (!cancelled) {
          setPacks(data)
          setLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(true)
          setLoading(false)
        }
      })
    return () => { cancelled = true }
  }, [])

  return (
    <div className="flex flex-col animate-fadeIn min-h-[calc(100dvh-4rem-env(safe-area-inset-bottom,0px))]">
      <TopBar title="Knowledge Packs" />

      <div className="flex-1 overflow-y-auto overscroll-none px-4 py-4 bg-surface">
        <div className="max-w-lg mx-auto space-y-4">

          {/* Header description */}
          <div className="flex items-start gap-3 pb-1">
            <div className="bg-primary/10 rounded-xl p-2.5 ring-1 ring-primary/15 flex-shrink-0 mt-0.5">
              <Database size={18} className="text-primary" />
            </div>
            <p className="text-sm text-text-muted leading-relaxed pt-1">
              Your offline field guides &mdash; each pack contains crop knowledge for a specific region.
            </p>
          </div>

          {/* Loading state */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 gap-3 animate-fadeIn">
              <Loader2 size={28} className="animate-spin text-primary" />
              <span className="text-sm text-text-muted">Loading packs...</span>
            </div>
          )}

          {/* Error state */}
          {!loading && error && (
            <div className="bg-card rounded-2xl shadow-sm border border-surface-dark p-6 text-center space-y-3 animate-slideUp">
              <Database size={32} className="mx-auto text-text-muted/40" />
              <p className="text-sm font-semibold text-text">Could not reach the server</p>
              <p className="text-xs text-text-muted">Make sure the backend is running and try again.</p>
              <button
                onClick={() => window.location.reload()}
                className="text-xs text-primary font-semibold hover:underline"
              >
                Retry
              </button>
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && packs.length === 0 && (
            <div className="bg-card rounded-2xl shadow-sm border border-surface-dark p-8 text-center space-y-3 animate-slideUp">
              <Database size={36} className="mx-auto text-text-muted/30" />
              <p className="text-sm font-semibold text-text">No Knowledge Packs found</p>
              <p className="text-xs text-text-muted">
                Create one from the Mission page.
              </p>
              <Link
                to="/mission"
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline mt-1"
              >
                <Plus size={13} />
                Start a Mission
              </Link>
            </div>
          )}

          {/* Pack cards */}
          {!loading && !error && packs.map((pack, i) => (
            <Link
              key={pack.pack_id}
              to={`/packs/${pack.pack_id}`}
              className={`block bg-card rounded-2xl shadow-sm border border-surface-dark overflow-hidden active:scale-[0.985] transition-transform animate-slideUp relative ${
                pack.loaded ? 'ring-2 ring-primary/20' : ''
              }`}
              style={{ animationDelay: `${i * 0.07}s` }}
            >
              {/* Active indicator bar */}
              {pack.loaded && (
                <div className="absolute top-0 left-0 bottom-0 w-1 bg-primary rounded-l-2xl z-10" />
              )}
              {/* Cover image */}
              <div className="h-32 relative overflow-hidden">
                <img
                  src={getPackCardImage(pack.pack_id)}
                  alt={`${pack.name} cover`}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-black/10 to-transparent" />
                {pack.loaded && (
                  <span className="absolute top-2 right-2 inline-flex items-center gap-1 text-[11px] font-bold bg-primary/90 text-white px-2 py-0.5 rounded-full shadow-sm">
                    <Check size={10} strokeWidth={3} />
                    Active
                  </span>
                )}
                <div className="absolute bottom-2 left-3 right-3">
                  <h2 className="font-heading font-bold text-base text-white leading-snug drop-shadow-md">
                    {pack.name}
                  </h2>
                  <div className="flex items-center gap-1.5 text-xs text-white/80 mt-0.5">
                    <MapPin size={11} className="flex-shrink-0" />
                    <span>{pack.region}</span>
                  </div>
                </div>
              </div>

              <div className="p-4 pt-3">
                {/* Stats row */}
                <div className="flex items-center gap-4 mb-3">
                  <div className="flex items-center gap-1.5 text-xs text-text-muted">
                    <Leaf size={13} className="text-primary flex-shrink-0" />
                    <span>
                      <span className="font-semibold text-text">{pack.crops.length}</span>
                      {' '}crop{pack.crops.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="h-3 w-px bg-surface-dark" />
                  <div className="flex items-center gap-1.5 text-xs text-text-muted">
                    <Bug size={13} className="text-tertiary flex-shrink-0" />
                    <span>
                      <span className="font-semibold text-text">{pack.diseases_count}</span>
                      {' '}disease{pack.diseases_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                </div>

                {/* Crop pills */}
                {pack.crops.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {pack.crops.map((crop) => (
                      <span
                        key={crop}
                        className="text-[11px] font-medium bg-primary/8 text-primary px-2 py-0.5 rounded-full capitalize"
                      >
                        {crop}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </Link>
          ))}

          {/* Create new link card */}
          {!loading && !error && (
            <Link
              to="/mission"
              className="flex items-center justify-between bg-card rounded-2xl shadow-sm border border-dashed border-surface-dark p-4 text-text-muted hover:border-primary/40 hover:text-primary active:scale-[0.985] transition-all animate-slideUp"
              style={{ animationDelay: `${packs.length * 0.07 + 0.05}s` }}
            >
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-surface border border-surface-dark flex items-center justify-center flex-shrink-0">
                  <Plus size={16} />
                </div>
                <span className="text-sm font-semibold">Create New Pack</span>
              </div>
              <span className="text-xs font-medium opacity-60">Mission Page &rarr;</span>
            </Link>
          )}

        </div>
      </div>
    </div>
  )
}
