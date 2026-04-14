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

// Frame ordering for auto-play mode
const FRAME_ORDER = [
  'title',
  'persona',
  'map',
  'stats',
  'architecture',
  'online-phase',
  'progress',
  'transition',
  'field-session',
  'pipeline',
  'grounded',
  'platform',
  'closing',
]

export default function App() {
  const [currentFrame, setCurrentFrame] = useState<string>('title')

  // Listen for hash changes — Playwright drives this
  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.slice(1) // remove #
      if (hash && FRAMES[hash]) {
        setCurrentFrame(hash)
      }
    }

    // Set initial frame from hash
    onHashChange()
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const FrameComponent = FRAMES[currentFrame]

  if (!FrameComponent) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-bg">
        <p className="text-cream-muted font-body text-xl">
          Unknown frame: {currentFrame}
        </p>
      </div>
    )
  }

  // Key forces re-mount on frame change, restarting all animations
  return (
    <div className="w-full h-full bg-bg overflow-hidden">
      <FrameComponent key={currentFrame} />
    </div>
  )
}
