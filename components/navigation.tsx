"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { Sparkles, ShoppingBag, User, Menu, X, Brain, Moon, Sun } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useCart } from "@/contexts/cart-context"
import { useTheme } from "@/contexts/theme-context"
import { supabaseBrowser } from "@/lib/supabase/client"
import type { User as SupabaseUser } from "@supabase/supabase-js"

const navigationItems = [
  { name: "Home", href: "/" },
  { name: "Shop", href: "/shop" },
  { name: "Flashfits AI", href: "/ai", icon: Brain },
  { name: "About", href: "/about" },
]

export function Navigation() {
  const [isOpen, setIsOpen] = useState(false)
  const pathname = usePathname()
  const { state } = useCart()
  const { theme, toggleTheme, mounted } = useTheme()
  const [user, setUser] = useState<SupabaseUser | null>(null)

  useEffect(() => {
    const supabase = supabaseBrowser()
    let mounted = true
    supabase.auth.getUser().then(({ data }) => {
      if (mounted) setUser(data.user)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })
    return () => {
      mounted = false
      sub.subscription.unsubscribe()
    }
  }, [])

  const signOut = async () => {
    const supabase = supabaseBrowser()
    await supabase.auth.signOut()
    setUser(null)
  }

  const isActive = (href: string) => {
    if (href === "/") {
      return pathname === "/"
    }
    return pathname.startsWith(href)
  }

  return (
    <nav className="sticky top-0 z-50 glass backdrop-blur-xl border-b border-border/50 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <div className="relative">
              <Sparkles className="h-8 w-8 text-primary group-hover:text-secondary transition-colors duration-300" />
              <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl group-hover:bg-secondary/30 transition-all duration-300" />
            </div>
            <span className="font-sans font-bold text-2xl bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent group-hover:from-secondary group-hover:via-accent group-hover:to-primary transition-all duration-500">
              Flashfits
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            {navigationItems.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-2 transition-all duration-300 font-medium relative group ${
                  isActive(item.href) 
                    ? "text-primary" 
                    : "text-muted-foreground hover:text-primary"
                }`}
              >
                {item.icon && <item.icon className="h-4 w-4" />}
                {item.name}
                <span className={`absolute -bottom-1 left-0 h-0.5 bg-gradient-to-r from-primary to-secondary transition-all duration-300 ${
                  isActive(item.href) ? 'w-full' : 'w-0 group-hover:w-full'
                }`} />
              </Link>
            ))}
          </div>

          {/* Right Side Actions */}
          <div className="flex items-center gap-4">
            {/* Desktop Actions */}
            <div className="hidden md:flex items-center gap-4">
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={toggleTheme}
                className="relative group hover:bg-primary/10 transition-all duration-300"
                disabled={!mounted}
              >
                {!mounted ? (
                  <div className="h-5 w-5 rounded-full bg-muted animate-pulse" />
                ) : theme === "light" ? (
                  <Moon className="h-5 w-5 text-foreground group-hover:text-primary transition-colors duration-300" />
                ) : (
                  <Sun className="h-5 w-5 text-foreground group-hover:text-primary transition-colors duration-300" />
                )}
                <div className="absolute inset-0 bg-gradient-to-br from-primary/0 to-secondary/0 group-hover:from-primary/10 group-hover:to-secondary/10 rounded-lg transition-all duration-300" />
              </Button>
              {user ? (
                <div className="flex items-center gap-2">
                  <span className="font-serif text-sm text-muted-foreground hidden lg:inline">
                    {user.email}
                  </span>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={signOut}
                    className="hover:bg-primary/10 hover:text-primary transition-all duration-300"
                  >
                    Sign out
                  </Button>
                </div>
              ) : (
                <Link href="/login">
                  <Button 
                    variant="ghost" 
                    size="icon"
                    className="hover:bg-primary/10 transition-all duration-300 group"
                  >
                    <User className="h-5 w-5 text-foreground group-hover:text-primary transition-colors duration-300" />
                  </Button>
                </Link>
              )}
              <Link href="/cart">
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="relative hover:bg-primary/10 transition-all duration-300 group"
                >
                  <ShoppingBag className="h-5 w-5 text-foreground group-hover:text-primary transition-colors duration-300" />
                  {state.itemCount > 0 && (
                    <Badge className="absolute -top-2 -right-2 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs bg-gradient-to-r from-primary to-secondary border-0 shadow-lg animate-glow-pulse">
                      {state.itemCount}
                    </Badge>
                  )}
                </Button>
              </Link>
            </div>

            {/* Mobile Menu */}
            <Sheet open={isOpen} onOpenChange={setIsOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="md:hidden">
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-80">
                <div className="flex items-center justify-between mb-8">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-6 w-6 text-primary" />
                    <span className="font-sans font-bold text-xl text-foreground">Flashfits</span>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => setIsOpen(false)}>
                    <X className="h-5 w-5" />
                  </Button>
                </div>

                <div className="space-y-6">
                  {/* Mobile Navigation Links */}
                  <div className="space-y-4">
                    {navigationItems.map((item) => (
                      <Link
                        key={item.name}
                        href={item.href}
                        onClick={() => setIsOpen(false)}
                        className={`flex items-center gap-3 text-lg transition-colors ${
                          isActive(item.href) ? "text-primary font-medium" : "text-foreground hover:text-primary"
                        }`}
                      >
                        {item.icon && <item.icon className="h-5 w-5" />}
                        {item.name}
                      </Link>
                    ))}
                  </div>

                  <div className="border-t border-border pt-6 space-y-4">
                    <Button 
                      variant="outline" 
                      className="w-full justify-start bg-transparent" 
                      onClick={toggleTheme}
                      disabled={!mounted}
                    >
                      {!mounted ? (
                        <>
                          <div className="h-4 w-4 mr-2 rounded-full bg-muted animate-pulse" />
                          Theme
                        </>
                      ) : theme === "light" ? (
                        <>
                          <Moon className="h-4 w-4 mr-2" />
                          Dark Mode
                        </>
                      ) : (
                        <>
                          <Sun className="h-4 w-4 mr-2" />
                          Light Mode
                        </>
                      )}
                    </Button>

                    {/* Mobile Cart */}
                    <Link href="/cart" onClick={() => setIsOpen(false)}>
                      <Button variant="outline" className="w-full justify-start bg-transparent">
                        <ShoppingBag className="h-4 w-4 mr-2" />
                        Cart
                        {state.itemCount > 0 && <Badge className="ml-auto">{state.itemCount}</Badge>}
                      </Button>
                    </Link>

                    {/* Mobile Auth */}
                    {user ? (
                      <Button variant="outline" className="w-full justify-start bg-transparent" onClick={signOut}>
                        <User className="h-4 w-4 mr-2" />
                        Sign out
                      </Button>
                    ) : (
                      <Link href="/login" onClick={() => setIsOpen(false)}>
                        <Button variant="outline" className="w-full justify-start bg-transparent">
                          <User className="h-4 w-4 mr-2" />
                          Sign in
                        </Button>
                      </Link>
                    )}
                  </div>
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </nav>
  )
}
