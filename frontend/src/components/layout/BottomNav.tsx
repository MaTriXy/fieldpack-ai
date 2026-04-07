import { NavLink } from 'react-router-dom'
import { Home, Rocket, Leaf, Database, Terminal } from 'lucide-react'

const tabs = [
  { to: '/', icon: Home, label: 'Home' },
  { to: '/mission', icon: Rocket, label: 'Mission' },
  { to: '/field', icon: Leaf, label: 'Field' },
  { to: '/packs', icon: Database, label: 'Packs' },
  ...(import.meta.env.DEV ? [{ to: '/debug', icon: Terminal, label: 'Debug' }] : []),
]

export default function BottomNav() {
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
                  className={`flex items-center justify-center w-9 h-7 rounded-full transition-all ${
                    isActive ? 'bg-primary-light/20' : ''
                  }`}
                  aria-hidden="true"
                >
                  <Icon size={20} aria-hidden="true" />
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
