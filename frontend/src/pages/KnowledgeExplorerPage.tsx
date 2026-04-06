import { useState } from 'react'
import { Search, ChevronDown, ChevronUp, Leaf, Database } from 'lucide-react'
import TopBar from '../components/layout/TopBar'

type KnowledgeType = 'all' | 'diseases' | 'treatments' | 'practices' | 'pests' | 'climate'
type ItemType = 'disease' | 'treatment' | 'practice' | 'pest' | 'climate'

interface KnowledgeItem {
  id: string
  type: ItemType
  title: string
  badges: { label: string; color: string }[]
  description: string
  details?: string[]
  linkedTreatments?: string[]
  materials?: string[]
}

const ITEMS: KnowledgeItem[] = [
  {
    id: '1',
    type: 'disease',
    title: 'Cassava Mosaic Disease',
    badges: [
      { label: 'Cassava', color: 'bg-primary/10 text-primary' },
      { label: 'High Severity', color: 'bg-tertiary/10 text-tertiary' },
      { label: 'Viral', color: 'bg-text-muted/10 text-text-muted' },
    ],
    description: 'Yellow mosaic patterns on leaves, leaf curling, stunted growth.',
    details: [
      'Pathogen: Begomovirus (family Geminiviridae)',
      'Vector: Whitefly (Bemisia tabaci)',
      'Yield loss: 20-95% in susceptible varieties',
    ],
    linkedTreatments: ['Neem Oil Spray', 'Resistant Varieties', 'Roguing'],
  },
  {
    id: '2',
    type: 'treatment',
    title: 'Neem Oil Spray',
    badges: [
      { label: 'Organic', color: 'bg-primary/10 text-primary' },
      { label: 'Easy', color: 'bg-secondary/10 text-secondary' },
    ],
    description: 'Natural pesticide using locally available neem leaves.',
    materials: ['Neem leaves', 'Water', 'Soap'],
  },
  {
    id: '3',
    type: 'practice',
    title: 'Rainy Season Planting Calendar',
    badges: [
      { label: 'Cassava', color: 'bg-primary/10 text-primary' },
      { label: 'Rice', color: 'bg-primary/10 text-primary' },
      { label: 'Jun\u2013Oct', color: 'bg-secondary/10 text-secondary' },
    ],
    description: 'Optimal planting windows and field preparation schedule for Casamance rainy season.',
  },
  {
    id: '4',
    type: 'disease',
    title: 'Rice Blast',
    badges: [
      { label: 'Rice', color: 'bg-primary/10 text-primary' },
      { label: 'High Severity', color: 'bg-tertiary/10 text-tertiary' },
      { label: 'Fungal', color: 'bg-text-muted/10 text-text-muted' },
    ],
    description: 'Fungal disease affecting leaves, nodes, and panicles of rice.',
    linkedTreatments: ['Fungicide Application', 'Crop Rotation', 'Resistant Varieties'],
  },
  {
    id: '5',
    type: 'pest',
    title: 'Cassava Green Mite',
    badges: [
      { label: 'Cassava', color: 'bg-primary/10 text-primary' },
      { label: 'Medium', color: 'bg-secondary/10 text-secondary' },
    ],
    description: 'Tiny mites causing leaf yellowing and stunting during dry season.',
  },
  {
    id: '6',
    type: 'climate',
    title: 'Casamance Rainy Season Climate',
    badges: [
      { label: 'Jun\u2013Oct', color: 'bg-secondary/10 text-secondary' },
      { label: 'Casamance', color: 'bg-primary/10 text-primary' },
    ],
    description: 'Rainfall 800\u20131200mm, temperatures 25\u201332\u00b0C, high humidity. Peak planting window June\u2013July.',
  },
]

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

export default function KnowledgeExplorerPage() {
  const [tab, setTab] = useState<KnowledgeType>('all')
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  const filtered = ITEMS.filter((item) => {
    if (tab !== 'all') {
      const typeMap: Record<string, ItemType> = {
        diseases: 'disease',
        treatments: 'treatment',
        practices: 'practice',
        pests: 'pest',
        climate: 'climate',
      }
      if (item.type !== typeMap[tab]) return false
    }
    if (search) {
      const s = search.toLowerCase()
      return item.title.toLowerCase().includes(s) || item.description.toLowerCase().includes(s)
    }
    return true
  })

  return (
    <div className="flex flex-col h-[calc(100dvh-4rem)]">
      <TopBar title="Knowledge Explorer" subtitle="Casamance Agriculture v1.0" back backTo="/packs" />

      {/* Search */}
      <div className="bg-card px-4 py-3 border-b border-surface-dark">
        <div className="max-w-lg mx-auto relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search diseases, treatments, crops..."
            className="w-full bg-surface rounded-lg pl-9 pr-4 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30"
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
              className={`shrink-0 px-3 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                tab === t.key
                  ? 'border-primary text-primary'
                  : 'border-transparent text-text-muted hover:text-text'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto px-4 py-4 bg-surface">
        <div className="max-w-lg mx-auto space-y-3">
          {filtered.map((item) => (
            <div
              key={item.id}
              className={`bg-card rounded-xl border-l-4 ${BORDER_COLORS[item.type]} shadow-sm overflow-hidden`}
            >
              <button
                onClick={() => setExpanded(expanded === item.id ? null : item.id)}
                className="w-full text-left px-4 py-3"
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
                <p className="text-xs text-text-muted mt-2 leading-relaxed">{item.description}</p>
              </button>

              {expanded === item.id && (
                <div className="px-4 pb-3 space-y-2 border-t border-surface-dark pt-2">
                  {item.details?.map((d) => (
                    <p key={d} className="text-xs text-text-muted">{d}</p>
                  ))}
                  {item.linkedTreatments && (
                    <div>
                      <p className="text-xs font-semibold text-text mb-1">Linked Treatments:</p>
                      <div className="flex gap-1.5 flex-wrap">
                        {item.linkedTreatments.map((t) => (
                          <span key={t} className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {item.materials && (
                    <div>
                      <p className="text-xs font-semibold text-text mb-1">Materials:</p>
                      <p className="text-xs text-text-muted">{item.materials.join(', ')}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom action */}
      <div className="bg-card border-t border-surface-dark px-4 py-3">
        <div className="max-w-lg mx-auto">
          <button className="w-full bg-primary text-white font-semibold text-sm py-2.5 rounded-lg hover:bg-primary-light transition-colors">
            Load into Field Assistant \u2192
          </button>
        </div>
      </div>
    </div>
  )
}
