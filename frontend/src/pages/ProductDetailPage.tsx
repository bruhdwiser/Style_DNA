import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, ShoppingBag, Star, Heart, Check, Minus, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { useCart } from '@/contexts/cart-context'
import { api, type ProductItem } from '@/lib/api'
import { resolveColor } from '@/lib/utils'
import { usePageTracking, trackProductView } from '@/lib/tracking'

const STANDARD_SIZES = ['XS', 'S', 'M', 'L', 'XL']

export default function ProductDetailPage() {
  usePageTracking()
  const { id } = useParams<{ id: string }>()
  const { addToCart } = useCart()

  const [product, setProduct] = useState<ProductItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedColor, setSelectedColor] = useState<string>('')
  const [selectedSize, setSelectedSize] = useState<string>('')
  const [quantity, setQuantity] = useState(1)
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
      })
      .catch((err) => {
        console.error('Error fetching product in alternate view:', err)
        setProduct(null)
      })
      .finally(() => setLoading(false))
  }, [id])

  const handleAddToCart = () => {
    if (!product) return
    addToCart(
      {
        id: product.id,
        name: product.name,
        price: product.price,
        originalPrice: product.originalPrice,
        image: product.image,
        category: product.category,
        selectedColor,
        selectedSize,
      },
      quantity
    )
    setAddedNotice(true)
    setTimeout(() => setAddedNotice(false), 3000)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <Navigation />
        <div className="flex-1 max-w-7xl mx-auto px-4 py-16 w-full flex items-center justify-center">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
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
          <h2 className="text-2xl font-bold mb-2">Item Unavailable</h2>
          <p className="text-muted-foreground text-sm mb-6">
            The requested fashion piece is currently not in our live inventory.
          </p>
          <Link to="/shop">
            <Button>Explore Catalog</Button>
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
        <div className="mb-6 flex items-center justify-between">
          <Link to="/shop">
            <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground hover:text-foreground">
              <ArrowLeft className="w-4 h-4" />
              Back to Collection
            </Button>
          </Link>
          <Link to={`/shop/${product.id}`} className="text-xs text-primary underline">
            Switch to Modern View
          </Link>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
          <div className="rounded-3xl overflow-hidden bg-muted border border-border aspect-3/4 shadow-md">
            <img
              src={product.image || '/placeholder.svg'}
              alt={product.name}
              className="w-full h-full object-cover"
            />
          </div>

          <div className="space-y-6">
            <div>
              <span className="text-xs font-semibold uppercase tracking-widest text-primary">
                {product.category}
              </span>
              <h1 className="text-3xl font-bold text-foreground mt-1">{product.name}</h1>
              <p className="text-2xl font-bold text-foreground mt-3">₹{product.price.toFixed(0)}</p>
            </div>

            <p className="text-sm text-muted-foreground leading-relaxed">
              {product.description ||
                'Elevate your everyday wardrobe with this thoughtfully tailored piece. Features ultra-fine stitching and durable luxury materials.'}
            </p>

            {/* Colors */}
            {product.colors && product.colors.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs font-semibold uppercase text-foreground">Color</span>
                <div className="flex gap-2">
                  {product.colors.map((c) => (
                    <button
                      key={c}
                      onClick={() => setSelectedColor(c)}
                      className={`px-3 py-1 text-xs rounded-full border transition-all ${
                        selectedColor === c
                          ? 'border-primary bg-primary text-primary-foreground font-semibold'
                          : 'border-border text-foreground hover:bg-muted'
                      }`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Sizes */}
            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase text-foreground">Size</span>
              <div className="flex gap-2">
                {(product.sizes && product.sizes.length > 0 ? product.sizes : STANDARD_SIZES).map(
                  (s) => (
                    <Button
                      key={s}
                      variant={selectedSize === s ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setSelectedSize(s)}
                      className="min-w-10 text-xs font-semibold"
                    >
                      {s}
                    </Button>
                  )
                )}
              </div>
            </div>

            {/* Quantity */}
            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase text-foreground">Quantity</span>
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  disabled={quantity <= 1}
                >
                  <Minus className="w-4 h-4" />
                </Button>
                <span className="font-semibold text-sm w-8 text-center">{quantity}</span>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setQuantity(quantity + 1)}
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
            </div>

            <div className="pt-4">
              <Button size="lg" onClick={handleAddToCart} className="w-full gap-2 shadow-lg">
                {addedNotice ? (
                  <>
                    <Check className="w-5 h-5" />
                    Added to Bag!
                  </>
                ) : (
                  <>
                    <ShoppingBag className="w-5 h-5" />
                    Add to Bag
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}
