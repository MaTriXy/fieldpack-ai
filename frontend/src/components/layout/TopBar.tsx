import { ArrowLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface TopBarProps {
  title: string
  subtitle?: string
  back?: boolean
  backTo?: string
  badge?: { label: string; variant: 'online' | 'offline' | 'live' }
  leftAction?: React.ReactNode
  rightAction?: React.ReactNode
  dark?: boolean
}

export default function TopBar({ title, subtitle, back, backTo, badge, leftAction, rightAction, dark }: TopBarProps) {
  const navigate = useNavigate()

  const badgeColors = {
    online: 'bg-secondary text-primary-dark',
    offline: 'bg-primary-light text-white',
    live: 'bg-green-500 text-white',
  }

  const handleBack = () => {
    if (backTo) {
      navigate(backTo)
    } else {
      navigate(-1)
    }
  }

  return (
    <header className={`sticky top-0 z-40 px-4 py-3 ${dark ? 'bg-debug-bg' : 'bg-primary'}`}>
      <div className="max-w-lg mx-auto flex items-center gap-3">
        {back && (
          <button onClick={handleBack} className="text-white p-2.5 -ml-2.5" aria-label="Go back">
            <ArrowLeft size={22} />
          </button>
        )}
        {leftAction}
        <div className="flex-1 min-w-0">
          <h1 className="text-white font-heading font-bold text-lg leading-tight truncate">
            {title}
          </h1>
          {subtitle && (
            <p className="text-white/70 text-xs truncate">{subtitle}</p>
          )}
        </div>
        {badge && (
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${badgeColors[badge.variant]}`}>
            {badge.label}
          </span>
        )}
        {rightAction}
      </div>
    </header>
  )
}
