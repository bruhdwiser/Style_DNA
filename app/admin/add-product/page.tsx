'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Trash2, Upload, X, Package } from 'lucide-react'
import Image from 'next/image'
import { api, ProductItem } from '@/lib/api/client'

export default function AddProductPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price_cents: '',
    category: '',
    image_url: '',
    colors: '',
    sizes: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [products, setProducts] = useState<ProductItem[]>([])
  const [loadingProducts, setLoadingProducts] = useState(true)
  const [selectedImage, setSelectedImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // Fetch existing products
  useEffect(() => {
    fetchProducts()
  }, [])

  const fetchProducts = async () => {
    try {
      setLoadingProducts(true)
      const data = await api.products.list({ limit: 100 })
      setProducts(data.items || [])
    } catch (err: any) {
      console.error('Error fetching products from FastAPI:', err)
      setError(err.message || 'Failed to fetch products')
      setProducts([])
    } finally {
      setLoadingProducts(false)
    }
  }

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedImage(file)
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const clearImage = () => {
    setSelectedImage(null)
    setImagePreview(null)
    setFormData({ ...formData, image_url: '' })
  }

  const handleDelete = async (product: ProductItem) => {
    if (!confirm('Are you sure you want to delete this product?')) return

    try {
      setDeletingId(product.id)
      await api.products.delete(product.id)

      // Remove from local state
      setProducts(products.filter(p => p.id !== product.id))
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err: any) {
      setError(err.message || 'Failed to delete product (Admin privileges required)')
      setTimeout(() => setError(''), 4000)
    } finally {
      setDeletingId(null)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess(false)

    try {
      let finalImageUrl = formData.image_url

      // If a local image is selected, convert to base64
      if (selectedImage) {
        const reader = new FileReader()
        finalImageUrl = await new Promise((resolve) => {
          reader.onloadend = () => resolve(reader.result as string)
          reader.readAsDataURL(selectedImage)
        })
      }

      await api.products.create({
        name: formData.name,
        description: formData.description,
        price_cents: parseInt(formData.price_cents) || 0,
        category: formData.category,
        image_url: finalImageUrl || '/placeholder.svg',
        colors: formData.colors ? formData.colors.split(',').map(c => c.trim()).filter(Boolean) : [],
        sizes: formData.sizes ? formData.sizes.split(',').map(s => s.trim()).filter(Boolean) : [],
      })

      setSuccess(true)
      setFormData({
        name: '',
        description: '',
        price_cents: '',
        category: '',
        image_url: '',
        colors: '',
        sizes: '',
      })
      clearImage()

      // Refresh products list
      fetchProducts()

      // Auto-hide success message
      setTimeout(() => setSuccess(false), 3000)
    } catch (err: any) {
      setError(err.message || 'Failed to add product (Admin privileges required)')
    } finally {
      setLoading(false)
    }
  }
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  return (
    <div className="min-h-screen bg-background py-12">
      <div className="container mx-auto px-4 max-w-7xl">
        <div className="mb-8">
          <Button
            variant="outline"
            onClick={() => router.push('/admin')}
            className="mb-4"
          >
            ← Back to Dashboard
          </Button>
          <h1 className="text-4xl font-bold mb-2">Product Management</h1>
          <p className="text-muted-foreground">
            Add new products and manage existing inventory
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Add Product Form */}
          <div>
            <Card>
              <CardHeader>
                <CardTitle>Add New Product</CardTitle>
                <CardDescription>
                  Fill in the details to add a new product
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Product Name</label>
                    <Input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      placeholder="e.g., ZARA Beige Satin Button-Down Blouse"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Description</label>
                    <textarea
                      name="description"
                      value={formData.description}
                      onChange={handleChange}
                      placeholder="Product description..."
                      className="w-full min-h-[100px] px-3 py-2 border rounded-md bg-background"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">Price (in cents)</label>
                      <Input
                        type="number"
                        name="price_cents"
                        value={formData.price_cents}
                        onChange={handleChange}
                        placeholder="4999"
                        required
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        ${(parseInt(formData.price_cents) || 0) / 100}
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2">Category</label>
                      <Input
                        type="text"
                        name="category"
                        value={formData.category}
                        onChange={handleChange}
                        placeholder="tops"
                        required
                      />
                    </div>
                  </div>

                  {/* Image Upload Section */}
                  <div>
                    <label className="block text-sm font-medium mb-2">Product Image</label>
                    
                    {!imagePreview ? (
                      <div className="space-y-3">
                        <div className="flex gap-2">
                          <label className="flex-1">
                            <div className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:bg-accent transition-colors">
                              <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                              <p className="text-sm font-medium mb-1">Upload from Computer</p>
                              <p className="text-xs text-muted-foreground">Click to select image</p>
                            </div>
                            <input
                              type="file"
                              accept="image/*"
                              onChange={handleImageSelect}
                              className="hidden"
                            />
                          </label>
                        </div>
                        
                        <div className="relative">
                          <div className="absolute inset-0 flex items-center">
                            <span className="w-full border-t" />
                          </div>
                          <div className="relative flex justify-center text-xs uppercase">
                            <span className="bg-background px-2 text-muted-foreground">Or</span>
                          </div>
                        </div>

                        <div>
                          <Input
                            type="url"
                            name="image_url"
                            value={formData.image_url}
                            onChange={handleChange}
                            placeholder="Paste image URL"
                          />
                        </div>
                      </div>
                    ) : (
                      <div className="relative">
                        <div className="border rounded-lg p-4 bg-accent/50">
                          <div className="relative h-48 mb-2">
                            <Image
                              src={imagePreview}
                              alt="Preview"
                              fill
                              className="object-contain rounded"
                            />
                          </div>
                          <p className="text-sm text-center text-muted-foreground truncate">
                            {selectedImage?.name || 'Image URL'}
                          </p>
                        </div>
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          onClick={clearImage}
                          className="absolute top-2 right-2"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Colors (comma-separated)
                    </label>
                    <Input
                      type="text"
                      name="colors"
                      value={formData.colors}
                      onChange={handleChange}
                      placeholder="Beige, White, Black"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Sizes (comma-separated)
                    </label>
                    <Input
                      type="text"
                      name="sizes"
                      value={formData.sizes}
                      onChange={handleChange}
                      placeholder="XS, S, M, L, XL"
                    />
                  </div>

                  {error && (
                    <div className="bg-red-500/10 border border-red-500 text-red-500 px-4 py-2 rounded-md">
                      {error}
                    </div>
                  )}

                  {success && (
                    <div className="bg-green-500/10 border border-green-500 text-green-500 px-4 py-2 rounded-md">
                      Product added successfully!
                    </div>
                  )}

                  <Button type="submit" disabled={loading} className="w-full">
                    {loading ? 'Adding...' : 'Add Product'}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>

          {/* Product List */}
          <div>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Package className="h-5 w-5" />
                  Current Products ({products.length})
                </CardTitle>
                <CardDescription>
                  Manage your existing product inventory
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loadingProducts ? (
                  <div className="text-center py-8 text-muted-foreground">
                    Loading products...
                  </div>
                ) : products.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No products yet. Add your first product!
                  </div>
                ) : (
                  <div className="space-y-3 max-h-[800px] overflow-y-auto pr-2">
                    {products.map((product) => (
                      <div
                        key={product.id}
                        className="border rounded-lg p-4 hover:bg-accent/50 transition-colors"
                      >
                        <div className="flex gap-4">
                          {(product.image_url || product.image) && (
                            <div className="relative w-20 h-20 flex-shrink-0 bg-accent rounded overflow-hidden">
                              <Image
                                src={product.image_url || product.image || '/placeholder.svg'}
                                alt={product.name}
                                fill
                                className="object-cover"
                              />
                            </div>
                          )}
                          <div className="flex-1 min-w-0">
                            <h3 className="font-semibold truncate">{product.name}</h3>
                            {product.description && (
                              <p className="text-sm text-muted-foreground truncate">
                                {product.description}
                              </p>
                            )}
                            <div className="flex items-center gap-3 mt-2 flex-wrap">
                              <span className="text-sm font-medium">
                                ${product.price ? product.price.toFixed(2) : ((product.price_cents || 0) / 100).toFixed(2)}
                              </span>
                              <span className="text-xs bg-accent px-2 py-1 rounded">
                                {product.category}
                              </span>
                            </div>
                            {(product.colors || product.sizes) && (
                              <div className="text-xs text-muted-foreground mt-1">
                                {product.colors && (
                                  <span>Colors: {product.colors.join(', ')}</span>
                                )}
                                {product.colors && product.sizes && ' • '}
                                {product.sizes && (
                                  <span>Sizes: {product.sizes.join(', ')}</span>
                                )}
                              </div>
                            )}
                          </div>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleDelete(product)}
                            disabled={deletingId === product.id}
                            className="flex-shrink-0"
                          >
                            {deletingId === product.id ? (
                              '...'
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
