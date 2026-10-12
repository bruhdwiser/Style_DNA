import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart3, Eye, ShoppingCart, Search, ArrowLeft, RefreshCw, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { api, type AnalyticsStatsResponse } from '@/lib/api'
import { useAuth } from '@/contexts/auth-context'

export default function AdminAnalyticsPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState<AnalyticsStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.analytics.stats()
      setStats(data)
    } catch (err: any) {
      console.error('Analytics stats load error:', err)
      setError(
        err.message ||
          'Failed to load analytics. Ensure your account is recognized as an administrator on the backend.'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
  }, [])

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navigation />

      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-border gap-4">
          <div className="flex items-center gap-4">
            <Link to="/admin">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div>
              <h1 className="text-3xl font-extrabold text-foreground tracking-tight">
                Analytics & Telemetry
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5">
                Real-time event tracking powered by FastAPI and Postgres
              </p>
            </div>
          </div>

          <Button variant="outline" size="sm" onClick={fetchStats} className="gap-2 self-start sm:self-auto">
            <RefreshCw className="w-4 h-4" />
            Refresh Data
          </Button>
        </div>

        {error && (
          <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl flex items-start gap-3 text-sm text-destructive">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Access Error</p>
              <p className="text-xs mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {loading ? (
          <div className="py-20 text-center space-y-3">
            <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-sm text-muted-foreground">Aggregating telemetry metrics...</p>
          </div>
        ) : stats ? (
          <div className="space-y-8">
            {/* Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card className="border-border/80">
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs uppercase font-semibold">Total Events</CardDescription>
                  <CardTitle className="text-3xl font-extrabold text-foreground">
                    {stats.totalEvents.toLocaleString()}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">Across all user interactions</p>
                </CardContent>
              </Card>

              <Card className="border-border/80">
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs uppercase font-semibold">Unique Sessions</CardDescription>
                  <CardTitle className="text-3xl font-extrabold text-primary">
                    {stats.totalSessions.toLocaleString()}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">Tracked shopper sessions</p>
                </CardContent>
              </Card>

              <Card className="border-border/80">
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs uppercase font-semibold">Page Views</CardDescription>
                  <CardTitle className="text-3xl font-extrabold text-secondary">
                    {stats.totalPageViews.toLocaleString()}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">Total pages navigated</p>
                </CardContent>
              </Card>

              <Card className="border-border/80">
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs uppercase font-semibold">Product Views</CardDescription>
                  <CardTitle className="text-3xl font-extrabold text-accent">
                    {stats.totalProductViews.toLocaleString()}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">Garment details explored</p>
                </CardContent>
              </Card>
            </div>

            {/* Event Breakdowns */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Event Type Breakdown */}
              <Card className="border-border/80">
                <CardHeader>
                  <CardTitle className="text-lg">Events by Category</CardTitle>
                  <CardDescription>Distribution of captured shopper behavior</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {stats.eventsByType.map((item) => (
                      <div
                        key={item.event_type}
                        className="flex items-center justify-between p-3 rounded-xl bg-muted/30 border border-border/50 text-sm"
                      >
                        <span className="font-semibold text-foreground uppercase tracking-wider text-xs">
                          {item.event_type}
                        </span>
                        <Badge variant="secondary" className="font-bold">
                          {item.count}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Top Pages */}
              <Card className="border-border/80">
                <CardHeader>
                  <CardTitle className="text-lg">Most Active Routes</CardTitle>
                  <CardDescription>Pages receiving the highest traffic</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {stats.topPages.map((item, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 rounded-xl bg-muted/30 border border-border/50 text-sm"
                      >
                        <span className="font-medium text-foreground truncate max-w-[280px]">
                          {item.page}
                        </span>
                        <span className="text-xs text-muted-foreground font-semibold">
                          {item.count} views
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Recent Events Table */}
            {stats.recentEvents && stats.recentEvents.length > 0 && (
              <Card className="border-border/80">
                <CardHeader>
                  <CardTitle className="text-lg">Recent Event Stream</CardTitle>
                  <CardDescription>Live incoming telemetry stream</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-border text-muted-foreground uppercase font-semibold">
                        <tr>
                          <th className="pb-3 pr-4">Type</th>
                          <th className="pb-3 pr-4">Payload</th>
                          <th className="pb-3">Timestamp</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/60">
                        {stats.recentEvents.slice(0, 10).map((ev) => (
                          <tr key={ev.id} className="hover:bg-muted/30">
                            <td className="py-2.5 pr-4 font-semibold text-foreground">
                              {ev.event_type}
                            </td>
                            <td className="py-2.5 pr-4 font-mono text-[11px] text-muted-foreground truncate max-w-xs">
                              {JSON.stringify(ev.event_data)}
                            </td>
                            <td className="py-2.5 text-muted-foreground whitespace-nowrap">
                              {new Date(ev.created_at).toLocaleTimeString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        ) : null}
      </main>

      <Footer />
    </div>
  )
}
