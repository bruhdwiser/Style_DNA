import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, CheckCircle2, AlertCircle } from 'lucide-react'
import { getSupabaseClient } from '@/lib/supabase'

export default function AuthCallbackPage() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const handleAuth = async () => {
      try {
        const supabase = getSupabaseClient()
        // Supabase JS handles the hash/code exchange automatically on getSession()
        const { data, error } = await supabase.auth.getSession()
        if (error) throw error

        if (data.session) {
          navigate('/', { replace: true })
        } else {
          // If hash is present, wait briefly for GoTrue listener
          setTimeout(async () => {
            const { data: retryData } = await supabase.auth.getSession()
            if (retryData.session) {
              navigate('/', { replace: true })
            } else {
              navigate('/login', { replace: true })
            }
          }, 800)
        }
      } catch (err: any) {
        console.error('OAuth callback processing error:', err)
        setError(err.message || 'OAuth verification failed.')
      }
    }

    handleAuth()
  }, [navigate])

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="text-center space-y-4 max-w-sm">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-primary to-accent flex items-center justify-center text-primary-foreground mx-auto animate-pulse shadow-lg">
          <Sparkles className="w-7 h-7" />
        </div>

        {error ? (
          <div className="space-y-3">
            <div className="flex items-center justify-center gap-2 text-destructive font-semibold">
              <AlertCircle className="w-5 h-5" />
              <span>Authentication Error</span>
            </div>
            <p className="text-xs text-muted-foreground">{error}</p>
            <button
              onClick={() => navigate('/login')}
              className="text-xs text-primary font-medium underline"
            >
              Return to Login
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <h2 className="text-lg font-bold text-foreground">Completing Sign-In...</h2>
            <p className="text-xs text-muted-foreground">
              Verifying credentials and syncing your style profile.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
