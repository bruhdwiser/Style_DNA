import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Sparkles, ShoppingBag, ShieldCheck, Truck, RefreshCw, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { ProductCard } from '@/components/product-card'
import { AiChatbot } from '@/components/ai-chatbot'
import { api, type ProductItem } from '@/lib/api'
import { usePageTracking } from '@/lib/tracking'

export default function HomePage() {
  usePageTracking()
  const [featuredProducts, setFeaturedProducts] = useState<ProductItem[]>([])
  const [loading, setLoading] = useState(true)
  const [chatbotOpen, setChatbotOpen] = useState(false)

  useEffect(() => {
    api.products
      .list({ limit: 4 })
      .then((res) => {
        setFeaturedProducts(res.items || [])
      })
      .catch((err) => {
        console.error('Failed to load featured products:', err)
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navigation />

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden py-20 lg:py-32 bg-gradient-to-b from-primary/10 via-background to-background">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div className="space-y-6 text-center lg:text-left">
                <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-primary/20 bg-primary/10 text-primary text-xs font-semibold uppercase tracking-wider">
                  <Sparkles className="w-3.5 h-3.5" />
                  Next-Gen Fashion Intelligence
                </div>

                <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground leading-[1.15]">
                  Style Engineered for Your{' '}
                  <span className="bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent">
                    Authentic Self
                  </span>
                </h1>

                <p className="text-lg text-muted-foreground max-w-xl mx-auto lg:mx-0 leading-relaxed">
                  Discover curated luxury, casual, and formal fashion with instant AI styling advice.
                  Tailored recommendations powered by FastAPI & intelligent retrieval.
                </p>

                <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start pt-2">
                  <Link to="/shop">
                    <Button size="lg" className="w-full sm:w-auto gap-2 text-base font-semibold">
                      Explore Collection
                      <ArrowRight className="w-4 h-4" />
                    </Button>
                  </Link>

                  <Button
                    variant="outline"
                    size="lg"
                    onClick={() => setChatbotOpen(true)}
                    className="w-full sm:w-auto gap-2 text-base font-medium"
                  >
                    <Sparkles className="w-4 h-4 text-accent" />
                    Ask AI Stylist
                  </Button>
                </div>

                {/* Micro metrics */}
                <div className="pt-6 grid grid-cols-3 gap-6 border-t border-border/80">
                  <div>
                    <p className="text-2xl font-bold text-foreground">1,200+</p>
                    <p className="text-xs text-muted-foreground">Handcrafted Pieces</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-foreground">99.8%</p>
                    <p className="text-xs text-muted-foreground">Style Satisfaction</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-foreground">FastAPI</p>
                    <p className="text-xs text-muted-foreground">Real-time Backend</p>
                  </div>
                </div>
              </div>

              {/* Hero visual */}
              <div className="relative mx-auto w-full max-w-md lg:max-w-none">
                <div className="relative rounded-3xl overflow-hidden shadow-2xl border border-border/60 bg-card/40 backdrop-blur-sm aspect-4/5">
                  <img
                    src="https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=800&auto=format&fit=crop&q=80"
                    alt="FlashFit Fashion"
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent flex flex-col justify-end p-8 text-white">
                    <span className="text-xs uppercase tracking-widest font-semibold text-accent">
                      Featured Trend
                    </span>
                    <h3 className="text-2xl font-bold">Timeless Modern Essentials</h3>
                    <p className="text-sm text-white/80 mt-1">
                      Effortless silhouettes blending day-to-night versatility.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Categories Section */}
        <section className="py-16 bg-muted/30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row items-center justify-between mb-10 gap-4">
              <div>
                <h2 className="text-3xl font-bold text-foreground">Explore by Style</h2>
                <p className="text-muted-foreground text-sm">Targeted collections for every mood</p>
              </div>
              <Link to="/shop">
                <Button variant="ghost" className="gap-1.5 text-primary">
                  View All <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                {
                  title: 'Casual Living',
                  cat: 'casual',
                  desc: 'Everyday elevated comfort for coffee runs and city walks',
                  img: 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600&auto=format&fit=crop&q=80',
                },
                {
                  title: 'Formal Precision',
                  cat: 'formal',
                  desc: 'Sharp tailoring designed to command respect in any boardroom',
                  img: 'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?w=600&auto=format&fit=crop&q=80',
                },
                {
                  title: 'Luxury Statement',
                  cat: 'luxury',
                  desc: 'Exquisite textures and silken accents for memorable evenings',
                  img: 'https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=600&auto=format&fit=crop&q=80',
                },
              ].map((c) => (
                <Link
                  key={c.cat}
                  to={`/shop?category=${c.cat}`}
                  className="group relative rounded-2xl overflow-hidden aspect-4/3 shadow-md border border-border"
                >
                  <img
                    src={c.img}
                    alt={c.title}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-black/40 group-hover:bg-black/50 transition-colors flex flex-col justify-end p-6 text-white">
                    <h3 className="text-xl font-bold">{c.title}</h3>
                    <p className="text-xs text-white/80 line-clamp-2 mt-1">{c.desc}</p>
                    <span className="text-xs font-semibold text-accent mt-3 flex items-center gap-1">
                      Shop Now <ArrowRight className="w-3.5 h-3.5" />
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* Featured Products */}
        <section className="py-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row items-center justify-between mb-10 gap-4">
              <div>
                <h2 className="text-3xl font-bold text-foreground">Featured Picks</h2>
                <p className="text-muted-foreground text-sm">Curated favorites chosen by our AI stylists</p>
              </div>
              <Link to="/shop">
                <Button variant="outline" className="gap-2">
                  <ShoppingBag className="w-4 h-4" />
                  Full Catalog
                </Button>
              </Link>
            </div>

            {loading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="rounded-2xl border border-border bg-card p-4 animate-pulse space-y-4">
                    <div className="aspect-3/4 bg-muted rounded-xl" />
                    <div className="h-4 bg-muted rounded w-3/4" />
                    <div className="h-4 bg-muted rounded w-1/2" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {featuredProducts.map((p) => (
                  <ProductCard key={p.id} {...p} />
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Trust Value Props */}
        <section className="py-16 border-t border-border bg-muted/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl bg-primary/10 text-primary">
                  <Truck className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="font-semibold text-foreground">Free Shipping</h4>
                  <p className="text-xs text-muted-foreground mt-1">Complimentary delivery over ₹2,000</p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl bg-primary/10 text-primary">
                  <RefreshCw className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="font-semibold text-foreground">Easy 30-Day Returns</h4>
                  <p className="text-xs text-muted-foreground mt-1">Hassle-free wardrobe exchanges</p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl bg-primary/10 text-primary">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="font-semibold text-foreground">Verified Authenticity</h4>
                  <p className="text-xs text-muted-foreground mt-1">100% premium quality guaranteed</p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl bg-primary/10 text-primary">
                  <Zap className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="font-semibold text-foreground">AI Personalized</h4>
                  <p className="text-xs text-muted-foreground mt-1">Styles matching your exact profile</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />
      <AiChatbot isOpen={chatbotOpen} onClose={() => setChatbotOpen(false)} />
    </div>
  )
}
