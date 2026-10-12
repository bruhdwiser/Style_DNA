import React from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, Heart } from 'lucide-react'

export function Footer() {
  return (
    <footer className="bg-card border-t border-border mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
          {/* Brand */}
          <div className="space-y-4">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-primary to-accent flex items-center justify-center text-primary-foreground">
                <Sparkles className="w-4 h-4" />
              </div>
              <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                FlashFit
              </span>
            </Link>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Curated, AI-powered fashion styling engineered for modern individuals. Express your authentic self.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="font-semibold text-sm mb-4">Shop</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link to="/shop?category=casual" className="hover:text-foreground">Casual</Link></li>
              <li><Link to="/shop?category=formal" className="hover:text-foreground">Formal</Link></li>
              <li><Link to="/shop?category=luxury" className="hover:text-foreground">Luxury</Link></li>
              <li><Link to="/shop" className="hover:text-foreground">All Collections</Link></li>
            </ul>
          </div>

          {/* AI Features */}
          <div>
            <h4 className="font-semibold text-sm mb-4">AI Features</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link to="/ai" className="hover:text-foreground">Style Assistant</Link></li>
              <li><Link to="/shop" className="hover:text-foreground">Outfit Matching</Link></li>
              <li><Link to="/about" className="hover:text-foreground">Technology</Link></li>
            </ul>
          </div>

          {/* Admin & System */}
          <div>
            <h4 className="font-semibold text-sm mb-4">Platform</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li><Link to="/admin" className="hover:text-foreground">Admin Portal</Link></li>
              <li><Link to="/admin/analytics" className="hover:text-foreground">Analytics Dashboard</Link></li>
              <li><Link to="/about" className="hover:text-foreground">About FlashFit</Link></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-border pt-8 flex flex-col sm:flex-row items-center justify-between text-xs text-muted-foreground gap-4">
          <p>© {new Date().getFullYear()} FlashFit AI. All rights reserved.</p>
          <p className="flex items-center gap-1">
            Engineered with <Heart className="w-3.5 h-3.5 text-accent inline fill-accent" /> for next-gen fashion.
          </p>
        </div>
      </div>
    </footer>
  )
}
