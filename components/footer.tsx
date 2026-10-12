"use client"

import { Sparkles } from "lucide-react"
import Link from "next/link"
import { useCookieConsent } from "@/contexts/cookie-consent-context"

const footerLinks = {
  Shop: [
    { name: "New Arrivals", href: "/shop?filter=new" },
    { name: "Best Sellers", href: "/shop?filter=bestsellers" },
    { name: "Sale", href: "/shop?filter=sale" },
    { name: "Gift Cards", href: "/gift-cards" },
  ],
  Support: [
    { name: "Size Guide", href: "/size-guide" },
    { name: "Shipping & Returns", href: "/shipping" },
    { name: "Contact Us", href: "/contact" },
    { name: "FAQ", href: "/faq" },
  ],
  Company: [
    { name: "About Us", href: "/about" },
    { name: "Careers", href: "/careers" },
    { name: "Press", href: "/press" },
    { name: "Sustainability", href: "/sustainability" },
  ],
}

export function Footer() {
  const { openSettings } = useCookieConsent()

  return (
    <footer className="relative border-t border-border/50 bg-gradient-to-b from-background to-muted/30 overflow-hidden">
      {/* Gradient background effect */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-gradient-to-br from-primary/20 to-transparent rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-gradient-to-br from-secondary/20 to-transparent rounded-full blur-3xl" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8">
          {/* Brand Section */}
          <div className="lg:col-span-2">
            <div className="flex items-center gap-2 mb-4 group">
              <div className="relative">
                <Sparkles className="h-6 w-6 text-primary group-hover:text-secondary transition-colors duration-300" />
                <div className="absolute inset-0 bg-primary/20 rounded-full blur-lg group-hover:bg-secondary/30 transition-all duration-300" />
              </div>
              <span className="font-sans font-bold text-xl gradient-text">Flashfits</span>
            </div>
            <p className="font-serif text-muted-foreground mb-6 max-w-md leading-relaxed">
              AI-powered fashion platform delivering personalized style recommendations for your unique taste.
            </p>
            <div className="flex gap-4">
              <Link 
                href="/newsletter" 
                className="text-sm text-muted-foreground hover:text-primary transition-all duration-300 relative group"
              >
                Newsletter
                <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-gradient-to-r from-primary to-secondary group-hover:w-full transition-all duration-300" />
              </Link>
              <Link 
                href="/privacy" 
                className="text-sm text-muted-foreground hover:text-primary transition-all duration-300 relative group"
              >
                Privacy Policy
                <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-gradient-to-r from-primary to-secondary group-hover:w-full transition-all duration-300" />
              </Link>
              <Link 
                href="/terms" 
                className="text-sm text-muted-foreground hover:text-primary transition-all duration-300 relative group"
              >
                Terms of Service
                <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-gradient-to-r from-primary to-secondary group-hover:w-full transition-all duration-300" />
              </Link>
            </div>
          </div>

          {/* Footer Links */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h3 className="font-sans font-semibold text-foreground mb-4">{category}</h3>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.name}>
                    <Link
                      href={link.href}
                      className="font-serif text-sm text-muted-foreground hover:text-primary transition-all duration-300 relative group inline-block"
                    >
                      {link.name}
                      <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-border/50 mt-12 pt-8 flex flex-col md:flex-row justify-between items-center">
          <p className="font-serif text-sm text-muted-foreground mb-4 md:mb-0">
            © 2025 Flashfits. All rights reserved.
          </p>
          <div className="flex gap-6">
            <Link 
              href="/accessibility" 
              className="text-sm text-muted-foreground hover:text-primary transition-all duration-300 relative group"
            >
              Accessibility
              <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
            </Link>
            <button
              onClick={openSettings}
              className="text-sm text-muted-foreground hover:text-primary transition-all duration-300 relative group"
            >
              Cookie Settings
              <span className="absolute -bottom-0.5 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
            </button>
          </div>
        </div>
      </div>
    </footer>
  )
}
