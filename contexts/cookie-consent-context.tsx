"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import Cookies from 'js-cookie'

interface CookiePreferences {
  necessary: boolean
  analytics: boolean
  marketing: boolean
}

interface CookieConsentContextType {
  hasConsent: boolean
  showBanner: boolean
  preferences: CookiePreferences
  acceptAll: () => void
  rejectAll: () => void
  savePreferences: (prefs: CookiePreferences) => void
  openSettings: () => void
  closeSettings: () => void
  showSettings: boolean
}

const CookieConsentContext = createContext<CookieConsentContextType | undefined>(undefined)

const COOKIE_CONSENT_NAME = 'flashfits_cookie_consent'
const COOKIE_PREFERENCES_NAME = 'flashfits_cookie_preferences'
const COOKIE_EXPIRY_DAYS = 365

export function CookieConsentProvider({ children }: { children: ReactNode }) {
  const [hasConsent, setHasConsent] = useState(false)
  const [showBanner, setShowBanner] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [preferences, setPreferences] = useState<CookiePreferences>({
    necessary: true, // Always true
    analytics: false,
    marketing: false,
  })

  useEffect(() => {
    // Check if user has already given consent
    const consent = Cookies.get(COOKIE_CONSENT_NAME)
    const savedPreferences = Cookies.get(COOKIE_PREFERENCES_NAME)

    if (consent === 'true') {
      setHasConsent(true)
      if (savedPreferences) {
        try {
          setPreferences(JSON.parse(savedPreferences))
        } catch (e) {
          console.error('Failed to parse cookie preferences', e)
        }
      }
    } else {
      // Show banner after a short delay for better UX
      setTimeout(() => setShowBanner(true), 1000)
    }
  }, [])

  const acceptAll = () => {
    const allPreferences: CookiePreferences = {
      necessary: true,
      analytics: true,
      marketing: true,
    }
    
    Cookies.set(COOKIE_CONSENT_NAME, 'true', { expires: COOKIE_EXPIRY_DAYS })
    Cookies.set(COOKIE_PREFERENCES_NAME, JSON.stringify(allPreferences), { expires: COOKIE_EXPIRY_DAYS })
    
    setHasConsent(true)
    setPreferences(allPreferences)
    setShowBanner(false)
    setShowSettings(false)
    
    // Initialize analytics and marketing if accepted
    initializeTracking(allPreferences)
  }

  const rejectAll = () => {
    const minimalPreferences: CookiePreferences = {
      necessary: true,
      analytics: false,
      marketing: false,
    }
    
    Cookies.set(COOKIE_CONSENT_NAME, 'true', { expires: COOKIE_EXPIRY_DAYS })
    Cookies.set(COOKIE_PREFERENCES_NAME, JSON.stringify(minimalPreferences), { expires: COOKIE_EXPIRY_DAYS })
    
    setHasConsent(true)
    setPreferences(minimalPreferences)
    setShowBanner(false)
    setShowSettings(false)
  }

  const savePreferences = (prefs: CookiePreferences) => {
    const newPreferences = { ...prefs, necessary: true } // Necessary cookies always enabled
    
    Cookies.set(COOKIE_CONSENT_NAME, 'true', { expires: COOKIE_EXPIRY_DAYS })
    Cookies.set(COOKIE_PREFERENCES_NAME, JSON.stringify(newPreferences), { expires: COOKIE_EXPIRY_DAYS })
    
    setHasConsent(true)
    setPreferences(newPreferences)
    setShowBanner(false)
    setShowSettings(false)
    
    initializeTracking(newPreferences)
  }

  const openSettings = () => {
    setShowSettings(true)
    setShowBanner(false)
  }

  const closeSettings = () => {
    setShowSettings(false)
  }

  const initializeTracking = (prefs: CookiePreferences) => {
    // Initialize analytics if enabled
    if (prefs.analytics) {
      // Add Google Analytics or other analytics code here
      console.log('Analytics tracking enabled')
    }
    
    // Initialize marketing if enabled
    if (prefs.marketing) {
      // Add marketing tracking code here
      console.log('Marketing tracking enabled')
    }
  }

  return (
    <CookieConsentContext.Provider
      value={{
        hasConsent,
        showBanner,
        preferences,
        acceptAll,
        rejectAll,
        savePreferences,
        openSettings,
        closeSettings,
        showSettings,
      }}
    >
      {children}
    </CookieConsentContext.Provider>
  )
}

export function useCookieConsent() {
  const context = useContext(CookieConsentContext)
  if (context === undefined) {
    throw new Error('useCookieConsent must be used within a CookieConsentProvider')
  }
  return context
}
