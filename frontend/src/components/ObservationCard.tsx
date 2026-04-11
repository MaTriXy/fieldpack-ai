import { useState } from 'react'
import { AlertTriangle, Leaf, Droplets, FileText, MapPin } from 'lucide-react'
import type { Observation } from '../lib/api'
import { apiUrl } from '../lib/config'

type ObsType = Observation['type']

const TYPE_CONFIG: Record<ObsType, { border: string; label: string; iconColor: string; Icon: typeof AlertTriangle }> = {
  disease_sighting:  { border: 'border-l-tertiary', label: 'Disease Sighting', iconColor: 'text-tertiary', Icon: AlertTriangle },
  crop_condition:    { border: 'border-l-primary', label: 'Crop Condition', iconColor: 'text-primary', Icon: Leaf },
  treatment_applied: { border: 'border-l-secondary', label: 'Treatment Applied', iconColor: 'text-secondary', Icon: Droplets },
  note:              { border: 'border-l-text-muted/40', label: 'Note', iconColor: 'text-text-muted', Icon: FileText },
}

const SEVERITY_COLORS: Record<string, string> = {
  mild: 'bg-primary/10 text-primary',
  moderate: 'bg-secondary/10 text-secondary',
  severe: 'bg-tertiary/10 text-tertiary',
}

function timeAgo(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 0) return 'just now'
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`
  return new Date(iso).toLocaleDateString()
}

interface ObservationCardProps {
  observation: Observation & { _queued?: boolean }
  style?: React.CSSProperties
}

export default function ObservationCard({ observation, style }: ObservationCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [imgError, setImgError] = useState(false)

  const obsType = observation.type as ObsType
  const config = TYPE_CONFIG[obsType] || TYPE_CONFIG.note
  const { border, label, iconColor, Icon } = config
  const isQueued = observation._queued || observation.synced === -1

  // Split details into bold first sentence + rest
  const details = observation.details || ''
  const sentenceEnd = details.search(/[.!?](\s|$)/)
  const firstSentence = sentenceEnd > 0 ? details.slice(0, sentenceEnd + 1) : details
  const restText = sentenceEnd > 0 ? details.slice(sentenceEnd + 1).trim() : ''

  const hasImage = !!observation.image_path && !imgError
  const imageSrc = observation.image_path?.startsWith('data:')
    ? observation.image_path
    : observation.image_path
      ? apiUrl(`/upload/files/${observation.image_path.split('/').pop()}`)
      : ''

  return (
    <div
      className={`bg-card rounded-xl shadow-sm border border-surface-dark border-l-4 ${border} overflow-hidden animate-slideUp active:scale-[0.985] transition-transform ${isQueued ? 'border-secondary ring-1 ring-secondary/20' : ''}`}
      style={style}
    >
      <button
        className="w-full text-left p-3.5 min-h-[44px]"
        onClick={() => setExpanded(e => !e)}
        aria-expanded={expanded}
      >
        <div className="flex gap-3">
          {/* Image thumbnail (when image exists and not expanded) */}
          {hasImage && !expanded && (
            <img
              src={imageSrc}
              alt=""
              className="w-16 h-16 rounded-lg object-cover flex-shrink-0"
              onError={() => setImgError(true)}
            />
          )}

          <div className="flex-1 min-w-0">
            {/* Header: type + time */}
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-1.5">
                <Icon size={14} className={iconColor} />
                <span className={`text-xs font-semibold ${iconColor}`}>{label}</span>
              </div>
              <span className="text-xs text-text-muted flex-shrink-0">{timeAgo(observation.timestamp)}</span>
            </div>

            {/* Details text */}
            <p className={`text-sm text-text leading-snug ${expanded ? '' : 'line-clamp-3'}`}>
              <span className="font-semibold">{firstSentence}</span>
              {restText && <> {restText}</>}
            </p>

            {/* Expanded image */}
            {hasImage && expanded && (
              <img
                src={imageSrc}
                alt="Observation photo"
                className="w-full h-48 rounded-lg object-cover mt-2"
                onError={() => setImgError(true)}
              />
            )}

            {/* Location */}
            {observation.location && (
              <div className="flex items-center gap-1 mt-1.5">
                <MapPin size={11} className="text-text-muted flex-shrink-0" />
                <span className="text-xs text-text-muted truncate">{observation.location}</span>
              </div>
            )}

            {/* Footer: severity + sync status */}
            <div className="flex items-center gap-2 mt-2">
              {observation.severity_observed && (
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full capitalize ${SEVERITY_COLORS[observation.severity_observed] || 'bg-surface text-text-muted'}`}>
                  {observation.severity_observed}
                </span>
              )}
              {isQueued ? (
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-secondary/15 text-secondary uppercase tracking-wide">
                  Pending
                </span>
              ) : observation.synced === 0 ? (
                <div className="flex items-center gap-1">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="animate-ping absolute h-full w-full rounded-full bg-secondary opacity-60" />
                    <span className="relative rounded-full h-1.5 w-1.5 bg-secondary" />
                  </span>
                  <span className="text-xs text-secondary">pending sync</span>
                </div>
              ) : (
                <div className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                  <span className="text-xs text-text-muted/50">synced</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </button>
    </div>
  )
}
