import React, { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/auth-context'
import { useCart } from '@/contexts/cart-context'
import {
  api,
  APPROVED_OUTFIT_TAGS,
  type OutfitResponse,
  type GenerateOutfitsResponse,
  type WardrobeCoverageResponse,
  type OutfitEventType,
  type GapAnalysisResponse,
} from '@/lib/api'
import './OutfitsPage.css'

// ---------------------------------------------------------------------------
// Constants & Options
// ---------------------------------------------------------------------------

const OCCASIONS = [
  { id: 'casual', label: 'Casual' },
  { id: 'date', label: 'Date Night / Romantic' },
  { id: 'work', label: 'Work / Office' },
  { id: 'party', label: 'Party / Night Out' },
  { id: 'formal', label: 'Formal' },
  { id: 'festive', label: 'Festive / Traditional' },
  { id: 'wedding', label: 'Wedding' },
  { id: 'college', label: 'College / Campus' },
  { id: 'lounge', label: 'Lounge / Relaxed' },
]

const VIBES = [
  { id: '', label: 'Any Vibe' },
  { id: 'romantic', label: 'Romantic' },
  { id: 'elegant', label: 'Elegant' },
  { id: 'classic', label: 'Classic' },
  { id: 'minimal', label: 'Minimal' },
  { id: 'bohemian', label: 'Bohemian' },
  { id: 'streetwear', label: 'Streetwear' },
]

const SEASONS = [
  { id: 'all_season', label: 'All Season' },
  { id: 'summer', label: 'Summer' },
  { id: 'winter', label: 'Winter' },
  { id: 'monsoon', label: 'Monsoon' },
]

const SKELETON_LABELS: Record<string, string> = {
  top_bottom: 'Top + Bottom',
  dress: 'One-Piece Dress',
  saree: 'Traditional Saree',
  ethnic_set: 'Ethnic Kurta Set',
  formal_suit: 'Formal Suit',
}

export default function OutfitsPage() {
  const { user, loading: authLoading } = useAuth()
  const { addToCart } = useCart()
  const navigate = useNavigate()

  // Tab State
  const [activeTab, setActiveTab] = useState<'studio' | 'saved' | 'gaps'>('studio')

  // Generator Inputs
  const [occasion, setOccasion] = useState('casual')
  const [vibe, setVibe] = useState('')
  const [season, setSeason] = useState('all_season')
  const [limit, setLimit] = useState(6)
  const [wardrobeOnly, setWardrobeOnly] = useState(false)
  const [budgetMax, setBudgetMax] = useState<string>('')

  // Outfits State
  const [generating, setGenerating] = useState(false)
  const [generationResponse, setGenerationResponse] = useState<GenerateOutfitsResponse | null>(null)
  const [generationError, setGenerationError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [savedOutfits, setSavedOutfits] = useState<OutfitResponse[]>([])
  const [loadingSaved, setLoadingSaved] = useState(false)
  const [savingOutfitIds, setSavingOutfitIds] = useState<Set<string>>(new Set())
  const [_coverage, setCoverage] = useState<WardrobeCoverageResponse | null>(null)
  const [profileWarning, setProfileWarning] = useState<string | null>(null)

  // Saved Outfits Tag Filtering & Editing State
  const [selectedSavedTag, setSelectedSavedTag] = useState<string>('All')
  const [_availableSavedTags, setAvailableSavedTags] = useState<string[]>([])
  const [tagModalOutfit, setTagModalOutfit] = useState<OutfitResponse | null>(null)
  const [modalTags, setModalTags] = useState<string[]>(['Try Later'])
  const [modalSubmitting, setModalSubmitting] = useState(false)

  // Gaps State
  const [gapsResponse, setGapsResponse] = useState<GapAnalysisResponse | null>(null)
  const [loadingGaps, setLoadingGaps] = useState(false)

  // Redirect if unauthenticated
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login?redirect=/outfits', { replace: true })
    }
  }, [authLoading, user, navigate])

  // Initial check: load coverage & style profile to detect missing state
  useEffect(() => {
    if (!user) return

    api.wardrobe
      .coverage()
      .then((cov) => setCoverage(cov))
      .catch((err) => console.debug('Coverage check failed:', err))

    api.styleProfile
      .get()
      .then((prof: any) => {
        if (!prof?.onboarding_complete) {
          setProfileWarning(
            'Your style profile is incomplete. Outfits will use neutral styling defaults until configured.'
          )
        }
      })
      .catch(() => {
        setProfileWarning(
          'Your style profile is not set up. Outfits will use neutral styling defaults.'
        )
      })
  }, [user])

  // Load saved looks with optional tag filtering
  const loadSavedOutfits = useCallback(async (tagFilter?: string) => {
    if (!user) return
    setLoadingSaved(true)
    const activeTag = tagFilter !== undefined ? tagFilter : selectedSavedTag
    try {
      const res = await api.outfits.getSaved(activeTag === 'All' ? undefined : activeTag)
      setSavedOutfits(res.outfits || [])
      if (res.available_tags) {
        setAvailableSavedTags(res.available_tags)
      }
    } catch (err: any) {
      console.error('Failed to load saved outfits:', err)
      setActionError(err?.message || 'Failed to load saved outfits.')
    } finally {
      setLoadingSaved(false)
    }
  }, [user, selectedSavedTag])

  // Load counterfactual gaps
  const loadGaps = useCallback(async () => {
    if (!user) return
    setLoadingGaps(true)
    try {
      const res = await api.gaps.list({
        occasion: occasion || undefined,
        budgetMax: budgetMax ? Number(budgetMax) : undefined,
      })
      setGapsResponse(res)
    } catch (err: any) {
      console.error('Failed to load wardrobe gaps:', err)
    } finally {
      setLoadingGaps(false)
    }
  }, [user, occasion, budgetMax])

  useEffect(() => {
    if (activeTab === 'saved') {
      loadSavedOutfits()
    } else if (activeTab === 'gaps') {
      loadGaps()
    }
  }, [activeTab, loadSavedOutfits, loadGaps])

  // Generate Outfits Handler (Deterministic normal generator, or shuffle with previous screen signatures)
  const handleGenerate = async (isShuffle = false) => {
    if (!user) return
    setGenerating(true)
    setGenerationError(null)
    setActionError(null)

    try {
      let currentSignatures: [string, string][][] | undefined = undefined
      if (isShuffle && generationResponse?.outfits) {
        currentSignatures = generationResponse.outfits
          .map((o) => o.core_signature)
          .filter((sig): sig is [string, string][] => Array.isArray(sig) && sig.length > 0)
      }

      const res = await api.outfits.generate({
        occasion,
        vibe: vibe || undefined,
        season,
        limit,
        wardrobe_only: wardrobeOnly,
        budget_max: !wardrobeOnly && budgetMax ? Number(budgetMax) : undefined,
        is_shuffle: isShuffle,
        exclude_core_signatures: currentSignatures && currentSignatures.length > 0 ? currentSignatures : undefined,
      })

      setGenerationResponse(res)
      if (res.profile_warning) {
        setProfileWarning(res.profile_warning)
      }
    } catch (err: any) {
      console.error('Outfit generation failed:', err)
      setGenerationError(err?.message || 'Failed to generate outfits. Please check your connection and try again.')
      // Never show stale outfits or false success on hard failure
      setGenerationResponse(null)
    } finally {
      setGenerating(false)
    }
  }

  // Open tag selector modal for saving an outfit or editing tags
  const handleOpenTagModal = (outfit: OutfitResponse) => {
    setTagModalOutfit(outfit)
    const initialTags = outfit.tags && outfit.tags.length > 0 ? outfit.tags : ['Try Later']
    setModalTags(initialTags)
  }

  // Save or update tags with optimistic UI update and rollback on failure
  const handleConfirmSaveTags = async () => {
    if (!tagModalOutfit) return
    const outfit = tagModalOutfit
    const outfitId = outfit.id
    const isCurrentlySaved = outfit.is_saved
    const chosenTags = modalTags.length > 0 ? modalTags : ['Try Later']

    setModalSubmitting(true)
    setActionError(null)

    // Optimistic UI updates
    if (generationResponse) {
      setGenerationResponse({
        ...generationResponse,
        outfits: generationResponse.outfits.map((o) =>
          o.id === outfitId ? { ...o, is_saved: true, tags: chosenTags } : o
        ),
      })
    }
    setSavedOutfits((prev) => {
      const exists = prev.some((o) => o.id === outfitId)
      if (exists) {
        return prev.map((o) => (o.id === outfitId ? { ...o, is_saved: true, tags: chosenTags } : o))
      }
      return [{ ...outfit, is_saved: true, tags: chosenTags }, ...prev]
    })

    try {
      if (isCurrentlySaved) {
        await api.outfits.updateTags(outfitId, chosenTags)
      } else {
        await api.outfits.save(outfitId, chosenTags)
      }
      setTagModalOutfit(null)
    } catch (err: any) {
      console.error('Save/Update tags failed:', err)
      // Revert optimistic update
      if (generationResponse) {
        setGenerationResponse({
          ...generationResponse,
          outfits: generationResponse.outfits.map((o) =>
            o.id === outfitId ? { ...o, is_saved: isCurrentlySaved, tags: outfit.tags || [] } : o
          ),
        })
      }
      if (activeTab === 'saved') {
        loadSavedOutfits()
      }
      setActionError(err?.message || 'Failed to save outfit tags. Please try again.')
    } finally {
      setModalSubmitting(false)
    }
  }

  // Explicit Unsave with optimistic update and rollback on failure
  const handleUnsave = async (outfit: OutfitResponse) => {
    const outfitId = outfit.id
    setSavingOutfitIds((prev) => new Set(prev).add(outfitId))
    setActionError(null)

    // Optimistic update
    if (generationResponse) {
      setGenerationResponse({
        ...generationResponse,
        outfits: generationResponse.outfits.map((o) =>
          o.id === outfitId ? { ...o, is_saved: false, tags: [] } : o
        ),
      })
    }
    setSavedOutfits((prev) => prev.filter((o) => o.id !== outfitId))

    try {
      await api.outfits.unsave(outfitId)
    } catch (err: any) {
      console.error('Unsave failed:', err)
      if (generationResponse) {
        setGenerationResponse({
          ...generationResponse,
          outfits: generationResponse.outfits.map((o) =>
            o.id === outfitId ? { ...o, is_saved: true, tags: outfit.tags || [] } : o
          ),
        })
      }
      if (activeTab === 'saved') {
        loadSavedOutfits()
      }
      setActionError(err?.message || 'Failed to remove look from saved. Please try again.')
    } finally {
      setSavingOutfitIds((prev) => {
        const next = new Set(prev)
        next.delete(outfitId)
        return next
      })
    }
  }

  // Handle "Not For Me" dislike event side-effect (clearing saved status and tags)
  const handleOutfitDisliked = (outfitId: string) => {
    if (generationResponse) {
      setGenerationResponse({
        ...generationResponse,
        outfits: generationResponse.outfits.map((o) =>
          o.id === outfitId ? { ...o, is_saved: false, tags: [] } : o
        ),
      })
    }
    setSavedOutfits((prev) => prev.filter((o) => o.id !== outfitId))
  }

  // Handle Tag Filter selection in Saved Looks tab
  const handleSelectFilterTag = (tag: string) => {
    setSelectedSavedTag(tag)
    loadSavedOutfits(tag)
  }

  return (
    <div className="outfits-page">
      <Navigation />

      {/* Header */}
      <div className="outfits-header">
        <div className="outfits-header-content">
          <div>
            <div className="outfits-badge-tag">STYLESENSE / THE FITTING ROOM</div>
            <h1 className="outfits-title">The fitting room.</h1>
            <p className="outfits-subtitle">
              Start with the plan. We’ll pull looks from your rack and show why they work.
            </p>
          </div>

          {/* Tab Switcher */}
          <div className="outfits-tabs-bar">
            <button
              className={`outfits-tab-btn ${activeTab === 'studio' ? 'active' : ''}`}
              onClick={() => setActiveTab('studio')}
            >
              BUILD
            </button>
            <button
              className={`outfits-tab-btn ${activeTab === 'saved' ? 'active' : ''}`}
              onClick={() => setActiveTab('saved')}
            >
              Saved Looks
              {savedOutfits.length > 0 && (
                <span className="tab-badge">{savedOutfits.length}</span>
              )}
            </button>
            <button
              className={`outfits-tab-btn ${activeTab === 'gaps' ? 'active' : ''}`}
              onClick={() => setActiveTab('gaps')}
            >
              GAPS
            </button>
            <Link to="/style-dna">
              <button className="outfits-tab-btn" type="button" title="View your preference pattern">
                YOUR PATTERN
              </button>
            </Link>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className={`outfits-container ${activeTab === 'studio' ? '' : 'single-column'}`}>
        {/* Visible Action Error Banner */}
        {actionError && (
          <div className="outfits-action-error-banner" role="alert">
            <div className="error-banner-content">
              <strong>Action Failed:</strong> <span>{actionError}</span>
            </div>
            <button
              type="button"
              className="error-dismiss-btn"
              onClick={() => setActionError(null)}
              title="Dismiss"
            >
              ✕
            </button>
          </div>
        )}

        {/* Visible Generation Error Banner */}
        {generationError && (
          <div className="outfits-action-error-banner" role="alert">
            <div className="error-banner-content">
              <strong>Generation Error:</strong> <span>{generationError}</span>
            </div>
            <button
              type="button"
              className="error-dismiss-btn"
              onClick={() => setGenerationError(null)}
              title="Dismiss"
            >
              ✕
            </button>
          </div>
        )}

        {/* Style Profile Warning (Non-blocking) */}
        {profileWarning && (
          <div className="outfits-warning-banner">
            <div className="warning-banner-content">
              <span>{profileWarning}</span>
            </div>
            <Link to="/style-onboarding" className="warning-action-link">
              SET THE BRIEF
              →
            </Link>
          </div>
        )}

        {/* Studio View */}
        {activeTab === 'studio' && (
          <>
            {/* Generator Brief Controls */}
            <div className="generator-controls-card">
              <div className="controls-section-title">
                WHAT’S THE PLAN?
              </div>

              {/* Occasion Chips */}
              <div className="chip-grid">
                {OCCASIONS.map((occ) => (
                  <button
                    key={occ.id}
                    type="button"
                    className={`control-chip ${occasion === occ.id ? 'selected' : ''}`}
                    onClick={() => setOccasion(occ.id)}
                  >
                    <span>{occ.label}</span>
                  </button>
                ))}
              </div>

              {/* Secondary Options Grid */}
              <div className="controls-secondary-row">
                {/* Vibe Selection */}
                <div className="control-field-group">
                  <label className="control-field-label">Style direction</label>
                  <select
                    className="control-select"
                    value={vibe}
                    onChange={(e) => setVibe(e.target.value)}
                  >
                    {VIBES.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Season Selection */}
                <div className="control-field-group">
                  <label className="control-field-label">Season Context</label>
                  <select
                    className="control-select"
                    value={season}
                    onChange={(e) => setSeason(e.target.value)}
                  >
                    {SEASONS.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Outfit Count */}
                <div className="control-field-group">
                  <label className="control-field-label">Outfits to Generate</label>
                  <select
                    className="control-select"
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                  >
                    <option value={3}>3 Outfits</option>
                    <option value={6}>6 Outfits</option>
                    <option value={9}>9 Outfits</option>
                  </select>
                </div>

                {/* Sole Opt-Out: Use Only My Rack Toggle (Default Off) */}
                <div
                  className="toggle-field"
                  onClick={() => setWardrobeOnly(!wardrobeOnly)}
                  title="Keep every look strictly to pieces already on your rack"
                >
                  <div className="toggle-field-label">
                    <span className="toggle-title">Use only my rack</span>
                    <span className="toggle-desc">
                      {wardrobeOnly
                        ? 'Rack only: store pieces strictly disabled'
                        : 'Store completion enabled: 1 shop piece may fill shortfalls'}
                    </span>
                  </div>
                  <div className={`toggle-switch ${wardrobeOnly ? 'checked' : ''}`}>
                    <div className="toggle-knob" />
                  </div>
                </div>

                {/* Optional Budget Limit (active only when wardrobeOnly is false) */}
                {!wardrobeOnly ? (
                  <div className="control-field-group">
                    <label className="control-field-label">Max Item Budget (₹ INR)</label>
                    <input
                      type="number"
                      placeholder="e.g. 2500"
                      className="control-select"
                      value={budgetMax}
                      onChange={(e) => setBudgetMax(e.target.value)}
                      min={100}
                      step={100}
                    />
                  </div>
                ) : (
                  <div className="control-field-group">
                    <label className="control-field-label text-muted-foreground">Max Item Budget</label>
                    <div className="budget-disabled-note">
                      Store pieces disabled while rack-only mode is active.
                    </div>
                  </div>
                )}
              </div>

              {/* Action Bar */}
              <div className="controls-action-bar">
                <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <span className="eyebrow">METHOD /</span>
                  <span>
                    Every look starts with your rack and the plan you set.
                  </span>
                </div>

                <button
                  type="button"
                  className="btn-generate-outfits"
                  onClick={() => handleGenerate(false)}
                  disabled={generating}
                >
                  {generating ? (
                    <>
                      Evaluating Combinations…
                    </>
                  ) : (
                    <>
                      PULL LOOKS
                    </>
                  )}
                </button>

                {generationResponse?.outfits && generationResponse.outfits.length > 0 && (
                  <button
                    type="button"
                    className="btn-shuffle-outfits"
                    onClick={() => handleGenerate(true)}
                    disabled={generating}
                    title="Generate alternative combinations excluding current looks"
                  >
                    <span>↻</span>
                    <span>SHUFFLE ALTERNATIVES</span>
                  </button>
                )}
              </div>
            </div>

            {/* Action Error Banner (Save or Feedback failures) */}
            {actionError && (
              <div className="outfits-action-error-banner">
                <span>{actionError}</span>
                <button
                  type="button"
                  onClick={() => setActionError(null)}
                  className="action-error-dismiss"
                  aria-label="Dismiss error"
                >
                  ✕
                </button>
              </div>
            )}

            {/* Results / Status Rendering */}
            {generating && (
              <div className="outfits-empty-card">
                <h3 className="empty-state-title">Putting looks together.</h3>
                <p className="empty-state-desc">
                  Checking your occasion, style direction, and season against your rack…
                </p>
              </div>
            )}

            {/* Hard Error State */}
            {!generating && generationError && (
              <div className="outfits-empty-card error-state">
                <h3 className="empty-state-title">Could not generate looks.</h3>
                <p className="empty-state-desc">{generationError}</p>
                <Button
                  onClick={() => handleGenerate(false)}
                  className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground"
                >
                  Retry Generation →
                </Button>
              </div>
            )}

            {!generating && generationResponse?.status === 'empty_wardrobe' && (
              <div className="outfits-empty-card">
                <h3 className="empty-state-title">Your rack is empty.</h3>
                <p className="empty-state-desc">
                  {generationResponse.message ||
                    'Add a few pieces to your rack before we can put a look together.'}
                </p>
                <Link to="/wardrobe">
                  <Button className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground">
                    Go to Wardrobe to Add Clothes
                    →
                  </Button>
                </Link>
              </div>
            )}

            {!generating && generationResponse?.status === 'missing_required_slots' && (
              <div className="outfits-empty-card">
                <h3 className="empty-state-title">Missing Required Clothing Pieces</h3>
                <p className="empty-state-desc">
                  {generationResponse.message ||
                    'Your wardrobe is missing core slots required to build complete looks for this occasion.'}
                </p>
                {generationResponse.missing_slots && generationResponse.missing_slots.length > 0 && (
                  <div className="missing-slots-pills">
                    {generationResponse.missing_slots.map((s) => (
                      <span key={s} className="missing-slot-pill">
                        Missing: {s.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                )}
                <Link to="/wardrobe">
                  <Button className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground">
                    Add Required Pieces in Wardrobe
                    →
                  </Button>
                </Link>
              </div>
            )}

            {!generating && generationResponse?.status === 'no_matching_combinations' && (
              <div className="outfits-empty-card">
                <h3 className="empty-state-title">No Combinations Found</h3>
                <p className="empty-state-desc">
                  {generationResponse.message ||
                    'No outfits matched your current combination of occasion, vibe, and season. Try adjusting the occasion or adding versatile essentials.'}
                </p>
                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setOccasion('casual')
                      setVibe('')
                      setSeason('all_season')
                    }}
                  >
                    Reset to Casual
                  </Button>
                  <Link to="/wardrobe">
                    <Button variant="default">View Wardrobe</Button>
                  </Link>
                </div>
              </div>
            )}

            {/* Structured Budget Warning / Cheapest Alternative */}
            {!generating && generationResponse?.no_products_in_budget && (
              <div className="budget-alert-banner">
                <div className="budget-alert-header">
                  <span>
                    Nothing in the shop fits your ₹{budgetMax || '0'} limit for this look.
                  </span>
                </div>
                {generationResponse.cheapest_alternative && (
                  <div className="cheapest-alt-wrapper">
                    <div className="cheapest-alt-info">
                      <img
                        src={generationResponse.cheapest_alternative.image_url || '/placeholder.svg'}
                        alt={generationResponse.cheapest_alternative.name}
                        className="cheapest-alt-thumb"
                      />
                      <div className="cheapest-alt-details">
                        <span className="cheapest-alt-name">
                          {generationResponse.cheapest_alternative.name}
                        </span>
                        <span className="cheapest-alt-meta">
                          Cheapest Alternative Available • ₹{generationResponse.cheapest_alternative.price} (₹{(generationResponse.cheapest_alternative.price - Number(budgetMax || 0)).toFixed(0)} over budget)
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setBudgetMax(String(generationResponse.cheapest_alternative!.price))}
                        title="Increase budget to match cheapest alternative"
                      >
                        Set Budget to ₹{generationResponse.cheapest_alternative.price}
                      </Button>
                      <Button
                        size="sm"
                        className="gap-1.5 bg-primary hover:bg-primary/90 text-primary-foreground"
                        onClick={() => {
                          const alt = generationResponse.cheapest_alternative!
                          addToCart({
                            id: alt.id,
                            name: alt.name,
                            price: alt.price,
                            image: alt.image_url || '/placeholder.svg',
                          })
                        }}
                      >
                        Add to Cart (₹{generationResponse.cheapest_alternative.price})
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {!generating &&
              generationResponse &&
              (generationResponse.status === 'success' || generationResponse.status === 'partial_results') &&
              generationResponse.outfits.length > 0 && (
                <div className="outfits-results-section">
                  {/* Partial Results Banner */}
                  {generationResponse.status === 'partial_results' && (
                    <div className="outfits-partial-banner">
                      <div className="partial-banner-header">
                        <span className="partial-banner-badge">COMPLETE SELECTION</span>
                        <span className="partial-banner-title">
                          Showing all {generationResponse.outfits.length} available unique {generationResponse.outfits.length === 1 ? 'look' : 'looks'} for this brief.
                        </span>
                      </div>
                      <p className="partial-banner-desc">
                        {generationResponse.message ||
                          'Your wardrobe and matching store pieces produced these unique combinations. All valid looks meeting the brief are displayed below.'}
                      </p>
                    </div>
                  )}

                  {/* Summary Quality Warning Banner */}
                  {generationResponse.quality_warning && (
                    <div className="outfits-quality-notice-banner">
                      <div className="quality-notice-badge">QUALITY NOTICE</div>
                      <div className="quality-notice-content">
                        <span className="quality-notice-title">Fallback Looks Included</span>
                        <p className="quality-notice-text">{generationResponse.quality_warning}</p>
                        <p className="quality-notice-sub">
                          These outfits satisfy your required garments, occasion, and seasonal rules, but fall below our standard 55% harmony threshold. They are included as last-resort alternatives so you have options.
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="outfits-results-header">
                    <div className="outfits-results-count">
                      Curated Looks ({generationResponse.outfits.length})
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Occasion: <strong className="text-foreground capitalize">{occasion}</strong>{' '}
                      {vibe && <>• Vibe: <strong className="text-foreground capitalize">{vibe}</strong></>}
                      {wardrobeOnly && <> • <strong className="text-foreground">Rack Only</strong></>}
                    </div>
                  </div>

                  <div className="outfits-grid">
                    {generationResponse.outfits.map((outfit) => (
                      <OutfitCard
                        key={outfit.id}
                        outfit={outfit}
                        isSaving={savingOutfitIds.has(outfit.id)}
                        onOpenTagModal={() => handleOpenTagModal(outfit)}
                        onUnsave={() => handleUnsave(outfit)}
                        onDisliked={() => handleOutfitDisliked(outfit.id)}
                      />
                    ))}
                  </div>
                </div>
              )}

            {/* Prompt to generate when no generation yet */}
            {!generating && !generationResponse && (
              <div className="outfits-empty-card">
                <h3 className="empty-state-title">Ready to pull a few looks.</h3>
                <p className="empty-state-desc">
                  Select your occasion and styling preferences above, then click{' '}
                  <strong>Pull looks</strong> to build a set from your closet.
                </p>
                <Button
                  onClick={() => handleGenerate()}
                  className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground"
                >
                  PULL A FEW LOOKS →
                </Button>
              </div>
            )}
          </>
        )}

        {/* Saved Looks Tab */}
        {activeTab === 'saved' && (
          <div className="saved-outfits-section">
            {/* Tag Filter Bar */}
            <div className="saved-tags-filter-bar">
              <span className="saved-tags-label">TAG FILTER:</span>
              <div className="saved-tags-chips">
                <button
                  type="button"
                  className={`saved-tag-filter-chip ${selectedSavedTag === 'All' ? 'active' : ''}`}
                  onClick={() => handleSelectFilterTag('All')}
                >
                  All
                </button>
                {APPROVED_OUTFIT_TAGS.map((t) => (
                  <button
                    key={t}
                    type="button"
                    className={`saved-tag-filter-chip ${selectedSavedTag === t ? 'active' : ''}`}
                    onClick={() => handleSelectFilterTag(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            {loadingSaved && (
              <div className="outfits-empty-card">
                <h3 className="empty-state-title">Loading Saved Looks</h3>
                <p className="empty-state-desc">Opening the looks you set aside…</p>
              </div>
            )}

            {!loadingSaved && savedOutfits.length === 0 && (
              <div className="outfits-empty-card">
                <h3 className="empty-state-title">
                  {selectedSavedTag === 'All' ? 'No Saved Outfits Yet' : `No Looks Tagged "${selectedSavedTag}"`}
                </h3>
                <p className="empty-state-desc">
                  {selectedSavedTag === 'All'
                    ? 'When a look feels right, save it here with custom tags for quick access.'
                    : `You have no saved outfits with the tag "${selectedSavedTag}".`}
                </p>
                {selectedSavedTag !== 'All' ? (
                  <Button
                    onClick={() => handleSelectFilterTag('All')}
                    className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground"
                  >
                    SHOW ALL SAVED LOOKS
                  </Button>
                ) : (
                  <Button
                    onClick={() => setActiveTab('studio')}
                    className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground"
                  >
                    BACK TO BUILD
                  </Button>
                )}
              </div>
            )}

            {!loadingSaved && savedOutfits.length > 0 && (
              <>
                <div className="outfits-results-header">
                  <div className="outfits-results-count">
                    Saved Looks ({savedOutfits.length})
                    {selectedSavedTag !== 'All' && ` • Tag: ${selectedSavedTag}`}
                  </div>
                </div>

                <div className="outfits-grid">
                  {savedOutfits.map((outfit) => (
                    <OutfitCard
                      key={outfit.id}
                      outfit={outfit}
                      isSaving={savingOutfitIds.has(outfit.id)}
                      onOpenTagModal={() => handleOpenTagModal(outfit)}
                      onUnsave={() => handleUnsave(outfit)}
                      onDisliked={() => handleOutfitDisliked(outfit.id)}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {/* Gaps Analysis Tab */}
        {activeTab === 'gaps' && (
          <div className="gaps-container">
            <div className="gaps-intro-card">
              <div className="gaps-intro-text">
                <h3>What would unlock more looks?</h3>
                <p>
                  See which missing pieces could make the most new combinations. Shop matches are real pieces currently available.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={loadGaps}
                  disabled={loadingGaps}
                  className="gap-1.5"
                >
                  Recalculate Gaps
                </Button>
              </div>
            </div>

            {loadingGaps && (
              <div className="outfits-empty-card">
                <h3 className="empty-state-title">Finding the next useful piece.</h3>
                <p className="empty-state-desc">
                  Checking which additions would give your rack more options…
                </p>
              </div>
            )}

            {!loadingGaps && gapsResponse && gapsResponse.gaps.length > 0 && (
              <div className="gaps-list">
                {gapsResponse.gaps.map((gap) => (
                  <div key={gap.id} className="gap-card">
                    <div className="gap-card-header">
                      <div className="gap-archetype-info">
                        <div className="gap-archetype-name">{gap.name}</div>
                        <div className="gap-archetype-badges">
                          <span className="gap-slot-badge">{gap.slot.replace(/_/g, ' ')}</span>
                          <span className="gap-utility-badge">
                            +{gap.new_outfits_total} new {gap.new_outfits_total === 1 ? 'look' : 'looks'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {gap.new_outfits_by_occasion && Object.keys(gap.new_outfits_by_occasion).length > 0 && (
                      <div className="gap-occasion-counts">
                        <span className="eyebrow">New looks by occasion:</span>
                        {Object.entries(gap.new_outfits_by_occasion).map(([occ, cnt]) =>
                          cnt > 0 ? (
                            <span key={occ} className="gap-occ-chip">
                              {occ}: <strong>+{cnt}</strong>
                            </span>
                          ) : null
                        )}
                      </div>
                    )}

                    {gap.budget_status === 'no_products_in_budget' && (
                      <div className="budget-alert-banner" style={{ margin: '0.75rem 0' }}>
                        <div className="budget-alert-header">
                          <span>Matching items exceed your budget limit.</span>
                        </div>
                        {gap.cheapest_alternative && (
                          <div className="cheapest-alt-wrapper">
                            <div className="cheapest-alt-info">
                              <img
                                src={gap.cheapest_alternative.image_url || '/placeholder.svg'}
                                alt={gap.cheapest_alternative.name}
                                className="cheapest-alt-thumb"
                              />
                              <div className="cheapest-alt-details">
                                <span className="cheapest-alt-name">{gap.cheapest_alternative.name}</span>
                                <span className="cheapest-alt-meta">
                                  Cheapest Available • ₹{gap.cheapest_alternative.price}
                                </span>
                              </div>
                            </div>
                            <Button
                              size="sm"
                              className="gap-1.5"
                              onClick={() => {
                                const alt = gap.cheapest_alternative!
                                addToCart({
                                  id: alt.id,
                                  name: alt.name,
                                  price: alt.price,
                                  image: alt.image_url || '/placeholder.svg',
                                })
                              }}
                            >
                              Add to Cart (₹{gap.cheapest_alternative.price})
                            </Button>
                          </div>
                        )}
                      </div>
                    )}

                    {gap.matching_products && gap.matching_products.length > 0 && (
                      <div>
                        <div className="gap-matches-title">
                          In the shop ({gap.matching_products.length})
                        </div>
                        <div className="gap-products-grid">
                          {gap.matching_products.map((prod) => (
                            <div key={prod.id} className="gap-product-card">
                              <img
                                src={prod.image_url || '/placeholder.svg'}
                                alt={prod.name}
                                className="gap-product-thumb"
                                loading="lazy"
                              />
                              <div className="gap-product-body">
                                <span className="gap-product-name" title={prod.name}>
                                  {prod.name}
                                </span>
                                <span className="gap-product-price">₹{prod.price}</span>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="gap-1 text-xs py-1 h-7 mt-1"
                                  onClick={() =>
                                    addToCart({
                                      id: prod.id,
                                      name: prod.name,
                                      price: prod.price,
                                      image: prod.image_url || '/placeholder.svg',
                                    })
                                  }
                                >
                                  Add to Cart
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tag Selection / Editing Modal */}
      {tagModalOutfit && (
        <div
          className="outfit-tag-modal-overlay"
          onClick={() => !modalSubmitting && setTagModalOutfit(null)}
        >
          <div className="outfit-tag-modal" onClick={(e) => e.stopPropagation()}>
            <div className="outfit-tag-modal-header">
              <h3 className="outfit-tag-modal-title">
                {tagModalOutfit.is_saved ? 'Edit Look Tags' : 'Save for Later'}
              </h3>
              <button
                className="outfit-tag-modal-close"
                onClick={() => !modalSubmitting && setTagModalOutfit(null)}
                type="button"
                disabled={modalSubmitting}
                title="Close"
              >
                ✕
              </button>
            </div>

            <p className="outfit-tag-modal-desc">
              Categorize this outfit in your saved looks. Select one or more tags:
            </p>

            <div className="outfit-tag-options">
              {APPROVED_OUTFIT_TAGS.map((tag) => {
                const isSelected = modalTags.includes(tag)
                return (
                  <button
                    key={tag}
                    type="button"
                    className={`outfit-tag-select-btn ${isSelected ? 'selected' : ''}`}
                    onClick={() => {
                      if (isSelected) {
                        const next = modalTags.filter((t) => t !== tag)
                        setModalTags(next.length > 0 ? next : ['Try Later'])
                      } else {
                        setModalTags([...modalTags, tag])
                      }
                    }}
                  >
                    <span className="tag-checkbox">{isSelected ? '✓' : ''}</span>
                    <span className="tag-name">{tag}</span>
                  </button>
                )
              })}
            </div>

            <div className="outfit-tag-modal-actions">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setTagModalOutfit(null)}
                disabled={modalSubmitting}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleConfirmSaveTags}
                disabled={modalSubmitting}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {modalSubmitting ? 'Saving…' : tagModalOutfit.is_saved ? 'Update Tags' : 'Save Outfit'}
              </Button>
            </div>
          </div>
        </div>
      )}

      <Footer />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Outfit Card Subcomponent
// ---------------------------------------------------------------------------

interface OutfitCardProps {
  outfit: OutfitResponse
  isSaving: boolean
  onOpenTagModal: () => void
  onUnsave: () => void
  onDisliked: () => void
}

function OutfitCard({
  outfit,
  isSaving,
  onOpenTagModal,
  onUnsave,
  onDisliked,
}: OutfitCardProps) {
  const { addToCart } = useCart()
  const [showScores, setShowScores] = useState(false)
  const [recentFeedback, setRecentFeedback] = useState<string | null>(null)
  const [actionPending, setActionPending] = useState(false)
  const [addedCartIds, setAddedCartIds] = useState<Set<string>>(new Set())

  const matchPercent = Math.round(outfit.score * 100)
  const skeletonName = SKELETON_LABELS[outfit.skeleton] || outfit.skeleton.replace(/_/g, ' ')

  const handleFeedback = async (eventType: OutfitEventType) => {
    setActionPending(true)
    try {
      await api.outfits.recordEvent(outfit.id, eventType)
      const labels: Record<string, string> = {
        wear: 'Wore it • Added to your pattern',
        like: 'Keep • Noted as a favorite',
        dislike: 'Not for me • Removed from saved',
        skip: 'Skipped for now',
      }
      setRecentFeedback(labels[eventType] || 'Feedback saved')
      setTimeout(() => setRecentFeedback(null), 3000)
      if (eventType === 'dislike') {
        onDisliked()
      }
    } catch (err) {
      console.error('Failed to record outfit event:', err)
      setRecentFeedback('Could not save feedback. Please try again.')
      setTimeout(() => setRecentFeedback(null), 3500)
    } finally {
      setActionPending(false)
    }
  }

  return (
    <div className="outfit-card">
      {/* Card Header */}
      <div className="outfit-card-header">
        <div className="outfit-badges-row">
          <span className="skeleton-badge">{skeletonName}</span>
          {outfit.is_below_threshold && (
            <span className="below-threshold-badge">
              Fallback Look
            </span>
          )}
          {!outfit.wardrobe_only && (
            <span className="mixed-look-badge">
              +1 Shop Piece
            </span>
          )}
          {outfit.vibe && <span className="vibe-badge">{outfit.vibe}</span>}
          <span className={`score-badge ${outfit.is_below_threshold ? 'below-threshold' : ''}`}>
            {matchPercent}% {outfit.is_below_threshold ? '(Below Target)' : 'Match'}
          </span>
        </div>

        <div className="outfit-card-actions">
          {outfit.is_saved ? (
            <div className="saved-btn-group">
              <button
                type="button"
                className="outfit-save-btn saved"
                onClick={onUnsave}
                disabled={isSaving}
                title="Remove from saved looks"
              >
                SAVED ✓
              </button>
              <button
                type="button"
                className="outfit-edit-tags-btn"
                onClick={onOpenTagModal}
                title="Edit outfit tags"
              >
                TAGS ✎
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="outfit-save-btn"
              onClick={onOpenTagModal}
              disabled={isSaving}
              title="Save this look with tags"
            >
              SAVE LOOK
            </button>
          )}
        </div>
      </div>

      {/* Render Tags Row if saved and has tags */}
      {outfit.is_saved && outfit.tags && outfit.tags.length > 0 && (
        <div className="outfit-card-tags-row">
          <span className="outfit-card-tags-label">TAGS:</span>
          {outfit.tags.map((t) => (
            <span key={t} className="outfit-tag-chip">
              {t}
            </span>
          ))}
        </div>
      )}

      {/* Card-Level Quality Warning Box for Below-Threshold Looks */}
      {outfit.is_below_threshold && (
        <div className="card-quality-warning">
          <span className="card-warning-tag">BELOW HARMONY THRESHOLD</span>
          <span className="card-warning-msg">
            {outfit.quality_warning ||
              'This combination is below the 55% quality threshold but is provided as an alternative combination to meet your requested count.'}
          </span>
        </div>
      )}

      {/* Outfit Slots Items Grid */}
      <div className="outfit-items-grid">
        {outfit.items.map((item, idx) => (
          <div key={`${item.slot}-${idx}`} className="outfit-slot-item">
            <span className="slot-tag">{item.slot.replace(/_/g, ' ')}</span>
            <div className="slot-img-wrap">
              {item.thumbnail_url || item.image_url ? (
                <img
                  src={item.thumbnail_url || item.image_url || ''}
                  alt={item.name}
                  className="slot-img"
                  loading="lazy"
                />
              ) : (
                <div className="slot-placeholder">
                  <span>NO PHOTO</span>
                  <span>{item.category}</span>
                </div>
              )}
            </div>

            <div className="slot-info">
              <span className="slot-name" title={item.name}>
                {item.name}
              </span>
              <div className="slot-meta-row">
                {item.primary_color && (
                  <span className="slot-color-tag">{item.primary_color}</span>
                )}
                {item.fit && <span className="slot-fit-tag">{item.fit}</span>}
              </div>

              {item.source_type === 'catalog' && item.product_id && (
                <div className="slot-catalog-indicator">
                  <div className="slot-catalog-header">
                    <span className="slot-catalog-badge">SHOP PIECE</span>
                    <span className="slot-catalog-price">₹{item.price ?? '—'}</span>
                  </div>
                  <div className="slot-catalog-reason">
                    Completes look by filling {item.slot.replace(/_/g, ' ')} slot
                  </div>
                  <button
                    type="button"
                    className={`slot-add-cart-btn ${addedCartIds.has(item.product_id) ? 'added' : ''}`}
                    onClick={async () => {
                      const pid = item.product_id!
                      setAddedCartIds((prev) => new Set(prev).add(pid))
                      await addToCart({
                        id: pid,
                        name: item.name,
                        price: item.price || 0,
                        image: item.thumbnail_url || item.image_url || '/placeholder.svg',
                      })
                      setTimeout(() => {
                        setAddedCartIds((prev) => {
                          const copy = new Set(prev)
                          copy.delete(pid)
                          return copy
                        })
                      }, 2500)
                    }}
                  >
                    {addedCartIds.has(item.product_id) ? (
                      <>
                        In Cart ✓
                      </>
                    ) : (
                      <>
                        Add to Cart (₹{item.price ?? 0})
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Why This Works Section (Factual structured reasons) */}
      <div className="outfit-explanation-box">
        <div className="explanation-header">
          <span>Why This Works</span>
        </div>
        <ul className="reasons-list">
          {outfit.fallback_reason && (
            <li className="reason-item catalog-completion-reason">
              <span className="reason-dot store-dot" />
              <span><strong>Shop Completion:</strong> {outfit.fallback_reason}</span>
            </li>
          )}
          {outfit.reasons.map((reason, rIdx) => (
            <li key={rIdx} className="reason-item">
              <span className="reason-dot" />
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Component Scores Drawer */}
      {outfit.component_scores && Object.keys(outfit.component_scores).length > 0 && (
        <div className="scores-drawer">
          <button
            type="button"
            className="scores-toggle-btn"
            onClick={() => setShowScores(!showScores)}
          >
            <span>What shaped the match</span>
            <span>{showScores ? '▲ Hide' : '▼ Show'}</span>
          </button>

          {showScores && (
            <div className="component-scores-grid">
              {Object.entries(outfit.component_scores).map(([dimension, val]) => (
                <div key={dimension} className="component-score-chip">
                  <span className="score-dimension-name">
                    {dimension.replace(/_/g, ' ')}
                  </span>
                  <span className="score-dimension-val">
                    {(Number(val) * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Outfit Interaction Feedback Bar */}
      <div className="outfit-feedback-bar">
        <div className="feedback-btn-group">
          <button
            type="button"
            className="feedback-action-btn"
            onClick={() => handleFeedback('wear')}
            disabled={actionPending}
            title="Mark this look as worn today"
          >
            <span>WORE IT</span>
          </button>
          <button
            type="button"
            className="feedback-action-btn"
            onClick={() => handleFeedback('like')}
            disabled={actionPending}
            title="Keep this look"
          >
            <span>KEEP</span>
          </button>
          <button
            type="button"
            className="feedback-action-btn"
            onClick={() => handleFeedback('dislike')}
            disabled={actionPending}
            title="Mark this look as not for you"
          >
            <span>NOT FOR ME</span>
          </button>
          <button
            type="button"
            className="feedback-action-btn"
            onClick={() => handleFeedback('skip')}
            disabled={actionPending}
            title="Skip this look for now"
          >
            <span>Skip</span>
          </button>
        </div>

        {recentFeedback && (
          <span className="feedback-status-pill">
            {recentFeedback}
          </span>
        )}
      </div>

    </div>
  )
}
