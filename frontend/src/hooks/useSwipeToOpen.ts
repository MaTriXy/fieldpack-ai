import { useEffect, useRef } from 'react'

export function useSwipeToOpen(onOpen: () => void) {
  const tracking = useRef(false)
  const startX = useRef(0)

  useEffect(() => {
    const onTouchStart = (e: TouchEvent) => {
      if (e.touches[0].clientX < 20) {
        tracking.current = true
        startX.current = e.touches[0].clientX
      }
    }

    const onTouchMove = (e: TouchEvent) => {
      if (!tracking.current) return
      const dx = e.touches[0].clientX - startX.current
      if (dx > 60) {
        tracking.current = false
        onOpen()
      }
    }

    const onTouchEnd = () => {
      tracking.current = false
    }

    document.addEventListener('touchstart', onTouchStart, { passive: true })
    document.addEventListener('touchmove', onTouchMove, { passive: true })
    document.addEventListener('touchend', onTouchEnd, { passive: true })

    return () => {
      document.removeEventListener('touchstart', onTouchStart)
      document.removeEventListener('touchmove', onTouchMove)
      document.removeEventListener('touchend', onTouchEnd)
    }
  }, [onOpen])
}
