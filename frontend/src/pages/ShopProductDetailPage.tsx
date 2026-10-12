import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, ShoppingBag, Star, Heart, Check, Sparkles, Share2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { ProductCard } from '@/components/product-card'
import { useCart } from '@/contexts/cart-context'
import { api, type ProductItem } from '@/lib/api'
import { resolveColor } from '@/lib/utils'
import { usePageTracking, trackProductView } from '@/lib/tracking'

const STANDARD_SIZES = ['XS', 'S', 'M', 'L', 'XL']

export default function ShopProductDetailPage() {
  usePageTracking()
  const { id } = useParams<{ id: string }>()
  const { addToCart } = useCart()

  const [product, setProduct] = useState<ProductItem | null>(null)
  const [similarProducts, setSimilarProducts] = useState<ProductItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedColor, setSelectedColor] = useState<string>('')
  const [selectedSize, setSelectedSize] = useState<string>('')
  const [isWishlisted, setIsWishlisted] = useState(false)
  const [addedNotice, setAddedNotice] = useState(false)

  useEffect(() => {
    if (!id) return
    setLoading(true)

    api.products
      .get(id)
      .then((data) => {
        setProduct(data)
        if (data.colors && data.colors.length > 0) setSelectedColor(data.colors[0])
        if (data.sizes && data.sizes.length > 0) setSelectedSize(data.sizes[0])
        trackProductView(data.id, data.name)

        if (data.category) {
          api.products
            .list({ category: data.category.toLowerCase(), limit: 4 })
            .then((sim) => {
              setSimilarProducts(sim.items.filter((item) => item.id !== id))
            })
            .catch(() => {})
        }
      })
      .catch((err) => {
        console.error('Error fetching product:', err)
        setProduct(null)
      })
      .finally(() => setLoading(false))
  }, [id])

  const handleAddToCart = () => {
    if (!product) return
    addToCart({
      id: product.id,
      name: product.name,
      price: product.price,
      originalPrice: product.originalPrice,
      image: product.image,
      category: product.category,
      selectedColor,
      selectedSize,
    })
    setAddedNotice(true)
    setTimeout(() => setAddedNotice(false), 3000)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Navigation />
        <div className="flex-1 max-w-7xl mx-auto px-4 py-16 w-full flex items-center justify-center">
          <div className="text-center space-y-3">
            <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm text-muted-foreground">Loading garment details...</p>
          </div>
        </div>
        <Footer />
      </div>
    )
  }

  if (!product) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Navigation />
        <div className="flex-1 max-w-md mx-auto px-4 py-24 text-center">
          <h2 className="text-2xl font-bold mb-2">Garment Not Found</h2>
          <p className="text-muted-foreground text-sm mb-6">
            The requested fashion piece could not be located in our catalog.
          </p>
          <Link to="/shop">
            <Button>Back to Shop</Button>
          </Link>
        </div>
        <Footer />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navigation />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full">
        {/* Breadcrumb / Back button */}
        <div className="mb-6">
          <Link to="/shop">
            <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground hover:text-foreground">
              <ArrowLeft className="w-4 h-4" />
              Back to Catalog
            </Button>
          </Link>
        </div>

        {/* Main Product Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start mb-20">
          {/* Gallery / Image */}
          <div className="relative rounded-3xl overflow-hidden bg-muted border border-border/80 aspect-3/4 shadow-lg">
            <img
              src={product.image || '/placeholder.svg'}
              alt={product.name}
              className="w-full h-full object-cover"
            />
            {product.isNew && (
              <Badge className="absolute top-4 left-4 bg-primary text-primary-foreground font-semibold">
                New Release
              </Badge>
            )}
            {product.isSale && (
              <Badge variant="destructive" className="absolute top-4 right-4 font-semibold">
                On Sale
              </Badge>
            )}
          </div>

          {/* Details & Actions */}
          <div className="space-y-6">
            <div>
              <span className="text-xs font-semibold uppercase tracking-widest text-primary">
                {product.category}
              </span>
              <h1 className="text-3xl sm:text-4xl font-extrabold text-foreground tracking-tight mt-1">
                {product.name}
              </h1>

              <div className="flex items-center gap-3 mt-3">
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <Star key={s} className="w-4 h-4 fill-amber-400 text-amber-400" />
                  ))}
                </div>
                <span className="text-xs text-muted-foreground font-medium">
                  4.8 • 142 reviews
                </span>
              </div>
            </div>

            {/* Price */}
            <div className="flex items-baseline gap-3 pb-6 border-b border-border">
              <span className="text-3xl font-extrabold text-foreground">
                ₹{product.price.toFixed(0)}
              </span>
              {product.originalPrice && product.originalPrice > product.price && (
                <span className="text-lg text-muted-foreground line-through">
                  ₹{product.originalPrice.toFixed(0)}
                </span>
              )}
              {product.originalPrice && product.originalPrice > product.price && (
                <span className="text-xs font-semibold text-destructive">
                  Save ₹{(product.originalPrice - product.price).toFixed(0)}
                </span>
              )}
            </div>

            {/* Description */}
            <p className="text-sm leading-relaxed text-muted-foreground">
              {product.description ||
                'Engineered with premium sustainable fabrics for versatile day-to-night styling. Designed to retain shape and deliver comfortable elegance in any setting.'}
            </p>

            {/* Color selection */}
            {product.colors && product.colors.length > 0 && (
              <div className="space-y-3">
                <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
                  Color: <span className="text-muted-foreground font-normal">{selectedColor}</span>
                </label>
                <div className="flex items-center gap-2">
                  {product.colors.map((color) => (
                    <button
                      key={color}
                      onClick={() => setSelectedColor(color)}
                      className={`w-8 h-8 rounded-full border-2 transition-all p-0.5 cursor-pointer ${
                        selectedColor === color
                          ? 'border-primary ring-2 ring-primary/30 scale-110'
                          : 'border-border/80 hover:border-foreground'
                      }`}
                      title={color}
                    >
                      <span
                        className="w-full h-full rounded-full block"
                        style={{ backgroundColor: resolveColor(color) }}
                      />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Size selection */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold uppercase tracking-wider text-foreground">
                  Select Size
                </label>
                <span className="text-xs text-primary cursor-pointer hover:underline">
                  Size Guide
                </span>
              </div>
              <div className="flex items-center gap-2">
                {(product.sizes && product.sizes.length > 0 ? product.sizes : STANDARD_SIZES).map(
                  (size) => (
                    <Button
                      key={size}
                      variant={selectedSize === size ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setSelectedSize(size)}
                      className="min-w-10 rounded-lg text-xs font-semibold"
                    >
                      {size}
                    </Button>
                  )
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-4 pt-4">
              <Button
                size="lg"
                onClick={handleAddToCart}
                className="flex-1 gap-2 text-base font-semibold shadow-lg"
              >
                {addedNotice ? (
                  <>
                    <Check className="w-5 h-5" />
                    Added to Bag!
                  </>
                ) : (
                  <>
                    <ShoppingBag className="w-5 h-5" />
                    Add to Shopping Bag
                  </>
                )}
              </Button>

              <Button
                variant="outline"
                size="lg"
                onClick={() => setIsWishlisted(!isWishlisted)}
                className={`px-4 ${isWishlisted ? 'text-destructive border-destructive/40' : ''}`}
              >
                <Heart className={`w-5 h-5 ${isWishlisted ? 'fill-destructive' : ''}`} />
              </Button>
            </div>
          </div>
        </div>

        {/* Similar Products */}
        {similarProducts.length > 0 && (
          <div className="pt-12 border-t border-border">
            <h2 className="text-2xl font-bold text-foreground mb-8">Complementary Looks</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {similarProducts.map((p) => (
                <ProductCard key={p.id} {...p} />
              ))}
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  )
}
