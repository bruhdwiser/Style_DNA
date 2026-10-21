import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
    <main className="auth-callback-page">
      <section className="auth-callback-note">
        <p className="eyebrow">STYLESENSE / ACCOUNT</p>

        {error ? (
          <div>
            <h1>That didn’t work.</h1>
            <p>{error}</p>
            <button onClick={() => navigate('/login')}>BACK TO SIGN IN →</button>
          </div>
        ) : (
          <div>
            <h1>Back in a moment.</h1>
            <p>Checking your sign-in and opening your rack…</p>
          </div>
        )}
      </section>
    </main>
  )
}
