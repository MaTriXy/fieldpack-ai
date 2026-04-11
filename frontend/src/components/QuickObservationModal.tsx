import { useState, useRef, useEffect } from 'react'
import { X, Camera, Loader2, AlertTriangle, Leaf, Droplets, FileText, MapPin, Smartphone } from 'lucide-react'
import { createObservation, uploadImageBase64 } from '../lib/api'
import { isNative } from '../lib/config'
import { getCameraConfig } from '../lib/settings'
import { enqueueObservation } from '../lib/offline-queue'

type ObsType = 'disease_sighting' | 'crop_condition' | 'treatment_applied' | 'note'

const TYPE_OPTIONS: { type: ObsType; label: string; Icon: typeof AlertTriangle; color: string; active: string }[] = [
  { type: 'disease_sighting', label: 'Disease', Icon: AlertTriangle, color: 'text-tertiary', active: 'bg-tertiary/15 text-tertiary ring-1 ring-tertiary/30' },
  { type: 'crop_condition', label: 'Condition', Icon: Leaf, color: 'text-primary', active: 'bg-primary/15 text-primary ring-1 ring-primary/30' },
  { type: 'treatment_applied', label: 'Treatment', Icon: Droplets, color: 'text-secondary', active: 'bg-secondary/15 text-secondary ring-1 ring-secondary/30' },
  { type: 'note', label: 'Note', Icon: FileText, color: 'text-text-muted', active: 'bg-surface-dark text-text ring-1 ring-text-muted/20' },
]

interface QuickObservationModalProps {
  isOpen: boolean
  onClose: () => void
  onSaved: (wasOffline: boolean) => void
  reachable: boolean
  initialData?: { type?: string; details?: string; location?: string } | null
}

export default function QuickObservationModal({ isOpen, onClose, onSaved, reachable, initialData }: QuickObservationModalProps) {
  const [obsType, setObsType] = useState<ObsType>('note')
  const [details, setDetails] = useState('')
  const [location, setLocation] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [pendingImage, setPendingImage] = useState<{ base64: string; format: string; preview: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Pre-fill from initialData when modal opens
  const prevOpen = useRef(false)
  useEffect(() => {
    if (isOpen && !prevOpen.current && initialData) {
      if (initialData.type) setObsType(initialData.type as ObsType)
      if (initialData.details) setDetails(initialData.details)
      if (initialData.location) setLocation(initialData.location)
    }
    prevOpen.current = isOpen
  }, [isOpen, initialData])

  const canSave = details.trim().length > 0

  const handleCamera = async () => {
    if (isNative()) {
      try {
        const { Camera: CapCamera, CameraResultType, CameraSource } = await import('@capacitor/camera')
        const camCfg = getCameraConfig()
        const photo = await CapCamera.getPhoto({
          quality: camCfg.quality,
          allowEditing: false,
          resultType: CameraResultType.Base64,
          source: CameraSource.Camera,
          width: camCfg.width,
          height: camCfg.height,
        })
        if (photo.base64String) {
          setPendingImage({
            base64: photo.base64String,
            format: photo.format || 'jpeg',
            preview: `data:image/${photo.format || 'jpeg'};base64,${photo.base64String}`,
          })
        }
      } catch {
        // User cancelled
      }
    } else {
      fileInputRef.current?.click()
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      const base64 = result.split(',')[1]
      const format = file.type.split('/')[1] || 'jpeg'
      setPendingImage({ base64, format, preview: result })
    }
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  const handleSave = async () => {
    if (!canSave) return
    setSaving(true)
    setError('')

    try {
      if (reachable) {
        // Online path: upload image + create via API
        let imagePath: string | undefined
        if (pendingImage) {
          imagePath = await uploadImageBase64(pendingImage.base64, pendingImage.format)
        }
        await createObservation({
          type: obsType,
          details: details.trim(),
          location: location.trim() || undefined,
          image_path: imagePath,
        })
      } else {
        // Offline path: save to localStorage queue
        enqueueObservation({
          type: obsType,
          details: details.trim(),
          location: location.trim() || null,
          image_base64: pendingImage?.base64 || null,
          image_format: pendingImage?.format || null,
        })
      }

      // Reset and close
      const wasOffline = !reachable
      setDetails('')
      setLocation('')
      setObsType('note')
      setPendingImage(null)
      onSaved(wasOffline)
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save observation')
    } finally {
      setSaving(false)
    }
  }

  const handleClose = () => {
    if (!saving) {
      setError('')
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center" onClick={handleClose}>
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 transition-opacity" />

      {/* Sheet */}
      <div
        className="relative w-full max-w-lg bg-card rounded-t-2xl shadow-xl animate-slideUp"
        onClick={e => e.stopPropagation()}
      >
        {/* Drag handle */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 rounded-full bg-surface-dark" />
        </div>

        <div className="px-4 pb-4 space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h2 className="font-heading font-bold text-lg text-text">New Observation</h2>
            <button onClick={handleClose} className="text-text-muted p-1 -mr-1 min-h-[44px] min-w-[44px] flex items-center justify-center">
              <X size={20} />
            </button>
          </div>

          {/* Type pills */}
          <div className="flex gap-2">
            {TYPE_OPTIONS.map(({ type, label, Icon, color, active }) => (
              <button
                key={type}
                onClick={() => setObsType(type)}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-lg text-xs font-semibold transition-all min-h-[44px] ${
                  obsType === type ? active : `bg-surface ${color}/60 hover:bg-surface-dark`
                }`}
              >
                <Icon size={14} />
                <span>{label}</span>
              </button>
            ))}
          </div>

          {/* Details textarea */}
          <div>
            <textarea
              value={details}
              onChange={e => setDetails(e.target.value)}
              placeholder="What did you observe?"
              rows={3}
              className="w-full bg-surface rounded-lg px-4 py-3 text-sm text-text placeholder:text-text-muted/50 outline-none focus:ring-2 focus:ring-primary/30 resize-none"
              style={{ maxHeight: '160px' }}
            />
          </div>

          {/* Location input */}
          <div className="relative">
            <MapPin size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              value={location}
              onChange={e => setLocation(e.target.value)}
              placeholder="Field name, area, or GPS (optional)"
              className="w-full bg-surface rounded-lg pl-9 pr-4 py-2.5 text-sm text-text placeholder:text-text-muted/50 outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>

          {/* Photo preview */}
          {pendingImage && (
            <div className="relative inline-block">
              <img
                src={pendingImage.preview}
                alt="Captured"
                className="w-20 h-20 rounded-lg object-cover border border-surface-dark"
              />
              <button
                onClick={() => setPendingImage(null)}
                className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-tertiary text-white rounded-full flex items-center justify-center"
              >
                <X size={10} />
              </button>
            </div>
          )}

          {/* Error */}
          {error && (
            <p className="text-xs text-tertiary">{error}</p>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3 pt-1 pb-[env(safe-area-inset-bottom)]">
            {!pendingImage && (
              <button
                onClick={handleCamera}
                disabled={saving}
                className="flex items-center gap-1.5 bg-surface rounded-lg px-4 py-2.5 text-sm font-medium text-text-muted hover:bg-surface-dark transition-colors min-h-[44px]"
              >
                <Camera size={16} />
                Photo
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={!canSave || saving}
              className="flex-1 flex items-center justify-center gap-2 bg-primary text-white font-semibold text-sm rounded-lg py-2.5 min-h-[44px] hover:bg-primary-light transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <Loader2 size={16} className="animate-spin" />
              ) : !reachable ? (
                <Smartphone size={16} />
              ) : null}
              {saving ? 'Saving...' : reachable ? 'Save Observation' : 'Save Locally'}
            </button>
          </div>
        </div>

        {/* Hidden file input for web camera fallback */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={handleFileSelect}
        />
      </div>
    </div>
  )
}
