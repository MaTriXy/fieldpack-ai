import { Outlet } from 'react-router-dom'
import BottomNav from './BottomNav'

export default function AppLayout() {
  return (
    <>
      <main className="pb-16">
        <Outlet />
      </main>
      <BottomNav />
    </>
  )
}
