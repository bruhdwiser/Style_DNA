import { NextRequest, NextResponse } from 'next/server'
import { supabaseServer } from '@/lib/supabase/server'
import { headers } from 'next/headers'

export async function POST(request: NextRequest) {
  try {
    const supabase = await supabaseServer()
    const headersList = await headers()
    
    // Get user session
    const { data: { user } } = await supabase.auth.getUser()
    
    const body = await request.json()
    const { eventType, eventData, sessionId } = body

    // Get IP address and user agent
    const ipAddress = headersList.get('x-forwarded-for') || headersList.get('x-real-ip') || 'unknown'
    const userAgent = headersList.get('user-agent') || 'unknown'

    // Insert analytics event
    const { data: event, error } = await supabase
      .from('analytics_events')
      .insert({
        event_type: eventType,
        event_data: eventData,
        user_id: user?.id || null,
        session_id: sessionId,
        ip_address: ipAddress,
        user_agent: userAgent,
      })
      .select()
      .single()

    if (error) {
      console.error('Error inserting analytics event:', error)
      return NextResponse.json({ error: error.message }, { status: 500 })
    }

    // Update or create session
    const { error: sessionError } = await supabase
      .from('user_sessions')
      .upsert({
        session_id: sessionId,
        user_id: user?.id || null,
        last_active_at: new Date().toISOString(),
        device_info: {
          userAgent,
        },
      }, {
        onConflict: 'session_id'
      })

    if (sessionError) {
      console.error('Error updating session:', sessionError)
    }

    return NextResponse.json({ success: true, event })
  } catch (error) {
    console.error('Analytics tracking error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
