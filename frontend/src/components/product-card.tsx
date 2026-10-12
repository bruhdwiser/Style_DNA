import React from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ShoppingBag, Star, Eye } from 'lucide-react'
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
  colors = ['Black', 'Navy'],
  sizes = ['S', 'M', 'L'],
  isNew = false,
  isSale = false,
  rating = 4.5,
  reviewCount = 120,
}: ProductCardProps) {
  const { addToCart } = useCart()

  const handleAddToCart = (e: React.MouseEvent) => {
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
    <Card className="group overflow-hidden rounded-2xl border-border bg-card/60 backdrop-blur-sm transition-all duration-300 hover:shadow-xl hover:-translate-y-1">
      <Link to={`/shop/${id}`} className="block relative aspect-3/4 overflow-hidden bg-muted">
        <img
          src={image || '/placeholder.svg'}
          alt={name}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          loading="lazy"
        />

        {/* Badges */}
        <div className="absolute top-3 left-3 flex flex-col gap-1.5 z-10">
          {isNew && <Badge className="bg-primary text-primary-foreground font-semibold">New</Badge>}
          {isSale && <Badge variant="destructive" className="font-semibold">Sale</Badge>}
        </div>

        {/* Quick actions overlay */}
        <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-between p-4">
          <Link
            to={`/product/${id}`}
            className="p-2 rounded-full bg-background/90 text-foreground hover:bg-background transition-colors"
            title="Alternative view"
            onClick={(e) => e.stopPropagation()}
          >
            <Eye className="w-4 h-4" />
          </Link>
          <Button
            size="sm"
            onClick={handleAddToCart}
            className="gap-1.5 shadow-lg bg-primary hover:bg-primary/90 text-primary-foreground font-medium"
          >
            <ShoppingBag className="w-4 h-4" />
            Add to Bag
          </Button>
        </div>
      </Link>

      <CardContent className="p-5">
        <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5">
          <span className="uppercase tracking-wider font-medium">{category}</span>
          <div className="flex items-center gap-1">
            <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
            <span>{rating}</span>
            <span>({reviewCount})</span>
          </div>
        </div>

        <Link to={`/shop/${id}`}>
          <h3 className="font-semibold text-base text-foreground group-hover:text-primary transition-colors line-clamp-1 mb-2">
            {name}
          </h3>
        </Link>

        {/* Colors preview */}
        {colors && colors.length > 0 && (
          <div className="flex items-center gap-1.5 mb-3">
            {colors.slice(0, 4).map((color, idx) => (
              <span
                key={idx}
                className="w-3.5 h-3.5 rounded-full border border-border/80 inline-block shadow-xs"
                style={{ backgroundColor: resolveColor(color) }}
                title={color}
              />
            ))}
            {colors.length > 4 && (
              <span className="text-[10px] text-muted-foreground">+{colors.length - 4}</span>
            )}
          </div>
        )}

        {/* Price */}
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold text-foreground">₹{price.toFixed(0)}</span>
          {originalPrice && originalPrice > price && (
            <span className="text-sm text-muted-foreground line-through">
              ₹{originalPrice.toFixed(0)}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
