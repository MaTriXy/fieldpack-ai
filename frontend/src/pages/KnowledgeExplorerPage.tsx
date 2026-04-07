import { useState, useEffect, useRef } from 'react'
import { Search, ChevronDown, ChevronUp, Leaf, Database } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import { browseKnowledge, type BrowseItem } from '../lib/api'

type KnowledgeType = 'all' | 'diseases' | 'treatments' | 'practices' | 'pests' | 'climate'
type ItemType = 'disease' | 'treatment' | 'practice' | 'pest' | 'climate'

interface KnowledgeItem {
  id: string
  type: ItemType
  title: string
  badges: { label: string; color: string }[]
  description: string
  details?: string[]
}

const TABS: { key: KnowledgeType; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'diseases', label: 'Diseases' },
  { key: 'treatments', label: 'Treatments' },
  { key: 'practices', label: 'Practices' },
  { key: 'pests', label: 'Pests' },
  { key: 'climate', label: 'Climate' },
]

const BORDER_COLORS: Record<ItemType, string> = {
  disease: 'border-l-tertiary',
  treatment: 'border-l-primary',
  practice: 'border-l-secondary',
  pest: 'border-l-tertiary-light',
  climate: 'border-l-secondary-light',
}

const STATS = [
  { label: '5 Crops', icon: Leaf },
  { label: '15 Diseases' },
  { label: '31 Treatments' },
  { label: '12 Pests' },
  { label: '190 Chunks', icon: Database },
]

const TAB_TO_TYPE: Record<string, string> = {
  all: 'all', diseases: 'disease', treatments: 'treatment',
  practices: 'practice', pests: 'pest', climate: 'climate',
}

function mapBrowseItem(item: BrowseItem): KnowledgeItem {
  return {
    id: item.id,
    type: item.type as ItemType,
    title: item.title,
    badges: item.badges,
    description: item.description,
    details: item.details,
  }
}

export default function KnowledgeExplorerPage() {
  const [tab, setTab] = useState<KnowledgeType>('all')
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [items, setItems] = useState<KnowledgeItem[]>([])
  const [loading, setLoading] = useState(true)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setLoading(true)
      browseKnowledge(TAB_TO_TYPE[tab] || 'all', search)
        .then((res) => {
          setItems(res.items.map(mapBrowseItem))
          setLoading(false)
        })
        .catch(() => setLoading(false))
    }, search ? 300 : 0)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [tab, search])

  return (
    <div className="flex flex-col h-[calc(100dvh-4rem-env(safe-area-inset-bottom,0px))] animate-fadeIn">
      <TopBar title="Knowledge Explorer" subtitle="Casamance, Senegal — Agriculture v1.0" back backTo="/packs" />

      {/* Search */}
      <div className="bg-card px-4 py-3 border-b border-surface-dark">
        <div className="max-w-lg mx-auto relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search diseases, treatments, crops..."
            className="w-full bg-surface rounded-lg pl-9 pr-4 py-2 text-base outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>
      </div>

      {/* Stats */}
      <div className="bg-card px-4 py-2 border-b border-surface-dark">
        <div className="max-w-lg mx-auto flex gap-2 overflow-x-auto scrollbar-hide">
          {STATS.map((s) => (
            <span key={s.label} className="shrink-0 text-xs font-medium bg-surface px-3 py-1 rounded-full text-primary">
              {s.label}
            </span>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-card px-4 border-b border-surface-dark">
        <div className="max-w-lg mx-auto flex gap-1 overflow-x-auto scrollbar-hide">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`shrink-0 px-3 py-2.5 text-xs font-medium border-b-2 transition-colors min-h-[44px] ${
                tab === t.key
                  ? 'border-primary-light text-primary'
                  : 'border-transparent text-text-muted hover:text-text'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto overscroll-none px-4 py-4 bg-surface">
        <div className="max-w-lg mx-auto space-y-3">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 gap-2 animate-fadeIn">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-text-muted">Loading knowledge...</span>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3 animate-fadeIn">
              <Search size={32} className="text-text-muted/30" />
              <p className="text-sm text-text-muted">No results found</p>
              <p className="text-xs text-text-muted/60 text-center max-w-[200px]">
                {search ? `No items match "${search}"` : 'No knowledge loaded yet. Load a pack first.'}
              </p>
            </div>
          ) : (
            items.map((item, i) => (
              <div
                key={item.id}
                className={`bg-card rounded-xl border-l-4 ${BORDER_COLORS[item.type] || 'border-l-text-muted'} shadow-sm overflow-hidden animate-slideUp`}
                style={{ animationDelay: `${Math.min(i, 10) * 0.05}s` }}
              >
                <button
                  onClick={() => setExpanded(expanded === item.id ? null : item.id)}
                  className="w-full text-left px-4 py-3 min-h-[44px]"
                >
                  <div className="flex items-start justify-between">
                    <h3 className="font-heading font-bold text-sm">{item.title}</h3>
                    {expanded === item.id ? (
                      <ChevronUp size={16} className="text-text-muted shrink-0 mt-0.5" />
                    ) : (
                      <ChevronDown size={16} className="text-text-muted shrink-0 mt-0.5" />
                    )}
                  </div>
                  <div className="flex gap-1.5 flex-wrap mt-1.5">
                    {item.badges.map((b) => (
                      <span key={b.label} className={`text-xs font-medium px-2 py-0.5 rounded-full ${b.color}`}>
                        {b.label}
                      </span>
                    ))}
                  </div>
                  <p className="text-sm text-text-muted mt-2 leading-relaxed">{item.description}</p>
                </button>

                <div
                  className="overflow-hidden transition-all duration-300 ease-in-out"
                  style={{ maxHeight: expanded === item.id && item.details?.length ? '500px' : '0px' }}
                >
                  <div className="px-4 pb-3 space-y-2 border-t border-surface-dark pt-2">
                    {item.details?.map((d) => (
                      <p key={d} className="text-xs text-text-muted">{d}</p>
                    ))}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Bottom action */}
      <div className="bg-card border-t border-surface-dark px-4 py-3">
        <div className="max-w-lg mx-auto">
          <button className="w-full bg-primary text-white font-semibold text-sm py-2.5 rounded-lg hover:bg-primary-light transition-colors min-h-[44px]">
            Load into Field Assistant →
          </button>
        </div>
      </div>
    </div>
  )
}
