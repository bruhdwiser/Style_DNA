import React, { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/auth-context'
import { api } from '@/lib/api'
import type { StyleProfileResponse, ConsentRecord } from '@/lib/api'
import './SettingsPage.css'

export default function SettingsPage() {
  const { user, loading: authLoading, signOut } = useAuth()
  const navigate = useNavigate()

  const [profile, setProfile] = useState<StyleProfileResponse | null>(null)
  const [consents, setConsents] = useState<ConsentRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)
  const [isDeletingGuidance, setIsDeletingGuidance] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [isDeleteAccountOpen, setIsDeleteAccountOpen] = useState(false)
  const [isDeletingAccount, setIsDeletingAccount] = useState(false)

  // Redirect if unauthenticated
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login?redirect=/settings', { replace: true })
    }
  }, [authLoading, user, navigate])

  const loadData = useCallback(async () => {
    if (!user) return
    setLoading(true)
    setError(null)
    try {
      const [profileData, consentsData] = await Promise.all([
        api.styleProfile.get().catch(() => null),
        api.styleProfile.getConsents().catch(() => ({ consents: [] })),
      ])
      setProfile(profileData)
      setConsents(consentsData.consents || [])
    } catch (err: any) {
      setError(err?.message || 'Failed to load profile and privacy settings.')
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    if (user) {
      loadData()
    }
  }, [user, loadData])

  // Consent helpers
  const isConsentGranted = (type: string) => {
    const found = consents.find((c) => c.consent_type === type)
    return Boolean(found?.granted)
  }

  const handleToggleConsent = async (type: string, currentGranted: boolean) => {
    try {
      setActionSuccess(null)
      const updated = await api.styleProfile.setConsent(type, !currentGranted)
      setConsents((prev) => {
        const index = prev.findIndex((c) => c.consent_type === type)
        if (index >= 0) {
          const next = [...prev]
          next[index] = updated
          return next
        }
        return [...prev, updated]
      })
      setActionSuccess(`Updated ${type} consent successfully.`)
      setTimeout(() => setActionSuccess(null), 3500)
    } catch (err: any) {
      setError(err?.message || 'Failed to update consent.')
    }
  }

  // Delete Body Guidance
  const handleDeleteBodyGuidance = async () => {
    if (!confirm('Are you sure you want to delete your derived body guidance? This will not affect outfit generation.')) {
      return
    }
    setIsDeletingGuidance(true)
    try {
      await api.styleProfile.deleteBodyGuidance()
      await loadData()
      setActionSuccess('Derived body guidance deleted permanently.')
      setTimeout(() => setActionSuccess(null), 3500)
    } catch (err: any) {
      setError(err?.message || 'Failed to delete body guidance.')
    } finally {
      setIsDeletingGuidance(false)
    }
  }

  // Export JSON
  const handleExportData = async () => {
    setIsExporting(true)
    try {
      const data = await api.account.exportData()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `stylesense_data_export_${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
      setActionSuccess('Personal data archive downloaded.')
      setTimeout(() => setActionSuccess(null), 3500)
    } catch (err: any) {
      setError(err?.message || 'Failed to export account data.')
    } finally {
      setIsExporting(false)
    }
  }

  // Delete Account
  const handleDeleteAccount = async () => {
    setIsDeletingAccount(true)
    try {
      await api.account.deleteAccount()
      alert('Your StyleSense account, private wardrobe images, and style records have been permanently purged.')
      await signOut()
      navigate('/', { replace: true })
    } catch (err: any) {
      setError(err?.message || 'Failed to delete account.')
      setIsDeletingAccount(false)
    }
  }

  if (authLoading || (loading && !profile)) {
    return (
      <div className="settings-page">
        <Navigation />
        <div className="settings-loading">
          <div className="settings-spinner" />
          <p>Loading your preferences & security settings…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="settings-page">
      <Navigation />

      <main className="settings-container">
        {/* Header */}
        <header className="settings-header">
          <div className="settings-badge">
            <span>YOUR DATA</span>
          </div>
          <h1 className="settings-title">Account & privacy.</h1>
          <p className="settings-subtitle">
            Your profile, closet permissions, data export, and account controls.
          </p>
        </header>

        {/* Banners */}
        {error && (
          <div className="settings-alert-error">
            <span>{error}</span>
          </div>
        )}

        {actionSuccess && (
          <div className="settings-alert-success">
            <span>{actionSuccess}</span>
          </div>
        )}

        {/* Grid Sections */}
        <div className="settings-grid">
          {/* Section 1: Style Profile */}
          <section className="settings-card">
            <div className="settings-card-header">
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold text-foreground">Style Preferences</h2>
              </div>
              <Link to="/style-onboarding?edit=true">
                <Button size="sm" variant="outline" className="gap-1.5 text-xs">
                  Edit Preferences
                </Button>
              </Link>
            </div>

            <div className="settings-card-body space-y-4">
              <div>
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Favorite Styles
                </span>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {profile?.favorite_styles?.length ? (
                    profile.favorite_styles.map((s) => (
                      <span key={s} className="pref-tag">
                        {s}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">None selected yet.</span>
                  )}
                </div>
              </div>

              <div>
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Favorite Colors
                </span>
                <div className="flex flex-wrap gap-2 mt-1.5">
                  {profile?.favorite_colors?.length ? (
                    profile.favorite_colors.map((c) => (
                      <span key={c} className="pref-color-pill">
                        <span className="color-dot" style={{ backgroundColor: c }} />
                        <span>{c}</span>
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">None selected yet.</span>
                  )}
                </div>
              </div>

              <div>
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Preferred Occasions
                </span>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {profile?.occasions?.length ? (
                    profile.occasions.map((o) => (
                      <span key={o} className="pref-tag">
                        {o}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">None selected yet.</span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-2 border-t border-border">
                <div>
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Budget Preference
                  </span>
                  <p className="text-sm font-medium text-foreground mt-0.5">
                    {profile?.budget_max
                      ? `Up to ₹${(profile.budget_max / 100).toLocaleString('en-IN')}`
                      : 'Flexible / No limit'}
                  </p>
                </div>
                <div>
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Body Silhouette
                  </span>
                  <p className="text-sm font-medium text-foreground mt-0.5">
                    {profile?.body_type || 'Unspecified (Neutral default)'}
                  </p>
                </div>
              </div>

              {/* Derived Body Guidance */}
              {profile?.body_guidance && Object.keys(profile.body_guidance).length > 0 && (
                <div className="body-guidance-box">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-accent-foreground uppercase tracking-wider flex items-center gap-1.5">
                      Derived Body Guidance (Optional)
                    </span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleDeleteBodyGuidance}
                      disabled={isDeletingGuidance}
                      className="text-xs text-destructive hover:bg-destructive/10 h-7 px-2"
                      title="Permanently delete derived body guidance"
                    >
                      {isDeletingGuidance ? 'Deleting…' : 'Delete Guidance'}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    It helps balance cuts and silhouettes. StyleSense never stores your measurements, calculates BMI, or judges weight. You can delete it at any time.
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* Section 2: Privacy & AI Consents */}
          <section className="settings-card">
            <div className="settings-card-header">
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold text-foreground">Permissions & privacy</h2>
              </div>
              <span className="text-xs text-primary bg-secondary px-2 py-0.5 font-medium">
                PERMISSIONS APPLY IMMEDIATELY
              </span>
            </div>

            <div className="settings-card-body space-y-5">
              <p className="text-xs text-muted-foreground leading-relaxed">
                Choose whether optional external photo suggestions can use your data. You can grant or revoke these permissions at
                any time with immediate effect.
              </p>

              {/* Consent 1: Body Guidance Storage */}
              <div className="consent-item">
                <div className="consent-info">
                  <h4 className="consent-title">Save silhouette guidance</h4>
                  <p className="consent-desc">
                    Allows StyleSense to keep neutral silhouette guidance for better-matched cut suggestions.
                  </p>
                </div>
                <div className="consent-toggle">
                  <Button
                    size="sm"
                    variant={isConsentGranted('body_guidance_storage') ? 'default' : 'outline'}
                    onClick={() =>
                      handleToggleConsent('body_guidance_storage', isConsentGranted('body_guidance_storage'))
                    }
                    className={`text-xs h-8 ${
                      isConsentGranted('body_guidance_storage')
                        ? 'bg-primary hover:bg-primary/90 text-primary-foreground'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {isConsentGranted('body_guidance_storage') ? 'Allowed' : 'Not allowed'}
                  </Button>
                </div>
              </div>

              {/* Consent 2: Wardrobe Photo Analysis */}
              <div className="consent-item">
                <div className="consent-info">
                  <h4 className="consent-title">External photo tag suggestions</h4>
                  <p className="consent-desc">
                    Allows an external service to read a sanitized clothing photo and suggest tags. Only sanitized photos are
                    sent; no personal profile data or measurements are ever transmitted.
                  </p>
                </div>
                <div className="consent-toggle">
                  <Button
                    size="sm"
                    variant={isConsentGranted('wardrobe_photo_analysis') ? 'default' : 'outline'}
                    onClick={() =>
                      handleToggleConsent('wardrobe_photo_analysis', isConsentGranted('wardrobe_photo_analysis'))
                    }
                    className={`text-xs h-8 ${
                      isConsentGranted('wardrobe_photo_analysis')
                        ? 'bg-primary hover:bg-primary/90 text-primary-foreground'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {isConsentGranted('wardrobe_photo_analysis') ? 'Allowed' : 'Not allowed'}
                  </Button>
                </div>
              </div>

              {/* Privacy Notice Box */}
              <div className="privacy-guarantee-box">
                <div className="text-xs text-muted-foreground space-y-1">
                  <p>
                    <strong>Privacy facts:</strong>
                  </p>
                  <ul className="list-disc list-inside space-y-0.5">
                    <li>Body measurements and weight estimates are never stored or sent to external services.</li>
                    <li>Closet photos stay private to your account.</li>
                    <li>Looks are built from your clothes and preferences without sending them to an external service.</li>
                  </ul>
                </div>
              </div>
            </div>
          </section>

          {/* Section 3: Data Portability (GDPR Export) */}
          <section className="settings-card">
            <div className="settings-card-header">
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold text-foreground">Data Portability</h2>
              </div>
            </div>

            <div className="settings-card-body space-y-4">
              <p className="text-sm text-muted-foreground">
                Download a full copy of your rack, style preferences, saved looks, feedback, and permissions as a JSON file.
              </p>

              <div className="pt-2">
                <Button
                  onClick={handleExportData}
                  disabled={isExporting}
                  className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm"
                >
                  {isExporting ? 'Exporting Archive…' : 'Export My Data (JSON)'}
                </Button>
              </div>
            </div>
          </section>

          {/* Section 4: Account & Asset Deletion */}
          <section className="settings-card border-destructive/30">
            <div className="settings-card-header">
              <div className="flex items-center gap-2 text-destructive">
                <h2 className="text-xl font-semibold">Your account</h2>
              </div>
            </div>

            <div className="settings-card-body space-y-4">
              <p className="text-sm text-muted-foreground">
                Permanently delete your account. This action immediately purges all your private wardrobe photos,
                style profile, saved looks, and feedback history. This cannot be undone.
              </p>

              <div className="pt-2">
                <Button
                  variant="destructive"
                  onClick={() => setIsDeleteAccountOpen(true)}
                  className="gap-2 shadow-sm"
                >
                  DELETE ACCOUNT & CLOSET
                </Button>
              </div>
            </div>
          </section>
        </div>
      </main>

      <Footer />

      {/* Confirmation Modal for Account Deletion */}
      {isDeleteAccountOpen && (
        <div className="modal-backdrop">
          <div className="modal-card modal-confirm">
            <h3 className="modal-title text-destructive flex items-center gap-2">
              Permanently Delete Account?
            </h3>
            <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
              This will permanently delete your StyleSense account (<strong>{user?.email}</strong>), along with all your
              wardrobe photos, style profiles, outfits, and affinities. This action is irreversible.
            </p>
            <div className="modal-actions mt-6">
              <Button
                variant="outline"
                onClick={() => setIsDeleteAccountOpen(false)}
                disabled={isDeletingAccount}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteAccount}
                disabled={isDeletingAccount}
              >
                {isDeletingAccount ? 'Purging Everything…' : 'Yes, Delete My Account'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
