"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { ShoppingBag, Minus, Plus, Trash2, ArrowLeft } from "lucide-react"
import Link from "next/link"
import { useCart } from "@/contexts/cart-context"
import { Navigation } from "@/components/navigation"
import { Footer } from "@/components/footer"
import { resolveColor } from "@/lib/utils"

import { api } from "@/lib/api/client"

export default function CartPage() {
  const { state, dispatch } = useCart()

  const updateQuantity = async (id: string, newQuantity: number) => {
    dispatch({ type: "UPDATE_QUANTITY", payload: { id, quantity: newQuantity } })
    // If the item has a backend cart itemId or matches product UUID, sync with backend
    await api.cart.update(id, newQuantity).catch(err => {
      console.warn("FastAPI cart item update notice:", err)
    })
  }

  const removeItem = async (id: string) => {
    dispatch({ type: "REMOVE_ITEM", payload: id })
    await api.cart.remove(id).catch(err => {
      console.warn("FastAPI cart item remove notice:", err)
    })
  }

  const clearCart = async () => {
    dispatch({ type: "CLEAR_CART" })
    await api.cart.clear().catch(err => {
      console.warn("FastAPI cart clear notice:", err)
    })
  }

  const shippingCost = state.total > 2000 ? 0 : 199
  const tax = state.total * 0.18
  const finalTotal = state.total + shippingCost + tax

  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <Navigation />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link href="/shop">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <h1 className="font-sans font-bold text-3xl md:text-4xl text-foreground">Shopping Cart</h1>
            <p className="font-serif text-muted-foreground">
              {state.itemCount} {state.itemCount === 1 ? "item" : "items"} in your cart
            </p>
          </div>
        </div>

        {state.items.length === 0 ? (
          /* Empty Cart */
          <div className="text-center py-16">
            <ShoppingBag className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <h2 className="font-sans font-bold text-2xl text-foreground mb-2">Your cart is empty</h2>
            <p className="font-serif text-muted-foreground mb-8">
              Discover amazing fashion pieces and add them to your cart
            </p>
            <Link href="/shop">
              <Button size="lg">Continue Shopping</Button>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Cart Items */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-sans font-semibold text-xl">Cart Items</h2>
                <Button variant="ghost" onClick={clearCart} className="text-destructive hover:text-destructive">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Clear Cart
                </Button>
              </div>

              {state.items.map((item) => (
                <Card key={`${item.id}-${item.selectedColor ?? 'no-color'}-${item.selectedSize ?? 'no-size'}`}>
                  <CardContent className="p-6">
                    <div className="flex gap-4">
                      <div className="w-24 h-32 bg-muted rounded-lg overflow-hidden flex-shrink-0">
                        <img
                          src={item.image || "/placeholder.svg"}
                          alt={item.name}
                          className="w-full h-full object-cover"
                        />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <h3 className="font-sans font-semibold text-foreground">{item.name}</h3>
                            <p className="font-serif text-sm text-muted-foreground">{item.category}</p>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => removeItem(item.id)}
                            className="text-muted-foreground hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>

                        <div className="flex items-center gap-4 mb-3">
                          <div className="flex items-center gap-2">
                            <span className="font-serif text-sm text-muted-foreground">Color:</span>
                            <div
                              className="w-4 h-4 rounded-full border border-border"
                              style={{ backgroundColor: resolveColor(item.selectedColor) }}
                            />
                            <span className="font-serif text-sm text-foreground">{item.selectedColor ?? "—"}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="font-serif text-sm text-muted-foreground">Size:</span>
                            <span className="font-serif text-sm text-foreground">{item.selectedSize}</span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-sans font-bold text-lg text-foreground">₹{item.price.toFixed(0)}</span>
                            {item.originalPrice && (
                              <span className="font-serif text-sm text-muted-foreground line-through">
                                ₹{item.originalPrice.toFixed(0)}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => updateQuantity(item.id, item.quantity - 1)}
                              disabled={item.quantity <= 1}
                            >
                              <Minus className="h-4 w-4" />
                            </Button>
                            <span className="font-sans font-medium text-foreground w-8 text-center">
                              {item.quantity}
                            </span>
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => updateQuantity(item.id, item.quantity + 1)}
                            >
                              <Plus className="h-4 w-4" />
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
            <div className="lg:col-span-1">
              <Card className="sticky top-24">
                <CardContent className="p-6">
                  <h2 className="font-sans font-semibold text-xl mb-4">Order Summary</h2>

                  <div className="space-y-3 mb-4">
                    <div className="flex justify-between">
                      <span className="font-serif text-muted-foreground">Subtotal</span>
                      <span className="font-sans font-medium">₹{state.total.toFixed(0)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-serif text-muted-foreground">Shipping</span>
                      <span className="font-sans font-medium">
                        {shippingCost === 0 ? "Free" : `₹${shippingCost.toFixed(0)}`}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-serif text-muted-foreground">Tax (GST 18%)</span>
                      <span className="font-sans font-medium">₹{tax.toFixed(0)}</span>
                    </div>
                  </div>

                  <Separator className="my-4" />

                  <div className="flex justify-between mb-6">
                    <span className="font-sans font-semibold text-lg">Total</span>
                    <span className="font-sans font-bold text-lg">₹{finalTotal.toFixed(0)}</span>
                  </div>

                  {state.total < 2000 && (
                    <div className="bg-secondary/10 border border-secondary/20 rounded-lg p-3 mb-4">
                      <p className="font-serif text-sm text-secondary-foreground">
                        Add ₹{(2000 - state.total).toFixed(0)} more for free shipping!
                      </p>
                    </div>
                  )}

                  <Button className="w-full mb-3" size="lg">
                    Proceed to Checkout
                  </Button>

                  <Link href="/shop">
                    <Button variant="outline" className="w-full bg-transparent">
                      Continue Shopping
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <Footer />
    </div>
  )
}
