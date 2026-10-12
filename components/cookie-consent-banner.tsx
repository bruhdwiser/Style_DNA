"use client"

import { useCookieConsent } from '@/contexts/cookie-consent-context'
import { Button } from '@/components/ui/button'
import { X, Cookie, Settings } from 'lucide-react'

export function CookieConsentBanner() {
  const { showBanner, acceptAll, rejectAll, openSettings } = useCookieConsent()

  if (!showBanner) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 p-4 sm:p-6 animate-in slide-in-from-bottom duration-500">
      <div className="max-w-7xl mx-auto">
        <div className="glass backdrop-blur-xl bg-background/95 border-2 border-primary/20 rounded-2xl shadow-2xl p-6 sm:p-8">
          <div className="flex flex-col gap-6">
            {/* Header */}
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-gradient-to-br from-primary to-secondary rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg">
                <Cookie className="h-6 w-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="font-sans font-bold text-xl mb-2 gradient-text">
                  We Value Your Privacy
                </h3>
                <p className="font-serif text-sm text-muted-foreground leading-relaxed">
                  We use cookies to enhance your browsing experience, serve personalized content, and analyze our traffic. 
                  By clicking "Accept All", you consent to our use of cookies. You can customize your preferences or decline non-essential cookies.
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3">
              <Button
                onClick={acceptAll}
                className="flex-1 bg-gradient-to-r from-primary via-secondary to-accent hover:shadow-xl hover:shadow-primary/50 transform hover:scale-105 transition-all duration-300"
              >
                Accept All
              </Button>
              <Button
                onClick={rejectAll}
                variant="outline"
                className="flex-1 border-2 border-primary/30 hover:border-primary hover:bg-primary/10"
              >
                Reject All
              </Button>
              <Button
                onClick={openSettings}
                variant="outline"
                className="flex-1 sm:flex-none border-2 border-secondary/30 hover:border-secondary hover:bg-secondary/10"
              >
                <Settings className="h-4 w-4 mr-2" />
                Customize
              </Button>
            </div>

            {/* Privacy Links */}
            <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
              <a href="/privacy" className="hover:text-primary transition-colors underline">
                Privacy Policy
              </a>
              <a href="/cookies" className="hover:text-primary transition-colors underline">
                Cookie Policy
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
