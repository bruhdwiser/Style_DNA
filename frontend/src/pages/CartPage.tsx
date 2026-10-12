import React from 'react'
import { Link } from 'react-router-dom'
import { ShoppingBag, ArrowLeft, Trash2, Minus, Plus, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { useCart } from '@/contexts/cart-context'
import { resolveColor } from '@/lib/utils'
import { usePageTracking } from '@/lib/tracking'

export default function CartPage() {
  usePageTracking()
  const { state, updateQuantity, removeItem, clearCart } = useCart()

  const shippingCost = state.total > 2000 || state.total === 0 ? 0 : 199
  const tax = state.total * 0.18
  const finalTotal = state.total + shippingCost + tax

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navigation />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link to="/shop">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-extrabold text-foreground tracking-tight">Shopping Bag</h1>
            <p className="text-muted-foreground text-sm">
              {state.itemCount} {state.itemCount === 1 ? 'item' : 'items'} in your active bag
            </p>
          </div>
        </div>

        {state.items.length === 0 ? (
          <div className="text-center py-20 border border-dashed border-border rounded-2xl bg-card/40">
            <ShoppingBag className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-foreground mb-2">Your shopping bag is empty</h2>
            <p className="text-muted-foreground text-sm mb-6 max-w-sm mx-auto">
              Explore our AI-curated collections and discover pieces crafted for your lifestyle.
            </p>
            <Link to="/shop">
              <Button size="lg" className="gap-2">
                Discover Outfits <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
            {/* Items list */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-border">
                <h2 className="font-semibold text-lg">Selected Items</h2>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearCart}
                  className="text-destructive hover:text-destructive hover:bg-destructive/10"
                >
                  <Trash2 className="w-4 h-4 mr-1.5" />
                  Empty Bag
                </Button>
              </div>

              {state.items.map((item) => (
                <Card
                  key={`${item.id}-${item.selectedColor || 'no-color'}-${item.selectedSize || 'no-size'}`}
                  className="overflow-hidden border-border/80"
                >
                  <CardContent className="p-4 sm:p-6">
                    <div className="flex gap-4">
                      {/* Image */}
                      <div className="w-24 h-32 bg-muted rounded-xl overflow-hidden flex-shrink-0 border border-border/60">
                        <img
                          src={item.image || '/placeholder.svg'}
                          alt={item.name}
                          className="w-full h-full object-cover"
                        />
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0 flex flex-col justify-between">
                        <div>
                          <div className="flex justify-between items-start gap-2">
                            <h3 className="font-semibold text-base text-foreground truncate">
                              {item.name}
                            </h3>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeItem(item.id)}
                              className="text-muted-foreground hover:text-destructive h-8 w-8"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                          <p className="text-xs text-muted-foreground capitalize mt-0.5">
                            {item.category || 'Fashion'}
                          </p>

                          <div className="flex items-center gap-4 mt-2 text-xs">
                            {item.selectedColor && (
                              <div className="flex items-center gap-1.5">
                                <span className="text-muted-foreground">Color:</span>
                                <span
                                  className="w-3 h-3 rounded-full border border-border inline-block"
                                  style={{ backgroundColor: resolveColor(item.selectedColor) }}
                                />
                                <span className="font-medium text-foreground">
                                  {item.selectedColor}
                                </span>
                              </div>
                            )}
                            {item.selectedSize && (
                              <div className="flex items-center gap-1">
                                <span className="text-muted-foreground">Size:</span>
                                <span className="font-medium text-foreground">{item.selectedSize}</span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Price & Quantity Controls */}
                        <div className="flex items-center justify-between pt-3 mt-2 border-t border-border/50">
                          <span className="font-bold text-base text-foreground">
                            ₹{(item.price * item.quantity).toFixed(0)}
                          </span>

                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => updateQuantity(item.id, item.quantity - 1)}
                              disabled={item.quantity <= 1}
                              className="h-8 w-8"
                            >
                              <Minus className="w-3.5 h-3.5" />
                            </Button>
                            <span className="w-6 text-center font-semibold text-xs">
                              {item.quantity}
                            </span>
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => updateQuantity(item.id, item.quantity + 1)}
                              className="h-8 w-8"
                            >
                              <Plus className="w-3.5 h-3.5" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Order Summary */}
            <div className="lg:col-span-1 sticky top-24">
              <Card className="border-border/80 shadow-md">
                <CardContent className="p-6 space-y-4">
                  <h3 className="font-bold text-lg text-foreground">Order Summary</h3>

                  <div className="space-y-2.5 text-sm">
                    <div className="flex justify-between text-muted-foreground">
                      <span>Subtotal</span>
                      <span className="font-semibold text-foreground">₹{state.total.toFixed(0)}</span>
                    </div>
                    <div className="flex justify-between text-muted-foreground">
                      <span>Standard Delivery</span>
                      <span className="font-semibold text-foreground">
                        {shippingCost === 0 ? 'FREE' : `₹${shippingCost.toFixed(0)}`}
                      </span>
                    </div>
                    <div className="flex justify-between text-muted-foreground">
                      <span>GST (18%)</span>
                      <span className="font-semibold text-foreground">₹{tax.toFixed(0)}</span>
                    </div>
                  </div>

                  <Separator />

                  <div className="flex justify-between items-baseline pt-1">
                    <span className="font-bold text-base">Estimated Total</span>
                    <span className="font-extrabold text-2xl text-foreground">
                      ₹{finalTotal.toFixed(0)}
                    </span>
                  </div>

                  {state.total < 2000 && state.total > 0 && (
                    <div className="p-3 bg-primary/10 rounded-xl text-xs text-primary font-medium">
                      Add ₹{(2000 - state.total).toFixed(0)} more to unlock complimentary delivery!
                    </div>
                  )}

                  <Button size="lg" className="w-full font-semibold shadow-lg">
                    Proceed to Checkout
                  </Button>

                  <Link to="/shop" className="block text-center">
                    <Button variant="ghost" size="sm" className="w-full text-xs text-muted-foreground">
                      Continue Shopping
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  )
}
