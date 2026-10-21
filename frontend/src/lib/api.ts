import { getSupabaseClient } from './supabase'

export interface ProductItem {
  id: string
  name: string
  description?: string
  price: number
  originalPrice?: number
  price_cents?: number
  category: string
  image: string
  colors: string[]
  sizes: string[]
  isNew: boolean
  isSale: boolean
  audience?: string
  slot?: string | null
  subtype?: string | null
  color_tags?: string[]
  formality?: number | null
  style_tags?: string[]
  occasions?: string[]
  seasons?: string[]
  fit?: string | null
  pattern?: string | null
  stock?: number
}

export interface ProductsResponse {
  items: ProductItem[]
  total: number
  nextOffset: number | null
  hasMore: boolean
}

export interface CartItemResponse {
  id: string
  cartId: string
  productId: string
  quantity: number
  selectedColor?: string | null
  selectedSize?: string | null
  createdAt?: string
  updatedAt?: string
  product?: {
    id: string
    name: string
    description?: string
    priceCents: number
    imageUrl?: string | null
    category?: string | null
  }
}

export interface CartResponse {
  cartId: string
  items: CartItemResponse[]
  totalCents: number
  total: number
  itemCount: number
}

export interface AiChatResponse {
  message: string
  recommendedProductIds: string[]
  source: string
}

export interface AnalyticsStatsResponse {
  totalEvents: number
  totalSessions: number
  totalPageViews: number
  totalProductViews: number
  totalSearches: number
  topPages: { page: string; count: number }[]
  topProducts: { product_id: string; count: number }[]
  recentEvents: {
    id: string
    event_type: string
    event_data: any
    created_at: string
  }[]
  eventsByType: { event_type: string; count: number }[]
}

function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || '/api/v1'
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl().replace(/\/+$/, '')
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  const url = `${baseUrl}${cleanEndpoint}`

  const headers = new Headers(options.headers || {})
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  try {
    const supabase = getSupabaseClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (session?.access_token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${session.access_token}`)
    }
  } catch (err) {
    // Session retrieval failed; proceed unauthenticated
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`
    try {
      const errorJson = await response.json()
      errorDetail = errorJson.detail || errorJson.error || errorDetail
    } catch {
      // Body not JSON
    }
    throw new Error(errorDetail)
  }

  if (response.status === 204) {
    return {} as T
  }

  return response.json() as Promise<T>
}

export const api = {
  products: {
    list: (params: {
      category?: string
      q?: string
      sort?: string
      limit?: number
      offset?: number
      styleTag?: string
      occasion?: string
      season?: string
    } = {}) => {
      const query = new URLSearchParams()
      if (params.category && params.category !== 'all') query.set('category', params.category)
      // The public API uses `search`; retain `q` here as the concise UI-facing
      // parameter used by the rack URL.
      if (params.q) query.set('search', params.q)
      const sortMap: Record<string, string> = {
        newest: 'featured',
        price_asc: 'price-low',
        price_desc: 'price-high',
      }
      if (params.sort) query.set('sort', sortMap[params.sort] || params.sort)
      if (params.limit !== undefined) query.set('limit', params.limit.toString())
      if (params.offset !== undefined) query.set('offset', params.offset.toString())
      if (params.styleTag) query.set('style_tag', params.styleTag)
      if (params.occasion) query.set('occasion', params.occasion)
      if (params.season) query.set('season', params.season)

      const qs = query.toString()
      return request<ProductsResponse>(`/products${qs ? `?${qs}` : ''}`)
    },

    get: (id: string) => {
      return request<ProductItem>(`/products/${id}`)
    },

    create: (data: {
      name: string
      description?: string
      price_cents: number
      category: string
      image_url?: string
      colors?: string[]
      sizes?: string[]
      style_tags?: string[]
      occasions?: string[]
      seasons?: string[]
      slot?: string
      subtype?: string
      fit?: string
    }) => {
      return request<ProductItem>('/products', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },

    delete: (id: string) => {
      return request<{ success: boolean; deleted_id: string }>(`/products/${id}`, {
        method: 'DELETE',
      })
    },
  },

  cart: {
    get: () => request<CartResponse>('/cart'),

    add: (item: {
      productId: string
      quantity?: number
      selectedColor?: string | null
      selectedSize?: string | null
    }) => {
      return request<CartItemResponse>('/cart', {
        method: 'POST',
        body: JSON.stringify(item),
      })
    },

    update: (itemId: string, quantity: number) => {
      return request<CartItemResponse>(`/cart/${itemId}`, {
        method: 'PATCH',
        body: JSON.stringify({ quantity }),
      })
    },

    remove: (itemId: string) => {
      return request<{ success: boolean; removed_item_id: string }>(`/cart/${itemId}`, {
        method: 'DELETE',
      })
    },

    clear: () => {
      return request<{ success: boolean; cleared: boolean }>('/cart', {
        method: 'DELETE',
      })
    },
  },

  ai: {
    chat: (message: string, conversationHistory?: string) => {
      return request<AiChatResponse>('/ai-chat', {
        method: 'POST',
        body: JSON.stringify({ message, conversationHistory }),
      })
    },
  },

  analytics: {
    track: (data: {
      eventType: string
      eventData?: Record<string, any>
      sessionId?: string
      pageUrl?: string
      referrer?: string
    }) => {
      return request<{ success: boolean; id?: string }>('/analytics/track', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },

    stats: () => request<AnalyticsStatsResponse>('/analytics/stats'),
  },

  admin: {
    status: () => request<any>('/admin/status'),
  },

  styleProfile: {
    get: () => request<StyleProfileResponse>('/style-profile'),

    update: (data: StyleProfileUpdate) =>
      request<StyleProfileResponse>('/style-profile', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),

    deleteBodyGuidance: () =>
      request<{ success: boolean; message: string }>('/style-profile/body-guidance', {
        method: 'DELETE',
      }),

    getConsents: () => request<ConsentListResponse>('/style-profile/consents'),

    setConsent: (consentType: string, granted: boolean) =>
      request<ConsentRecord>('/style-profile/consents', {
        method: 'PUT',
        body: JSON.stringify({ consent_type: consentType, granted }),
      }),
  },

  wardrobe: {
    list: (params?: {
      slot?: string
      category?: string
      needs_review?: boolean
      page?: number
      pageSize?: number
    }) => {
      const query = new URLSearchParams()
      if (params?.slot) query.set('slot', params.slot)
      if (params?.category) query.set('category', params.category)
      if (params?.needs_review !== undefined) query.set('needs_review', String(params.needs_review))
      if (params?.page) query.set('page', String(params.page))
      if (params?.pageSize) query.set('page_size', String(params.pageSize))
      const qs = query.toString()
      return request<WardrobeListResponse>(`/wardrobe${qs ? `?${qs}` : ''}`)
    },

    coverage: () => request<WardrobeCoverageResponse>('/wardrobe/coverage'),

    get: (id: string) => request<WardrobeItem>(`/wardrobe/${id}`),

    getUploadUrl: (filename: string, contentType = 'image/jpeg') =>
      request<{ upload_url: string; token: string; storage_path: string }>('/wardrobe/upload-url', {
        method: 'POST',
        body: JSON.stringify({ filename, content_type: contentType }),
      }),

    finalizeUpload: (data: FinalizeUploadPayload) =>
      request<WardrobeItem>('/wardrobe/finalize-upload', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    directUpload: (formData: FormData) =>
      request<WardrobeItem>('/wardrobe/upload', {
        method: 'POST',
        body: formData,
      }),

    update: (id: string, data: WardrobeUpdatePayload) =>
      request<WardrobeItem>(`/wardrobe/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),

    suggestTags: (formData: FormData) =>
      request<TagSuggestionResponse>('/wardrobe/suggest-tags', {
        method: 'POST',
        body: formData,
      }),

    delete: (id: string) =>
      request<{ success: boolean; message: string }>(`/wardrobe/${id}`, {
        method: 'DELETE',
      }),
  },

  account: {
    exportData: () => request<Record<string, any>>('/auth/export'),
    deleteAccount: () => request<{ success: boolean; message: string }>('/auth/account', {
      method: 'DELETE',
    }),
  },

  outfits: {
    generate: (data: GenerateOutfitsPayload) =>
      request<GenerateOutfitsResponse>('/outfits/generate', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    getSaved: (tag?: string) => {
      const qs = tag ? `?tag=${encodeURIComponent(tag)}` : ''
      return request<SavedOutfitsListResponse>(`/outfits/saved${qs}`)
    },

    get: (id: string) => request<OutfitResponse>(`/outfits/${id}`),

    save: (id: string, tags?: string[]) =>
      request<{ success: boolean; message: string; is_saved: boolean; tags: string[] }>(`/outfits/${id}/save`, {
        method: 'POST',
        body: JSON.stringify(tags ? { tags } : {}),
      }),

    updateTags: (id: string, tags: string[]) =>
      request<{ success: boolean; tags: string[] }>(`/outfits/${id}/tags`, {
        method: 'PUT',
        body: JSON.stringify({ tags }),
      }),

    unsave: (id: string) =>
      request<{ success: boolean; message: string }>(`/outfits/${id}/save`, {
        method: 'DELETE',
      }),

    recordEvent: (outfitId: string, eventType: OutfitEventType, metadata?: Record<string, any>) =>
      request<OutfitEventResponse>(`/outfits/${outfitId}/events`, {
        method: 'POST',
        body: JSON.stringify({ event_type: eventType, metadata }),
      }),
  },

  styleDna: {
    get: () => request<StyleDnaResponse>('/style-dna'),

    reset: () =>
      request<{ success: boolean; message: string }>('/style-dna/reset', {
        method: 'POST',
      }),
  },

  gaps: {
    list: (params?: { occasion?: string; budgetMax?: number; limit?: number }) => {
      const query = new URLSearchParams()
      if (params?.occasion) query.set('occasion', params.occasion)
      if (params?.budgetMax !== undefined) query.set('budget_max', String(params.budgetMax))
      if (params?.limit !== undefined) query.set('limit', String(params.limit))
      const qs = query.toString()
      return request<GapAnalysisResponse>(`/gaps${qs ? `?${qs}` : ''}`)
    },
  },
}

// Style profile types
export interface StyleProfileResponse {
  user_id: string
  favorite_styles: string[]
  favorite_colors: string[]
  budget_min: number | null
  budget_max: number | null
  occasions: string[]
  body_type: string | null
  body_guidance: Record<string, any> | null
  onboarding_complete: boolean
  created_at: string | null
  updated_at: string | null
}

export interface StyleProfileUpdate {
  favorite_styles?: string[]
  favorite_colors?: string[]
  budget_min?: number | null
  budget_max?: number | null
  occasions?: string[]
  body_type?: string | null
  onboarding_complete?: boolean
}

export interface ConsentRecord {
  consent_type: string
  granted: boolean
  granted_at: string | null
  revoked_at: string | null
}

export interface ConsentListResponse {
  consents: ConsentRecord[]
}

// Wardrobe types
export interface WardrobeItem {
  id: string
  user_id: string
  image_url: string
  storage_path: string
  thumbnail_path?: string | null
  signed_image_url?: string | null
  signed_thumbnail_url?: string | null
  category: string
  slot: string
  sub_category?: string | null
  color_tags: string[]
  primary_color?: string | null
  fit?: string | null
  formality: number
  occasions: string[]
  seasons: string[]
  style_tags: string[]
  pattern?: string | null
  neckline?: string | null
  rise?: string | null
  length?: string | null
  notes?: string | null
  needs_review: boolean
  metadata: Record<string, any>
  created_at?: string | null
  updated_at?: string | null
}

export interface WardrobeListResponse {
  items: WardrobeItem[]
  total: number
  page: number
  page_size: number
}

export interface WardrobeCoverageResponse {
  total_items: number
  needs_review_count: number
  slots: Record<string, number>
  core_coverage: {
    tops: number
    bottoms: number
    one_piece: number
    shoes: number
    layers: number
    accessories: number
  }
  is_ready_for_outfits: boolean
  missing_slots: string[]
  critical_missing: string[]
}

export interface FinalizeUploadPayload {
  storage_path: string
  category: string
  sub_category?: string | null
  primary_color?: string | null
  fit?: string | null
  pattern?: string | null
  notes?: string | null
}

export interface WardrobeUpdatePayload {
  category?: string
  slot?: string
  sub_category?: string | null
  primary_color?: string | null
  color_tags?: string[]
  fit?: string | null
  formality?: number
  occasions?: string[]
  seasons?: string[]
  style_tags?: string[]
  pattern?: string | null
  neckline?: string | null
  rise?: string | null
  length?: string | null
  notes?: string | null
  needs_review?: boolean
}

export interface TagSuggestionResponse {
  category: string
  slot: string
  sub_category?: string | null
  primary_color: string
  color_tags: string[]
  fit?: string | null
  pattern?: string | null
  formality: number
  occasions: string[]
  seasons: string[]
  style_tags: string[]
  source: string
  requires_user_confirmation: boolean
  message?: string | null
}

// Outfit types
export interface GenerateOutfitsPayload {
  occasion: string
  vibe?: string
  season?: string
  wardrobe_only?: boolean
  allow_one_new_item?: boolean
  budget_max?: number
  min_quality_threshold?: number
  limit?: number
  seed?: number
  is_shuffle?: boolean
  exclude_core_signatures?: [string, string][][]
}

export interface OutfitSlotItem {
  slot: string
  source_type: string
  wardrobe_item_id?: string | null
  product_id?: string | null
  name: string
  category: string
  sub_category?: string | null
  primary_color?: string | null
  color_tags: string[]
  fit?: string | null
  price?: number | null
  price_cents?: number | null
  thumbnail_url?: string | null
  image_url?: string | null
}

export const APPROVED_OUTFIT_TAGS = ['Work', 'Date Night', 'Wedding', 'Vacation', 'Try Later'] as const
export type OutfitTag = typeof APPROVED_OUTFIT_TAGS[number]

export interface OutfitResponse {
  id: string
  user_id: string
  occasion: string
  vibe?: string | null
  skeleton: string
  score: number
  component_scores: Record<string, number>
  reasons: string[]
  ai_summary?: string | null
  wardrobe_only: boolean
  fallback_reason?: string | null
  unlocked_by_product_id?: string | null
  is_saved: boolean
  tags?: string[]
  items: OutfitSlotItem[]
  created_at?: string | null
  is_below_threshold?: boolean
  quality_warning?: string | null
  vibe_coverage?: string | null
  core_signature?: [string, string][]
}

export interface CatalogProductSuggestion {
  id: string
  name: string
  price: number
  price_cents: number
  image_url?: string | null
  category: string
  slot?: string | null
  subtype?: string | null
  audience?: string | null
  occasions: string[]
  color_tags: string[]
  stock: number
}

export interface GenerateOutfitsResponse {
  outfits: OutfitResponse[]
  status: string
  message?: string | null
  missing_slots: string[]
  profile_warning?: string | null
  budget_status?: string | null
  no_products_in_budget?: boolean
  cheapest_alternative?: CatalogProductSuggestion | null
  quality_warning?: string | null
  vibe_coverage?: string | null
}

export interface SavedOutfitsListResponse {
  outfits: OutfitResponse[]
  total: number
  available_tags?: string[]
}

// Gap Analysis Types
export interface GapSuggestionItem {
  id: string
  name: string
  category: string
  slot: string
  suitability: number
  new_outfits_total: number
  new_outfits_by_occasion: Record<string, number>
  utility: number
  matching_products: CatalogProductSuggestion[]
  budget_status: 'within_budget' | 'no_products_in_budget' | 'no_products_found' | string
  budget_reason?: string | null
  cheapest_alternative?: CatalogProductSuggestion | null
}

export interface GapAnalysisResponse {
  gaps: GapSuggestionItem[]
  total_gaps: number
  wardrobe_item_count: number
  occasion_filter?: string | null
  budget_max?: number | null
  message?: string | null
}

// Style DNA & Event Types
export type OutfitEventType = 'like' | 'dislike' | 'save' | 'skip' | 'wear'

export interface OutfitEventResponse {
  id: string
  user_id: string
  outfit_id: string
  event_type: string
  metadata: Record<string, any>
  created_at?: string | null
}

export interface StyleDnaPreferenceItem {
  dimension: string
  name: string
  score: number
}

export interface StyleDnaAffinities {
  colors: Record<string, number>
  categories: Record<string, number>
  styles: Record<string, number>
}

export interface StyleDnaResponse {
  total_events: number
  event_counts: {
    like: number
    dislike: number
    save: number
    skip: number
    wear: number
  }
  affinities: StyleDnaAffinities
  top_preferences: StyleDnaPreferenceItem[]
  avoidances: StyleDnaPreferenceItem[]
  influence_cap: number
  message?: string | null
}
