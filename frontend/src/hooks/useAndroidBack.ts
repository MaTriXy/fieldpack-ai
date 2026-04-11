import { useEffect } from 'react'
import { isNative } from '../lib/config'

/**
 * Register Android hardware back button handlers.
 * Handlers are called in order; first one returning true consumes the event.
 */
export function useAndroidBack(handlers: (() => boolean)[]) {
  useEffect(() => {
    if (!isNative()) return

    let listener: { remove: () => void } | null = null
    import('@capacitor/app').then(({ App }) => {
      App.addListener('backButton', ({ canGoBack }) => {
        for (const handler of handlers) {
          if (handler()) return // consumed
        }
        if (canGoBack) window.history.back()
        else App.exitApp()
      }).then(l => { listener = l })
    }).catch(() => {})

    return () => { listener?.remove() }
  }, handlers)
}
