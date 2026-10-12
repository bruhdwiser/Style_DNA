import React, { createContext, useContext, useReducer, useEffect } from "react"
import { api } from "@/lib/api"
import { useAuth } from "./auth-context"

export interface CartItem {
  id: string
  name: string
  price: number
  originalPrice?: number
  image: string
  category?: string
  quantity: number
  selectedColor?: string
  selectedSize?: string
}

interface CartState {
  items: CartItem[]
  total: number
  itemCount: number
}

type CartAction =
  | { type: "ADD_ITEM"; payload: Omit<CartItem, "quantity"> }
  | { type: "REMOVE_ITEM"; payload: string }
  | { type: "UPDATE_QUANTITY"; payload: { id: string; quantity: number } }
  | { type: "CLEAR_CART" }
  | { type: "SET_CART"; payload: CartItem[] }

const CartContext = createContext<{
  state: CartState
  dispatch: React.Dispatch<CartAction>
  addToCart: (item: Omit<CartItem, "quantity">, quantity?: number) => Promise<void>
  updateQuantity: (id: string, quantity: number) => Promise<void>
  removeItem: (id: string) => Promise<void>
  clearCart: () => Promise<void>
} | null>(null)

const cartReducer = (state: CartState, action: CartAction): CartState => {
  switch (action.type) {
    case "SET_CART": {
      const items = action.payload
      const total = items.reduce((sum, item) => sum + item.price * item.quantity, 0)
      const itemCount = items.reduce((sum, item) => sum + item.quantity, 0)
      return { items, total, itemCount }
    }

    case "ADD_ITEM": {
      const existingItemIndex = state.items.findIndex(
        (item) =>
          item.id === action.payload.id &&
          item.selectedColor === action.payload.selectedColor &&
          item.selectedSize === action.payload.selectedSize
      )

      let updatedItems: CartItem[]

      if (existingItemIndex > -1) {
        updatedItems = state.items.map((item, index) =>
          index === existingItemIndex ? { ...item, quantity: item.quantity + 1 } : item
        )
      } else {
        updatedItems = [...state.items, { ...action.payload, quantity: 1 }]
      }

      const total = updatedItems.reduce((sum, item) => sum + item.price * item.quantity, 0)
      const itemCount = updatedItems.reduce((sum, item) => sum + item.quantity, 0)

      return { items: updatedItems, total, itemCount }
    }

    case "REMOVE_ITEM": {
      const updatedItems = state.items.filter((item) => item.id !== action.payload)
      const total = updatedItems.reduce((sum, item) => sum + item.price * item.quantity, 0)
      const itemCount = updatedItems.reduce((sum, item) => sum + item.quantity, 0)
      return { items: updatedItems, total, itemCount }
    }

    case "UPDATE_QUANTITY": {
      const updatedItems = state.items
        .map((item) =>
          item.id === action.payload.id ? { ...item, quantity: action.payload.quantity } : item
        )
        .filter((item) => item.quantity > 0)

      const total = updatedItems.reduce((sum, item) => sum + item.price * item.quantity, 0)
      const itemCount = updatedItems.reduce((sum, item) => sum + item.quantity, 0)
      return { items: updatedItems, total, itemCount }
    }

    case "CLEAR_CART":
      return { items: [], total: 0, itemCount: 0 }

    default:
      return state
  }
}

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(cartReducer, { items: [], total: 0, itemCount: 0 })
  const { user } = useAuth()

  // Sync cart from FastAPI when user is authenticated
  useEffect(() => {
    if (!user) return

    api.cart
      .get()
      .then((cartData) => {
        if (cartData && Array.isArray(cartData.items)) {
          const mappedItems: CartItem[] = cartData.items.map((item) => ({
            id: item.productId,
            name: item.product?.name || "Product",
            price: item.product ? item.product.priceCents / 100 : 0,
            image: item.product?.imageUrl || "/placeholder.svg",
            category: item.product?.category || "Fashion",
            quantity: item.quantity,
            selectedColor: item.selectedColor || undefined,
            selectedSize: item.selectedSize || undefined,
          }))
          dispatch({ type: "SET_CART", payload: mappedItems })
        }
      })
      .catch((err) => {
        console.warn("Could not sync cart from backend:", err)
      })
  }, [user])

  const addToCart = async (item: Omit<CartItem, "quantity">, quantity = 1) => {
    dispatch({ type: "ADD_ITEM", payload: item })
    try {
      await api.cart.add({
        productId: item.id,
        quantity,
        selectedColor: item.selectedColor,
        selectedSize: item.selectedSize,
      })
    } catch (err) {
      console.warn("Backend cart add error:", err)
    }
  }

  const updateQuantity = async (id: string, quantity: number) => {
    dispatch({ type: "UPDATE_QUANTITY", payload: { id, quantity } })
    try {
      await api.cart.update(id, quantity)
    } catch (err) {
      console.warn("Backend cart update error:", err)
    }
  }

  const removeItem = async (id: string) => {
    dispatch({ type: "REMOVE_ITEM", payload: id })
    try {
      await api.cart.remove(id)
    } catch (err) {
      console.warn("Backend cart remove error:", err)
    }
  }

  const clearCart = async () => {
    dispatch({ type: "CLEAR_CART" })
    try {
      await api.cart.clear()
    } catch (err) {
      console.warn("Backend cart clear error:", err)
    }
  }

  return (
    <CartContext.Provider
      value={{ state, dispatch, addToCart, updateQuantity, removeItem, clearCart }}
    >
      {children}
    </CartContext.Provider>
  )
}

export const useCart = () => {
  const context = useContext(CartContext)
  if (!context) {
    throw new Error("useCart must be used within a CartProvider")
  }
  return context
}
