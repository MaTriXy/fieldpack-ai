import { useState, useEffect, useCallback, useRef } from 'react'
import { ClipboardList, Camera, Loader2, WifiOff, Smartphone, Check } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import ObservationCard from '../components/ObservationCard'
import QuickObservationModal from '../components/QuickObservationModal'
import {
  listObservations,
  getObservationStats,
  type Observation,
  type ObservationStats,
} from '../lib/api'
import { getQueuedObservations, flushObservationQueue, type QueuedObservation } from '../lib/offline-queue'
import { useBackendReachable } from '../hooks/useBackendReachable'

export default function ObservationsPage() {
  const [observations, setObservations] = useState<Observation[]>([])
  const [stats, setStats] = useState<ObservationStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [queuedObs, setQueuedObs] = useState<QueuedObservation[]>([])
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<{ synced: number; failed: number } | null>(null)

  const { reachable } = useBackendReachable()
  const prevReachable = useRef(reachable)

  const refreshQueue = useCallback(() => {
    setQueuedObs(getQueuedObservations())
  }, [])

  const fetchData = useCallback(() => {
    setLoading(true)
    setError(false)
    refreshQueue()
    Promise.all([listObservations(), getObservationStats()])
      .then(([listRes, statsRes]) => {
        setObservations(listRes.observations)
        setStats(statsRes)
        setLoading(false)
      })
      .catch(() => {
        setError(true)
        setLoading(false)
      })
  }, [refreshQueue])

  useEffect(() => { fetchData() }, [fetchData])

  const refresh = () => {
    refreshQueue()
    Promise.all([listObservations(), getObservationStats()])
      .then(([listRes, statsRes]) => {
        setObservations(listRes.observations)
        setStats(statsRes)
      })
      .catch(() => {})
  }

  // Auto-sync when backend reconnects
  useEffect(() => {
    if (reachable && !prevReachable.current && queuedObs.length > 0) {
      setSyncing(true)
      flushObservationQueue()
        .then((result) => {
          setSyncResult(result)
          refresh()
          setTimeout(() => setSyncResult(null), 5000)
        })
        .catch(() => {
          refreshQueue()
        })
        .finally(() => {
          setSyncing(false)
        })
    }
    prevReachable.current = reachable
  }, [reachable]) // eslint-disable-line react-hooks/exhaustive-deps

  // Merge queued observations at top of feed
  const allObservations: (Observation & { _queued?: boolean; _queueId?: string })[] = [
    ...queuedObs.map((q, i) => ({
      id: -(i + 1),
      timestamp: q.created_at,
      type: q.type as Observation['type'],
      location: q.location,
      details: q.details,
      image_path: q.image_base64 ? `data:image/${q.image_format || 'jpeg'};base64,${q.image_base64}` : null,
      synced: -1,
      crop_id: null,
      severity_observed: null,
      _queued: true,
      _queueId: q.id,
    })),
    ...observations,
  ]

  const queueCount = queuedObs.length

  return (
    <div className="flex flex-col animate-fadeIn min-h-[calc(100dvh-4rem-env(safe-area-inset-bottom,0px))]">
      <TopBar title="Field Journal" badge={{ label: 'Offline', variant: 'offline' }} />

      <div className="flex-1 overflow-y-auto overscroll-none px-4 py-4 bg-surface">
        <div className="max-w-lg mx-auto space-y-3">

          {/* Sync banners */}
          {syncing && (
            <div className="bg-secondary/10 border border-secondary/20 rounded-xl px-4 py-3 flex items-center gap-2 animate-slideUp">
              <Loader2 size={14} className="animate-spin text-secondary" />
              <span className="text-xs font-medium text-secondary">Syncing observations...</span>
            </div>
          )}

          {syncResult && (
            <div className="bg-primary/10 border border-primary/20 rounded-xl px-4 py-3 flex items-center gap-2 animate-slideUp">
              <Check size={14} className="text-primary" />
              <span className="text-xs font-medium text-primary">
                {syncResult.synced} observation{syncResult.synced !== 1 ? 's' : ''} synced
                {syncResult.failed > 0 && ` · ${syncResult.failed} failed`}
              </span>
            </div>
          )}

          {/* Offline banner */}
          {!reachable && (
            <div className="bg-surface-dark rounded-xl px-4 py-2.5 flex items-center gap-2 animate-slideUp">
              <WifiOff size={13} className="text-text-muted flex-shrink-0" />
              <span className="text-xs text-text-muted">Offline — observations will save to your phone</span>
            </div>
          )}

          {/* Status strip */}
          {!loading && !error && stats && (
            <div className="bg-card border border-surface-dark rounded-xl px-4 py-3 flex items-center justify-between shadow-sm animate-slideUp">
              <div className="flex items-center gap-2">
                <ClipboardList size={14} className="text-primary" />
                <span className="text-sm font-semibold text-text">{stats.total + queueCount}</span>
                <span className="text-xs text-text-muted">observation{(stats.total + queueCount) !== 1 ? 's' : ''}</span>
              </div>

              <div className="h-4 w-px bg-surface-dark" />

              {stats.unsynced > 0 ? (
                <div className="flex items-center gap-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute h-full w-full rounded-full bg-secondary opacity-60" />
                    <span className="relative rounded-full h-2 w-2 bg-secondary" />
                  </span>
                  <span className="text-xs font-medium text-secondary">{stats.unsynced} pending sync</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                  <span className="text-xs text-text-muted">all synced</span>
                </div>
              )}

              {queueCount > 0 && (
                <>
                  <div className="h-4 w-px bg-surface-dark" />
                  <div className="flex items-center gap-1.5">
                    <Smartphone size={12} className="text-secondary" />
                    <span className="text-xs font-medium text-secondary">{queueCount} on phone</span>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-16 gap-3 animate-fadeIn">
              <Loader2 size={28} className="animate-spin text-primary" />
              <span className="text-sm text-text-muted">Loading field journal...</span>
            </div>
          )}

          {/* Error state */}
          {!loading && error && (
            <div className="bg-card rounded-2xl shadow-sm border border-surface-dark p-6 text-center space-y-3 animate-slideUp">
              <WifiOff size={32} className="mx-auto text-text-muted/40" />
              <p className="text-sm font-semibold text-text">Could not load observations</p>
              <p className="text-xs text-text-muted">Make sure the backend is running and a pack is loaded.</p>
              <button
                onClick={fetchData}
                className="text-xs text-primary font-semibold hover:underline"
              >
                Retry
              </button>
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && allObservations.length === 0 && (
            <div className="bg-card rounded-2xl shadow-sm border border-surface-dark p-8 text-center space-y-3 animate-slideUp">
              <ClipboardList size={36} className="mx-auto text-text-muted/30" />
              <p className="text-sm font-semibold text-text">No observations yet</p>
              <p className="text-xs text-text-muted">
                Tap the button below to record your first field observation, or log one through Field Chat.
              </p>
            </div>
          )}

          {/* Observation feed */}
          {!loading && !error && allObservations.map((obs, i) => (
            <ObservationCard
              key={obs._queued ? `queued-${obs._queueId}` : obs.id}
              observation={obs}
              style={{ animationDelay: `${i * 0.05}s` }}
            />
          ))}

          {/* Bottom spacer for the fixed button */}
          {!loading && <div className="h-16" aria-hidden="true" />}
        </div>
      </div>

      {/* New Observation button — fixed above bottom nav */}
      {!loading && !error && (
        <div className="px-4 pb-2 pt-2 bg-surface border-t border-surface-dark/50">
          <div className="max-w-lg mx-auto">
            <button
              onClick={() => setShowModal(true)}
              className="w-full flex items-center justify-center gap-2 bg-primary text-white font-semibold text-sm py-3 rounded-xl shadow-md hover:bg-primary-light transition-colors active:scale-[0.98] min-h-[44px]"
            >
              <Camera size={18} />
              New Observation
            </button>
          </div>
        </div>
      )}

      <QuickObservationModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSaved={refresh}
        reachable={reachable}
      />
    </div>
  )
}
