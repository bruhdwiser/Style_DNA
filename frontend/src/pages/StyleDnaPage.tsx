import React, { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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

  // Fetch preference history
  const loadDna = useCallback(async () => {
    if (!user) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.styleDna.get()
      setData(res)
    } catch (err: any) {
      setError(err?.message || 'Could not load your pattern.')
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
      setError(err?.message || 'Could not start your pattern over.')
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
            <div className="dna-badge-tag">STYLESENSE / YOUR PATTERN</div>
            <h1 className="dna-title">Your pattern.</h1>
            <p className="dna-subtitle">
              A running record of the looks you keep, wear, and skip. Every score comes from your feedback.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link to="/outfits">
              <Button variant="outline" className="gap-2">
                THE FITTING ROOM
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Main Container */}
      <div className="dna-container">
        {/* How preference history influences suggestions */}
        <div className="dna-transparency-card">
          <div>
            <h2 className="transparency-title">A small nudge, with a clear ceiling.</h2>
            <p className="transparency-text">
              Your feedback gives future looks a small nudge. Occasion, season, and fit still come first.
            </p>
          </div>
        </div>

        {error && (
          <div className="p-4 mb-6 bg-destructive/10 border border-destructive/30 text-destructive text-sm flex items-center gap-2">
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="p-12 text-center text-muted-foreground">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <span>READING YOUR PATTERN…</span>
          </div>
        ) : !data ? null : (
          <>
            {/* Feedback summary */}
            <div className="dna-metrics-grid">
              <div className="dna-metric-card">
                <div className="metric-header">
                  <span className="metric-label">Total feedback</span>
                </div>
                <div className="metric-value">{data.total_events}</div>
                <span className="text-xs text-muted-foreground">Across all your looks</span>
              </div>

              <div className="dna-metric-card">
                <div className="metric-header">
                  <span className="metric-label">Wears</span>
                </div>
                <div className="metric-value">{data.event_counts.wear}</div>
                <span className="metric-weight-tag weight-positive">Strong signal</span>
              </div>

              <div className="dna-metric-card">
                <div className="metric-header">
                  <span className="metric-label">Saves</span>
                </div>
                <div className="metric-value">{data.event_counts.save}</div>
                <span className="metric-weight-tag weight-positive">Positive signal</span>
              </div>

              <div className="dna-metric-card">
                <div className="metric-header">
                  <span className="metric-label">Likes</span>
                </div>
                <div className="metric-value">{data.event_counts.like}</div>
                <span className="metric-weight-tag weight-positive">Positive signal</span>
              </div>

              <div className="dna-metric-card">
                <div className="metric-header">
                  <span className="metric-label">Skips</span>
                </div>
                <div className="metric-value">{data.event_counts.skip}</div>
                <span className="metric-weight-tag weight-negative">Light signal</span>
              </div>

              <div className="dna-metric-card">
                <div className="metric-header">
                  <span className="metric-label">Dislikes</span>
                </div>
                <div className="metric-value">{data.event_counts.dislike}</div>
                <span className="metric-weight-tag weight-negative">Strong signal</span>
              </div>
            </div>

            {/* Top Preferences & Avoidances Section */}
            <div className="dna-split-section">
              {/* Positive Affinities */}
              <div className="preference-panel">
                <div className="panel-header">
                  <span>What you keep</span>
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
                  <span>What you skip</span>
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
                  Colours you favor
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
                  Shapes and pieces you favor
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
                  Styles you favor
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
              <div className="dna-empty-state">
                <h3 className="text-lg font-bold text-foreground mb-1">No Feedback Recorded Yet</h3>
                <p className="text-sm text-muted-foreground max-w-md mx-auto mb-4">
                    Give a few looks a quick rating in the fitting room to make your favorites clearer.
                </p>
                <Link to="/outfits">
                  <Button className="gap-2">
                  OPEN THE FITTING ROOM
                    →
                  </Button>
                </Link>
              </div>
            )}

            {/* Reset Action Footer */}
            <div className="dna-footer-actions">
              <div className="reset-warning-content">
                <div>
                  <h4 className="reset-title">Start your pattern over</h4>
                  <p className="reset-desc">
                    Clear your feedback history and return your pattern to a neutral starting point.
                  </p>
                </div>
              </div>

              <Button
                variant="destructive"
                size="sm"
                onClick={() => setResetModalOpen(true)}
                disabled={data.total_events === 0}
              >
                START OVER
              </Button>
            </div>
          </>
        )}
      </div>

      {/* Reset Confirmation Modal */}
      {resetModalOpen && (
        <div className="reset-modal-backdrop" onClick={() => setResetModalOpen(false)}>
          <div className="reset-modal" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-foreground mb-2">Start over?</h3>
            <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
              This will permanently delete all {data?.total_events || 0} feedback entries and reset your
              color, category, and style preferences.
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setResetModalOpen(false)} disabled={resetting}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={handleResetDna} disabled={resetting}>
                {resetting ? 'RESETTING…' : 'YES, START OVER'}
              </Button>
            </div>
          </div>
        </div>
      )}

      <Footer />
    </div>
  )
}
