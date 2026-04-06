import { NavLink } from 'react-router-dom'
import { Home, Rocket, Leaf, Database, Terminal } from 'lucide-react'

const tabs = [
  { to: '/', icon: Home, label: 'Home' },
  { to: '/mission', icon: Rocket, label: 'Mission' },
  { to: '/field', icon: Leaf, label: 'Field' },
  { to: '/packs', icon: Database, label: 'Packs' },
  { to: '/debug', icon: Terminal, label: 'Debug' },
]

export default function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-card border-t border-surface-dark z-50">
      <div className="max-w-lg mx-auto flex justify-around items-center h-16">
        {tabs.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 px-3 py-2 text-xs font-medium transition-colors ${
                isActive
                  ? 'text-primary'
                  : 'text-text-muted hover:text-primary-light'
              }`
            }
          >
            <Icon size={22} />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
