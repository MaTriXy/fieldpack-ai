import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { Home, Rocket, Leaf, Database, ClipboardList } from 'lucide-react'
import { getQueuedObservationCount, getQueuedChatMessageCount } from '../../lib/offline-queue'

const tabs = [
  { to: '/', icon: Home, label: 'Home' },
  { to: '/mission', icon: Rocket, label: 'Mission' },
  { to: '/field', icon: Leaf, label: 'Field' },
  { to: '/packs', icon: Database, label: 'Packs' },
  { to: '/observations', icon: ClipboardList, label: 'Log' },
]

export default function BottomNav() {
  const [queueCount, setQueueCount] = useState(0)

  useEffect(() => {
    function updateCount() {
      setQueueCount(getQueuedObservationCount() + getQueuedChatMessageCount())
    }
    updateCount()
    window.addEventListener('storage', updateCount)
    const interval = setInterval(updateCount, 5000)
    return () => { window.removeEventListener('storage', updateCount); clearInterval(interval) }
  }, [])

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-card border-t border-surface-dark z-50 pb-[env(safe-area-inset-bottom)]" aria-label="Main navigation">
      <div className="max-w-lg mx-auto flex justify-around items-center h-16">
        {tabs.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `relative flex flex-col items-center gap-0.5 px-3 py-2 text-xs transition-all min-w-[44px] min-h-[44px] justify-center active:scale-90 ${
                isActive
                  ? 'text-primary-light font-semibold'
                  : 'text-text-muted/70 font-medium hover:text-text-muted'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={`relative flex items-center justify-center w-9 h-7 rounded-full transition-all ${
                    isActive ? 'bg-primary-light/20' : ''
                  }`}
                  aria-hidden="true"
                >
                  <Icon size={20} aria-hidden="true" />
                  {label === 'Log' && queueCount > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 flex items-center justify-center bg-secondary text-white text-[9px] font-bold rounded-full px-1">
                      {queueCount}
                    </span>
                  )}
                </span>
                <span>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
