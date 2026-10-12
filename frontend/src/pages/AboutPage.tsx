import React from 'react'
import { Sparkles, Cpu, Layers, ShieldCheck, Heart, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { Link } from 'react-router-dom'
import { usePageTracking } from '@/lib/tracking'

export default function AboutPage() {
  usePageTracking()

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navigation />

      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 w-full space-y-16">
        {/* Intro */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-primary/10 text-primary text-xs font-semibold uppercase">
            <Sparkles className="w-3.5 h-3.5" />
            Our Vision
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight">
            The Intersection of Fashion & Intelligence
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            FlashFit is reimagining online fashion commerce. We combine high-end textile aesthetics
            with precision AI recommendations, delivering personal styling that adapts to you.
          </p>
        </div>

        {/* Pillars */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="p-8 rounded-3xl bg-card border border-border shadow-md space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
              <Cpu className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-foreground">AI Styling Engine</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Powered by server-side OpenRouter models and strict catalog retrieval, our stylist
              suggests verified garments without hallucinated links or phantom prices.
            </p>
          </div>

          <div className="p-8 rounded-3xl bg-card border border-border shadow-md space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-secondary/10 text-secondary flex items-center justify-center">
              <Layers className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-foreground">Modern Tech Stack</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Built on a decoupled React + Vite frontend and a blazing-fast FastAPI Python backend,
              backed by Supabase Postgres, Auth, and Storage.
            </p>
          </div>

          <div className="p-8 rounded-3xl bg-card border border-border shadow-md space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-accent/10 text-accent flex items-center justify-center">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-foreground">Security First</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Row-Level Security (RLS) safeguards every cart item and profile. Secrets stay strictly
              on the server—never leaked into browser bundles.
            </p>
          </div>
        </div>

        {/* Story */}
        <div className="p-8 sm:p-12 rounded-3xl bg-gradient-to-br from-card via-card to-primary/5 border border-border/80 shadow-lg space-y-6">
          <h2 className="text-2xl sm:text-3xl font-bold text-foreground">
            Built for Discerning Shoppers
          </h2>
          <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
            Standard ecommerce search forces shoppers to wade through hundreds of irrelevant
            thumbnails. FlashFit changes the paradigm: talk directly to an AI conversational
            partner that understands silhouettes, color theory, and dress codes, and receive exact
            matches from our curated catalog in seconds.
          </p>

          <div className="pt-2">
            <Link to="/shop">
              <Button size="lg" className="gap-2">
                Explore the Collection <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}
