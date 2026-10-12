'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'

interface AnalyticsStats {
  totalEvents: number
  totalSessions: number
  totalPageViews: number
  totalProductViews: number
  totalSearches: number
  topPages: { page: string; count: number }[]
  topProducts: { product_id: string; count: number }[]
  recentEvents: {
    id: string
    event_type: string
    event_data: any
    created_at: string
  }[]
  eventsByType: { event_type: string; count: number }[]
}

import { api } from '@/lib/api/client'
import { getSupabaseClient } from '@/lib/supabase/client'

export default function AdminAnalyticsPage() {
  const [stats, setStats] = useState<AnalyticsStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [userEmail, setUserEmail] = useState<string | null>(null)

  useEffect(() => {
    checkAdminAndFetch()
  }, [])

  const checkAdminAndFetch = async () => {
    try {
      setLoading(true)
      setError(null)
      const supabase = getSupabaseClient()
      const { data: { session } } = await supabase.auth.getSession()

      if (!session) {
        setError('Authentication required. Please sign in with an administrator account.')
        setLoading(false)
        return
      }

      setUserEmail(session.user.email ?? 'Admin')
      const data = await api.analytics.stats()
      setStats(data)
    } catch (err: any) {
      console.error('Analytics fetch error from FastAPI:', err)
      setError(err.message || 'Failed to load analytics data. Ensure your account has admin privileges.')
    } finally {
      setLoading(false)
    }
  }

  const fetchAnalytics = () => {
    checkAdminAndFetch()
  }

  if (loading) {
    return (
      <>
        <Navigation />
        <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 flex items-center justify-center">
          <div className="text-center space-y-4">
            <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-lg text-muted-foreground">Loading analytics...</p>
          </div>
        </div>
        <Footer />
      </>
    )
  }

  if (error) {
    return (
      <>
        <Navigation />
        <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 flex items-center justify-center p-4">
          <Card className="max-w-md border-red-500/20">
            <CardHeader><CardTitle className="text-red-500">Error</CardTitle></CardHeader>
            <CardContent><p>{error}</p><Button onClick={fetchAnalytics} className="mt-4">Retry</Button></CardContent>
          </Card>
        </div>
        <Footer />
      </>
    )
  }

  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 py-12 px-4">
        <div className="max-w-7xl mx-auto space-y-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">Analytics Dashboard</h1>
              <p className="text-muted-foreground mt-2">Track user activity and engagement</p>
            </div>
            <Button onClick={handleLogout} variant="outline">Logout</Button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="border-primary/20 hover:border-primary/40 transition-all"><CardHeader className="pb-3"><CardDescription>Total Events</CardDescription><CardTitle className="text-3xl">{stats?.totalEvents || 0}</CardTitle></CardHeader></Card>
            <Card className="border-primary/20 hover:border-primary/40 transition-all"><CardHeader className="pb-3"><CardDescription>Total Sessions</CardDescription><CardTitle className="text-3xl">{stats?.totalSessions || 0}</CardTitle></CardHeader></Card>
            <Card className="border-primary/20 hover:border-primary/40 transition-all"><CardHeader className="pb-3"><CardDescription>Page Views</CardDescription><CardTitle className="text-3xl">{stats?.totalPageViews || 0}</CardTitle></CardHeader></Card>
            <Card className="border-primary/20 hover:border-primary/40 transition-all"><CardHeader className="pb-3"><CardDescription>Product Views</CardDescription><CardTitle className="text-3xl">{stats?.totalProductViews || 0}</CardTitle></CardHeader></Card>
          </div>
          <Card className="border-primary/20">
            <CardHeader><CardTitle>Events by Type</CardTitle><CardDescription>Breakdown of user activities</CardDescription></CardHeader>
            <CardContent>
              <div className="space-y-3">
                {stats?.eventsByType && stats.eventsByType.length > 0 ? stats.eventsByType.map((item) => (
                  <div key={item.event_type} className="flex items-center justify-between">
                    <div className="flex items-center gap-3"><Badge variant="outline">{item.event_type}</Badge></div>
                    <span className="font-semibold">{item.count}</span>
                  </div>
                )) : <p className="text-muted-foreground text-center py-4">No events yet</p>}
              </div>
            </CardContent>
          </Card>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="border-primary/20">
              <CardHeader><CardTitle>Top Pages</CardTitle><CardDescription>Most visited pages</CardDescription></CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {stats?.topPages && stats.topPages.length > 0 ? stats.topPages.map((item, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <span className="text-sm truncate max-w-xs">{item.page}</span>
                      <Badge>{item.count} views</Badge>
                    </div>
                  )) : <p className="text-muted-foreground text-center py-4">No page views yet</p>}
                </div>
              </CardContent>
            </Card>
            <Card className="border-primary/20">
              <CardHeader><CardTitle>Top Products</CardTitle><CardDescription>Most viewed products</CardDescription></CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {stats?.topProducts && stats.topProducts.length > 0 ? stats.topProducts.map((item, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <span className="text-sm">Product #{item.product_id}</span>
                      <Badge>{item.count} views</Badge>
                    </div>
                  )) : <p className="text-muted-foreground text-center py-4">No product views yet</p>}
                </div>
              </CardContent>
            </Card>
          </div>
          <Card className="border-primary/20">
            <CardHeader><CardTitle>Recent Events</CardTitle><CardDescription>Latest user activities</CardDescription></CardHeader>
            <CardContent>
              <div className="space-y-4">
                {stats?.recentEvents && stats.recentEvents.length > 0 ? stats.recentEvents.map((event) => (
                  <div key={event.id} className="flex items-start justify-between border-b border-border/50 pb-4 last:border-0">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{event.event_type}</Badge>
                        <span className="text-sm text-muted-foreground">{new Date(event.created_at).toLocaleString()}</span>
                      </div>
                      <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-w-lg">{JSON.stringify(event.event_data, null, 2)}</pre>
                    </div>
                  </div>
                )) : <p className="text-muted-foreground text-center py-4">No recent events</p>}
              </div>
            </CardContent>
          </Card>
          <div className="flex justify-center"><Button onClick={fetchAnalytics} variant="outline">Refresh Data</Button></div>
        </div>
      </div>
      <Footer />
    </>
  )
}
