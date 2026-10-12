import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Sparkles, Mail, Lock, AlertCircle, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { getSupabaseClient } from '@/lib/supabase'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSignUp, setIsSignUp] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [infoMessage, setInfoMessage] = useState<string | null>(null)

  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as any)?.from || '/'

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setInfoMessage(null)

    try {
      const supabase = getSupabaseClient()
      if (isSignUp) {
        const { error: signUpError } = await supabase.auth.signUp({
          email,
          password,
        })
        if (signUpError) throw signUpError
        setInfoMessage('Account created! Check your email or sign in directly.')
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        })
        if (signInError) throw signInError
        navigate(from, { replace: true })
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify your credentials.')
    } finally {
      setLoading(false)
    }
  }

  const handleOAuthLogin = async (provider: 'google' | 'github') => {
    try {
      const supabase = getSupabaseClient()
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        },
      })
      if (oauthError) throw oauthError
    } catch (err: any) {
      setError(err.message || `Failed to initialize ${provider} sign-in.`)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navigation />

      <main className="flex-1 flex items-center justify-center p-4 py-12">
        <Card className="w-full max-w-md border-border/80 shadow-2xl backdrop-blur-xl bg-card/90">
          <CardHeader className="text-center space-y-2 pb-6">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-primary to-accent flex items-center justify-center text-primary-foreground mx-auto shadow-md">
              <Sparkles className="w-6 h-6" />
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight">
              {isSignUp ? 'Create FlashFit Account' : 'Welcome to FlashFit'}
            </CardTitle>
            <CardDescription className="text-sm">
              {isSignUp
                ? 'Join to access tailored fashion AI styling and save your cart'
                : 'Sign in to sync your bag, recommendations, and saved styles'}
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            {error && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-xl flex items-start gap-2.5 text-xs text-destructive">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {infoMessage && (
              <div className="p-3 bg-primary/10 border border-primary/20 rounded-xl text-xs text-primary font-medium">
                {infoMessage}
              </div>
            )}

            {/* Email / Password Form */}
            <form onSubmit={handleEmailAuth} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    className="pl-9"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="pl-9"
                  />
                </div>
              </div>

              <Button type="submit" disabled={loading} className="w-full font-semibold shadow-md">
                {loading ? 'Processing...' : isSignUp ? 'Sign Up' : 'Sign In'}
              </Button>
            </form>

            <div className="relative flex items-center justify-center">
              <span className="w-full border-t border-border" />
              <span className="bg-card px-2 text-xs uppercase tracking-wider text-muted-foreground absolute">
                Or Continue With
              </span>
            </div>

            {/* Social Logins */}
            <div className="grid grid-cols-2 gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOAuthLogin('google')}
                className="text-xs font-medium"
              >
                Google
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOAuthLogin('github')}
                className="text-xs font-medium"
              >
                GitHub
              </Button>
            </div>

            {/* Toggle Sign Up / Sign In */}
            <div className="text-center pt-2">
              <button
                type="button"
                onClick={() => {
                  setIsSignUp(!isSignUp)
                  setError(null)
                  setInfoMessage(null)
                }}
                className="text-xs text-primary font-medium hover:underline cursor-pointer"
              >
                {isSignUp
                  ? 'Already have an account? Sign in instead'
                  : "Don't have an account yet? Create one now"}
              </button>
            </div>
          </CardContent>
        </Card>
      </main>

      <Footer />
    </div>
  )
}
