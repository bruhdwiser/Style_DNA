import { supabaseBrowser } from '@/lib/supabase/client'

export interface ApiErrorPayload {
  code: string
  message: string
  details?: any
}

export class ApiClientError extends Error {
  status: number
  code: string
  details?: any

  constructor(status: number, error: ApiErrorPayload) {
    super(error.message || 'API request failed')
    this.name = 'ApiClientError'
    this.status = status
    this.code = error.code || `HTTP_${status}`
    this.details = error.details
  }
}

// In browser: use relative proxy path /fastapi by default (proxied by next.config.mjs to FastAPI)
// or use NEXT_PUBLIC_API_URL / NEXT_PUBLIC_FASTAPI_URL if explicitly provided.
function getBaseUrl(): string {
  if (typeof window !== 'undefined') {
    return process.env.NEXT_PUBLIC_FASTAPI_URL || process.env.NEXT_PUBLIC_API_URL || '/fastapi'
  }
  return process.env.FASTAPI_INTERNAL_URL || process.env.FASTAPI_URL || 'http://127.0.0.1:8000/api/v1'
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  requiresAuth: boolean = false
): Promise<T> {
  const baseUrl = getBaseUrl().replace(/\/$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = `${baseUrl}${normalizedPath}`

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  // Obtain verified Supabase token if available or required
  if (typeof window !== 'undefined') {
    try {
      const supabase = supabaseBrowser()
      const { data: { session } } = await supabase.auth.getSession()
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }
    } catch (e) {
      // In SSR or unauthenticated state, continue
    }
  }

  if (requiresAuth && !headers['Authorization']) {
    throw new ApiClientError(401, {
      code: 'UNAUTHORIZED',
      message: 'You must be signed in to perform this action.',
    })
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  // Parse JSON response
  let data: any = null
  const contentType = response.headers.get('content-type')
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json()
    } catch {
      data = null
    }
  }

  if (!response.ok) {
    const errorPayload: ApiErrorPayload = data?.error || {
      code: `HTTP_${response.status}`,
      message: data?.message || response.statusText || 'Request failed',
      details: data?.details,
    }
    throw new ApiClientError(response.status, errorPayload)
  }

  return data as T
}

// ==============================================================================
// Typed API Methods
// ==============================================================================

export interface ProductItem {
  id: string // Consistent UUID
  name: string
  description?: string
  price: number
  originalPrice?: number
  price_cents: number
  original_price_cents?: number
  category: string
  image: string
  image_url?: string
  colors: string[]
  sizes: string[]
  isNew?: boolean
  isSale?: boolean
  is_new?: boolean
  is_sale?: boolean
  dbId?: string
  created_at?: string
}

export interface ProductListResponse {
  items: ProductItem[]
  total: number
  nextOffset: number
  hasMore: boolean
}

export interface CartItem {
  id: string
  product_id: string
  quantity: number
  selected_color?: string
  selected_size?: string
  product?: {
    id: string
    name: string
    price: number
    price_cents: number
    image: string
    category: string
  }
}

export interface CartResponse {
  items: CartItem[]
  total_cents: number
  total: number
  item_count: number
}

export interface RecommendedProduct {
  id: string
  name: string
  price: number
  image_url?: string
  category?: string
}

export interface ChatResponse {
  message: string
  recommended_products: RecommendedProduct[]
  model_used?: string
}

export const api = {
  products: {
    list: async (params?: {
      limit?: number
      offset?: number
      search?: string
      category?: string
      sort?: string
    }): Promise<ProductListResponse> => {
      const q = new URLSearchParams()
      if (params?.limit !== undefined) q.set('limit', String(params.limit))
      if (params?.offset !== undefined) q.set('offset', String(params.offset))
      if (params?.search) q.set('search', params.search)
      if (params?.category) q.set('category', params.category)
      if (params?.sort) q.set('sort', params.sort)
      const queryStr = q.toString() ? `?${q.toString()}` : ''
      return request<ProductListResponse>(`/products${queryStr}`)
    },

    get: async (id: string): Promise<ProductItem> => {
      return request<ProductItem>(`/products/${id}`)
    },

    create: async (data: {
      name: string
      description?: string
      price_cents: number
      category: string
      image_url?: string
      colors?: string[]
      sizes?: string[]
      is_new?: boolean
      is_sale?: boolean
    }): Promise<ProductItem> => {
      return request<ProductItem>('/products', {
        method: 'POST',
        body: JSON.stringify(data),
      }, true)
    },

    delete: async (id: string): Promise<{ success: boolean; deleted_id: string }> => {
      return request<{ success: boolean; deleted_id: string }>(`/products/${id}`, {
        method: 'DELETE',
      }, true)
    },
  },

  cart: {
    get: async (): Promise<CartResponse> => {
      return request<CartResponse>('/cart', {}, true)
    },

    add: async (data: {
      productId: string
      quantity?: number
      selectedColor?: string
      selectedSize?: string
    }): Promise<CartItem> => {
      return request<CartItem>('/cart', {
        method: 'POST',
        body: JSON.stringify(data),
      }, true)
    },

    update: async (itemId: string, quantity: number): Promise<CartItem> => {
      return request<CartItem>(`/cart/${itemId}`, {
        method: 'PATCH',
        body: JSON.stringify({ quantity }),
      }, true)
    },

    remove: async (itemId: string): Promise<{ success: boolean; deleted_id: string }> => {
      return request<{ success: boolean; deleted_id: string }>(`/cart/${itemId}`, {
        method: 'DELETE',
      }, true)
    },

    clear: async (): Promise<{ success: boolean; cleared: boolean }> => {
      return request<{ success: boolean; cleared: boolean }>('/cart', {
        method: 'DELETE',
      }, true)
    },
  },

  ai: {
    chat: async (data: {
      message: string
      conversationHistory?: string
    }): Promise<ChatResponse> => {
      return request<ChatResponse>('/ai-chat', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
  },

  analytics: {
    track: async (data: {
      eventType: string
      eventData: Record<string, any>
      sessionId: string
    }): Promise<{ success: boolean; event_id?: string }> => {
      return request<{ success: boolean; event_id?: string }>('/analytics/track', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },

    stats: async (): Promise<any> => {
      return request<any>('/analytics/stats', {}, true)
    },
  },

  admin: {
    status: async (): Promise<any> => {
      return request<any>('/admin/status', {}, true)
    },
  },
}
