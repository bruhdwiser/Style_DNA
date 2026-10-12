import { supabaseServer } from '@/lib/supabase/server'
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const { message, conversationHistory } = await request.json()

    if (!process.env.OPENROUTER_API_KEY) {
      return NextResponse.json(
        { error: 'OpenRouter API key not configured' },
        { status: 500 }
      )
    }

    // Fetch products from Supabase
    const supabase = await supabaseServer()
    const { data: products, error } = await supabase
      .from('products')
      .select('*')
      .limit(50) // Limit for API response size

    if (error) {
      console.error('Error fetching products:', error)
    }

    console.log(`Fetched ${products?.length || 0} products from database`)

    // Create context about available products with their IDs for linking
    const productContext = products && products.length > 0
      ? products
          .map(
            (p) =>
              `- ${p.name} (ID: ${p.id}): ${p.description || 'No description'}, Price: ₹${(p.price_cents / 100).toFixed(2)}, Category: ${p.category || 'General'}`
          )
          .join('\n')
      : 'No products available in catalog yet'

    // Build the prompt with context
    const systemPrompt = `You are Flashfits AI, a professional fashion styling assistant for our e-commerce store.

**YOUR CATALOG** (These are the ONLY products you can recommend):
${productContext}

**YOUR ROLE:**
- Help customers find perfect fashion items from OUR CATALOG ONLY
- Provide personalized styling advice and outfit recommendations
- Match products to customer's needs, preferences, and occasions
- Build complete outfits using our available products

**CRITICAL RULES FOR PRODUCT RECOMMENDATIONS:**
1. ONLY recommend products that are listed in YOUR CATALOG above
2. ALWAYS include clickable links using this EXACT format: [Product Name](/product/ID)
   Example: [ZARA Beige Satin Button-Down Blouse](/product/123)
3. Include the product's price in RUPEES (₹) when recommending it
4. When building outfits, suggest 2-4 complementary items from our catalog
5. If catalog doesn't have what user wants, suggest the closest alternatives we DO have

**RESPONSE STYLE:**
- Friendly, enthusiastic, and knowledgeable about fashion
- Start with a warm greeting or acknowledgment
- Provide brief styling context before product links
- Keep responses concise (3-5 sentences max) but helpful
- End with an encouraging call-to-action

**EXAMPLE RESPONSE FORMAT:**
"Great choice! For a business casual look, I recommend:
• [ZARA BLUE PLAIN STRIPPED SHIRT](/product/1) - ₹2499.00 - Perfect professional base
• [H&M WHITE SHIRT WITH GRAY STRIPES](/product/2) - ₹1999.00 - Alternative option

These pieces are versatile and can be styled multiple ways. Click any product to view details! 👔"

**CONVERSATION HISTORY:**
${conversationHistory || 'This is the start of a new conversation'}

**USER'S MESSAGE:**
${message}

**YOUR RESPONSE:** (Remember: Include product links in [Name](/product/ID) format)`

    // Get model from environment variable or use default
    const primaryModel = process.env.OPENROUTER_MODEL || 'meta-llama/llama-3-8b-instruct:free'
    
    // Fallback models in case primary fails
    const models = [
      primaryModel,
      'meta-llama/llama-3.2-3b-instruct:free',
      'microsoft/phi-3-mini-128k-instruct:free',
      'mistralai/mistral-7b-instruct:free'
    ]

    let lastError = null
    
    for (const model of models) {
      try {
        console.log(`Trying model: ${model}`)
        
        // Call OpenRouter API
        const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
            'Content-Type': 'application/json',
            'HTTP-Referer': process.env.NEXT_PUBLIC_SITE_URL || 'https://flashfits.vercel.app',
            'X-Title': 'Flashfits Fashion AI'
          },
          body: JSON.stringify({
            model: model,
            messages: [
              {
                role: 'user',
                content: systemPrompt
              }
            ],
            temperature: 0.7,
            max_tokens: 1500
          })
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          console.error(`OpenRouter API error for ${model}:`, JSON.stringify(errorData, null, 2))
          lastError = errorData
          continue // Try next model
        }

        const data = await response.json()
        const text = data.choices[0]?.message?.content || 'Sorry, I could not generate a response.'
        
        console.log(`Success with model: ${model}`)
        return NextResponse.json({ message: text })
      } catch (err) {
        console.error(`Error with model ${model}:`, err)
        lastError = err
        continue // Try next model
      }
    }

    // If all models failed
    console.error('All models failed. Last error:', lastError)
    return NextResponse.json(
      { error: 'All AI models are currently unavailable. Please try again later.' },
      { status: 503 }
    )
  } catch (error) {
    console.error('Error in AI chat:', error)
    return NextResponse.json(
      { error: 'Failed to process your request. Please try again.' },
      { status: 500 }
    )
  }
}