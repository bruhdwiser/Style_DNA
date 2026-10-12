import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/auth-context'
import { api } from '@/lib/api'
import type { StyleProfileUpdate, StyleProfileResponse } from '@/lib/api'
import './StyleOnboardingPage.css'

// -------------------------------------------------------------------------
// Option data
// -------------------------------------------------------------------------
const STYLE_OPTIONS = [
  { id: 'minimal', label: 'Minimal', emoji: '🤍' },
  { id: 'classic', label: 'Classic', emoji: '👔' },
  { id: 'traditional', label: 'Traditional', emoji: '🪷' },
  { id: 'streetwear', label: 'Streetwear', emoji: '🧢' },
  { id: 'bohemian', label: 'Bohemian', emoji: '🌿' },
  { id: 'elegant', label: 'Elegant', emoji: '✨' },
  { id: 'romantic', label: 'Romantic', emoji: '🌹' },
  { id: 'casual', label: 'Casual', emoji: '👕' },
  { id: 'trend', label: 'Trendy', emoji: '🔥' },
]

const COLOR_OPTIONS = [
  { id: 'black', label: 'Black', hex: '#1a1a1a' },
  { id: 'white', label: 'White', hex: '#fafafa' },
  { id: 'navy', label: 'Navy', hex: '#1e3a5f' },
  { id: 'burgundy', label: 'Burgundy', hex: '#722f37' },
  { id: 'blush', label: 'Blush', hex: '#de9e9e' },
  { id: 'sage', label: 'Sage', hex: '#9caf88' },
  { id: 'mustard', label: 'Mustard', hex: '#d4a843' },
  { id: 'teal', label: 'Teal', hex: '#2e8b8b' },
  { id: 'ivory', label: 'Ivory', hex: '#f5f0e1' },
  { id: 'coral', label: 'Coral', hex: '#e8705a' },
  { id: 'lavender', label: 'Lavender', hex: '#b39ddb' },
  { id: 'olive', label: 'Olive', hex: '#6b7c3e' },
]

const OCCASION_OPTIONS = [
  { id: 'casual', label: 'Casual', emoji: '☕' },
  { id: 'date', label: 'Date Night', emoji: '🍷' },
  { id: 'work', label: 'Work', emoji: '💼' },
  { id: 'college', label: 'College', emoji: '🎓' },
  { id: 'party', label: 'Party', emoji: '🎉' },
  { id: 'formal', label: 'Formal', emoji: '🥂' },
  { id: 'festive', label: 'Festive', emoji: '🪔' },
  { id: 'wedding', label: 'Wedding', emoji: '💍' },
  { id: 'lounge', label: 'Lounge', emoji: '🛋️' },
]

const BODY_TYPE_OPTIONS = [
  { id: 'Hourglass', label: 'Hourglass', description: 'Balanced bust and hips, defined waist' },
  { id: 'Pear', label: 'Pear', description: 'Hips wider than shoulders' },
  { id: 'Rectangle', label: 'Rectangle', description: 'Balanced proportions throughout' },
  { id: 'Inverted Triangle', label: 'Inverted Triangle', description: 'Shoulders wider than hips' },
  { id: 'Apple', label: 'Apple', description: 'Fuller midsection' },
]

type Step = 'styles' | 'colors' | 'occasions' | 'budget' | 'body' | 'done'
const STEPS: Step[] = ['styles', 'colors', 'occasions', 'budget', 'body']

export default function StyleOnboardingPage() {
  const { user, session, loading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [currentStep, setCurrentStep] = useState(0)
  const [saving, setSaving] = useState(false)
  const [loadingProfile, setLoadingProfile] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [selectedStyles, setSelectedStyles] = useState<string[]>([])
  const [selectedColors, setSelectedColors] = useState<string[]>([])
  const [selectedOccasions, setSelectedOccasions] = useState<string[]>([])
  const [budgetMin, setBudgetMin] = useState<string>('')
  const [budgetMax, setBudgetMax] = useState<string>('')
  const [bodyType, setBodyType] = useState<string | null>(null)
  const [bodyConsent, setBodyConsent] = useState(false)

  const isEditing = new URLSearchParams(window.location.search).get('edit') === 'true'

  // Load existing profile
  useEffect(() => {
    if (authLoading) return
    if (!session) {
      navigate('/login', { replace: true })
      return
    }

    const loadProfile = async () => {
      try {
        const profile: StyleProfileResponse = await api.styleProfile.get()
        if (profile.onboarding_complete && !isEditing) {
          navigate('/', { replace: true })
          return
        }
        // Pre-fill from existing data
        if (profile.favorite_styles.length) setSelectedStyles(profile.favorite_styles)
        if (profile.favorite_colors.length) setSelectedColors(profile.favorite_colors)
        if (profile.occasions.length) setSelectedOccasions(profile.occasions)
        if (profile.budget_min !== null) setBudgetMin(String(profile.budget_min / 100))
        if (profile.budget_max !== null) setBudgetMax(String(profile.budget_max / 100))
        if (profile.body_type) setBodyType(profile.body_type)
      } catch {
        // No profile yet — fine, start fresh
      } finally {
        setLoadingProfile(false)
      }
    }
    loadProfile()
  }, [authLoading, session, navigate, isEditing])

  const toggleItem = useCallback(
    (list: string[], setList: React.Dispatch<React.SetStateAction<string[]>>, id: string) => {
      setList((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
    },
    []
  )

  const stepName = STEPS[currentStep]
  const isLast = currentStep === STEPS.length - 1

  const handleNext = () => {
    if (isLast) {
      handleSave()
    } else {
      setCurrentStep((s) => Math.min(s + 1, STEPS.length - 1))
    }
  }

  const handleBack = () => setCurrentStep((s) => Math.max(s - 1, 0))

  const handleSkipOnboarding = async () => {
    setSaving(true)
    setError(null)
    try {
      await api.styleProfile.update({ onboarding_complete: true })
      navigate(isEditing ? '/settings' : '/', { replace: true })
    } catch (err: any) {
      setError(err?.message || 'Failed to skip onboarding')
    } finally {
      setSaving(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      // Grant or revoke body guidance consent
      if (bodyType && bodyConsent) {
        await api.styleProfile.setConsent('body_guidance_storage', true)
      }

      const payload: StyleProfileUpdate = {
        favorite_styles: selectedStyles,
        favorite_colors: selectedColors,
        occasions: selectedOccasions,
        budget_min: budgetMin ? Math.round(parseFloat(budgetMin) * 100) : null,
        budget_max: budgetMax ? Math.round(parseFloat(budgetMax) * 100) : null,
        body_type: bodyType || null,
        onboarding_complete: true,
      }
      await api.styleProfile.update(payload)
      navigate(isEditing ? '/settings' : '/', { replace: true })
    } catch (err: any) {
      setError(err?.message || 'Failed to save profile')
    } finally {
      setSaving(false)
    }
  }

  if (authLoading || loadingProfile) {
    return (
      <div className="onboarding-loading">
        <div className="onboarding-spinner" />
        <p>Loading your style profile…</p>
      </div>
    )
  }

  return (
    <div className="onboarding-container">
      <div className="onboarding-card">
        {/* Header */}
        <div className="onboarding-header">
          <h1 className="onboarding-title">
            {isEditing ? '🎨 Edit Style Preferences' : '✨ Style Profile'}
          </h1>
          <p className="onboarding-subtitle">
            {isEditing
              ? 'Update your aesthetic preferences, occasions, and budget settings.'
              : 'Tell us what you love so we can curate your perfect outfits'}
          </p>
          <button
            className="onboarding-skip-link"
            onClick={handleSkipOnboarding}
            disabled={saving}
          >
            {isEditing ? 'Cancel & Return →' : 'Skip for now →'}
          </button>
        </div>

        {/* Progress */}
        <div className="onboarding-progress">
          {STEPS.map((s, i) => (
            <div
              key={s}
              className={`onboarding-progress-dot ${i <= currentStep ? 'active' : ''} ${
                i < currentStep ? 'completed' : ''
              }`}
              onClick={() => setCurrentStep(i)}
            />
          ))}
        </div>

        {/* Step Content */}
        <div className="onboarding-step">
          {stepName === 'styles' && (
            <StepSection title="What's your vibe?" subtitle="Pick styles that speak to you">
              <div className="onboarding-chips">
                {STYLE_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    className={`onboarding-chip ${selectedStyles.includes(opt.id) ? 'selected' : ''}`}
                    onClick={() => toggleItem(selectedStyles, setSelectedStyles, opt.id)}
                  >
                    <span className="chip-emoji">{opt.emoji}</span>
                    <span className="chip-label">{opt.label}</span>
                  </button>
                ))}
              </div>
            </StepSection>
          )}

          {stepName === 'colors' && (
            <StepSection title="Favourite colours" subtitle="Pick the shades that make you smile">
              <div className="onboarding-colors">
                {COLOR_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    className={`onboarding-color-btn ${selectedColors.includes(opt.id) ? 'selected' : ''}`}
                    onClick={() => toggleItem(selectedColors, setSelectedColors, opt.id)}
                    title={opt.label}
                  >
                    <span
                      className="color-swatch"
                      style={{ backgroundColor: opt.hex }}
                    />
                    <span className="color-name">{opt.label}</span>
                  </button>
                ))}
              </div>
            </StepSection>
          )}

          {stepName === 'occasions' && (
            <StepSection title="Dress for…" subtitle="Where do you need outfits?">
              <div className="onboarding-chips">
                {OCCASION_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    className={`onboarding-chip ${selectedOccasions.includes(opt.id) ? 'selected' : ''}`}
                    onClick={() => toggleItem(selectedOccasions, setSelectedOccasions, opt.id)}
                  >
                    <span className="chip-emoji">{opt.emoji}</span>
                    <span className="chip-label">{opt.label}</span>
                  </button>
                ))}
              </div>
            </StepSection>
          )}

          {stepName === 'budget' && (
            <StepSection title="Budget range" subtitle="Optional — helps us pick the right items (₹ INR)">
              <div className="onboarding-budget">
                <div className="budget-field">
                  <label htmlFor="budget-min">Min ₹</label>
                  <input
                    id="budget-min"
                    type="number"
                    min="0"
                    placeholder="e.g. 500"
                    value={budgetMin}
                    onChange={(e) => setBudgetMin(e.target.value)}
                  />
                </div>
                <span className="budget-separator">—</span>
                <div className="budget-field">
                  <label htmlFor="budget-max">Max ₹</label>
                  <input
                    id="budget-max"
                    type="number"
                    min="0"
                    placeholder="e.g. 5000"
                    value={budgetMax}
                    onChange={(e) => setBudgetMax(e.target.value)}
                  />
                </div>
              </div>
            </StepSection>
          )}

          {stepName === 'body' && (
            <StepSection
              title="Body type"
              subtitle="Completely optional — helps us suggest flattering fits. You can change or remove this anytime."
            >
              <div className="onboarding-body-types">
                {BODY_TYPE_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    className={`body-type-card ${bodyType === opt.id ? 'selected' : ''}`}
                    onClick={() => setBodyType((prev) => (prev === opt.id ? null : opt.id))}
                  >
                    <span className="body-type-label">{opt.label}</span>
                    <span className="body-type-desc">{opt.description}</span>
                  </button>
                ))}
              </div>

              {bodyType && (
                <div className="consent-section">
                  <label className="consent-label">
                    <input
                      type="checkbox"
                      checked={bodyConsent}
                      onChange={(e) => setBodyConsent(e.target.checked)}
                    />
                    <span>
                      Store body-fit guidance for future outfits.{' '}
                      <em>You can revoke this and delete your data anytime in settings.</em>
                    </span>
                  </label>
                </div>
              )}

              <p className="body-note">
                We never store raw measurements, calculate BMI, or make judgments.
                Body type only helps us suggest better silhouettes.
              </p>
            </StepSection>
          )}
        </div>

        {/* Error */}
        {error && <div className="onboarding-error">{error}</div>}

        {/* Navigation */}
        <div className="onboarding-nav">
          {currentStep > 0 && (
            <button className="nav-btn nav-back" onClick={handleBack} disabled={saving}>
              ← Back
            </button>
          )}
          <button
            className="nav-btn nav-next"
            onClick={handleNext}
            disabled={saving}
          >
            {saving ? 'Saving…' : isLast ? 'Finish ✨' : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  )
}

// -------------------------------------------------------------------------
// Reusable step wrapper
// -------------------------------------------------------------------------
function StepSection({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <div className="step-section">
      <h2 className="step-title">{title}</h2>
      <p className="step-subtitle">{subtitle}</p>
      {children}
    </div>
  )
}
