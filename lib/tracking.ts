import Cookies from 'js-cookie'
import { api } from '@/lib/api/client'

// Generate or get session ID
function getSessionId(): string {
  let sessionId = Cookies.get('flashfits_session_id')
  if (!sessionId) {
    sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    Cookies.set('flashfits_session_id', sessionId, { expires: 1 }) // 1 day session
  }
  return sessionId
}

// Send event to FastAPI backend
async function sendToBackend(eventType: string, eventData: any) {
  try {
    const sessionId = getSessionId()
    await api.analytics.track({
      eventType,
      eventData,
      sessionId,
    })
  } catch (error) {
    console.error('Failed to send analytics to FastAPI:', error)
  }
}

interface PageView {
  url: string
  title: string
  timestamp: number
}

interface ProductView {
  id: string
  name: string
  timestamp: number
}

interface SearchQuery {
  query: string
  timestamp: number
}

interface UserHistory {
  pageViews: PageView[]
  lastVisit: number
  visitCount: number
}

const HISTORY_COOKIE_NAME = 'flashfits_user_history'
const MAX_HISTORY_ITEMS = 50
const COOKIE_EXPIRY_DAYS = 30

/**
 * Track a page view in user history
 */
export function trackPageView(url: string, title: string) {
  // Check if analytics cookies are enabled
  const preferences = Cookies.get('flashfits_cookie_preferences')
  if (!preferences) return

  try {
    const prefs = JSON.parse(preferences)
    if (!prefs.analytics) return // Don't track if analytics not enabled
  } catch (e) {
    return
  }

  const history = getUserHistory()
  
  const newPageView: PageView = {
    url,
    title,
    timestamp: Date.now(),
  }

  // Add new page view and keep only the latest items
  history.pageViews = [newPageView, ...history.pageViews].slice(0, MAX_HISTORY_ITEMS)
  history.lastVisit = Date.now()
  history.visitCount += 1

  saveUserHistory(history)
  
  // Send to backend
  sendToBackend('page_view', { url, title })
}

/**
 * Get user browsing history
 */
export function getUserHistory(): UserHistory {
  const historyData = Cookies.get(HISTORY_COOKIE_NAME)
  
  if (!historyData) {
    return {
      pageViews: [],
      lastVisit: Date.now(),
      visitCount: 0,
    }
  }

  try {
    return JSON.parse(historyData)
  } catch (e) {
    console.error('Failed to parse user history', e)
    return {
      pageViews: [],
      lastVisit: Date.now(),
      visitCount: 0,
    }
  }
}

/**
 * Save user history to cookies
 */
function saveUserHistory(history: UserHistory) {
  try {
    Cookies.set(HISTORY_COOKIE_NAME, JSON.stringify(history), { 
      expires: COOKIE_EXPIRY_DAYS 
    })
  } catch (e) {
    console.error('Failed to save user history', e)
  }
}

/**
 * Clear user history
 */
export function clearUserHistory() {
  Cookies.remove(HISTORY_COOKIE_NAME)
}

/**
 * Get recently viewed pages
 */
export function getRecentPages(limit: number = 10): PageView[] {
  const history = getUserHistory()
  return history.pageViews.slice(0, limit)
}

/**
 * Track product view
 */
export function trackProductView(productId: string, productName: string) {
  const preferences = Cookies.get('flashfits_cookie_preferences')
  if (!preferences) return

  try {
    const prefs = JSON.parse(preferences)
    if (!prefs.analytics) return
  } catch (e) {
    return
  }

  const viewedProducts = getViewedProducts()
  const newView: ProductView = {
    id: productId,
    name: productName,
    timestamp: Date.now(),
  }

  // Add to viewed products
  const updated = [newView, ...viewedProducts.filter((p: ProductView) => p.id !== productId)].slice(0, 20)
  
  Cookies.set('flashfits_viewed_products', JSON.stringify(updated), { 
    expires: COOKIE_EXPIRY_DAYS 
  })
  
  // Send to backend
  sendToBackend('product_view', { productId, productName })
}

/**
 * Get viewed products
 */
export function getViewedProducts(): ProductView[] {
  const data = Cookies.get('flashfits_viewed_products')
  if (!data) return []
  
  try {
    return JSON.parse(data)
  } catch (e) {
    return []
  }
}

/**
 * Track search query
 */
export function trackSearch(query: string) {
  const preferences = Cookies.get('flashfits_cookie_preferences')
  if (!preferences) return

  try {
    const prefs = JSON.parse(preferences)
    if (!prefs.analytics) return
  } catch (e) {
    return
  }

  const searches = getSearchHistory()
  const newSearch: SearchQuery = {
    query,
    timestamp: Date.now(),
  }

  const updated = [newSearch, ...searches].slice(0, 30)
  
  Cookies.set('flashfits_search_history', JSON.stringify(updated), { 
    expires: COOKIE_EXPIRY_DAYS 
  })
  
  // Send to backend
  sendToBackend('search', { query })
}

/**
 * Get search history
 */
export function getSearchHistory(): SearchQuery[] {
  const data = Cookies.get('flashfits_search_history')
  if (!data) return []
  
  try {
    return JSON.parse(data)
  } catch (e) {
    return []
  }
}
