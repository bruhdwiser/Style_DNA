import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Sparkles,
  Plus,
  Trash2,
  Edit2,
  CheckCircle,
  AlertTriangle,
  Upload,
  Download,
  ShieldAlert,
  X,
  Filter,
  Layers,
  ArrowRight,
  Eye,
} from 'lucide-react'
import { useAuth } from '@/contexts/auth-context'
import { api } from '@/lib/api'
import type {
  WardrobeItem,
  WardrobeCoverageResponse,
  FinalizeUploadPayload,
  WardrobeUpdatePayload,
} from '@/lib/api'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { Button } from '@/components/ui/button'
import './WardrobePage.css'

// -------------------------------------------------------------------------
// Taxonomy & Quick-tag options
// -------------------------------------------------------------------------

const CATEGORIES = [
  { id: 'top', label: 'Top', emoji: '👚', slot: 'top' },
  { id: 'bottom', label: 'Bottom', emoji: '👖', slot: 'bottom' },
  { id: 'dress', label: 'Dress', emoji: '👗', slot: 'dress' },
  { id: 'saree', label: 'Saree', emoji: '🥻', slot: 'saree' },
  { id: 'ethnic_set', label: 'Ethnic Set', emoji: '✨', slot: 'ethnic_set' },
  { id: 'layer', label: 'Outerwear / Layer', emoji: '🧥', slot: 'layer' },
  { id: 'shoes', label: 'Shoes', emoji: '👟', slot: 'shoes' },
  { id: 'bag', label: 'Bag', emoji: '👜', slot: 'bag' },
  { id: 'jewelry', label: 'Jewelry / Accessory', emoji: '💍', slot: 'jewelry' },
]

const SUBCATEGORIES_BY_CATEGORY: Record<string, string[]> = {
  top: ['T-Shirt', 'Shirt', 'Blouse', 'Crop Top', 'Kurta', 'Sweater', 'Tank'],
  bottom: ['Jeans', 'Trousers', 'Pants', 'Skirt', 'Shorts', 'Palazzo', 'Salwar', 'Leggings'],
  dress: ['Maxi Dress', 'Midi Dress', 'Mini Dress', 'Jumpsuit', 'Evening Gown'],
  saree: ['Silk Saree', 'Cotton Saree', 'Chiffon Saree', 'Georgette Saree', 'Party Saree'],
  ethnic_set: ['Kurta Set', 'Anarkali', 'Lehenga', 'Co-ord Set'],
  layer: ['Blazer', 'Jacket', 'Cardigan', 'Shrug', 'Coat', 'Dupatta'],
  shoes: ['Sneakers', 'Sandals', 'Heels', 'Flats', 'Boots', 'Loafers', 'Juttis'],
  bag: ['Handbag', 'Tote', 'Crossbody', 'Clutch', 'Backpack'],
  jewelry: ['Necklace', 'Earrings', 'Bracelet', 'Watch', 'Scarf', 'Belt'],
}

const COLOR_SWATCHES = [
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
  { id: 'olive', label: 'Olive', hex: '#6b7c3e' },
  { id: 'grey', label: 'Grey', hex: '#8e8e93' },
]

const FITS = ['Regular', 'Slim', 'Relaxed', 'Oversized']
const PATTERNS = ['solid', 'floral', 'striped', 'printed', 'plaid']
const FORMALITY_LABELS = ['Casual', 'Smart Casual', 'Formal', 'Festive / Wedding']

export default function WardrobePage() {
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()

  // State
  const [items, setItems] = useState<WardrobeItem[]>([])
  const [coverage, setCoverage] = useState<WardrobeCoverageResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeFilter, setActiveFilter] = useState<string>('all')

  // Modals
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<WardrobeItem | null>(null)
  const [deleteConfirmItem, setDeleteConfirmItem] = useState<WardrobeItem | null>(null)
  const [isDeleteAccountOpen, setIsDeleteAccountOpen] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  // Redirect if unauthenticated
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login?redirect=/wardrobe', { replace: true })
    }
  }, [authLoading, user, navigate])

  // Load wardrobe data
  const loadWardrobeData = useCallback(async () => {
    if (!user) return
    setLoading(true)
    setError(null)
    try {
      const [listRes, covRes] = await Promise.all([
        api.wardrobe.list({ pageSize: 100 }),
        api.wardrobe.coverage(),
      ])
      setItems(listRes.items || [])
      setCoverage(covRes)
    } catch (err: any) {
      setError(err?.message || 'Failed to load wardrobe data.')
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    if (user) {
      loadWardrobeData()
    }
  }, [user, loadWardrobeData])

  // Filtered items
  const filteredItems = useMemo(() => {
    if (activeFilter === 'all') return items
    if (activeFilter === 'needs_review') return items.filter((i) => i.needs_review)
    return items.filter((i) => i.slot === activeFilter || i.category === activeFilter)
  }, [items, activeFilter])

  // Delete an item
  const handleDeleteItem = async (item: WardrobeItem) => {
    setActionLoading(true)
    try {
      await api.wardrobe.delete(item.id)
      setDeleteConfirmItem(null)
      await loadWardrobeData()
    } catch (err: any) {
      alert(err?.message || 'Failed to delete item.')
    } finally {
      setActionLoading(false)
    }
  }

  // Export data
  const handleExportData = async () => {
    try {
      const data = await api.account.exportData()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `flashfit_wardrobe_export_${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err: any) {
      alert(err?.message || 'Failed to export data.')
    }
  }

  // Delete account
  const handleDeleteAccount = async () => {
    if (!confirm('Are you absolutely sure? This will delete all your clothes, profile, and data permanently.')) {
      return
    }
    setActionLoading(true)
    try {
      await api.account.deleteAccount()
      alert('Account and all wardrobe assets successfully deleted.')
      navigate('/', { replace: true })
      window.location.reload()
    } catch (err: any) {
      alert(err?.message || 'Failed to delete account.')
    } finally {
      setActionLoading(false)
    }
  }

  if (authLoading || (loading && items.length === 0)) {
    return (
      <div className="wardrobe-loading-screen">
        <div className="wardrobe-spinner" />
        <p>Opening your digital closet…</p>
      </div>
    )
  }

  return (
    <div className="wardrobe-page">
      <Navigation />

      {/* Top Header */}
      <div className="wardrobe-header">
        <div className="wardrobe-header-content">
          <div>
            <div className="wardrobe-badge-tag">
              <Sparkles className="w-3.5 h-3.5 text-accent" />
              Private Digital Wardrobe
            </div>
            <h1 className="wardrobe-title">My Wardrobe</h1>
            <p className="wardrobe-subtitle">
              Upload clothes, manage styles, and view outfit readiness across all slots.
            </p>
          </div>

          <div className="wardrobe-header-actions">
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportData}
              className="gap-2 text-xs"
              title="Export all wardrobe and profile data as JSON"
            >
              <Download className="w-4 h-4" />
              Export Data
            </Button>

            <Link to="/outfits">
              <Button
                variant="outline"
                className="gap-2 border-primary/40 text-primary hover:bg-primary/10"
              >
                <Sparkles className="w-4 h-4 text-accent" />
                Generate Outfits
              </Button>
            </Link>

            <Button
              onClick={() => setIsUploadModalOpen(true)}
              className="gap-2 bg-primary hover:bg-primary/90 text-primary-foreground shadow-md"
            >
              <Plus className="w-4 h-4" />
              Add Item
            </Button>
          </div>
        </div>
      </div>

      {/* Main Container */}
      <div className="wardrobe-container">
        {error && (
          <div className="wardrobe-alert-error">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Slot Coverage Summary Card */}
        {coverage && (
          <div className="wardrobe-coverage-card">
            <div className="coverage-card-header">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-primary" />
                <h2 className="text-lg font-semibold text-foreground">Outfit Slot Coverage</h2>
              </div>

              {coverage.is_ready_for_outfits ? (
                <div className="flex items-center gap-2">
                  <div className="coverage-ready-badge">
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                    <span>Ready for Outfits</span>
                  </div>
                  <Link to="/outfits">
                    <Button size="sm" className="gap-1.5 bg-primary text-primary-foreground text-xs h-8">
                      <Sparkles className="w-3.5 h-3.5" />
                      Create Looks
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="coverage-incomplete-badge">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  <span>Coverage Needed</span>
                </div>
              )}
            </div>

            {/* Critical Warnings */}
            {!coverage.is_ready_for_outfits && coverage.critical_missing.length > 0 && (
              <div className="coverage-warning-banner">
                <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                <span>
                  To generate full outfits, your wardrobe needs at least:{' '}
                  <strong>
                    {coverage.critical_missing.includes('shoes') && '👟 1 pair of shoes '}
                    {coverage.critical_missing.includes('tops_or_one_piece') && '👚 1 top or dress '}
                    {coverage.critical_missing.includes('bottoms') && '👖 1 bottom '}
                  </strong>
                </span>
              </div>
            )}

            {/* Slot Pillars Grid */}
            <div className="coverage-pillars-grid">
              <div className={`pillar-card ${coverage.core_coverage.tops > 0 ? 'covered' : 'empty'}`}>
                <div className="pillar-icon">👚</div>
                <div className="pillar-info">
                  <span className="pillar-name">Tops</span>
                  <span className="pillar-count">{coverage.core_coverage.tops} items</span>
                </div>
              </div>

              <div className={`pillar-card ${coverage.core_coverage.bottoms > 0 ? 'covered' : 'empty'}`}>
                <div className="pillar-icon">👖</div>
                <div className="pillar-info">
                  <span className="pillar-name">Bottoms</span>
                  <span className="pillar-count">{coverage.core_coverage.bottoms} items</span>
                </div>
              </div>

              <div className={`pillar-card ${coverage.core_coverage.one_piece > 0 ? 'covered' : 'empty'}`}>
                <div className="pillar-icon">👗</div>
                <div className="pillar-info">
                  <span className="pillar-name">Dresses / Sarees</span>
                  <span className="pillar-count">{coverage.core_coverage.one_piece} items</span>
                </div>
              </div>

              <div className={`pillar-card ${coverage.core_coverage.shoes > 0 ? 'covered' : 'empty'}`}>
                <div className="pillar-icon">👟</div>
                <div className="pillar-info">
                  <span className="pillar-name">Shoes</span>
                  <span className="pillar-count">{coverage.core_coverage.shoes} items</span>
                </div>
              </div>

              <div className={`pillar-card ${coverage.core_coverage.layers > 0 ? 'covered' : 'optional'}`}>
                <div className="pillar-icon">🧥</div>
                <div className="pillar-info">
                  <span className="pillar-name">Layers</span>
                  <span className="pillar-count">{coverage.core_coverage.layers} items</span>
                </div>
              </div>

              <div className={`pillar-card ${coverage.core_coverage.accessories > 0 ? 'covered' : 'optional'}`}>
                <div className="pillar-icon">👜</div>
                <div className="pillar-info">
                  <span className="pillar-name">Accessories</span>
                  <span className="pillar-count">{coverage.core_coverage.accessories} items</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Filter Navigation */}
        <div className="wardrobe-filter-bar">
          <div className="filter-chips-scroll">
            <button
              className={`filter-chip ${activeFilter === 'all' ? 'active' : ''}`}
              onClick={() => setActiveFilter('all')}
            >
              All Items ({items.length})
            </button>

            {coverage && coverage.needs_review_count > 0 && (
              <button
                className={`filter-chip review-chip ${activeFilter === 'needs_review' ? 'active' : ''}`}
                onClick={() => setActiveFilter('needs_review')}
              >
                ⚠️ Needs Review ({coverage.needs_review_count})
              </button>
            )}

            <button
              className={`filter-chip ${activeFilter === 'top' ? 'active' : ''}`}
              onClick={() => setActiveFilter('top')}
            >
              Tops
            </button>
            <button
              className={`filter-chip ${activeFilter === 'bottom' ? 'active' : ''}`}
              onClick={() => setActiveFilter('bottom')}
            >
              Bottoms
            </button>
            <button
              className={`filter-chip ${activeFilter === 'dress' ? 'active' : ''}`}
              onClick={() => setActiveFilter('dress')}
            >
              Dresses
            </button>
            <button
              className={`filter-chip ${activeFilter === 'saree' ? 'active' : ''}`}
              onClick={() => setActiveFilter('saree')}
            >
              Sarees
            </button>
            <button
              className={`filter-chip ${activeFilter === 'shoes' ? 'active' : ''}`}
              onClick={() => setActiveFilter('shoes')}
            >
              Shoes
            </button>
            <button
              className={`filter-chip ${activeFilter === 'layer' ? 'active' : ''}`}
              onClick={() => setActiveFilter('layer')}
            >
              Outerwear
            </button>
            <button
              className={`filter-chip ${activeFilter === 'bag' ? 'active' : ''}`}
              onClick={() => setActiveFilter('bag')}
            >
              Bags
            </button>
            <button
              className={`filter-chip ${activeFilter === 'jewelry' ? 'active' : ''}`}
              onClick={() => setActiveFilter('jewelry')}
            >
              Jewelry
            </button>
          </div>
        </div>

        {/* Wardrobe Items Grid */}
        {filteredItems.length === 0 ? (
          <div className="wardrobe-empty-state">
            <div className="empty-state-icon">✨</div>
            <h3 className="empty-state-title">
              {activeFilter === 'all' ? 'Your closet is empty' : 'No items match this filter'}
            </h3>
            <p className="empty-state-desc">
              {activeFilter === 'all'
                ? 'Add your favorite tops, bottoms, and shoes to start generating custom personalized outfits.'
                : 'Try switching filters or add a new piece to your wardrobe.'}
            </p>
            <Button onClick={() => setIsUploadModalOpen(true)} className="gap-2">
              <Plus className="w-4 h-4" />
              Add Your First Item
            </Button>
          </div>
        ) : (
          <div className="wardrobe-grid">
            {filteredItems.map((item) => (
              <div key={item.id} className="wardrobe-card">
                {/* Image */}
                <div className="card-image-wrap">
                  <img
                    src={item.signed_thumbnail_url || item.signed_image_url || '/placeholder.svg'}
                    alt={item.sub_category || item.category}
                    className="card-image"
                    loading="lazy"
                  />
                  {item.needs_review && (
                    <div className="card-badge-review" title="Tags were auto-derived; click Edit to confirm">
                      Needs Review
                    </div>
                  )}
                  <div className="card-slot-tag">{item.slot}</div>
                </div>

                {/* Info */}
                <div className="card-content">
                  <div className="card-title-row">
                    <h3 className="card-title">
                      {item.sub_category || item.category}
                    </h3>
                    {item.fit && <span className="card-fit-badge">{item.fit}</span>}
                  </div>

                  <div className="card-tags-row">
                    {item.primary_color && (
                      <span className="color-indicator" title={item.primary_color}>
                        <span
                          className="swatch-dot"
                          style={{
                            backgroundColor:
                              COLOR_SWATCHES.find((c) => c.id === item.primary_color?.toLowerCase())?.hex ||
                              item.primary_color,
                          }}
                        />
                        {item.primary_color}
                      </span>
                    )}
                    <span className="formality-badge">
                      {FORMALITY_LABELS[item.formality] || 'Casual'}
                    </span>
                  </div>

                  {item.occasions && item.occasions.length > 0 && (
                    <div className="card-occasions">
                      {item.occasions.slice(0, 3).map((occ) => (
                        <span key={occ} className="occ-pill">
                          {occ}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="card-actions">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setEditingItem(item)}
                      className="edit-btn gap-1.5 flex-1"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                      {item.needs_review ? 'Review Tags' : 'Edit'}
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleteConfirmItem(item)}
                      className="delete-btn text-destructive hover:bg-destructive/10"
                      title="Delete item"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Data Privacy & Account Deletion Footer */}
        <div className="wardrobe-privacy-footer">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">
              All images and style tags are private to your account and enforced with Supabase RLS.
            </span>
          </div>

          <button
            onClick={() => setIsDeleteAccountOpen(true)}
            className="text-xs text-destructive/80 hover:text-destructive underline"
          >
            Manage Data & Delete Account
          </button>
        </div>
      </div>

      <Footer />

      {/* Upload & Quick-Tag Modal */}
      {isUploadModalOpen && (
        <UploadModal
          onClose={() => setIsUploadModalOpen(false)}
          onSuccess={async () => {
            setIsUploadModalOpen(false)
            await loadWardrobeData()
          }}
        />
      )}

      {/* Edit Tags Modal */}
      {editingItem && (
        <EditItemModal
          item={editingItem}
          onClose={() => setEditingItem(null)}
          onSuccess={async () => {
            setEditingItem(null)
            await loadWardrobeData()
          }}
        />
      )}

      {/* Delete Item Confirmation Modal */}
      {deleteConfirmItem && (
        <div className="modal-backdrop">
          <div className="modal-card modal-confirm">
            <h3 className="modal-title text-destructive flex items-center gap-2">
              <Trash2 className="w-5 h-5" />
              Delete Wardrobe Item?
            </h3>
            <p className="text-sm text-muted-foreground mt-2">
              Are you sure you want to delete this {deleteConfirmItem.sub_category || deleteConfirmItem.category}? Its
              image and tags will be permanently removed from your private storage.
            </p>
            <div className="modal-actions mt-6">
              <Button
                variant="outline"
                onClick={() => setDeleteConfirmItem(null)}
                disabled={actionLoading}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => handleDeleteItem(deleteConfirmItem)}
                disabled={actionLoading}
              >
                {actionLoading ? 'Deleting…' : 'Delete Item'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Account Modal */}
      {isDeleteAccountOpen && (
        <div className="modal-backdrop">
          <div className="modal-card modal-confirm">
            <h3 className="modal-title text-destructive flex items-center gap-2">
              <ShieldAlert className="w-5 h-5" />
              Account & Data Purge
            </h3>
            <p className="text-sm text-muted-foreground mt-2">
              This action permanently purges:
            </p>
            <ul className="text-xs text-muted-foreground list-disc list-inside mt-2 space-y-1">
              <li>All uploaded wardrobe photos and thumbnails in private storage</li>
              <li>All wardrobe catalog items and tag metadata</li>
              <li>Your style profile and stored body-fit guidance</li>
              <li>All active shopping carts and user consent logs</li>
            </ul>
            <div className="modal-actions mt-6">
              <Button
                variant="outline"
                onClick={() => setIsDeleteAccountOpen(false)}
                disabled={actionLoading}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteAccount}
                disabled={actionLoading}
              >
                {actionLoading ? 'Purging…' : 'Purge Everything & Delete'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// -------------------------------------------------------------------------
// Upload & Quick-Tag Modal Component
// -------------------------------------------------------------------------

function UploadModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void
  onSuccess: () => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [category, setCategory] = useState<string>('top')
  const [subCategory, setSubCategory] = useState<string>('T-Shirt')
  const [primaryColor, setPrimaryColor] = useState<string>('black')
  const [fit, setFit] = useState<string>('Regular')
  const [pattern, setPattern] = useState<string>('solid')
  const [notes, setNotes] = useState<string>('')
  const [uploading, setUploading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // AI Auto-Tag State
  const [aiSuggesting, setAiSuggesting] = useState<boolean>(false)
  const [aiSuggestedInfo, setAiSuggestedInfo] = useState<string | null>(null)
  const [showConsentModal, setShowConsentModal] = useState<boolean>(false)
  const [consentConfirmed, setConsentConfirmed] = useState<boolean>(false)

  const handleRequestAiTags = async () => {
    if (!file) {
      setError('Please choose a garment photo first.')
      return
    }
    const storedConsent = localStorage.getItem('wardrobe_ai_consent') === 'true'
    if (!storedConsent && !consentConfirmed) {
      setShowConsentModal(true)
      return
    }
    await executeAiTagSuggestion(true)
  }

  const executeAiTagSuggestion = async (consent: boolean) => {
    if (!file) return
    setAiSuggesting(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('consent_confirmed', String(consent))

      const res = await api.wardrobe.suggestTags(formData)
      if (res.category) {
        setCategory(res.category)
        const available = SUBCATEGORIES_BY_CATEGORY[res.category] || []
        if (res.sub_category && available.includes(res.sub_category)) {
          setSubCategory(res.sub_category)
        } else if (available.length) {
          setSubCategory(available[0])
        }
      }
      if (res.primary_color) setPrimaryColor(res.primary_color)
      if (res.fit) setFit(res.fit.charAt(0).toUpperCase() + res.fit.slice(1))
      if (res.pattern) setPattern(res.pattern)

      setAiSuggestedInfo(
        `AI proposed: ${res.category} • ${res.sub_category || ''} (${res.primary_color}). Please review & adjust below!`
      )
      localStorage.setItem('wardrobe_ai_consent', 'true')
      setConsentConfirmed(true)
      setShowConsentModal(false)
    } catch (err: any) {
      setError(err?.message || 'AI tag suggestion failed. You can choose tags manually below.')
    } finally {
      setAiSuggesting(false)
    }
  }

  // Handle category change -> default subcategory
  const handleCategoryChange = (cat: string) => {
    setCategory(cat)
    const available = SUBCATEGORIES_BY_CATEGORY[cat] || []
    setSubCategory(available[0] || '')
  }

  // File selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (!selected) return

    // Quick client-side size check (10MB)
    if (selected.size > 10 * 1024 * 1024) {
      setError('File exceeds 10 MB limit.')
      return
    }

    setFile(selected)
    setPreviewUrl(URL.createObjectURL(selected))
    setError(null)
  }

  // Submit flow
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      setError('Please select an image of your garment.')
      return
    }

    setUploading(true)
    setError(null)

    try {
      // Step 1: Request signed upload URL from FastAPI
      const session = await api.wardrobe.getUploadUrl(file.name, file.type || 'image/jpeg')

      // Step 2: Upload directly to Supabase Storage via signed URL
      let directUploadSuccess = false
      try {
        const uploadRes = await fetch(session.upload_url, {
          method: 'PUT',
          body: file,
          headers: {
            'Content-Type': file.type || 'image/jpeg',
          },
        })
        if (uploadRes.ok) {
          directUploadSuccess = true
        }
      } catch (uploadErr) {
        // Fallback to direct multipart upload endpoint if direct storage fails (e.g. CORS)
        directUploadSuccess = false
      }

      if (directUploadSuccess) {
        // Step 3: Finalize upload with FastAPI (Pillow sanitization, EXIF stripping, tag derivation)
        const payload: FinalizeUploadPayload = {
          storage_path: session.storage_path,
          category,
          sub_category: subCategory,
          primary_color: primaryColor,
          fit,
          pattern,
          notes: notes.trim() || null,
        }
        await api.wardrobe.finalizeUpload(payload)
      } else {
        // Fallback: Direct multipart upload to FastAPI endpoint
        const formData = new FormData()
        formData.append('file', file)
        formData.append('category', category)
        if (subCategory) formData.append('sub_category', subCategory)
        if (primaryColor) formData.append('primary_color', primaryColor)
        if (fit) formData.append('fit', fit)
        if (pattern) formData.append('pattern', pattern)
        if (notes.trim()) formData.append('notes', notes.trim())

        await api.wardrobe.directUpload(formData)
      }

      onSuccess()
    } catch (err: any) {
      setError(err?.message || 'Failed to upload and process item.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="modal-card modal-upload">
        <div className="modal-header">
          <div>
            <h2 className="modal-title">Add Garment to Wardrobe</h2>
            <p className="modal-subtitle">
              Upload a clear photo. We will sanitize the image and auto-derive styling tags.
            </p>
          </div>
          <button onClick={onClose} className="modal-close-btn" disabled={uploading}>
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          {error && <div className="modal-error">{error}</div>}

          {/* Photo Dropzone / Picker */}
          <div className="upload-dropzone">
            {previewUrl ? (
              <div className="preview-wrap">
                <img src={previewUrl} alt="Preview" className="preview-img" />
                <label htmlFor="file-change" className="change-photo-btn">
                  Change Photo
                  <input
                    id="file-change"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handleFileChange}
                    className="hidden"
                    disabled={uploading}
                  />
                </label>
              </div>
            ) : (
              <label htmlFor="file-input" className="dropzone-label">
                <Upload className="w-8 h-8 text-primary/70 mb-2" />
                <span className="font-medium text-foreground">Click or drop garment photo</span>
                <span className="text-xs text-muted-foreground mt-1">JPEG, PNG, or WebP up to 10 MB</span>
                <input
                  id="file-input"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileChange}
                  className="hidden"
                  disabled={uploading}
                />
              </label>
            )}
          </div>

          {/* AI Auto-Tag Assist Trigger */}
          {file && (
            <div className="flex items-center justify-between p-3 bg-primary/10 border border-primary/25 rounded-xl my-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-accent" />
                <span className="text-xs text-foreground font-medium">Auto-detect tags with AI?</span>
              </div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={handleRequestAiTags}
                disabled={aiSuggesting || uploading}
                className="text-xs gap-1.5 border-primary/40 text-primary hover:bg-primary/20 h-8"
              >
                {aiSuggesting ? 'Analyzing Photo…' : '✨ Suggest Tags with AI'}
              </Button>
            </div>
          )}

          {aiSuggestedInfo && (
            <div className="flex items-center gap-2 p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-emerald-400 my-2">
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
              <span>{aiSuggestedInfo}</span>
            </div>
          )}

          {/* Quick-Tag Fields */}
          <div className="quicktag-section">
            <h4 className="section-heading">Quick Tags</h4>

            {/* Category */}
            <div className="form-group">
              <label className="form-label">Garment Category</label>
              <div className="category-chips-grid">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    className={`category-chip ${category === cat.id ? 'active' : ''}`}
                    onClick={() => handleCategoryChange(cat.id)}
                    disabled={uploading}
                  >
                    <span>{cat.emoji}</span>
                    <span>{cat.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Subcategory */}
            {SUBCATEGORIES_BY_CATEGORY[category] && (
              <div className="form-group">
                <label className="form-label">Specific Subtype</label>
                <select
                  value={subCategory}
                  onChange={(e) => setSubCategory(e.target.value)}
                  className="form-select"
                  disabled={uploading}
                >
                  {SUBCATEGORIES_BY_CATEGORY[category].map((sub) => (
                    <option key={sub} value={sub}>
                      {sub}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Primary Color */}
            <div className="form-group">
              <label className="form-label">Primary Color</label>
              <div className="colors-grid">
                {COLOR_SWATCHES.map((swatch) => (
                  <button
                    key={swatch.id}
                    type="button"
                    className={`color-pick-btn ${primaryColor === swatch.id ? 'selected' : ''}`}
                    onClick={() => setPrimaryColor(swatch.id)}
                    title={swatch.label}
                    disabled={uploading}
                  >
                    <span className="swatch-color" style={{ backgroundColor: swatch.hex }} />
                    <span className="swatch-name">{swatch.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Fit & Pattern */}
            <div className="form-row-2">
              <div className="form-group">
                <label className="form-label">Fit Silhouette</label>
                <select
                  value={fit}
                  onChange={(e) => setFit(e.target.value)}
                  className="form-select"
                  disabled={uploading}
                >
                  {FITS.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Pattern</label>
                <select
                  value={pattern}
                  onChange={(e) => setPattern(e.target.value)}
                  className="form-select"
                  disabled={uploading}
                >
                  {PATTERNS.map((p) => (
                    <option key={p} value={p}>
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Notes */}
            <div className="form-group">
              <label className="form-label">Private Notes (Optional)</label>
              <input
                type="text"
                placeholder="e.g. Linen shirt for summer brunch"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="form-input"
                disabled={uploading}
              />
            </div>

            <div className="taxonomy-callout">
              <Sparkles className="w-4 h-4 text-primary flex-shrink-0" />
              <span>
                Styling tags (occasions, seasons, formality, archetype) will be derived automatically and
                placed in <strong>Needs Review</strong> status for your inspection.
              </span>
            </div>
          </div>

          <div className="modal-actions">
            <Button type="button" variant="outline" onClick={onClose} disabled={uploading}>
              Cancel
            </Button>
            <Button type="submit" disabled={uploading || !file}>
              {uploading ? 'Processing Image…' : 'Add to Closet ✨'}
            </Button>
          </div>
        </form>

        {/* Specific Consent Modal for AI Photo Tagging */}
        {showConsentModal && (
          <div className="modal-backdrop">
            <div className="modal-card modal-confirm">
              <h3 className="modal-title flex items-center gap-2 text-foreground">
                <Sparkles className="w-5 h-5 text-accent" />
                Consent for AI Garment Tagging
              </h3>
              <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
                FlashFit can inspect your photo to suggest category, color, fit, and pattern.
              </p>
              <ul className="text-xs text-muted-foreground list-disc list-inside space-y-1 my-3 bg-muted/40 p-3 rounded-lg border border-border">
                <li>Only the sanitized garment image is sent to OpenRouter.</li>
                <li><strong>No personal profile data or body measurements are ever sent.</strong></li>
                <li>All suggested tags are proposed for your confirmation before saving.</li>
              </ul>
              <div className="modal-actions mt-5">
                <Button variant="outline" size="sm" onClick={() => setShowConsentModal(false)}>
                  Cancel (Tag Manually)
                </Button>
                <Button
                  size="sm"
                  className="bg-primary text-primary-foreground"
                  onClick={() => executeAiTagSuggestion(true)}
                  disabled={aiSuggesting}
                >
                  {aiSuggesting ? 'Analyzing…' : 'I Consent & Suggest Tags'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// -------------------------------------------------------------------------
// Edit Item Modal Component
// -------------------------------------------------------------------------

function EditItemModal({
  item,
  onClose,
  onSuccess,
}: {
  item: WardrobeItem
  onClose: () => void
  onSuccess: () => void
}) {
  const [subCategory, setSubCategory] = useState<string>(item.sub_category || '')
  const [slot, setSlot] = useState<string>(item.slot)
  const [primaryColor, setPrimaryColor] = useState<string>(item.primary_color || '')
  const [fit, setFit] = useState<string>(item.fit || 'Regular')
  const [formality, setFormality] = useState<number>(item.formality)
  const [occasions, setOccasions] = useState<string[]>(item.occasions || [])
  const [notes, setNotes] = useState<string>(item.notes || '')
  const [markReviewed, setMarkReviewed] = useState<boolean>(true)
  const [saving, setSaving] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const ALL_OCCASIONS = ['casual', 'college', 'work', 'party', 'formal', 'festive', 'wedding', 'lounge']

  const toggleOccasion = (occ: string) => {
    setOccasions((prev) => (prev.includes(occ) ? prev.filter((o) => o !== occ) : [...prev, occ]))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const payload: WardrobeUpdatePayload = {
        sub_category: subCategory.trim() || null,
        slot,
        primary_color: primaryColor,
        fit,
        formality,
        occasions,
        notes: notes.trim() || null,
        needs_review: markReviewed ? false : item.needs_review,
      }
      await api.wardrobe.update(item.id, payload)
      onSuccess()
    } catch (err: any) {
      setError(err?.message || 'Failed to update tags.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="modal-card modal-edit">
        <div className="modal-header">
          <div>
            <h2 className="modal-title">Review & Edit Garment Tags</h2>
            <p className="modal-subtitle">Confirm or adjust auto-derived attributes for accurate outfit matching.</p>
          </div>
          <button onClick={onClose} className="modal-close-btn" disabled={saving}>
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          {error && <div className="modal-error">{error}</div>}

          <div className="edit-grid-2">
            <div>
              <img
                src={item.signed_image_url || item.signed_thumbnail_url || '/placeholder.svg'}
                alt="Item"
                className="edit-preview-img"
              />
            </div>

            <div className="space-y-4">
              <div className="form-group">
                <label className="form-label">Garment Subtype</label>
                <input
                  type="text"
                  value={subCategory}
                  onChange={(e) => setSubCategory(e.target.value)}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Skeleton Slot</label>
                <select value={slot} onChange={(e) => setSlot(e.target.value)} className="form-select">
                  <option value="top">Top</option>
                  <option value="bottom">Bottom</option>
                  <option value="ethnic_bottom">Ethnic Bottom</option>
                  <option value="dress">Dress</option>
                  <option value="saree">Saree</option>
                  <option value="ethnic_set">Ethnic Set</option>
                  <option value="layer">Layer / Outerwear</option>
                  <option value="shoes">Shoes</option>
                  <option value="bag">Bag</option>
                  <option value="jewelry">Jewelry</option>
                  <option value="dupatta">Dupatta</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Formality Level</label>
                <div className="formality-options">
                  {[0, 1, 2, 3].map((level) => (
                    <button
                      key={level}
                      type="button"
                      className={`formality-chip ${formality === level ? 'active' : ''}`}
                      onClick={() => setFormality(level)}
                    >
                      {FORMALITY_LABELS[level]}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Occasions */}
          <div className="form-group">
            <label className="form-label">Suitable Occasions</label>
            <div className="occasions-chip-wrap">
              {ALL_OCCASIONS.map((occ) => (
                <button
                  key={occ}
                  type="button"
                  className={`occ-chip ${occasions.includes(occ) ? 'active' : ''}`}
                  onClick={() => toggleOccasion(occ)}
                >
                  {occ.charAt(0).toUpperCase() + occ.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Mark Reviewed Checkbox */}
          {item.needs_review && (
            <div className="review-confirm-box">
              <label className="flex items-center gap-2 cursor-pointer text-sm font-medium">
                <input
                  type="checkbox"
                  checked={markReviewed}
                  onChange={(e) => setMarkReviewed(e.target.checked)}
                />
                <span>Confirm tags and mark this item as reviewed</span>
              </label>
            </div>
          )}

          <div className="modal-actions">
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving…' : 'Save Changes'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
