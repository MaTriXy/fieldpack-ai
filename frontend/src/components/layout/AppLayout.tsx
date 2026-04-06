import { Outlet } from 'react-router-dom'
import BottomNav from './BottomNav'

export default function AppLayout() {
  return (
    <>
      {/* pb accounts for fixed BottomNav height + device safe-area-inset-bottom.
          Pages that manage their own full-height layout (flex col + h-[calc(100dvh-...)])
          are not affected because they constrain themselves internally. */}
      <main className="pb-[calc(4rem+env(safe-area-inset-bottom))]">
        <Outlet />
      </main>
      <BottomNav />
    </>
  )
}
