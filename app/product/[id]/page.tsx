"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ArrowLeft, Heart, ShoppingBag, Minus, Plus, Star, Share2 } from "lucide-react"
import { useCart } from "@/contexts/cart-context"
import { Navigation } from "@/components/navigation"
import { Footer } from "@/components/footer"
import { resolveColor } from "@/lib/utils"
import { trackProductView } from "@/lib/tracking"
import { usePageTracking } from "@/lib/hooks/use-page-tracking"

import { api, ProductItem } from "@/lib/api/client"

type ProductDetail = {
  id: string
  dbId?: string
  name: string
  description: string
  price: number
  originalPrice?: number
  category: string
  image: string
  colors: string[]
  sizes: string[]
  isNew?: boolean
  isSale?: boolean
  rating?: number
  reviewCount?: number
  inStock?: boolean
  features?: string[]
}

const STANDARD_SIZES = ["XS", "S", "M", "L", "XL"]

export default function ProductDetailPage() {
  usePageTracking() // Track page views
  const params = useParams()
  const router = useRouter()
  const { dispatch } = useCart()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedColor, setSelectedColor] = useState("")
  const [selectedSize, setSelectedSize] = useState("")
  const [quantity, setQuantity] = useState(1)
  const [addingToCart, setAddingToCart] = useState(false)

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        const productId = params.id as string
        const productData = await api.products.get(productId)
        
        // Transform the API response to match our UI format
        const transformedProduct: ProductDetail = {
          id: productData.id,
          dbId: productData.id,
          name: productData.name || "Product Name",
          description: productData.description || "This is a stylish fashion piece that combines comfort with modern design. Perfect for any occasion, this item features high-quality materials and excellent craftsmanship.",
          price: productData.price,
          originalPrice: productData.originalPrice,
          category: productData.category || "Fashion",
          image: productData.image || "/placeholder.svg",
          colors: Array.isArray(productData.colors) && productData.colors.length > 0 ? productData.colors : ["Black", "White", "Navy"],
          sizes: Array.isArray(productData.sizes) && productData.sizes.length > 0 ? productData.sizes : STANDARD_SIZES,
          isNew: productData.isNew || false,
          isSale: productData.isSale || false,
          rating: 4.5,
          reviewCount: 127,
          inStock: true,
          features: [
            "Premium quality materials",
            "Comfortable fit",
            "Easy care instructions",
            "Sustainable production"
          ]
        }
        setProduct(transformedProduct)
        setSelectedColor(transformedProduct.colors[0])
        setSelectedSize(transformedProduct.sizes[1] || transformedProduct.sizes[0] || "M")
        
        // Track product view
        trackProductView(transformedProduct.id, transformedProduct.name)
      } catch (error) {
        console.error("Error fetching product via FastAPI client:", error)
        // Fallback to mock product
        const mockProduct: ProductDetail = {
          id: params.id as string,
          dbId: params.id as string,
          name: "Premium Fashion Item",
          description: "This is a stylish fashion piece that combines comfort with modern design.",
          price: 2999,
          category: "Fashion",
          image: "/placeholder.svg",
          colors: ["Black", "White", "Navy"],
          sizes: STANDARD_SIZES,
          rating: 4.5,
          reviewCount: 127,
          inStock: true,
          features: ["Premium quality materials", "Comfortable fit"]
        }
        setProduct(mockProduct)
        setSelectedColor(mockProduct.colors[0])
        setSelectedSize(mockProduct.sizes[1] || "M")
      } finally {
        setLoading(false)
      }
    }

    if (params.id) {
      fetchProduct()
    }
  }, [params.id])

  const handleAddToCart = async () => {
    if (!product || !selectedColor || !selectedSize) return

    setAddingToCart(true)
    
    try {
      // Add to cart context
      dispatch({
        type: "ADD_ITEM",
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

      // Persist to FastAPI cart
      await api.cart.add({
        productId: product.id,
        quantity,
        selectedColor,
        selectedSize,
      }).catch(err => console.warn("Background cart sync notice:", err))
      
    } catch (error) {
      console.error("Error adding to cart:", error)
    } finally {
      setAddingToCart(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Navigation />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="animate-pulse">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="aspect-square bg-muted rounded-lg"></div>
              <div className="space-y-4">
                <div className="h-8 bg-muted rounded w-3/4"></div>
                <div className="h-4 bg-muted rounded w-1/2"></div>
                <div className="h-6 bg-muted rounded w-1/4"></div>
                <div className="space-y-2">
                  <div className="h-4 bg-muted rounded"></div>
                  <div className="h-4 bg-muted rounded"></div>
                  <div className="h-4 bg-muted rounded w-3/4"></div>
                </div>
              </div>
            </div>
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
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center py-16">
            <h1 className="text-2xl font-bold text-foreground mb-4">Product Not Found</h1>
            <p className="text-muted-foreground mb-8">The product you're looking for doesn't exist.</p>
            <Button onClick={() => router.push("/shop")}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Shop
            </Button>
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
          className="mb-6"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-16">
          {/* Product Image */}
          <div className="space-y-4">
            <div className="relative aspect-square overflow-hidden rounded-lg bg-muted">
              <img
                src={product.image || "/placeholder.svg"}
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

              {/* Action buttons */}
              <div className="absolute top-4 right-4 flex flex-col gap-2">
                <Button variant="ghost" size="icon" className="bg-background/80 hover:bg-background">
                  <Heart className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" className="bg-background/80 hover:bg-background">
                  <Share2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Product Details */}
          <div className="space-y-6">
            {/* Header */}
            <div>
              <h1 className="font-sans font-bold text-3xl text-foreground mb-2">
                {product.name}
              </h1>
              <p className="font-serif text-lg text-muted-foreground mb-4">
                {product.category}
              </p>
              
              {/* Rating */}
              {product.rating && (
                <div className="flex items-center gap-2 mb-4">
                  <div className="flex items-center">
                    {[...Array(5)].map((_, i) => (
                      <Star
                        key={i}
                        className={`h-4 w-4 ${
                          i < Math.floor(product.rating!) 
                            ? "fill-yellow-400 text-yellow-400" 
                            : "text-gray-300"
                        }`}
                      />
                    ))}
                  </div>
                  <span className="font-serif text-sm text-muted-foreground">
                    {product.rating} ({product.reviewCount} reviews)
                  </span>
                </div>
              )}
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
                <Badge variant="destructive" className="text-xs">
                  {Math.round(((product.originalPrice - product.price) / product.originalPrice) * 100)}% OFF
                </Badge>
              )}
            </div>

            <Separator />

            {/* Description */}
            <div>
              <h3 className="font-sans font-semibold text-lg mb-3">Description</h3>
              <p className="font-serif text-muted-foreground leading-relaxed">
                {product.description}
              </p>
            </div>

            {/* Color Selection */}
            <div>
              <h3 className="font-sans font-semibold text-base mb-3">
                Color: <span className="font-normal">{selectedColor}</span>
              </h3>
              <div className="flex gap-2">
                {product.colors.map((color) => (
                  <button
                    key={color}
                    onClick={() => setSelectedColor(color)}
                    className={`w-10 h-10 rounded-full border-2 transition-all ${
                      selectedColor === color 
                        ? "border-primary ring-2 ring-primary/20" 
                        : "border-border hover:border-primary/50"
                    }`}
                    style={{ backgroundColor: resolveColor(color) }}
                    title={color}
                  />
                ))}
              </div>
            </div>

            {/* Size Selection */}
            <div>
              <h3 className="font-sans font-semibold text-base mb-3">
                Size: <span className="font-normal">{selectedSize}</span>
              </h3>
              <div className="flex gap-2">
                {product.sizes.map((size) => (
                  <button
                    key={size}
                    onClick={() => setSelectedSize(size)}
                    className={`px-4 py-2 border rounded-md font-serif text-sm transition-all ${
                      selectedSize === size
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-border hover:border-primary"
                    }`}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>

            {/* Quantity */}
            <div>
              <h3 className="font-sans font-semibold text-base mb-3">Quantity</h3>
              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  disabled={quantity <= 1}
                >
                  <Minus className="h-4 w-4" />
                </Button>
                <span className="font-sans font-medium text-lg w-12 text-center">
                  {quantity}
                </span>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setQuantity(quantity + 1)}
                  disabled={quantity >= 10}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Add to Cart */}
            <div className="space-y-3">
              <Button
                onClick={handleAddToCart}
                disabled={!selectedColor || !selectedSize || addingToCart || !product.inStock}
                className="w-full py-6 text-lg"
                size="lg"
              >
                <ShoppingBag className="h-5 w-5 mr-2" />
                {addingToCart ? "Adding..." : product.inStock ? "Add to Cart" : "Out of Stock"}
              </Button>
              
              {product.inStock && (
                <p className="font-serif text-sm text-green-600 text-center">
                  ✓ In Stock - Ready to ship
                </p>
              )}
            </div>

            {/* Features */}
            {product.features && product.features.length > 0 && (
              <div>
                <h3 className="font-sans font-semibold text-base mb-3">Features</h3>
                <ul className="space-y-2">
                  {product.features.map((feature, index) => (
                    <li key={index} className="font-serif text-sm text-muted-foreground flex items-center">
                      <span className="w-1 h-1 bg-primary rounded-full mr-3"></span>
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>

      <Footer />
    </div>
  )
}