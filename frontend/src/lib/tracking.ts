import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { api } from '@/lib/api'

export function usePageTracking() {
  const location = useLocation()

  useEffect(() => {
    let sessionId = sessionStorage.getItem('flashfit_session_id')
    if (!sessionId) {
      sessionId = `sess_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
      sessionStorage.setItem('flashfit_session_id', sessionId)
    }

    api.analytics
      .track({
        eventType: 'page_view',
        pageUrl: window.location.href,
        referrer: document.referrer || undefined,
        sessionId,
        eventData: { path: location.pathname, search: location.search },
      })
      .catch(() => {
        // Silent fail for tracking
      })
  }, [location.pathname, location.search])
}

export function trackProductView(productId: string, productName: string) {
  let sessionId = sessionStorage.getItem('flashfit_session_id')
  if (!sessionId) {
    sessionId = `sess_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
    sessionStorage.setItem('flashfit_session_id', sessionId)
  }

  api.analytics
    .track({
      eventType: 'product_view',
      pageUrl: window.location.href,
      sessionId,
      eventData: { productId, productName },
    })
    .catch(() => {})
}
