import { useEffect, useState } from 'react'
import PersonaFrame from './frames/PersonaFrame'
import MapFrame from './frames/MapFrame'
import StatsFrame from './frames/StatsFrame'
import ArchitectureFrame from './frames/ArchitectureFrame'
import OnlinePhaseFrame from './frames/OnlinePhaseFrame'
import ProgressFrame from './frames/ProgressFrame'
import TransitionFrame from './frames/TransitionFrame'
import FieldSessionFrame from './frames/FieldSessionFrame'
import GroundedFrame from './frames/GroundedFrame'
import PlatformFrame from './frames/PlatformFrame'
import TitleFrame from './frames/TitleFrame'
import ClosingFrame from './frames/ClosingFrame'
import PipelineFrame from './frames/PipelineFrame'

const FRAMES: Record<string, React.FC> = {
  persona: PersonaFrame,
  map: MapFrame,
  stats: StatsFrame,
  architecture: ArchitectureFrame,
  'online-phase': OnlinePhaseFrame,
  progress: ProgressFrame,
  transition: TransitionFrame,
  'field-session': FieldSessionFrame,
  grounded: GroundedFrame,
  platform: PlatformFrame,
  title: TitleFrame,
  closing: ClosingFrame,
  pipeline: PipelineFrame,
}

/**
 * RecordingPage — single 1920x1080 canvas for OBS capture.
 *
 * The frame component fills the FULL 1920x1080 canvas so its background
 * photo covers everything seamlessly. A CSS transform shifts the frame's
 * non-background content left so it doesn't overlap the phone.
 * The phone floats on top on the right side.
 */
export default function RecordingPage() {
  const [currentFrame, setCurrentFrame] = useState<string>('title')
  const [fullScreenPhone, setFullScreenPhone] = useState(false)

  useEffect(() => {
    document.documentElement.classList.add('recording-mode')
    return () => document.documentElement.classList.remove('recording-mode')
  }, [])

  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.slice(1)
      if (hash === '__full-phone__') {
        setFullScreenPhone(true)
        return
      }
      setFullScreenPhone(false)
      if (hash && FRAMES[hash]) {
        setCurrentFrame(hash)
      }
    }

    onHashChange()
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const FrameComponent = FRAMES[currentFrame]

  if (fullScreenPhone) {
    return (
      <div
        className="flex items-center justify-center"
        style={{
          width: 1920,
          height: 1080,
          background: '#0F1A14',
          overflow: 'hidden',
        }}
      >
        <PhoneMockup size="large" />
      </div>
    )
  }

  return (
    <div
      style={{
        width: 1920,
        height: 1080,
        position: 'relative',
        overflow: 'hidden',
        background: '#0F1A14',
      }}
    >
      {/* Layer 1: Frame at full 1920x1080.
          The frame's photo-bg uses position:absolute + inset:0 + width:100%,
          so at 1920px wide the photo seamlessly fills the entire canvas.
          padding-right pushes flex-centered content into the left 1152px
          while the absolutely-positioned background photo ignores padding. */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 1, paddingRight: 768 }}>
        {FrameComponent && <FrameComponent key={currentFrame} />}
      </div>

      {/* Layer 2: Gradient overlay — darkens the right side for phone contrast */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          background: `linear-gradient(
            to right,
            rgba(15, 26, 20, 0.0) 0%,
            rgba(15, 26, 20, 0.0) 52%,
            rgba(15, 26, 20, 0.40) 65%,
            rgba(15, 26, 20, 0.65) 80%,
            rgba(15, 26, 20, 0.78) 100%
          )`,
          pointerEvents: 'none',
          zIndex: 2,
        }}
      />

      {/* Layer 3: Phone mockup */}
      <div
        className="flex items-center justify-center"
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: 768,
          height: 1080,
          zIndex: 3,
        }}
      >
        <PhoneMockup size="normal" />
      </div>
    </div>
  )
}

// ─── Phone Mockup ───────────────────────────────────────────────────────────

const PHONE_IFRAME_URL = 'http://localhost:5173'

const PHONE_NORMAL = { width: 468, height: 1000, bezel: 12, radius: 50 }
const PHONE_LARGE = { width: 490, height: 1046, bezel: 14, radius: 52 }

function PhoneMockup({ size }: { size: 'normal' | 'large' }) {
  const dims = size === 'large' ? PHONE_LARGE : PHONE_NORMAL
  const outerW = dims.width + dims.bezel * 2
  const outerH = dims.height + dims.bezel * 2
  const screenRadius = 28

  return (
    <div
      style={{
        width: outerW,
        height: outerH,
        borderRadius: dims.radius,
        background: '#1a1a1a',
        border: '2px solid #333',
        boxShadow: '0 25px 80px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.05)',
        position: 'relative',
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {/* Screen area */}
      <div
        className="phone-screen"
        style={{
          position: 'absolute',
          top: dims.bezel,
          left: dims.bezel,
          width: dims.width,
          height: dims.height,
          borderRadius: screenRadius,
          overflow: 'hidden',
          background: '#000',
        }}
      >
        <iframe
          name="phone-app"
          src={PHONE_IFRAME_URL}
          style={{
            width: dims.width,
            height: dims.height,
            border: 'none',
            display: 'block',
          }}
          allow="camera"
          scrolling="no"
        />
      </div>

      {/* Bottom bar */}
      <div
        style={{
          position: 'absolute',
          bottom: 6,
          left: '50%',
          transform: 'translateX(-50%)',
          width: 120,
          height: 4,
          borderRadius: 2,
          background: 'rgba(255,255,255,0.2)',
          zIndex: 10,
        }}
      />
    </div>
  )
}
