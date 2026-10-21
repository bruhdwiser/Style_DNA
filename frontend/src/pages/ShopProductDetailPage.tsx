import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
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
      <div className="page-shell product-loading-page">
        <Navigation />
        <div className="product-loading-state">
          <div>
            <p className="eyebrow">STYLESENSE / THE RACK</p>
            <h1>One moment.</h1>
            <p>Opening the piece dossier…</p>
          </div>
        </div>
        <Footer />
      </div>
    )
  }

  if (!product) {
    return (
      <div className="page-shell product-missing-page">
        <Navigation />
        <div className="product-missing-state">
          <p className="eyebrow">STYLESENSE / THE RACK</p>
          <h1>That piece<br /><em>has left the building.</em></h1>
          <p>
            We can’t find this item in the rack anymore.
          </p>
          <Link to="/shop">
            <Button>BACK TO THE RACK →</Button>
          </Link>
        </div>
        <Footer />
      </div>
    )
  }

  return (
    <div className="page-shell product-detail-page">
      <Navigation />

      <main className="page-main product-detail-main">
        <Link to="/shop" className="product-back-link">← THE RACK</Link>

        {/* Main Product Layout */}
        <div className="product-dossier">
          {/* Gallery / Image */}
          <div className="product-dossier-image">
            <img
              src={product.image || '/placeholder.svg'}
              alt={product.name}
              className="w-full h-full object-cover"
            />
            {(product.isNew || product.isSale) && <span className="product-dossier-stamp">{product.isSale ? 'PRICE DROP' : 'NEW IN'}</span>}
            <span className="product-dossier-index">FF / {product.id.slice(0, 4).toUpperCase()}</span>
          </div>

          {/* Details & Actions */}
          <div className="product-dossier-info">
            <div>
              <span className="eyebrow">
                {product.category}
              </span>
              <h1 className="product-dossier-title">
                {product.name}
              </h1>
            </div>

            {/* Price */}
            <div className="product-dossier-price">
              <span>
                ₹{product.price.toFixed(0)}
              </span>
              {product.originalPrice && product.originalPrice > product.price && (
                <del>
                  ₹{product.originalPrice.toFixed(0)}
                </del>
              )}
              {product.originalPrice && product.originalPrice > product.price && (
                <span className="product-savings">
                  SAVE ₹{(product.originalPrice - product.price).toFixed(0)}
                </span>
              )}
            </div>

            {/* Description */}
            <p className="product-dossier-description">
              {product.description ||
                `A ${product.category} piece from the StyleSense rack, ready for another way to wear.`}
            </p>

            {/* Color selection */}
            {product.colors && product.colors.length > 0 && (
              <div className="product-choice-group">
                <label className="eyebrow">
                  COLOUR / <span>{selectedColor}</span>
                </label>
                <div className="product-colour-options">
                  {product.colors.map((color) => (
                    <button
                      key={color}
                      onClick={() => setSelectedColor(color)}
                      className={`product-colour-option${selectedColor === color ? ' selected' : ''}`}
                      title={color}
                      aria-label={`Select ${color}`}
                      aria-pressed={selectedColor === color}
                    >
                      <span className="product-colour-swatch" style={{ backgroundColor: resolveColor(color) }} />
                      <span>{color}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Size selection */}
            <div className="product-choice-group">
              <div className="product-choice-heading">
                <label className="eyebrow">SIZE / {selectedSize}</label>
                <span className="product-size-note">CHOOSE WHAT YOU USUALLY WEAR</span>
              </div>
              <div className="product-size-options">
                {(product.sizes && product.sizes.length > 0 ? product.sizes : STANDARD_SIZES).map(
                  (size) => (
                    <Button
                      key={size}
                      variant={selectedSize === size ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setSelectedSize(size)}
                      className="product-size-option"
                    >
                      {size}
                    </Button>
                  )
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="product-dossier-actions">
              <Button
                size="lg"
                onClick={handleAddToCart}
                className="product-add-button"
              >
                {addedNotice ? 'IN THE BAG ✓' : 'ADD TO BAG →'}
              </Button>
            </div>
            <p className="product-dossier-note">Colour, size, and fit details are shown as provided by the seller.</p>
          </div>
        </div>

        {/* Similar Products */}
        {similarProducts.length > 0 && (
          <div className="product-related">
            <h2>More from this rail.</h2>
            <div className="product-grid">
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
