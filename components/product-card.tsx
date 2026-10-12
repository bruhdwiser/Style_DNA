"use client"

import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Heart, ShoppingBag } from "lucide-react"
import { resolveColor } from "@/lib/utils"

interface Product {
  id: string | number
  dbId?: string
  name: string
  price: number
  originalPrice?: number
  category: string
  image: string
  colors: string[]
  sizes: string[]
  isNew: boolean
  isSale: boolean
}

interface ProductCardProps {
  product: Product
  onAddToCart?: (productId: string) => void
  onToggleWishlist?: (productId: string) => void
}

export function ProductCard({ product, onAddToCart, onToggleWishlist }: ProductCardProps) {
  return (
    <Card className="group cursor-pointer overflow-hidden card-hover glass border-2 border-primary/5 hover:border-primary/20 backdrop-blur-sm transition-all duration-500">
      <div className="relative aspect-[3/4] bg-gradient-to-br from-muted to-muted/50 overflow-hidden">
        <img
          src={product.image || "/placeholder.svg"}
          alt={product.name}
          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
        />

        {/* Gradient overlay on hover */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

        {/* Badges */}
        <div className="absolute top-3 left-3 flex flex-col gap-2">
          {product.isNew && (
            <Badge variant="secondary" className="text-xs backdrop-blur-md bg-primary/90 text-white border-0 shadow-lg">
              ✨ New
            </Badge>
          )}
          {product.isSale && (
            <Badge className="bg-gradient-to-r from-accent to-destructive text-white text-xs border-0 shadow-lg">
              🔥 Sale
            </Badge>
          )}
        </div>

        {/* Action Buttons */}
        <div className="absolute top-3 right-3 flex flex-col gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="glass backdrop-blur-md border border-white/20 hover:bg-primary/20 hover:border-primary opacity-0 group-hover:opacity-100 transition-all duration-300 hover:scale-110"
            onClick={() => onToggleWishlist?.(String(product.id))}
          >
            <Heart className="h-4 w-4 text-white" />
          </Button>
        </div>

        {/* Quick Add Button */}
        <div className="absolute bottom-3 left-3 right-3 transform translate-y-4 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-500">
          <Button 
            className="w-full bg-gradient-to-r from-primary to-secondary hover:from-secondary hover:to-accent text-white border-0 shadow-lg font-semibold" 
            size="sm" 
            onClick={() => onAddToCart?.(String(product.id))}
          >
            <ShoppingBag className="h-4 w-4 mr-2" />
            Quick Add
          </Button>
        </div>
      </div>

      <CardContent className="p-4 bg-gradient-to-b from-card to-card/80">
        <div className="mb-2">
          <Link href={`/product/${product.dbId || product.id}`}>
            <h3 className="font-sans font-semibold text-foreground group-hover:gradient-text transition-all duration-300 cursor-pointer">
              {product.name}
            </h3>
          </Link>
          <p className="font-serif text-sm text-muted-foreground">{product.category}</p>
        </div>

        <div className="flex items-center gap-2 mb-3">
          <span className="font-sans font-bold text-lg gradient-text">₹{product.price.toFixed(0)}</span>
          {product.originalPrice && (
            <span className="font-serif text-sm text-muted-foreground line-through">₹{product.originalPrice.toFixed(0)}</span>
          )}
        </div>

        {/* Color Options */}
        <div className="flex items-center gap-2 mb-2">
          <span className="font-serif text-xs text-muted-foreground">Colors:</span>
          <div className="flex gap-1">
            {product.colors.slice(0, 3).map((color, index) => (
              <div
                key={index}
                className="w-5 h-5 rounded-full border-2 border-border hover:border-primary transition-all duration-300 hover:scale-110 shadow-sm"
                style={{ backgroundColor: resolveColor(color) }}
              />
            ))}
            {product.colors.length > 3 && (
              <span className="font-serif text-xs text-muted-foreground">+{product.colors.length - 3}</span>
            )}
          </div>
        </div>

        {/* Size Options */}
        <div className="flex items-center gap-2">
          <span className="font-serif text-xs text-muted-foreground">Sizes:</span>
          <span className="font-serif text-xs text-foreground">{product.sizes.join(", ")}</span>
        </div>
      </CardContent>
    </Card>
  )
}
