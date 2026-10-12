"use client"

import { useState } from 'react'
import { useCookieConsent } from '@/contexts/cookie-consent-context'
import { Button } from '@/components/ui/button'
import { X, Cookie, Shield, TrendingUp, Megaphone } from 'lucide-react'

export function CookieSettingsDialog() {
  const { showSettings, closeSettings, savePreferences, preferences } = useCookieConsent()
  const [localPreferences, setLocalPreferences] = useState(preferences)

  if (!showSettings) return null

  const handleSave = () => {
    savePreferences(localPreferences)
  }

  const cookieCategories = [
    {
      id: 'necessary',
      icon: Shield,
      title: 'Necessary Cookies',
      description: 'Essential for the website to function properly. These cannot be disabled.',
      color: 'from-green-500 to-emerald-500',
      required: true,
    },
    {
      id: 'analytics',
      icon: TrendingUp,
      title: 'Analytics Cookies',
      description: 'Help us understand how visitors interact with our website by collecting anonymous data.',
      color: 'from-primary to-secondary',
      required: false,
    },
    {
      id: 'marketing',
      icon: Megaphone,
      title: 'Marketing Cookies',
      description: 'Used to track visitors across websites to display relevant advertisements.',
      color: 'from-accent to-pink-500',
      required: false,
    },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
      <div className="max-w-2xl w-full max-h-[90vh] overflow-y-auto glass backdrop-blur-xl bg-background/95 border-2 border-primary/20 rounded-3xl shadow-2xl animate-in zoom-in-95 duration-300">
        {/* Header */}
        <div className="sticky top-0 bg-background/95 backdrop-blur-xl border-b border-border/50 p-6 sm:p-8">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="w-14 h-14 bg-gradient-to-br from-primary to-secondary rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg">
                <Cookie className="h-7 w-7 text-white" />
              </div>
              <div>
                <h2 className="font-sans font-bold text-2xl mb-2 gradient-text">
                  Cookie Settings
                </h2>
                <p className="font-serif text-sm text-muted-foreground">
                  Manage your cookie preferences below
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={closeSettings}
              className="hover:bg-destructive/10 hover:text-destructive"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 sm:p-8 space-y-6">
          {cookieCategories.map((category) => {
            const Icon = category.icon
            const isEnabled = localPreferences[category.id as keyof typeof localPreferences]

            return (
              <div
                key={category.id}
                className="relative overflow-hidden rounded-2xl border-2 border-border/50 hover:border-primary/30 transition-all duration-300 group"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-4 flex-1">
                      <div className={`w-12 h-12 bg-gradient-to-br ${category.color} rounded-xl flex items-center justify-center flex-shrink-0 shadow-md group-hover:scale-110 transition-transform duration-300`}>
                        <Icon className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-sans font-bold text-lg mb-2 flex items-center gap-2">
                          {category.title}
                          {category.required && (
                            <span className="text-xs font-normal px-2 py-1 bg-primary/10 text-primary rounded-full">
                              Required
                            </span>
                          )}
                        </h3>
                        <p className="font-serif text-sm text-muted-foreground leading-relaxed">
                          {category.description}
                        </p>
                      </div>
                    </div>

                    {/* Toggle Switch */}
                    <button
                      onClick={() => {
                        if (!category.required) {
                          setLocalPreferences({
                            ...localPreferences,
                            [category.id]: !isEnabled,
                          })
                        }
                      }}
                      disabled={category.required}
                      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-300 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${
                        isEnabled ? 'bg-gradient-to-r from-primary to-secondary' : 'bg-gray-300 dark:bg-gray-600'
                      } ${category.required ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-300 ease-in-out ${
                          isEnabled ? 'translate-x-5' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </div>
                </div>

                {/* Gradient border effect on hover */}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 bg-gradient-to-r from-primary/10 via-secondary/10 to-accent/10 transition-opacity duration-300 pointer-events-none" />
              </div>
            )
          })}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-background/95 backdrop-blur-xl border-t border-border/50 p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row gap-3">
            <Button
              onClick={handleSave}
              className="flex-1 bg-gradient-to-r from-primary via-secondary to-accent hover:shadow-xl hover:shadow-primary/50 transform hover:scale-105 transition-all duration-300"
            >
              Save Preferences
            </Button>
            <Button
              onClick={closeSettings}
              variant="outline"
              className="flex-1 sm:flex-none border-2 border-primary/30 hover:border-primary hover:bg-primary/10"
            >
              Cancel
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-4 text-center">
            Changes will take effect immediately. You can update your preferences at any time.
          </p>
        </div>
      </div>
    </div>
  )
}
