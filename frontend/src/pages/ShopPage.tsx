import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { ProductCard } from '@/components/product-card'
import { api, type ProductItem } from '@/lib/api'
import { usePageTracking } from '@/lib/tracking'

const CATEGORIES = [
  { id: 'all', label: 'EVERYTHING' },
  { id: 'casual', label: 'OFF-DUTY' },
  { id: 'formal', label: 'TAILORED' },
  { id: 'luxury', label: 'AFTER HOURS' },
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

  useEffect(() => {
    setLoading(true)
    api.products.list({ category: currentCategory, q: currentSearch, sort: sortBy, limit: 50 })
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

  const updateParams = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams)
    if (value && value !== 'all') next.set(key, value)
    else next.delete(key)
    setSearchParams(next)
  }

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault()
    updateParams('q', searchQuery.trim())
  }

  const clearFilters = () => {
    setSearchParams(new URLSearchParams())
    setSearchQuery('')
  }

  return (
    <div className="page-shell shop-page">
      <Navigation />
      <main className="page-main shop-main">
        <div className="shop-heading">
          <div>
            <p className="eyebrow">STYLESENSE / THE RACK</p>
            <h1>The rack<span>.</span></h1>
          </div>
          <p className="shop-intro">Clothes worth getting out of bed for.<br />Find a piece. Make it yours.</p>
        </div>

        <div className="shop-controls">
          <nav className="shop-categories" aria-label="Filter by collection">
            {CATEGORIES.map((category) => (
              <button
                type="button"
                key={category.id}
                onClick={() => updateParams('category', category.id)}
                className={currentCategory === category.id ? 'is-selected' : ''}
                aria-pressed={currentCategory === category.id}
              >
                {category.label}
              </button>
            ))}
          </nav>
          <div className="shop-tools">
            <form onSubmit={submitSearch} className="shop-search">
              <label htmlFor="rack-search">SEARCH THE RACK</label>
              <input
                id="rack-search"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Try linen, black, jacket…"
              />
              <button type="submit" aria-label="Search">→</button>
            </form>
            <label className="shop-sort">
              <span>SORT</span>
              <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
                <option value="newest">Just in</option>
                <option value="price_asc">Price: low to high</option>
                <option value="price_desc">Price: high to low</option>
              </select>
            </label>
          </div>
        </div>

        <div className="shop-results-line">
          <span>{loading ? 'CHECKING THE RACK…' : `${total} ${total === 1 ? 'PIECE' : 'PIECES'}`}</span>
          {(currentCategory !== 'all' || currentSearch) && (
            <button type="button" onClick={clearFilters}>CLEAR FILTERS ×</button>
          )}
        </div>

        {loading ? (
          <div className="product-grid shop-product-grid" aria-label="Loading pieces">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => <div className="product-skeleton" key={i} />)}
          </div>
        ) : products.length ? (
          <div className="product-grid shop-product-grid">
            {products.map((product) => <ProductCard key={product.id} {...product} />)}
          </div>
        ) : (
          <div className="shop-empty">
            <span className="eyebrow">NOTHING ON THIS RAIL</span>
            <h2>No pieces found.</h2>
            <p>Try a shorter search or open the whole rack again.</p>
            <button type="button" onClick={clearFilters}>SHOW EVERYTHING →</button>
          </div>
        )}
      </main>
      <Footer />
    </div>
  )
}
