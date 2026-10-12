"use client"

import type React from "react"
import { createContext, useContext, useReducer, useEffect, type ReactNode } from "react"
import { api } from "@/lib/api/client"
import { supabaseBrowser } from "@/lib/supabase/client"

export interface CartItem {
  id: string // Consistent product UUID
  name: string
  price: number
  originalPrice?: number
  image: string
  category: string
  selectedColor?: string
  selectedSize?: string
  quantity: number
}

interface CartState {
  items: CartItem[]
  total: number
  itemCount: number
}

type CartAction =
  | { type: "ADD_ITEM"; payload: Omit<CartItem, "quantity"> & { quantity?: number } }
  | { type: "REMOVE_ITEM"; payload: string }
  | { type: "UPDATE_QUANTITY"; payload: { id: string; quantity: number } }
  | { type: "CLEAR_CART" }
  | { type: "SET_ITEMS"; payload: CartItem[] }

const CartContext = createContext<{
  state: CartState
  dispatch: React.Dispatch<CartAction>
  syncWithBackend: () => Promise<void>
} | null>(null)

function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case "SET_ITEMS": {
      const items = action.payload
      const total = items.reduce((sum, item) => sum + item.price * item.quantity, 0)
      const itemCount = items.reduce((sum, item) => sum + item.quantity, 0)
      return { items, total, itemCount }
    }

    case "ADD_ITEM": {
      const addQty = action.payload.quantity || 1
      const existingItem = state.items.find(
        (item) =>
          item.id === String(action.payload.id) &&
          item.selectedColor === action.payload.selectedColor &&
          item.selectedSize === action.payload.selectedSize,
      )

      let newItems: CartItem[]
      if (existingItem) {
        newItems = state.items.map((item) =>
          item.id === existingItem.id &&
          item.selectedColor === existingItem.selectedColor &&
          item.selectedSize === existingItem.selectedSize
            ? { ...item, quantity: item.quantity + addQty }
            : item,
        )
      } else {
        newItems = [...state.items, { ...action.payload, id: String(action.payload.id), quantity: addQty }]
      }

      const total = newItems.reduce((sum, item) => sum + item.price * item.quantity, 0)
      const itemCount = newItems.reduce((sum, item) => sum + item.quantity, 0)

      return { items: newItems, total, itemCount }
    }

    case "REMOVE_ITEM": {
      const targetId = String(action.payload)
      const newItems = state.items.filter((item) => String(item.id) !== targetId)
      const total = newItems.reduce((sum, item) => sum + item.price * item.quantity, 0)
      const itemCount = newItems.reduce((sum, item) => sum + item.quantity, 0)

      return { items: newItems, total, itemCount }
    }

    case "UPDATE_QUANTITY": {
      const targetId = String(action.payload.id)
      const newItems = state.items
        .map((item) =>
          String(item.id) === targetId ? { ...item, quantity: Math.max(0, action.payload.quantity) } : item,
        )
        .filter((item) => item.quantity > 0)

      const total = newItems.reduce((sum, item) => sum + item.price * item.quantity, 0)
      const itemCount = newItems.reduce((sum, item) => sum + item.quantity, 0)

      return { items: newItems, total, itemCount }
    }

    case "CLEAR_CART":
      return { items: [], total: 0, itemCount: 0 }

    default:
      return state
  }
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(cartReducer, {
    items: [],
    total: 0,
    itemCount: 0,
  })

  // Sync cart with FastAPI backend when authenticated
  const syncWithBackend = async () => {
    try {
      const supabase = supabaseBrowser()
      const { data: { session } } = await supabase.auth.getSession()
      if (session) {
        const cartData = await api.cart.get()
        if (cartData?.items) {
          const transformed: CartItem[] = cartData.items.map((i) => ({
            id: i.product_id,
            name: i.product?.name || 'Product',
            price: i.product?.price || 0,
            image: i.product?.image || '/placeholder.svg',
            category: i.product?.category || 'General',
            selectedColor: i.selected_color,
            selectedSize: i.selected_size,
            quantity: i.quantity,
          }))
          dispatch({ type: 'SET_ITEMS', payload: transformed })
        }
      }
    } catch {
      // Offline or unauthenticated; retain local state
    }
  }

  useEffect(() => {
    syncWithBackend()
  }, [])

  return (
    <CartContext.Provider value={{ state, dispatch, syncWithBackend }}>
      {children}
    </CartContext.Provider>
  )
}

export function useCart() {
  const context = useContext(CartContext)
  if (!context) {
    throw new Error("useCart must be used within a CartProvider")
  }
  return context
}
