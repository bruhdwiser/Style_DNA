import { NextRequest, NextResponse } from 'next/server'
import { supabaseServer } from '@/lib/supabase/server'

export async function GET(request: NextRequest) {
  try {
    const supabase = await supabaseServer()
    
    const { data: events, error: eventsError } = await supabase
      .from('analytics_events')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(100)

    if (eventsError) {
      console.error('Analytics error:', eventsError)
      return NextResponse.json({
        totalEvents: 0,
        totalSessions: 0,
        totalPageViews: 0,
        totalProductViews: 0,
        totalSearches: 0,
        topPages: [],
        topProducts: [],
        recentEvents: [],
        eventsByType: [],
      })
    }

    const now = new Date()
    const last7Days = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)

    const { count: totalEvents } = await supabase
      .from('analytics_events')
      .select('*', { count: 'exact', head: true })

    const { count: uniqueVisitors } = await supabase
      .from('user_sessions')
      .select('*', { count: 'exact', head: true })

    const { count: pageViews } = await supabase
      .from('analytics_events')
      .select('*', { count: 'exact', head: true })
      .eq('event_type', 'page_view')

    const { count: productViews } = await supabase
      .from('analytics_events')
      .select('*', { count: 'exact', head: true })
      .eq('event_type', 'product_view')

    const { count: searchQueries } = await supabase
      .from('analytics_events')
      .select('*', { count: 'exact', head: true })
      .eq('event_type', 'search')

    const { data: pageViewEvents } = await supabase
      .from('analytics_events')
      .select('event_data')
      .eq('event_type', 'page_view')
      .gte('created_at', last7Days.toISOString())

    const pageCounts: Record<string, number> = {}
    pageViewEvents?.forEach((event: any) => {
      const url = event.event_data?.url || 'unknown'
      pageCounts[url] = (pageCounts[url] || 0) + 1
    })

    const topPages = Object.entries(pageCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([url, count]) => ({ page: url, count }))

    const { data: productViewEvents } = await supabase
      .from('analytics_events')
      .select('event_data')
      .eq('event_type', 'product_view')
      .gte('created_at', last7Days.toISOString())

    const productCounts: Record<string, { name: string; count: number }> = {}
    productViewEvents?.forEach((event: any) => {
      const productId = event.event_data?.productId || 'unknown'
      const productName = event.event_data?.productName || 'Unknown Product'
      if (!productCounts[productId]) {
        productCounts[productId] = { name: productName, count: 0 }
      }
      productCounts[productId].count++
    })

    const topProducts = Object.entries(productCounts)
      .sort(([, a], [, b]) => b.count - a.count)
      .slice(0, 10)
      .map(([id, data]) => ({ product_id: id, count: data.count }))

    const { data: eventsByType } = await supabase
      .from('analytics_events')
      .select('event_type')
      .gte('created_at', last7Days.toISOString())

    const eventTypeCounts: Record<string, number> = {}
    eventsByType?.forEach((event: any) => {
      const type = event.event_type || 'unknown'
      eventTypeCounts[type] = (eventTypeCounts[type] || 0) + 1
    })

    return NextResponse.json({
      totalEvents: totalEvents || 0,
      totalSessions: uniqueVisitors || 0,
      totalPageViews: pageViews || 0,
      totalProductViews: productViews || 0,
      totalSearches: searchQueries || 0,
      topPages,
      topProducts,
      recentEvents: events || [],
      eventsByType: Object.entries(eventTypeCounts).map(([event_type, count]) => ({ event_type, count })),
    })
  } catch (error) {
    console.error('Error fetching analytics:', error)
    return NextResponse.json({
      totalEvents: 0,
      totalSessions: 0,
      totalPageViews: 0,
      totalProductViews: 0,
      totalSearches: 0,
      topPages: [],
      topProducts: [],
      recentEvents: [],
      eventsByType: [],
    })
  }
}
