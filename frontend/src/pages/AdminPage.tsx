import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { api, type ProductItem } from '@/lib/api'
import { useAuth } from '@/contexts/auth-context'

export default function AdminPage() {
  const { user } = useAuth()
  const [products, setProducts] = useState<ProductItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // Form state
  const [form, setForm] = useState({
    name: '',
    description: '',
    price_cents: '',
    category: 'casual',
    image_url: '',
    colors: '',
    sizes: '',
    style_tags: '',
    occasions: '',
    seasons: '',
  })
  const [creating, setCreating] = useState(false)

  const loadProducts = async () => {
    try {
      setLoading(true)
      const res = await api.products.list({ limit: 100 })
      setProducts(res.items || [])
    } catch (err: any) {
      console.error('Failed to load products in admin:', err)
      setError(err.message || 'Failed to load products. Check server connection.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProducts()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setError(null)
    setSuccess(null)

    try {
      await api.products.create({
        name: form.name,
        description: form.description,
        price_cents: parseInt(form.price_cents) || 0,
        category: form.category,
        image_url: form.image_url || '/placeholder.svg',
        colors: form.colors
          ? form.colors.split(',').map((c) => c.trim()).filter(Boolean)
          : [],
        sizes: form.sizes
          ? form.sizes.split(',').map((s) => s.trim()).filter(Boolean)
          : [],
        style_tags: form.style_tags
          ? form.style_tags.split(',').map((tag) => tag.trim().toLowerCase()).filter(Boolean)
          : [],
        occasions: form.occasions
          ? form.occasions.split(',').map((tag) => tag.trim().toLowerCase()).filter(Boolean)
          : [],
        seasons: form.seasons
          ? form.seasons.split(',').map((tag) => tag.trim().toLowerCase()).filter(Boolean)
          : [],
      })

      setSuccess('Product added successfully to catalog!')
      setForm({
        name: '',
        description: '',
        price_cents: '',
        category: 'casual',
        image_url: '',
        colors: '',
        sizes: '',
        style_tags: '',
        occasions: '',
        seasons: '',
      })
      loadProducts()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err: any) {
      setError(err.message || 'Creation rejected. Server authorization required.')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (productId: string) => {
    if (!confirm('Are you sure you want to delete this product?')) return

    try {
      setDeletingId(productId)
      await api.products.delete(productId)
      setProducts((prev) => prev.filter((p) => p.id !== productId))
      setSuccess('Product removed.')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err: any) {
      setError(err.message || 'Deletion rejected. Server authorization required.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navigation />

      <main className="admin-main">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-border gap-4">
          <div className="admin-page-heading">
            <p className="eyebrow">STYLESENSE / STAFF</p>
            <h1 className="font-display text-4xl sm:text-5xl font-normal text-foreground">Stock room.</h1>
            <p className="font-mono text-xs text-muted-foreground mt-1">
              SIGNED IN / <span className="font-medium text-foreground">{user?.email}</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link to="/admin/analytics">
              <Button variant="outline" className="gap-2">
                STORE NOTES →
              </Button>
            </Link>
          </div>
        </div>

        {error && (
            <div className="admin-notice error">
            <div>
              <p className="font-semibold">Operation Notice</p>
              <p className="text-xs mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {success && (
            <div className="admin-notice">
            <span>{success}</span>
          </div>
        )}

        {/* 2-Column layout: Add Product & Inventory */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          {/* Add Product Form */}
          <Card className="admin-sheet">
            <CardHeader>
              <CardTitle className="text-xl">Add a piece</CardTitle>
              <CardDescription>
                Add a product to the public rack.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">
                    Product Name
                  </label>
                  <Input
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="e.g. Italian Silk Evening Dress"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">
                    Description
                  </label>
                  <textarea
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    placeholder="Describe tailoring, occasion, and fabric..."
                    rows={3}
                    className="w-full rounded-none border border-border bg-card p-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">
                      Price (Paise)
                    </label>
                    <Input
                      type="number"
                      value={form.price_cents}
                      onChange={(e) => setForm({ ...form, price_cents: e.target.value })}
                      placeholder="499900 (₹4,999)"
                      required
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">
                      Category
                    </label>
                    <select
                      value={form.category}
                      onChange={(e) => setForm({ ...form, category: e.target.value })}
                      className="w-full h-9 rounded-none border border-border bg-card px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                    >
                      <option value="casual">Casual</option>
                      <option value="formal">Formal</option>
                      <option value="luxury">Luxury</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">
                    Style tags (comma-separated)
                  </label>
                  <Input
                    value={form.style_tags}
                    onChange={(e) => setForm({ ...form, style_tags: e.target.value })}
                    placeholder="minimal, classic, streetwear"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">Occasions</label>
                    <Input value={form.occasions} onChange={(e) => setForm({ ...form, occasions: e.target.value })} placeholder="work, party" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">Seasons</label>
                    <Input value={form.seasons} onChange={(e) => setForm({ ...form, seasons: e.target.value })} placeholder="summer, all_season" />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground uppercase">
                    Image URL
                  </label>
                  <Input
                    value={form.image_url}
                    onChange={(e) => setForm({ ...form, image_url: e.target.value })}
                    placeholder="https://images.unsplash.com/..."
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">
                      Colors (comma-separated)
                    </label>
                    <Input
                      value={form.colors}
                      onChange={(e) => setForm({ ...form, colors: e.target.value })}
                      placeholder="Black, Navy, Cream"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">
                      Sizes (comma-separated)
                    </label>
                    <Input
                      value={form.sizes}
                      onChange={(e) => setForm({ ...form, sizes: e.target.value })}
                      placeholder="S, M, L, XL"
                    />
                  </div>
                </div>

                <Button type="submit" disabled={creating} className="w-full gap-2">
                  {creating ? 'SAVING PIECE…' : 'ADD TO THE RACK →'}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Current Inventory */}
          <Card className="admin-sheet">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-xl flex items-center gap-2">
                  On the rack ({products.length})
                </CardTitle>
              <CardDescription>Public pieces / stock room actions</CardDescription>
              </div>
            </CardHeader>

            <CardContent>
              {loading ? (
                <div className="py-12 text-center text-sm text-muted-foreground">
                  Loading inventory...
                </div>
              ) : products.length === 0 ? (
                <div className="py-12 text-center text-sm text-muted-foreground">
                  No products in catalog yet.
                </div>
              ) : (
                <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
                  {products.map((p) => (
                    <div
                      key={p.id}
                      className="p-3.5 rounded-none border border-border flex items-center justify-between gap-4 hover:bg-muted/40 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <img
                          src={p.image || '/placeholder.svg'}
                          alt={p.name}
                          className="w-12 h-14 object-cover rounded-none bg-muted flex-shrink-0"
                        />
                        <div className="min-w-0">
                          <h4 className="font-semibold text-sm text-foreground truncate">{p.name}</h4>
                          <p className="text-xs text-muted-foreground capitalize">
                            {p.category} / ₹{p.price.toFixed(0)}
                          </p>
                        </div>
                      </div>

                      <Button
                        variant="destructive"
                        size="icon"
                        onClick={() => handleDelete(p.id)}
                        disabled={deletingId === p.id}
                        className="admin-remove"
                      >
                        REMOVE
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
      <Footer />
    </div>
  )
}
