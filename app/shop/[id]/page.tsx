"use client"

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Heart, ShoppingBag, Star } from 'lucide-react'
import { useCart } from '@/contexts/cart-context'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { resolveColor } from '@/lib/utils'

import { api, ProductItem } from '@/lib/api/client'

export default function ProductDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { dispatch } = useCart()
  const [product, setProduct] = useState<ProductItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedColor, setSelectedColor] = useState<string>('')
  const [selectedSize, setSelectedSize] = useState<string>('')
  const [isWishlisted, setIsWishlisted] = useState(false)
  const [similarProducts, setSimilarProducts] = useState<ProductItem[]>([])
  const [similarLoading, setSimilarLoading] = useState(false)

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        const productId = params.id as string
        const data = await api.products.get(productId)
        setProduct(data)
        // Set default selections
        if (data.colors && data.colors.length > 0) {
          setSelectedColor(data.colors[0])
        }
        if (data.sizes && data.sizes.length > 0) {
          setSelectedSize(data.sizes[0])
        }

        // Fetch similar products from the same category
        if (data.category && ['casual', 'luxury', 'formal'].includes(data.category.toLowerCase())) {
          fetchSimilarProducts(data.category.toLowerCase(), productId)
        }
      } catch (error) {
        console.error('Error fetching product from FastAPI:', error)
      } finally {
        setLoading(false)
      }
    }

    const fetchSimilarProducts = async (category: string, currentProductId: string) => {
      setSimilarLoading(true)
      try {
        const result = await api.products.list({ limit: 4, category })
        setSimilarProducts(result.items.filter((item: ProductItem) => item.id !== currentProductId))
      } catch (error) {
        console.error('Error fetching similar products:', error)
      } finally {
        setSimilarLoading(false)
      }
    }

    if (params.id) {
      fetchProduct()
    }
  }, [params.id])

  const handleAddToCart = async () => {
    if (!product || !selectedColor || !selectedSize) return

    dispatch({
      type: 'ADD_ITEM',
      payload: {
        id: product.id,
        name: product.name,
        price: product.price,
        originalPrice: product.originalPrice,
        image: product.image,
        category: product.category,
        selectedColor,
        selectedSize,
      },
    })

    await api.cart.add({
      productId: product.id,
      quantity: 1,
      selectedColor,
      selectedSize,
    }).catch(err => console.warn("Cart sync background notice:", err))

    console.log('Added to cart:', product.name)
  }

  const toggleWishlist = () => {
    setIsWishlisted(!isWishlisted)
    // Here you would typically save to a wishlist API
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation />
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading product...</p>
          </div>
        </div>
        <Footer />
      </div>
    )
  }

  if (!product) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation />
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <h1 className="text-2xl font-bold mb-4">Product Not Found</h1>
            <p className="text-muted-foreground mb-4">The product you're looking for doesn't exist.</p>
            <Button onClick={() => router.push('/shop')}>Back to Shop</Button>
          </div>
        </div>
        <Footer />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Back Button */}
        <Button
          variant="ghost"
          onClick={() => router.back()}
          className="mb-6 flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Button>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Product Image */}
          <div className="space-y-4">
            <Card className="overflow-hidden">
              <div className="relative aspect-square bg-muted">
                <img
                  src={product.image || '/placeholder.svg'}
                  alt={product.name}
                  className="w-full h-full object-cover"
                />
                
                {/* Badges */}
                <div className="absolute top-4 left-4 flex flex-col gap-2">
                  {product.isNew && (
                    <Badge variant="secondary" className="text-xs">
                      New
                    </Badge>
                  )}
                  {product.isSale && (
                    <Badge className="bg-destructive text-destructive-foreground text-xs">
                      Sale
                    </Badge>
                  )}
                </div>
              </div>
            </Card>
          </div>

          {/* Product Details */}
          <div className="space-y-6">
            <div>
              <h1 className="font-sans font-bold text-3xl text-foreground mb-2">
                {product.name}
              </h1>
              <p className="font-serif text-lg text-muted-foreground">
                {product.category}
              </p>
            </div>

            {/* Price */}
            <div className="flex items-center gap-3">
              <span className="font-sans font-bold text-3xl text-foreground">
                ₹{product.price.toFixed(0)}
              </span>
              {product.originalPrice && (
                <span className="font-serif text-xl text-muted-foreground line-through">
                  ₹{product.originalPrice.toFixed(0)}
                </span>
              )}
              {product.originalPrice && (
                <Badge variant="destructive" className="text-sm">
                  Save ₹{(product.originalPrice - product.price).toFixed(0)}
                </Badge>
              )}
            </div>

            {/* Rating */}
            <div className="flex items-center gap-2">
              <div className="flex items-center">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className={`h-4 w-4 ${
                      i < 4 ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'
                    }`}
                  />
                ))}
              </div>
              <span className="font-serif text-sm text-muted-foreground">(4.0) 127 reviews</span>
            </div>

            {/* Description */}
            <div>
              <h3 className="font-sans font-semibold text-lg mb-2">Description</h3>
              <p className="font-serif text-muted-foreground leading-relaxed">
                {product.description}
              </p>
            </div>

            {/* Color Selection */}
            {product.colors && product.colors.length > 0 && (
              <div>
                <h3 className="font-sans font-semibold text-lg mb-3">
                  Color: <span className="font-normal">{selectedColor}</span>
                </h3>
                <div className="flex gap-3">
                  {product.colors.map((color) => (
                    <button
                      key={color}
                      onClick={() => setSelectedColor(color)}
                      className={`w-12 h-12 rounded-full border-2 transition-all ${
                        selectedColor === color
                          ? 'border-primary scale-110'
                          : 'border-border hover:border-primary/50'
                      }`}
                      style={{ backgroundColor: resolveColor(color) }}
                      title={color}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Size Selection */}
            {product.sizes && product.sizes.length > 0 && (
              <div>
                <h3 className="font-sans font-semibold text-lg mb-3">
                  Size: <span className="font-normal">{selectedSize}</span>
                </h3>
                <div className="flex gap-2">
                  {product.sizes.map((size) => (
                    <button
                      key={size}
                      onClick={() => setSelectedSize(size)}
                      className={`px-4 py-2 border rounded-md font-serif text-sm transition-all ${
                        selectedSize === size
                          ? 'border-primary bg-primary text-primary-foreground'
                          : 'border-border hover:border-primary'
                      }`}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-4 pt-4">
              <Button
                onClick={handleAddToCart}
                size="lg"
                className="flex-1"
                disabled={!selectedColor || !selectedSize}
              >
                <ShoppingBag className="h-5 w-5 mr-2" />
                Add to Cart
              </Button>
              <Button
                variant="outline"
                size="lg"
                onClick={toggleWishlist}
                className={isWishlisted ? 'bg-red-50 border-red-200 text-red-600' : ''}
              >
                <Heart
                  className={`h-5 w-5 ${isWishlisted ? 'fill-current' : ''}`}
                />
              </Button>
            </div>

            {/* Additional Info */}
            <div className="border-t pt-6 space-y-3">
              <div className="flex justify-between">
                <span className="font-serif text-muted-foreground">SKU</span>
                <span className="font-mono text-sm">{product.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-serif text-muted-foreground">Category</span>
                <span className="font-serif">{product.category}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-serif text-muted-foreground">Availability</span>
                <span className="font-serif text-green-600">In Stock</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Similar Products Section */}
      {similarProducts.length > 0 && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="mb-8">
            <h2 className="font-sans font-bold text-2xl md:text-3xl text-foreground mb-2">
              Similar {product.category.charAt(0).toUpperCase() + product.category.slice(1)} Pieces
            </h2>
            <p className="font-serif text-muted-foreground">
              Discover more {product.category} fashion that matches your style
            </p>
          </div>

          {similarLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {similarProducts.slice(0, 4).map((similarProduct) => (
                <Card
                  key={similarProduct.id}
                  className="group cursor-pointer overflow-hidden hover:shadow-lg transition-all duration-300 h-full flex flex-col"
                  onClick={() => router.push(`/shop/${similarProduct.id}`)}
                >
                  <div className="relative aspect-[4/5] bg-muted overflow-hidden">
                    <img
                      src={similarProduct.image || "/placeholder.svg"}
                      alt={similarProduct.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />

                    {/* Badges */}
                    <div className="absolute top-2 left-2 flex flex-col gap-1">
                      {similarProduct.isNew && (
                        <Badge variant="secondary" className="text-xs">
                          New
                        </Badge>
                      )}
                      {similarProduct.isSale && <Badge className="bg-destructive text-destructive-foreground text-xs">Sale</Badge>}
                    </div>
                  </div>

                  <CardContent className="p-3 flex-1 flex flex-col justify-between">
                    <div className="mb-2">
                      <h3 className="font-sans font-semibold text-sm text-foreground group-hover:text-primary transition-colors line-clamp-2 leading-tight">
                        {similarProduct.name}
                      </h3>
                      <p className="font-serif text-xs text-muted-foreground capitalize">{similarProduct.category}</p>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1">
                        <span className="font-sans font-bold text-base text-foreground">₹{similarProduct.price.toFixed(0)}</span>
                        {similarProduct.originalPrice && (
                          <span className="font-serif text-xs text-muted-foreground line-through">
                            ₹{similarProduct.originalPrice.toFixed(0)}
                          </span>
                        )}
                      </div>
                      {similarProduct.isSale && similarProduct.originalPrice && (
                        <Badge variant="outline" className="text-xs text-destructive border-destructive">
                          -{Math.round(((similarProduct.originalPrice - similarProduct.price) / similarProduct.originalPrice) * 100)}%
                        </Badge>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      <Footer />
    </div>
  )
}