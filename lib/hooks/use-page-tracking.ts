"use client"

import { useEffect } from 'react'
import { usePathname } from 'next/navigation'
import { trackPageView } from '@/lib/tracking'

/**
 * Hook to automatically track page views
 * Usage: Add `usePageTracking()` to any client component
 */
export function usePageTracking() {
  const pathname = usePathname()

  useEffect(() => {
    // Track page view when pathname changes
    if (pathname) {
      const title = document.title || 'Flashfits'
      trackPageView(pathname, title)
    }
  }, [pathname])
}
