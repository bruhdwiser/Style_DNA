"use client"

import { useState } from 'react'
import { supabaseBrowser } from '@/lib/supabase/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { Mail, ArrowRight, Github, Chrome } from 'lucide-react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const signInWithEmail = async () => {
    setError(null)
    setLoading(true)
    const supabase = supabaseBrowser()
    
    // Get the correct redirect URL based on environment
    const redirectTo = typeof window !== 'undefined' 
      ? `${window.location.origin}/auth/callback`
      : undefined
    
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { 
        emailRedirectTo: redirectTo,
      },
    })
    if (error) setError(error.message)
    else setSent(true)
    setLoading(false)
  }

  const signInOAuth = async (provider: 'google' | 'github') => {
    setError(null)
    setLoading(true)
    const supabase = supabaseBrowser()
    
    // Get the correct redirect URL based on environment
    const redirectTo = typeof window !== 'undefined' 
      ? `${window.location.origin}/auth/callback`
      : undefined
    
    const { error } = await supabase.auth.signInWithOAuth({ 
      provider,
      options: {
        redirectTo,
      },
    })
    if (error) {
      setError(error.message)
      setLoading(false)
    }
    // Don't set loading to false on success - user will be redirected
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <main className="max-w-6xl mx-auto px-4 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
          {/* Form */}
          <div className="max-w-md w-full mx-auto lg:mx-0">
            <h1 className="font-sans font-bold text-3xl md:text-4xl mb-2">Welcome back</h1>
            <p className="font-serif text-muted-foreground mb-6">Sign in to continue your Flashfits experience.</p>

            <Card className="shadow-sm">
              <CardContent className="p-6 space-y-5">
                {sent ? (
                  <div className="space-y-2">
                    <div className="text-foreground font-sans text-xl">Check your email</div>
                    <p className="font-serif text-sm text-muted-foreground">
                      We sent a magic link to <span className="font-medium">{email}</span>. Open it on this device to finish signing in.
                    </p>
                    <Button className="mt-2" variant="outline" onClick={() => setSent(false)}>
                      Use a different email
                    </Button>
                  </div>
                ) : (
                  <>
                    <div className="space-y-2">
                      <label className="font-serif text-sm text-muted-foreground" htmlFor="email">Email address</label>
                      <Input id="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
                    </div>
                    <Button onClick={signInWithEmail} disabled={!email || loading} className="w-full">
                      {loading ? (
                        <span className="inline-flex items-center gap-2">
                          <Mail className="h-4 w-4" /> Sending...
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-2">
                          <Mail className="h-4 w-4" /> Send magic link <ArrowRight className="h-4 w-4" />
                        </span>
                      )}
                    </Button>
                    {error && <p className="text-destructive text-sm">{error}</p>}

                    <div className="relative text-center">
                      <span className="bg-background px-3 font-serif text-xs text-muted-foreground relative z-10">or continue with</span>
                      <div className="border-t border-border absolute inset-x-0 top-1/2 -translate-y-1/2" />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <Button 
                        variant="outline" 
                        onClick={() => signInOAuth('google')} 
                        disabled={loading}
                        className="w-full bg-transparent"
                      >
                        <Chrome className="h-4 w-4 mr-2" /> Google
                      </Button>
                      <Button 
                        variant="outline" 
                        onClick={() => signInOAuth('github')} 
                        disabled={loading}
                        className="w-full bg-transparent"
                      >
                        <Github className="h-4 w-4 mr-2" /> GitHub
                      </Button>
                    </div>

                    <p className="font-serif text-xs text-muted-foreground text-center">
                      By continuing, you agree to our Terms and Privacy Policy.
                    </p>
                  </>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Visual side */}
          <div className="hidden lg:block">
            <div className="relative rounded-2xl overflow-hidden border border-border">
              <img
                src="/elegant-woman-in-minimalist-fashion-outfit.png"
                alt="Minimalist fashion"
                className="w-full h-[520px] object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-background/80 via-background/20 to-transparent" />
              <div className="absolute bottom-6 left-6 right-6">
                <h2 className="font-sans text-2xl font-bold">Effortless style starts here</h2>
                <p className="font-serif text-muted-foreground max-w-md">
                  Sign in to sync your cart, wishlist, and personalized AI recommendations.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}
