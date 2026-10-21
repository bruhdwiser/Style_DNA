import React from 'react'
import { Routes, Route } from 'react-router-dom'
import HomePage from '@/pages/HomePage'
import ShopPage from '@/pages/ShopPage'
import ShopProductDetailPage from '@/pages/ShopProductDetailPage'
import CartPage from '@/pages/CartPage'
import LoginPage from '@/pages/LoginPage'
import AuthCallbackPage from '@/pages/AuthCallbackPage'
import AiStylistPage from '@/pages/AiStylistPage'
import AboutPage from '@/pages/AboutPage'
import AdminPage from '@/pages/AdminPage'
import AdminAnalyticsPage from '@/pages/AdminAnalyticsPage'
import StyleOnboardingPage from '@/pages/StyleOnboardingPage'
import WardrobePage from '@/pages/WardrobePage'
import OutfitsPage from '@/pages/OutfitsPage'
import StyleDnaPage from '@/pages/StyleDnaPage'
import SettingsPage from '@/pages/SettingsPage'
import { AdminGuard } from '@/components/AdminGuard'

export function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/shop" element={<ShopPage />} />
      <Route path="/shop/:id" element={<ShopProductDetailPage />} />
      <Route path="/product/:id" element={<ShopProductDetailPage />} />
      <Route path="/cart" element={<CartPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route path="/ai" element={<AiStylistPage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/style-onboarding" element={<StyleOnboardingPage />} />
      <Route path="/wardrobe" element={<WardrobePage />} />
      <Route path="/outfits" element={<OutfitsPage />} />
      <Route path="/style-dna" element={<StyleDnaPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/profile" element={<SettingsPage />} />

      {/* Admin routes wrapped with UI route guard; FastAPI handles server-side authorization */}
      <Route
        path="/admin"
        element={
          <AdminGuard>
            <AdminPage />
          </AdminGuard>
        }
      />
      <Route
        path="/admin/add-product"
        element={
          <AdminGuard>
            <AdminPage />
          </AdminGuard>
        }
      />
      <Route
        path="/admin/analytics"
        element={
          <AdminGuard>
            <AdminAnalyticsPage />
          </AdminGuard>
        }
      />

      {/* Fallback */}
      <Route path="*" element={<HomePage />} />
    </Routes>
  )
}

export default App
