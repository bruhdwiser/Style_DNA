import { NextRequest, NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    hasGeminiKey: !!process.env.GEMINI_API_KEY,
    hasSupabaseUrl: !!process.env.NEXT_PUBLIC_SUPABASE_URL,
    hasSupabaseKey: !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    geminiKeyLength: process.env.GEMINI_API_KEY?.length || 0
  })
}