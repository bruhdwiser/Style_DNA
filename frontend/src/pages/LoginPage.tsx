import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/button'
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

  const handleEmailAuth = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setInfoMessage(null)
    try {
      const supabase = getSupabaseClient()
      if (isSignUp) {
        const { error: signUpError } = await supabase.auth.signUp({ email, password })
        if (signUpError) throw signUpError
        setInfoMessage('Your account is ready. Check your email to confirm, then sign in.')
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({ email, password })
        if (signInError) throw signInError
        navigate(from, { replace: true })
      }
    } catch (err: any) {
      setError(err.message || 'Sign in failed. Check your details and try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleOAuthLogin = async (provider: 'google' | 'github') => {
    setError(null)
    try {
      const supabase = getSupabaseClient()
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider,
        options: { redirectTo: `${window.location.origin}/auth/callback` },
      })
      if (oauthError) throw oauthError
    } catch (err: any) {
      setError(err.message || `Could not start ${provider} sign in.`)
    }
  }

  return (
    <div className="page-shell login-page">
      <Navigation />
      <main className="login-main">
        <div className="login-image">
          <img src="/elegant-woman-in-minimalist-fashion-outfit.png" alt="A considered everyday look" />
          <div className="login-image-label">STYLESENSE / PERSONAL CLOSET</div>
        </div>
        <section className="login-form-panel">
          <p className="eyebrow">YOUR RACK IS WAITING</p>
          <h1>{isSignUp ? 'Make room.' : 'Back again.'}</h1>
          <p className="login-deck">{isSignUp ? 'Save your pieces and build a closet that works harder.' : 'Sign in to get back to your closet and saved looks.'}</p>

          {error && <p className="login-message error" role="alert">{error}</p>}
          {infoMessage && <p className="login-message success" role="status">{infoMessage}</p>}

          <form onSubmit={handleEmailAuth} className="login-form">
            <label htmlFor="login-email">EMAIL ADDRESS</label>
            <input id="login-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" required autoComplete="email" />
            <label htmlFor="login-password">PASSWORD</label>
            <input id="login-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Your password" required autoComplete={isSignUp ? 'new-password' : 'current-password'} />
            <Button type="submit" size="lg" disabled={loading} className="login-submit">
              {loading ? 'ONE MOMENT…' : isSignUp ? 'CREATE ACCOUNT →' : 'SIGN IN →'}
            </Button>
          </form>

          <div className="login-divider"><span>OR CONTINUE WITH</span></div>
          <div className="login-providers">
            <Button type="button" variant="outline" onClick={() => handleOAuthLogin('google')}>GOOGLE</Button>
            <Button type="button" variant="outline" onClick={() => handleOAuthLogin('github')}>GITHUB</Button>
          </div>
          <button type="button" className="login-toggle" onClick={() => { setIsSignUp((value) => !value); setError(null); setInfoMessage(null) }}>
            {isSignUp ? 'ALREADY HAVE A RACK? SIGN IN' : 'NEW HERE? CREATE AN ACCOUNT'}
          </button>
        </section>
      </main>
      <Footer />
    </div>
  )
}
