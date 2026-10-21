import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { api, type AnalyticsStatsResponse } from '@/lib/api'

export default function AdminAnalyticsPage() {
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

      <main className="analytics-main">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-border gap-4">
          <div className="analytics-page-heading">
            <Link to="/admin">
              <span className="analytics-back-link">← STOCK ROOM</span>
            </Link>
            <div>
              <p className="eyebrow">STYLESENSE / STORE NOTES</p>
              <h1 className="font-display text-4xl sm:text-5xl font-normal text-foreground">
                Store notes.
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5">
                Activity across the rack and fitting room.
              </p>
            </div>
          </div>

          <Button variant="outline" size="sm" onClick={fetchStats} className="self-start sm:self-auto font-mono text-xs">
            REFRESH DATA ↻
          </Button>
        </div>

        {error && (
          <div className="admin-notice error">
            <div>
              <p className="font-semibold">Access Error</p>
              <p className="text-xs mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {loading ? (
          <div className="py-20 text-center space-y-3">
            <div className="w-8 h-8 border-2 border-border border-t-primary animate-spin mx-auto" />
            <p className="font-mono text-xs text-muted-foreground tracking-wider">READING STORE NOTES…</p>
          </div>
        ) : stats ? (
          <div className="space-y-8">
            {/* Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card className="border-border">
                <CardHeader className="pb-2">
                  <CardDescription className="font-mono text-[10px] tracking-wider uppercase text-muted-foreground">Total Events</CardDescription>
                  <CardTitle className="font-display text-4xl font-normal text-foreground">
                    {stats.totalEvents.toLocaleString()}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">Across all user interactions</p>
                </CardContent>
              </Card>

              <Card className="border-border">
                <CardHeader className="pb-2">
                  <CardDescription className="font-mono text-[10px] tracking-wider uppercase text-muted-foreground">Unique Sessions</CardDescription>
                  <CardTitle className="font-display text-4xl font-normal text-forest">
                    {stats.totalSessions.toLocaleString()}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">Tracked shopper sessions</p>
                </CardContent>
              </Card>

              <Card className="border-border">
                <CardHeader className="pb-2">
                  <CardDescription className="font-mono text-[10px] tracking-wider uppercase text-muted-foreground">Page Views</CardDescription>
                  <CardTitle className="font-display text-4xl font-normal text-dusty-teal">
                    {stats.totalPageViews.toLocaleString()}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">Total pages navigated</p>
                </CardContent>
              </Card>

              <Card className="border-border">
                <CardHeader className="pb-2">
                  <CardDescription className="font-mono text-[10px] tracking-wider uppercase text-muted-foreground">Product Views</CardDescription>
                  <CardTitle className="font-display text-4xl font-normal text-clay">
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
                        className="analytics-row"
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
                        className="analytics-row"
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
