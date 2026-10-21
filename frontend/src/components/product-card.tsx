import React from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useCart } from '@/contexts/cart-context'
import { resolveColor } from '@/lib/utils'

export interface ProductCardProps {
  id: string
  name: string
  price: number
  originalPrice?: number
  category: string
  image: string
  colors?: string[]
  sizes?: string[]
  isNew?: boolean
  isSale?: boolean
  style_tags?: string[]
  occasions?: string[]
  rating?: number
  reviewCount?: number
}

export function ProductCard({
  id,
  name,
  price,
  originalPrice,
  category,
  image,
  colors = [],
  sizes = [],
  isNew = false,
  isSale = false,
  style_tags = [],
  occasions = [],
}: ProductCardProps) {
  const { addToCart } = useCart()

  const handleAddToCart = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    addToCart({
      id,
      name,
      price,
      originalPrice,
      image,
      category,
      selectedColor: colors[0] || 'Standard',
      selectedSize: sizes[0] || 'M',
    })
  }

  return (
    <article className="product-tile">
      <Link to={`/shop/${id}`} className="product-tile-image-link" aria-label={`View ${name}`}>
        <div className="product-tile-image">
          <img src={image || '/placeholder.svg'} alt={name} loading="lazy" />
          {isSale ? (
            <span className="product-stamp product-stamp--sale">PRICE DROP</span>
          ) : isNew ? (
            <span className="product-stamp product-stamp--new">NEW IN</span>
          ) : null}
          <span className="product-image-index">FF / {id.slice(0, 4).toUpperCase()}</span>
        </div>
      </Link>

      <div className="product-tile-copy">
        <div className="product-tile-kicker">
          <span>{category || 'PIECE'}</span>
          {colors.length > 0 && <span>{colors.length} COLOUR{colors.length === 1 ? '' : 'S'}</span>}
        </div>
        <Link to={`/shop/${id}`} className="product-tile-name">{name}</Link>
        {(style_tags.length > 0 || occasions.length > 0) && (
          <div className="product-tile-tags" aria-label="Clothing tags">
            {[...style_tags, ...occasions].slice(0, 3).map((tag) => (
              <span key={tag}>{tag.replace(/_/g, ' ')}</span>
            ))}
          </div>
        )}
        <div className="product-tile-bottom">
          <p className="product-tile-price">
            ₹{price.toFixed(0)}
            {originalPrice && originalPrice > price && (
              <del>₹{originalPrice.toFixed(0)}</del>
            )}
          </p>
          <div className="product-tile-colors" aria-label="Available colours">
            {colors.slice(0, 4).map((color, idx) => (
              <span
                key={`${color}-${idx}`}
                title={color}
                aria-label={color}
                style={{ backgroundColor: resolveColor(color) }}
              />
            ))}
          </div>
        </div>
        <Button type="button" variant="link" onClick={handleAddToCart} className="product-tile-add">
          ADD TO BAG <span aria-hidden="true">+</span>
        </Button>
      </div>
    </article>
  )
}
