import React, { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Shield,
  User,
  Sparkles,
  Download,
  Trash2,
  CheckCircle,
  AlertTriangle,
  Lock,
  Eye,
  RefreshCw,
  Palette,
  ExternalLink,
} from 'lucide-react'
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
      a.download = `flashfit_data_export_${new Date().toISOString().slice(0, 10)}.json`
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
      alert('Your FlashFit account, private wardrobe images, and style records have been permanently purged.')
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
            <Shield className="w-4 h-4 text-primary" />
            <span>Privacy & Profile</span>
          </div>
          <h1 className="settings-title">Account & Privacy Settings</h1>
          <p className="settings-subtitle">
            Manage your style preferences, optional AI features, data portability, and consent records.
          </p>
        </header>

        {/* Banners */}
        {error && (
          <div className="settings-alert-error">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {actionSuccess && (
          <div className="settings-alert-success">
            <CheckCircle className="w-5 h-5 flex-shrink-0" />
            <span>{actionSuccess}</span>
          </div>
        )}

        {/* Grid Sections */}
        <div className="settings-grid">
          {/* Section 1: Style Profile */}
          <section className="settings-card">
            <div className="settings-card-header">
              <div className="flex items-center gap-2">
                <Palette className="w-5 h-5 text-primary" />
                <h2 className="text-xl font-semibold text-foreground">Style Preferences</h2>
              </div>
              <Link to="/style-onboarding?edit=true">
                <Button size="sm" variant="outline" className="gap-1.5 text-xs">
                  <Sparkles className="w-3.5 h-3.5 text-accent" />
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
                      <Sparkles className="w-3.5 h-3.5" />
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
                      <Trash2 className="w-3 h-3 mr-1" />
                      {isDeletingGuidance ? 'Deleting…' : 'Delete Guidance'}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Guidance is derived entirely in memory to balance cuts and silhouettes. FlashFit never stores raw
                    measurements, calculates BMI, or judges weight. You can delete this at any time.
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* Section 2: Privacy & AI Consents */}
          <section className="settings-card">
            <div className="settings-card-header">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-emerald-500" />
                <h2 className="text-xl font-semibold text-foreground">AI & Privacy Consents</h2>
              </div>
              <span className="text-xs text-emerald-600 bg-emerald-500/10 px-2 py-0.5 rounded-full font-medium">
                Enforced by RLS
              </span>
            </div>

            <div className="settings-card-body space-y-5">
              <p className="text-xs text-muted-foreground leading-relaxed">
                Control how optional AI features interact with your data. You can grant or revoke these permissions at
                any time with immediate effect.
              </p>

              {/* Consent 1: Body Guidance Storage */}
              <div className="consent-item">
                <div className="consent-info">
                  <h4 className="consent-title">Derived Body Guidance Storage</h4>
                  <p className="consent-desc">
                    Allows FlashFit to retain neutral body silhouette guidance derived in memory to personalize cut suggestions.
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
                        ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {isConsentGranted('body_guidance_storage') ? 'Granted ✓' : 'Revoked'}
                  </Button>
                </div>
              </div>

              {/* Consent 2: Wardrobe Photo Analysis */}
              <div className="consent-item">
                <div className="consent-info">
                  <h4 className="consent-title">AI Wardrobe Photo Analysis</h4>
                  <p className="consent-desc">
                    Allows OpenRouter AI to analyze uploaded clothing photos for tag suggestions. Only sanitized photos are
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
                        ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {isConsentGranted('wardrobe_photo_analysis') ? 'Granted ✓' : 'Revoked'}
                  </Button>
                </div>
              </div>

              {/* Privacy Notice Box */}
              <div className="privacy-guarantee-box">
                <Lock className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                <div className="text-xs text-muted-foreground space-y-1">
                  <p>
                    <strong>Our Ethical AI Guarantee:</strong>
                  </p>
                  <ul className="list-disc list-inside space-y-0.5">
                    <li>No body measurements or weight estimates are ever stored or sent to AI.</li>
                    <li>Wardrobe images are strictly stored in private, user-scoped storage buckets.</li>
                    <li>Deterministic rules dominate; outfit validity is guaranteed without AI.</li>
                  </ul>
                </div>
              </div>
            </div>
          </section>

          {/* Section 3: Data Portability (GDPR Export) */}
          <section className="settings-card">
            <div className="settings-card-header">
              <div className="flex items-center gap-2">
                <Download className="w-5 h-5 text-primary" />
                <h2 className="text-xl font-semibold text-foreground">Data Portability</h2>
              </div>
            </div>

            <div className="settings-card-body space-y-4">
              <p className="text-sm text-muted-foreground">
                In compliance with GDPR and data portability standards, you can download a full copy of all your
                personal wardrobe items, styling preferences, saved outfits, events, and consents in JSON format.
              </p>

              <div className="pt-2">
                <Button
                  onClick={handleExportData}
                  disabled={isExporting}
                  className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm"
                >
                  <Download className="w-4 h-4" />
                  {isExporting ? 'Exporting Archive…' : 'Export My Data (JSON)'}
                </Button>
              </div>
            </div>
          </section>

          {/* Section 4: Account & Asset Deletion */}
          <section className="settings-card border-destructive/30">
            <div className="settings-card-header">
              <div className="flex items-center gap-2 text-destructive">
                <Trash2 className="w-5 h-5" />
                <h2 className="text-xl font-semibold">Danger Zone</h2>
              </div>
            </div>

            <div className="settings-card-body space-y-4">
              <p className="text-sm text-muted-foreground">
                Permanently delete your account. This action immediately purges all your private wardrobe photos,
                style profile, saved outfits, feedback events, and database records. This cannot be undone.
              </p>

              <div className="pt-2">
                <Button
                  variant="destructive"
                  onClick={() => setIsDeleteAccountOpen(true)}
                  className="gap-2 shadow-sm"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete Account & Purge Closet
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
              <Trash2 className="w-5 h-5" />
              Permanently Delete Account?
            </h3>
            <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
              This will permanently delete your FlashFit account (<strong>{user?.email}</strong>), along with all your
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
