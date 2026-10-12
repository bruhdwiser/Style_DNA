import React, { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Sparkles,
  ShieldCheck,
  RotateCcw,
  Heart,
  Bookmark,
  ThumbsDown,
  FastForward,
  Shirt,
  Info,
  Layers,
  ArrowRight,
  Palette,
  Tag,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/auth-context'
import { api, type StyleDnaResponse } from '@/lib/api'
import './StyleDnaPage.css'

const COLOR_HEX_MAP: Record<string, string> = {
  black: '#18181b',
  white: '#ffffff',
  navy: '#1e3a8a',
  blue: '#3b82f6',
  beige: '#d4b996',
  brown: '#78350f',
  gray: '#71717a',
  grey: '#71717a',
  green: '#15803d',
  olive: '#556b2f',
  red: '#dc2626',
  maroon: '#800000',
  pink: '#ec4899',
  purple: '#9333ea',
  yellow: '#eab308',
  mustard: '#d97706',
  orange: '#ea580c',
  rust: '#b45309',
  cream: '#fffdd0',
  gold: '#d4af37',
  silver: '#c0c0c0',
  teal: '#0d9488',
}

export default function StyleDnaPage() {
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [data, setData] = useState<StyleDnaResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [resetModalOpen, setResetModalOpen] = useState(false)
  const [resetting, setResetting] = useState(false)

  // Redirect if unauthenticated
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login?redirect=/style-dna', { replace: true })
    }
  }, [authLoading, user, navigate])

  // Fetch Style DNA
  const loadDna = useCallback(async () => {
    if (!user) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.styleDna.get()
      setData(res)
    } catch (err: any) {
      setError(err?.message || 'Failed to load Style DNA.')
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    if (user) {
      loadDna()
    }
  }, [user, loadDna])

  // Handle Reset
  const handleResetDna = async () => {
    setResetting(true)
    try {
      await api.styleDna.reset()
      setResetModalOpen(false)
      await loadDna()
    } catch (err: any) {
      setError(err?.message || 'Failed to reset Style DNA.')
    } finally {
      setResetting(false)
    }
  }

  return (
    <div className="style-dna-page">
      <Navigation />

      {/* Top Header */}
      <div className="style-dna-header">
        <div className="style-dna-header-content">
          <div>
            <div className="dna-badge-tag">
              <Sparkles className="w-3.5 h-3.5" />
              Transparent Behavioral DNA
            </div>
            <h1 className="dna-title">My Style DNA</h1>
            <p className="dna-subtitle">
              Inspect your personalized clothing and color affinities. Every score is computed
              deterministically from your feedback with mathematically bounded ranking influence.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link to="/outfits">
              <Button variant="outline" className="gap-2">
                <Layers className="w-4 h-4" />
                Outfit Studio
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Main Container */}
      <div className="dna-container">
        {/* Transparency & Bounded Influence Banner */}
        <div className="dna-transparency-card">
          <div className="transparency-icon-box">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="transparency-title">Transparent & Bounded Influence</h2>
            <p className="transparency-text">
              Style DNA uses transparent frequency counts across interactions: <strong>Wore (+3.0)</strong>,{' '}
              <strong>Saved (+2.0)</strong>, <strong>Liked (+1.0)</strong>, <strong>Skipped (-0.5)</strong>, and{' '}
              <strong>Disliked (-2.0)</strong>. Ranking adjustments are capped at a maximum of{' '}
              <strong>±{( (data?.influence_cap || 0.08) * 100).toFixed(0)}%</strong> so outfit validity,
              seasonality, and occasion formality always dominate. No opaque neural networks or computer vision.
            </p>
          </div>
        </div>

        {error && (
          <div className="p-4 mb-6 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="p-12 text-center text-muted-foreground">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <span>Loading Style DNA affinities…</span>
          </div>
        ) : !data ? null : (
          <>
            {/* Interaction Event Summary */}
            <div className="dna-metrics-grid">
              <div className="dna-metric-card">
                <div className="metric-header">
                  <span className="metric-label">Total Events</span>
                  <span className="metric-icon">📊</span>
                </div>
                <div className="metric-value">{data.total_events}</div>
                <span className="text-xs text-muted-foreground">Logged actions</span>
              </div>

              <div className="dna-metric-card">
                <div className="metric-header">
                  <span className="metric-label">Wears</span>
                  <span className="metric-icon">👔</span>
                </div>
                <div className="metric-value">{data.event_counts.wear}</div>
                <span className="metric-weight-tag weight-positive">+3.0 weight</span>
              </div>

              <div className="dna-metric-card">
                <div className="metric-header">
                  <span className="metric-label">Saves</span>
                  <span className="metric-icon">🔖</span>
                </div>
                <div className="metric-value">{data.event_counts.save}</div>
                <span className="metric-weight-tag weight-positive">+2.0 weight</span>
              </div>

              <div className="dna-metric-card">
                <div className="metric-header">
                  <span className="metric-label">Likes</span>
                  <span className="metric-icon">👍</span>
                </div>
                <div className="metric-value">{data.event_counts.like}</div>
                <span className="metric-weight-tag weight-positive">+1.0 weight</span>
              </div>

              <div className="dna-metric-card">
                <div className="metric-header">
                  <span className="metric-label">Skips</span>
                  <span className="metric-icon">⏭️</span>
                </div>
                <div className="metric-value">{data.event_counts.skip}</div>
                <span className="metric-weight-tag weight-negative">-0.5 weight</span>
              </div>

              <div className="dna-metric-card">
                <div className="metric-header">
                  <span className="metric-label">Dislikes</span>
                  <span className="metric-icon">👎</span>
                </div>
                <div className="metric-value">{data.event_counts.dislike}</div>
                <span className="metric-weight-tag weight-negative">-2.0 weight</span>
              </div>
            </div>

            {/* Top Preferences & Avoidances Section */}
            <div className="dna-split-section">
              {/* Positive Affinities */}
              <div className="preference-panel">
                <div className="panel-header">
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                  <span>Favorite Attributes</span>
                </div>
                {data.top_preferences.length > 0 ? (
                  <div className="chips-wrap">
                    {data.top_preferences.map((item, idx) => (
                      <span key={idx} className="affinity-chip fav">
                        <span className="chip-dimension-tag">{item.dimension}</span>
                        <span>{item.name}</span>
                        <span className="text-xs font-mono">({Math.round(item.score * 100)}%)</span>
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground m-0">
                    Interact with outfits in the studio (like, save, or wear) to discover your favorite styles and colors.
                  </p>
                )}
              </div>

              {/* Avoidances */}
              <div className="preference-panel">
                <div className="panel-header">
                  <ThumbsDown className="w-5 h-5 text-red-400" />
                  <span>Avoided Attributes</span>
                </div>
                {data.avoidances.length > 0 ? (
                  <div className="chips-wrap">
                    {data.avoidances.map((item, idx) => (
                      <span key={idx} className="affinity-chip avoid">
                        <span className="chip-dimension-tag">{item.dimension}</span>
                        <span>{item.name}</span>
                        <span className="text-xs font-mono">({Math.round(item.score * 100)}%)</span>
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground m-0">
                    No avoided attributes yet. Disliking or skipping outfits will deprioritize specific traits with bounded influence.
                  </p>
                )}
              </div>
            </div>

            {/* Color Affinities Gauges */}
            {data.affinities.colors && Object.keys(data.affinities.colors).length > 0 && (
              <div className="dna-gauges-section">
                <h3 className="gauges-section-title">
                  <Palette className="w-5 h-5 text-primary" />
                  Color Affinities
                </h3>
                <div className="gauges-grid">
                  {Object.entries(data.affinities.colors).map(([color, score]) => {
                    const pct = Math.round(score * 100)
                    const statusClass =
                      score >= 0.55 ? 'preferred' : score <= 0.45 ? 'avoided' : 'neutral'
                    const hex = COLOR_HEX_MAP[color.toLowerCase()] || '#71717a'

                    return (
                      <div key={color} className="gauge-row-item">
                        <div className="gauge-label-row">
                          <span className="gauge-name">
                            <span
                              className="gauge-swatch"
                              style={{ backgroundColor: hex }}
                            />
                            {color}
                          </span>
                          <span className={`gauge-score score-${statusClass}`}>{pct}%</span>
                        </div>
                        <div className="gauge-bar-track">
                          <div
                            className={`gauge-bar-fill fill-${statusClass}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Category Affinities Gauges */}
            {data.affinities.categories && Object.keys(data.affinities.categories).length > 0 && (
              <div className="dna-gauges-section">
                <h3 className="gauges-section-title">
                  <Shirt className="w-5 h-5 text-primary" />
                  Category & Silhouette Affinities
                </h3>
                <div className="gauges-grid">
                  {Object.entries(data.affinities.categories).map(([category, score]) => {
                    const pct = Math.round(score * 100)
                    const statusClass =
                      score >= 0.55 ? 'preferred' : score <= 0.45 ? 'avoided' : 'neutral'

                    return (
                      <div key={category} className="gauge-row-item">
                        <div className="gauge-label-row">
                          <span className="gauge-name">{category.replace(/_/g, ' ')}</span>
                          <span className={`gauge-score score-${statusClass}`}>{pct}%</span>
                        </div>
                        <div className="gauge-bar-track">
                          <div
                            className={`gauge-bar-fill fill-${statusClass}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Style Tag Affinities Gauges */}
            {data.affinities.styles && Object.keys(data.affinities.styles).length > 0 && (
              <div className="dna-gauges-section">
                <h3 className="gauges-section-title">
                  <Tag className="w-5 h-5 text-primary" />
                  Style & Aesthetic Affinities
                </h3>
                <div className="gauges-grid">
                  {Object.entries(data.affinities.styles).map(([style, score]) => {
                    const pct = Math.round(score * 100)
                    const statusClass =
                      score >= 0.55 ? 'preferred' : score <= 0.45 ? 'avoided' : 'neutral'

                    return (
                      <div key={style} className="gauge-row-item">
                        <div className="gauge-label-row">
                          <span className="gauge-name">{style.replace(/_/g, ' ')}</span>
                          <span className={`gauge-score score-${statusClass}`}>{pct}%</span>
                        </div>
                        <div className="gauge-bar-track">
                          <div
                            className={`gauge-bar-fill fill-${statusClass}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Empty state when no events yet */}
            {data.total_events === 0 && (
              <div className="p-10 text-center rounded-xl bg-zinc-900/40 border border-zinc-800 mb-8">
                <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mx-auto mb-3">
                  <Sparkles className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-bold text-foreground mb-1">No Feedback Recorded Yet</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto mb-4">
                  Generate outfits in the studio and give feedback (like, dislike, save, wear) to train
                  your transparent Style DNA.
                </p>
                <Link to="/outfits">
                  <Button className="gap-2">
                    Open Outfit Studio
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
              </div>
            )}

            {/* Reset Action Footer */}
            <div className="dna-footer-actions">
              <div className="reset-warning-content">
                <RotateCcw className="w-5 h-5 text-destructive flex-shrink-0" />
                <div>
                  <h4 className="reset-title">Reset Style DNA</h4>
                  <p className="reset-desc">
                    Clear all recorded events and restore all affinities to neutral 50%.
                  </p>
                </div>
              </div>

              <Button
                variant="destructive"
                size="sm"
                onClick={() => setResetModalOpen(true)}
                disabled={data.total_events === 0}
              >
                Reset All Affinities
              </Button>
            </div>
          </>
        )}
      </div>

      {/* Reset Confirmation Modal */}
      {resetModalOpen && (
        <div className="reset-modal-backdrop" onClick={() => setResetModalOpen(false)}>
          <div className="reset-modal" onClick={(e) => e.stopPropagation()}>
            <div className="w-12 h-12 rounded-xl bg-destructive/10 text-destructive flex items-center justify-center mb-4">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-foreground mb-2">Reset Style DNA?</h3>
            <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
              This will permanently delete all {data?.total_events || 0} interaction events and reset your
              color, category, and style affinities back to neutral.
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setResetModalOpen(false)} disabled={resetting}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleResetDna} disabled={resetting}>
                {resetting ? 'Resetting…' : 'Yes, Reset Style DNA'}
              </Button>
            </div>
          </div>
        </div>
      )}

      <Footer />
    </div>
  )
}
