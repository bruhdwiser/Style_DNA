import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Trash2, Package, Shield, BarChart3, ArrowLeft, AlertCircle, Check } from 'lucide-react'
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

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-border gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-primary/10 text-primary">
                <Shield className="w-5 h-5" />
              </span>
              <h1 className="text-3xl font-extrabold text-foreground tracking-tight">
                Admin Management Portal
              </h1>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Active admin: <span className="font-semibold text-foreground">{user?.email}</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link to="/admin/analytics">
              <Button variant="outline" className="gap-2">
                <BarChart3 className="w-4 h-4 text-primary" />
                View Analytics
              </Button>
            </Link>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl flex items-start gap-3 text-sm text-destructive">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Operation Notice</p>
              <p className="text-xs mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {success && (
          <div className="p-4 bg-primary/10 border border-primary/20 rounded-xl flex items-center gap-3 text-sm text-primary font-medium">
            <Check className="w-5 h-5 flex-shrink-0" />
            <span>{success}</span>
          </div>
        )}

        {/* 2-Column layout: Add Product & Inventory */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          {/* Add Product Form */}
          <Card className="border-border/80 shadow-md">
            <CardHeader>
              <CardTitle className="text-xl">Add New Product</CardTitle>
              <CardDescription>
                Create a new garment entry. Enforced with server-side admin role validation.
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
                    className="w-full rounded-md border border-input bg-background p-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-foreground uppercase">
                      Price (Cents)
                    </label>
                    <Input
                      type="number"
                      value={form.price_cents}
                      onChange={(e) => setForm({ ...form, price_cents: e.target.value })}
                      placeholder="4999 (₹49.99)"
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
                      className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                    >
                      <option value="casual">Casual</option>
                      <option value="formal">Formal</option>
                      <option value="luxury">Luxury</option>
                    </select>
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

                <Button type="submit" disabled={creating} className="w-full gap-2 shadow-md">
                  <Plus className="w-4 h-4" />
                  {creating ? 'Saving Product...' : 'Add Product'}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Current Inventory */}
          <Card className="border-border/80 shadow-md">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-xl flex items-center gap-2">
                  <Package className="w-5 h-5 text-primary" />
                  Live Inventory ({products.length})
                </CardTitle>
                <CardDescription>Manage and remove items from the catalog</CardDescription>
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
                      className="p-3.5 rounded-xl border border-border flex items-center justify-between gap-4 hover:bg-muted/40 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <img
                          src={p.image || '/placeholder.svg'}
                          alt={p.name}
                          className="w-12 h-14 object-cover rounded-lg bg-muted flex-shrink-0"
                        />
                        <div className="min-w-0">
                          <h4 className="font-semibold text-sm text-foreground truncate">{p.name}</h4>
                          <p className="text-xs text-muted-foreground capitalize">
                            {p.category} • ₹{p.price.toFixed(0)}
                          </p>
                        </div>
                      </div>

                      <Button
                        variant="destructive"
                        size="icon"
                        onClick={() => handleDelete(p.id)}
                        disabled={deletingId === p.id}
                        className="h-8 w-8 flex-shrink-0"
                      >
                        <Trash2 className="w-4 h-4" />
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
