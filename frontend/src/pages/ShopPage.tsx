import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, Filter, Sparkles, SlidersHorizontal } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { ProductCard } from '@/components/product-card'
import { AiChatbot } from '@/components/ai-chatbot'
import { api, type ProductItem } from '@/lib/api'
import { usePageTracking } from '@/lib/tracking'

const CATEGORIES = [
  { id: 'all', label: 'All Collections' },
  { id: 'casual', label: 'Casual' },
  { id: 'formal', label: 'Formal' },
  { id: 'luxury', label: 'Luxury' },
]

export default function ShopPage() {
  usePageTracking()
  const [searchParams, setSearchParams] = useSearchParams()
  const currentCategory = searchParams.get('category') || 'all'
  const currentSearch = searchParams.get('q') || ''

  const [products, setProducts] = useState<ProductItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState(currentSearch)
  const [sortBy, setSortBy] = useState('newest')
  const [chatbotOpen, setChatbotOpen] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.products
      .list({
        category: currentCategory,
        q: currentSearch,
        sort: sortBy,
        limit: 50,
      })
      .then((res) => {
        setProducts(res.items || [])
        setTotal(res.total || 0)
      })
      .catch((err) => {
        console.error('Error fetching products:', err)
        setProducts([])
      })
      .finally(() => setLoading(false))
  }, [currentCategory, currentSearch, sortBy])

  const handleCategorySelect = (catId: string) => {
    const nextParams = new URLSearchParams(searchParams)
    if (catId === 'all') {
      nextParams.delete('category')
    } else {
      nextParams.set('category', catId)
    }
    setSearchParams(nextParams)
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const nextParams = new URLSearchParams(searchParams)
    if (searchQuery.trim()) {
      nextParams.set('q', searchQuery.trim())
    } else {
      nextParams.delete('q')
    }
    setSearchParams(nextParams)
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navigation />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 pb-6 border-b border-border gap-4">
          <div>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-foreground tracking-tight">
              Curated Catalog
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              Explore {total} premium fashion items curated for quality and fit
            </p>
          </div>

          <Button
            variant="outline"
            onClick={() => setChatbotOpen(true)}
            className="gap-2 border-primary/30 text-primary hover:bg-primary/5"
          >
            <Sparkles className="w-4 h-4 text-accent" />
            Ask AI to Find Outfits
          </Button>
        </div>

        {/* Filter bar */}
        <div className="flex flex-col lg:flex-row items-center justify-between gap-4 mb-8">
          {/* Categories */}
          <div className="flex items-center gap-2 overflow-x-auto w-full lg:w-auto pb-2 lg:pb-0 scrollbar-none">
            {CATEGORIES.map((cat) => (
              <Button
                key={cat.id}
                variant={currentCategory === cat.id ? 'default' : 'outline'}
                size="sm"
                onClick={() => handleCategorySelect(cat.id)}
                className="rounded-full text-xs font-semibold whitespace-nowrap"
              >
                {cat.label}
              </Button>
            ))}
          </div>

          {/* Search & Sort */}
          <div className="flex items-center gap-3 w-full lg:w-auto">
            <form onSubmit={handleSearchSubmit} className="relative flex-1 lg:w-64">
              <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search collection..."
                className="pl-9 h-9 text-xs"
              />
            </form>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="h-9 px-3 rounded-md border border-input bg-background text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="newest">Newest First</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
            </select>
          </div>
        </div>

        {/* Product Grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <div key={i} className="rounded-2xl border border-border bg-card p-4 animate-pulse space-y-4">
                <div className="aspect-3/4 bg-muted rounded-xl" />
                <div className="h-4 bg-muted rounded w-3/4" />
                <div className="h-4 bg-muted rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : products.length === 0 ? (
          <div className="text-center py-20 border border-dashed border-border rounded-2xl bg-card/40">
            <SlidersHorizontal className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-foreground">No pieces found</h3>
            <p className="text-sm text-muted-foreground max-w-sm mx-auto mt-1 mb-6">
              Try adjusting your search terms or category filters to find matching garments.
            </p>
            <Button
              variant="outline"
              onClick={() => {
                setSearchParams(new URLSearchParams())
                setSearchQuery('')
              }}
            >
              Reset Filters
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {products.map((product) => (
              <ProductCard key={product.id} {...product} />
            ))}
          </div>
        )}
      </main>

      <Footer />
      <AiChatbot isOpen={chatbotOpen} onClose={() => setChatbotOpen(false)} />
    </div>
  )
}
