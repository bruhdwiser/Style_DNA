import React, { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Sparkles,
  Bookmark,
  BookmarkCheck,
  AlertTriangle,
  RefreshCw,
  Layers,
  ArrowRight,
  Info,
  Calendar,
  Compass,
  Sliders,
  CheckCircle,
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  FastForward,
  ShoppingCart,
} from 'lucide-react'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/auth-context'
import { useCart } from '@/contexts/cart-context'
import {
  api,
  type OutfitResponse,
  type GenerateOutfitsResponse,
  type WardrobeCoverageResponse,
  type OutfitEventType,
  type GapAnalysisResponse,
  type CatalogProductSuggestion,
} from '@/lib/api'
import './OutfitsPage.css'

// ---------------------------------------------------------------------------
// Constants & Options
// ---------------------------------------------------------------------------

const OCCASIONS = [
  { id: 'casual', label: 'Casual', icon: '☕' },
  { id: 'work', label: 'Work / Office', icon: '💼' },
  { id: 'party', label: 'Party / Night Out', icon: '✨' },
  { id: 'formal', label: 'Formal', icon: '👔' },
  { id: 'festive', label: 'Festive / Traditional', icon: '🪔' },
  { id: 'wedding', label: 'Wedding', icon: '💍' },
  { id: 'college', label: 'College / Campus', icon: '🎒' },
  { id: 'lounge', label: 'Lounge / Relaxed', icon: '🛋️' },
]

const VIBES = [
  { id: '', label: 'Any Vibe' },
  { id: 'minimal', label: 'Minimal' },
  { id: 'classic', label: 'Classic' },
  { id: 'bohemian', label: 'Bohemian' },
  { id: 'streetwear', label: 'Streetwear' },
  { id: 'elegant', label: 'Elegant' },
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
  const [wardrobeOnly, setWardrobeOnly] = useState(true)
  const [allowOneNewItem, setAllowOneNewItem] = useState(false)
  const [budgetMax, setBudgetMax] = useState<string>('')

  // Outfits State
  const [generating, setGenerating] = useState(false)
  const [generationResponse, setGenerationResponse] = useState<GenerateOutfitsResponse | null>(null)
  const [savedOutfits, setSavedOutfits] = useState<OutfitResponse[]>([])
  const [loadingSaved, setLoadingSaved] = useState(false)
  const [savingOutfitIds, setSavingOutfitIds] = useState<Set<string>>(new Set())
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [coverage, setCoverage] = useState<WardrobeCoverageResponse | null>(null)
  const [profileWarning, setProfileWarning] = useState<string | null>(null)

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

  // Load saved looks
  const loadSavedOutfits = useCallback(async () => {
    if (!user) return
    setLoadingSaved(true)
    try {
      const res = await api.outfits.getSaved()
      setSavedOutfits(res.outfits || [])
    } catch (err: any) {
      console.error('Failed to load saved outfits:', err)
    } finally {
      setLoadingSaved(false)
    }
  }, [user])

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

  // Generate Outfits Handler
  const handleGenerate = async () => {
    if (!user) return
    setGenerating(true)
    try {
      const res = await api.outfits.generate({
        occasion,
        vibe: vibe || undefined,
        season,
        limit,
        wardrobe_only: wardrobeOnly,
        allow_one_new_item: allowOneNewItem,
        budget_max: budgetMax ? Number(budgetMax) : undefined,
      })
      setGenerationResponse(res)
      if (res.profile_warning) {
        setProfileWarning(res.profile_warning)
      }
    } catch (err: any) {
      console.error('Outfit generation failed:', err)
      setGenerationResponse({
        outfits: [],
        status: 'error',
        message: err?.message || 'Failed to generate outfits. Please try again.',
        missing_slots: [],
      })
    } finally {
      setGenerating(false)
    }
  }

  // Toggle Save / Unsave
  const handleToggleSave = async (outfit: OutfitResponse) => {
    const isCurrentlySaved = outfit.is_saved
    const outfitId = outfit.id

    setSavingOutfitIds((prev) => new Set(prev).add(outfitId))

    // Optimistic UI updates
    if (generationResponse) {
      setGenerationResponse({
        ...generationResponse,
        outfits: generationResponse.outfits.map((o) =>
          o.id === outfitId ? { ...o, is_saved: !isCurrentlySaved } : o
        ),
      })
    }
    if (isCurrentlySaved) {
      setSavedOutfits((prev) => prev.filter((o) => o.id !== outfitId))
    }

    try {
      if (isCurrentlySaved) {
        await api.outfits.unsave(outfitId)
      } else {
        await api.outfits.save(outfitId)
      }
    } catch (err: any) {
      console.error('Save toggle failed:', err)
      // Revert optimistic update
      if (generationResponse) {
        setGenerationResponse({
          ...generationResponse,
          outfits: generationResponse.outfits.map((o) =>
            o.id === outfitId ? { ...o, is_saved: isCurrentlySaved } : o
          ),
        })
      }
      if (activeTab === 'saved') {
        loadSavedOutfits()
      }
    } finally {
      setSavingOutfitIds((prev) => {
        const next = new Set(prev)
        next.delete(outfitId)
        return next
      })
    }
  }

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div className="outfits-page">
      <Navigation />

      {/* Header */}
      <div className="outfits-header">
        <div className="outfits-header-content">
          <div>
            <div className="outfits-badge-tag">
              <Sparkles className="w-3.5 h-3.5 text-accent" />
              Pure Algorithmic Styling Engine
            </div>
            <h1 className="outfits-title">AI Outfit Studio</h1>
            <p className="outfits-subtitle">
              Intelligent outfits curated directly from your authenticated digital wardrobe.
              Every recommendation features deterministic scoring and factual reasons.
            </p>
          </div>

          {/* Tab Switcher */}
          <div className="outfits-tabs-bar">
            <button
              className={`outfits-tab-btn ${activeTab === 'studio' ? 'active' : ''}`}
              onClick={() => setActiveTab('studio')}
            >
              <Compass className="w-4 h-4" />
              Outfit Studio
            </button>
            <button
              className={`outfits-tab-btn ${activeTab === 'saved' ? 'active' : ''}`}
              onClick={() => setActiveTab('saved')}
            >
              <Bookmark className="w-4 h-4" />
              Saved Looks
              {savedOutfits.length > 0 && (
                <span className="tab-badge">{savedOutfits.length}</span>
              )}
            </button>
            <button
              className={`outfits-tab-btn ${activeTab === 'gaps' ? 'active' : ''}`}
              onClick={() => setActiveTab('gaps')}
            >
              <Layers className="w-4 h-4 text-amber-400" />
              Wardrobe Gaps
            </button>
            <Link to="/style-dna">
              <button className="outfits-tab-btn" type="button" title="View transparent Style DNA affinities">
                <Sparkles className="w-4 h-4 text-purple-400" />
                Style DNA
              </button>
            </Link>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="outfits-container">
        {/* Style Profile Warning (Non-blocking) */}
        {profileWarning && (
          <div className="outfits-warning-banner">
            <div className="warning-banner-content">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{profileWarning}</span>
            </div>
            <Link to="/style-onboarding" className="warning-action-link">
              Complete Style Profile
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        )}

        {/* Studio View */}
        {activeTab === 'studio' && (
          <>
            {/* Generator Brief Controls */}
            <div className="generator-controls-card">
              <div className="controls-section-title">
                <Calendar className="w-4 h-4 text-primary" />
                Select Occasion
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
                    <span>{occ.icon}</span>
                    <span>{occ.label}</span>
                  </button>
                ))}
              </div>

              {/* Secondary Options Grid */}
              <div className="controls-secondary-row">
                {/* Vibe Selection */}
                <div className="control-field-group">
                  <label className="control-field-label">Aesthetic Vibe</label>
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

                {/* Allow One New Item Toggle */}
                <div
                  className="toggle-field"
                  onClick={() => {
                    const nextVal = !allowOneNewItem
                    setAllowOneNewItem(nextVal)
                    if (nextVal) {
                      setWardrobeOnly(false)
                    }
                  }}
                  title="Allow fallback with 1 catalog item if wardrobe lacks required slot or too few good outfits"
                >
                  <div className="toggle-field-label">
                    <span className="toggle-title">Allow 1 New Item</span>
                    <span className="toggle-desc">Fallback unlocks missing slot</span>
                  </div>
                  <div className={`toggle-switch ${allowOneNewItem ? 'checked' : ''}`}>
                    <div className="toggle-knob" />
                  </div>
                </div>

                {/* Wardrobe Only Toggle */}
                <div
                  className="toggle-field"
                  onClick={() => {
                    const nextVal = !wardrobeOnly
                    setWardrobeOnly(nextVal)
                    if (nextVal) {
                      setAllowOneNewItem(false)
                    }
                  }}
                  title="When active, strictly uses your private wardrobe items (never catalog items)"
                >
                  <div className="toggle-field-label">
                    <span className="toggle-title">Wardrobe-Only Mode</span>
                    <span className="toggle-desc">Excludes all catalog products</span>
                  </div>
                  <div className={`toggle-switch ${wardrobeOnly ? 'checked' : ''}`}>
                    <div className="toggle-knob" />
                  </div>
                </div>

                {/* Optional Budget Limit (active when allowOneNewItem is selected) */}
                {allowOneNewItem && (
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
                )}
              </div>

              {/* Action Bar */}
              <div className="controls-action-bar">
                <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5" />
                  <span>
                    Deterministic pure engine evaluates color harmony, occasion brief, and body-fit rules.
                  </span>
                </div>

                <button
                  type="button"
                  className="btn-generate-outfits"
                  onClick={handleGenerate}
                  disabled={generating}
                >
                  {generating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Evaluating Combinations…
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Generate Outfits
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Results / Status Rendering */}
            {generating && (
              <div className="outfits-empty-card">
                <div className="empty-state-icon-box">
                  <RefreshCw className="w-8 h-8 animate-spin" />
                </div>
                <h3 className="empty-state-title">Styling in Progress</h3>
                <p className="empty-state-desc">
                  Filtering skeletons, scoring color harmony, checking seasonal compatibility, and
                  generating factual explanations…
                </p>
              </div>
            )}

            {!generating && generationResponse?.status === 'empty_wardrobe' && (
              <div className="outfits-empty-card">
                <div className="empty-state-icon-box">
                  <Layers className="w-8 h-8" />
                </div>
                <h3 className="empty-state-title">Your Wardrobe is Empty</h3>
                <p className="empty-state-desc">
                  {generationResponse.message ||
                    'Add clothes to your private wardrobe before the engine can generate outfits.'}
                </p>
                <Link to="/wardrobe">
                  <Button className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground">
                    Go to Wardrobe to Add Clothes
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
              </div>
            )}

            {!generating && generationResponse?.status === 'missing_required_slots' && (
              <div className="outfits-empty-card">
                <div className="empty-state-icon-box">
                  <AlertTriangle className="w-8 h-8 text-amber-500" />
                </div>
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
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
              </div>
            )}

            {!generating && generationResponse?.status === 'no_matching_combinations' && (
              <div className="outfits-empty-card">
                <div className="empty-state-icon-box">
                  <Sliders className="w-8 h-8" />
                </div>
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
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span>
                    No catalog products available within your budget limit of ₹{budgetMax || '0'} could complete this look.
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
                      <ShoppingCart className="w-3.5 h-3.5" />
                      Add to Cart (₹{generationResponse.cheapest_alternative.price})
                    </Button>
                  </div>
                )}
              </div>
            )}

            {!generating &&
              generationResponse?.status === 'success' &&
              generationResponse.outfits.length > 0 && (
                <div className="outfits-results-section">
                  <div className="outfits-results-header">
                    <div className="outfits-results-count">
                      Curated Looks ({generationResponse.outfits.length})
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Occasion: <strong className="text-foreground capitalize">{occasion}</strong>{' '}
                      {vibe && <>• Vibe: <strong className="text-foreground capitalize">{vibe}</strong></>}
                    </div>
                  </div>

                  <div className="outfits-grid">
                    {generationResponse.outfits.map((outfit) => (
                      <OutfitCard
                        key={outfit.id}
                        outfit={outfit}
                        isSaving={savingOutfitIds.has(outfit.id)}
                        copiedId={copiedId}
                        onToggleSave={() => handleToggleSave(outfit)}
                        onCopyId={() => handleCopyId(outfit.id)}
                      />
                    ))}
                  </div>
                </div>
              )}

            {/* Prompt to generate when no generation yet */}
            {!generating && !generationResponse && (
              <div className="outfits-empty-card">
                <div className="empty-state-icon-box">
                  <Sparkles className="w-8 h-8" />
                </div>
                <h3 className="empty-state-title">Ready to Curate Your Looks</h3>
                <p className="empty-state-desc">
                  Select your occasion and styling preferences above, then click{' '}
                  <strong>Generate Outfits</strong> to run the pure Python styling rules engine on your
                  wardrobe.
                </p>
                <Button
                  onClick={handleGenerate}
                  className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground"
                >
                  <Sparkles className="w-4 h-4" />
                  Generate Initial Looks
                </Button>
              </div>
            )}
          </>
        )}

        {/* Saved Looks Tab */}
        {activeTab === 'saved' && (
          <div className="saved-outfits-section">
            {loadingSaved && (
              <div className="outfits-empty-card">
                <div className="empty-state-icon-box">
                  <RefreshCw className="w-8 h-8 animate-spin" />
                </div>
                <h3 className="empty-state-title">Loading Saved Looks</h3>
                <p className="empty-state-desc">Retrieving your bookmarked outfits from storage…</p>
              </div>
            )}

            {!loadingSaved && savedOutfits.length === 0 && (
              <div className="outfits-empty-card">
                <div className="empty-state-icon-box">
                  <Bookmark className="w-8 h-8 text-muted-foreground" />
                </div>
                <h3 className="empty-state-title">No Saved Outfits Yet</h3>
                <p className="empty-state-desc">
                  When you find looks you love in the Outfit Studio, bookmark them to save them here
                  for quick access.
                </p>
                <Button
                  onClick={() => setActiveTab('studio')}
                  className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground"
                >
                  <Sparkles className="w-4 h-4" />
                  Go to Outfit Studio
                </Button>
              </div>
            )}

            {!loadingSaved && savedOutfits.length > 0 && (
              <>
                <div className="outfits-results-header">
                  <div className="outfits-results-count">
                    Saved Looks ({savedOutfits.length})
                  </div>
                </div>

                <div className="outfits-grid">
                  {savedOutfits.map((outfit) => (
                    <OutfitCard
                      key={outfit.id}
                      outfit={outfit}
                      isSaving={savingOutfitIds.has(outfit.id)}
                      copiedId={copiedId}
                      onToggleSave={() => handleToggleSave(outfit)}
                      onCopyId={() => handleCopyId(outfit.id)}
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
                <h3>Wardrobe Counterfactual Gap Analysis</h3>
                <p>
                  Calculates which missing clothing archetypes unlock the largest number of versatile,
                  high-scoring outfits for your wardrobe. Attached products are real Supabase catalog essentials.
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
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingGaps ? 'animate-spin' : ''}`} />
                  Recalculate Gaps
                </Button>
              </div>
            </div>

            {loadingGaps && (
              <div className="outfits-empty-card">
                <RefreshCw className="w-8 h-8 animate-spin" />
                <h3 className="empty-state-title">Analyzing Counterfactual Combinations</h3>
                <p className="empty-state-desc">
                  Simulating additions for each slot and calculating unlocked outfits…
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
                          <span className="gap-slot-badge">Slot: {gap.slot}</span>
                          <span className="gap-utility-badge">
                            <Sparkles className="w-3 h-3" />
                            +{gap.new_outfits_total} Outfits Unlocked (Utility: {gap.utility})
                          </span>
                        </div>
                      </div>
                    </div>

                    {gap.new_outfits_by_occasion && Object.keys(gap.new_outfits_by_occasion).length > 0 && (
                      <div className="gap-occasion-counts">
                        <span className="font-semibold text-zinc-300">New looks by occasion:</span>
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
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
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
                              <ShoppingCart className="w-3.5 h-3.5" />
                              Add to Cart (₹{gap.cheapest_alternative.price})
                            </Button>
                          </div>
                        )}
                      </div>
                    )}

                    {gap.matching_products && gap.matching_products.length > 0 && (
                      <div>
                        <div className="gap-matches-title">
                          <Sparkles className="w-3.5 h-3.5 text-primary" />
                          Matching Catalog Essentials ({gap.matching_products.length})
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
                                  <ShoppingCart className="w-3 h-3" />
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
  copiedId: string | null
  onToggleSave: () => void
  onCopyId: () => void
}

function OutfitCard({
  outfit,
  isSaving,
  copiedId,
  onToggleSave,
  onCopyId,
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
        wear: 'Worn! +3.0 DNA',
        like: 'Liked! +1.0 DNA',
        dislike: 'Disliked! -2.0 DNA',
        skip: 'Skipped -0.5 DNA',
      }
      setRecentFeedback(labels[eventType] || 'Feedback saved')
      setTimeout(() => setRecentFeedback(null), 3000)
    } catch (err) {
      console.error('Failed to record outfit event:', err)
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
          {!outfit.wardrobe_only && (
            <span className="mixed-look-badge" title={`Fallback reason: ${outfit.fallback_reason || 'Catalog fallback'}`}>
              <Sparkles className="w-3 h-3" />
              Mixed Look {outfit.fallback_reason ? `(${outfit.fallback_reason.replace(/_/g, ' ')})` : ''}
            </span>
          )}
          {outfit.vibe && <span className="vibe-badge">{outfit.vibe}</span>}
          <span className="score-badge">{matchPercent}% Match</span>
        </div>

        <button
          type="button"
          className={`outfit-save-btn ${outfit.is_saved ? 'saved' : ''}`}
          onClick={onToggleSave}
          disabled={isSaving}
          title={outfit.is_saved ? 'Remove from saved' : 'Save this look'}
        >
          {outfit.is_saved ? (
            <BookmarkCheck className="w-4 h-4 text-primary" />
          ) : (
            <Bookmark className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Outfit Slots Items Grid */}
      <div className="outfit-items-grid">
        {outfit.items.map((item, idx) => (
          <div key={`${item.slot}-${idx}`} className="outfit-slot-item">
            <span className="slot-tag">{item.slot}</span>
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
                  <span>👗</span>
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
                  <span className="slot-catalog-badge">Catalog Item</span>
                  <span className="slot-catalog-price">₹{item.price ?? '—'}</span>
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
                        <Check className="w-3 h-3" />
                        In Cart
                      </>
                    ) : (
                      <>
                        <ShoppingCart className="w-3 h-3" />
                        Add to Cart
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
          <Sparkles className="w-3.5 h-3.5 text-accent" />
          <span>Why This Works</span>
        </div>
        {outfit.ai_summary && (
          <p className="text-xs text-accent-foreground font-medium italic mb-2.5 leading-relaxed bg-primary/10 p-2.5 rounded-lg border border-primary/20">
            "{outfit.ai_summary}"
          </p>
        )}
        <ul className="reasons-list">
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
            <span>Dimension Score Breakdown</span>
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
            title="Mark as worn today (+3.0 Style DNA affinity)"
          >
            <span>👔</span>
            <span>Wore</span>
          </button>
          <button
            type="button"
            className="feedback-action-btn"
            onClick={() => handleFeedback('like')}
            disabled={actionPending}
            title="Like this outfit (+1.0 Style DNA affinity)"
          >
            <ThumbsUp className="w-3 h-3 text-blue-400" />
            <span>Like</span>
          </button>
          <button
            type="button"
            className="feedback-action-btn"
            onClick={() => handleFeedback('dislike')}
            disabled={actionPending}
            title="Dislike this outfit (-2.0 Style DNA affinity)"
          >
            <ThumbsDown className="w-3 h-3 text-red-400" />
            <span>Dislike</span>
          </button>
          <button
            type="button"
            className="feedback-action-btn"
            onClick={() => handleFeedback('skip')}
            disabled={actionPending}
            title="Skip for now (-0.5 Style DNA affinity)"
          >
            <FastForward className="w-3 h-3 text-zinc-400" />
            <span>Skip</span>
          </button>
        </div>

        {recentFeedback && (
          <span className="feedback-status-pill">
            <CheckCircle className="w-3 h-3 text-emerald-400" />
            {recentFeedback}
          </span>
        )}
      </div>

      {/* Card Footer with stable UUID */}
      <div className="outfit-card-footer">
        <span className="outfit-id-tag">
          Look ID: {outfit.id.substring(0, 8)}…
        </span>
        <button
          type="button"
          className="hover:text-foreground flex items-center gap-1 text-xs"
          onClick={onCopyId}
          title="Copy Look ID"
        >
          {copiedId === outfit.id ? (
            <>
              <Check className="w-3 h-3 text-emerald-400" />
              <span>Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy ID</span>
            </>
          )}
        </button>
      </div>
    </div>
  )
}
