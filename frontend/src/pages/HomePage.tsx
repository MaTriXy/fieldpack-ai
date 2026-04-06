import { Link } from 'react-router-dom'
import { Rocket, Leaf, WifiOff, Database } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="bg-surface">
      {/* Hero */}
      <div className="bg-primary px-6 pt-10 pb-12 text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Leaf className="text-secondary" size={32} />
          <h1 className="font-heading text-3xl font-extrabold text-white">FieldPack AI</h1>
        </div>
        <p className="text-white/80 text-sm font-medium">
          Offline intelligence for the field
        </p>
        <p className="text-white/60 text-xs mt-1">
          Powered by Gemma 4 &middot; Built for humanitarian workers
        </p>
      </div>

      {/* CTA Cards */}
      <div className="px-4 -mt-6 space-y-4 max-w-lg mx-auto">
        {/* Phase 1: Create Pack */}
        <Link
          to="/mission"
          className="block bg-card rounded-xl p-5 shadow-md border border-surface-dark hover:shadow-lg transition-shadow"
        >
          <div className="flex items-start gap-4">
            <div className="bg-primary/10 rounded-lg p-3">
              <Rocket className="text-primary" size={28} />
            </div>
            <div className="flex-1">
              <h2 className="font-heading font-bold text-lg text-text">
                Create Knowledge Pack
              </h2>
              <p className="text-text-muted text-sm mt-1">
                Dispatch AI agents to gather crop knowledge for your region
              </p>
              <div className="mt-3 inline-flex items-center gap-1.5 bg-primary text-white text-sm font-semibold px-4 py-2 rounded-lg">
                Start Mission
                <Rocket size={14} />
              </div>
            </div>
          </div>
        </Link>

        {/* Phase 2: Field Session */}
        <Link
          to="/field"
          className="block bg-card rounded-xl p-5 shadow-md border border-surface-dark hover:shadow-lg transition-shadow"
        >
          <div className="flex items-start gap-4">
            <div className="bg-secondary/10 rounded-lg p-3">
              <Leaf className="text-secondary" size={28} />
            </div>
            <div className="flex-1">
              <h2 className="font-heading font-bold text-lg text-text">
                Start Field Session
              </h2>
              <p className="text-text-muted text-sm mt-1">
                Use an existing pack for offline crop diagnosis and advice
              </p>
              <div className="mt-3 inline-flex items-center gap-1.5 bg-secondary text-primary-dark text-sm font-semibold px-4 py-2 rounded-lg">
                Select Pack
                <Database size={14} />
              </div>
            </div>
          </div>
        </Link>
      </div>

      {/* Status */}
      <div className="px-4 mt-6 max-w-lg mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <WifiOff size={14} className="text-primary" />
          <span>Offline Ready</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <Database size={14} className="text-secondary" />
          <span>No Pack Loaded</span>
        </div>
        <span className="text-xs text-text-muted/50">v1.0.0-beta</span>
      </div>
    </div>
  )
}
