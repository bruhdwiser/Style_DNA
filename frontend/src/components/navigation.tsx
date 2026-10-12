import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ShoppingBag, Sparkles, User, Menu, X, Shield, LogOut, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useCart } from '@/contexts/cart-context'
import { useAuth } from '@/contexts/auth-context'

export function Navigation() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { state } = useCart()
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate('/')
  }

  return (
    <nav className="sticky top-0 z-50 backdrop-blur-md bg-background/80 border-b border-border transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-accent flex items-center justify-center text-primary-foreground shadow-md transition-transform group-hover:scale-105">
              <Sparkles className="w-5 h-5" />
            </div>
            <span className="font-bold text-2xl tracking-tight bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent">
              FlashFit
            </span>
          </Link>

          {/* Desktop Links */}
          <div className="hidden md:flex items-center gap-8 font-medium">
            <Link to="/shop" className="text-foreground/80 hover:text-primary transition-colors">
              Shop
            </Link>
            <Link to="/wardrobe" className="text-foreground/80 hover:text-primary transition-colors">
              Wardrobe
            </Link>
            <Link to="/outfits" className="text-foreground/80 hover:text-primary transition-colors">
              Outfits
            </Link>
            <Link to="/style-dna" className="text-foreground/80 hover:text-primary transition-colors">
              Style DNA
            </Link>
            <Link to="/ai" className="text-foreground/80 hover:text-primary transition-colors flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-accent" />
              AI Stylist
            </Link>
            <Link to="/about" className="text-foreground/80 hover:text-primary transition-colors">
              About
            </Link>
            <Link to="/admin" className="text-foreground/80 hover:text-primary transition-colors flex items-center gap-1">
              <Shield className="w-3.5 h-3.5" />
              Admin
            </Link>
          </div>

          {/* Actions */}
          <div className="hidden md:flex items-center gap-4">
            <Link to="/cart">
              <Button variant="ghost" size="icon" className="relative">
                <ShoppingBag className="w-5 h-5" />
                {state.itemCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-accent text-accent-foreground text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center shadow">
                    {state.itemCount}
                  </span>
                )}
              </Button>
            </Link>

            {user ? (
              <div className="flex items-center gap-2">
                <Link
                  to="/settings"
                  className="flex items-center gap-2 px-3 py-1.5 bg-muted hover:bg-muted/80 rounded-full text-xs font-medium max-w-[180px] truncate transition-colors"
                  title="View Settings & Privacy"
                >
                  <User className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                  <span className="truncate">{user.email}</span>
                </Link>
                <Link to="/settings">
                  <Button variant="ghost" size="icon" title="Settings & Privacy">
                    <Settings className="w-4 h-4 text-muted-foreground hover:text-primary" />
                  </Button>
                </Link>
                <Button variant="ghost" size="icon" onClick={handleSignOut} title="Sign Out">
                  <LogOut className="w-4 h-4 text-muted-foreground hover:text-destructive" />
                </Button>
              </div>
            ) : (
              <Link to="/login">
                <Button variant="outline" size="sm" className="gap-2">
                  <User className="w-4 h-4" />
                  Sign In
                </Button>
              </Link>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center gap-2">
            <Link to="/cart">
              <Button variant="ghost" size="icon" className="relative">
                <ShoppingBag className="w-5 h-5" />
                {state.itemCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-accent text-accent-foreground text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center">
                    {state.itemCount}
                  </span>
                )}
              </Button>
            </Link>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-border bg-background/95 backdrop-blur-md px-4 pt-2 pb-6 space-y-3">
          <Link
            to="/shop"
            className="block py-2 text-foreground font-medium"
            onClick={() => setMobileMenuOpen(false)}
          >
            Shop
          </Link>
          <Link
            to="/wardrobe"
            className="block py-2 text-foreground font-medium"
            onClick={() => setMobileMenuOpen(false)}
          >
            Wardrobe
          </Link>
          <Link
            to="/outfits"
            className="block py-2 text-foreground font-medium"
            onClick={() => setMobileMenuOpen(false)}
          >
            Outfits
          </Link>
          <Link
            to="/style-dna"
            className="block py-2 text-foreground font-medium"
            onClick={() => setMobileMenuOpen(false)}
          >
            Style DNA
          </Link>
          <Link
            to="/ai"
            className="block py-2 text-foreground font-medium flex items-center gap-2"
            onClick={() => setMobileMenuOpen(false)}
          >
            <Sparkles className="w-4 h-4 text-accent" />
            AI Stylist
          </Link>
          <Link
            to="/about"
            className="block py-2 text-foreground font-medium"
            onClick={() => setMobileMenuOpen(false)}
          >
            About
          </Link>
          <Link
            to="/admin"
            className="block py-2 text-foreground font-medium"
            onClick={() => setMobileMenuOpen(false)}
          >
            Admin
          </Link>
          <Link
            to="/settings"
            className="block py-2 text-foreground font-medium flex items-center gap-2"
            onClick={() => setMobileMenuOpen(false)}
          >
            <Settings className="w-4 h-4 text-primary" />
            Settings & Privacy
          </Link>
          <div className="pt-2 border-t border-border">
            {user ? (
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-muted-foreground truncate">{user.email}</span>
                <Button variant="outline" size="sm" onClick={handleSignOut}>
                  Sign Out
                </Button>
              </div>
            ) : (
              <Link to="/login" onClick={() => setMobileMenuOpen(false)}>
                <Button className="w-full mt-2">Sign In</Button>
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}
