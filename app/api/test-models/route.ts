import { NextResponse } from 'next/server'

export async function GET() {
  try {
    if (!process.env.OPENROUTER_API_KEY) {
      return NextResponse.json({ error: 'No OpenRouter API key configured' }, { status: 500 })
    }

    // Test OpenRouter models (free models used in chatbot)
    const testModels = [
      'meta-llama/llama-3-8b-instruct:free',
      'meta-llama/llama-3.2-3b-instruct:free',
      'microsoft/phi-3-mini-128k-instruct:free',
      'mistralai/mistral-7b-instruct:free'
    ]
    
    const results = []
    
    for (const modelName of testModels) {
      try {
        const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
            'Content-Type': 'application/json',
            'HTTP-Referer': process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3001',
          },
          body: JSON.stringify({
            model: modelName,
            messages: [
              {
                role: 'user',
                content: 'Hello! Respond with just "OK"'
              }
            ],
            max_tokens: 50
          })
        })

        const data = await response.json()
        
        if (data.choices && data.choices[0]?.message?.content) {
          results.push({ 
            model: modelName, 
            status: 'success',
            response: data.choices[0].message.content
          })
        } else if (data.error) {
          results.push({ 
            model: modelName, 
            status: 'failed', 
            error: data.error.message || JSON.stringify(data.error)
          })
        } else {
          results.push({ 
            model: modelName, 
            status: 'failed', 
            error: 'No response generated'
          })
        }
      } catch (err: any) {
        results.push({ 
          model: modelName, 
          status: 'failed', 
          error: err.message || 'Unknown error'
        })
      }
    }
    
    return NextResponse.json({ testResults: results })
  } catch (error: any) {
    return NextResponse.json({ 
      error: error.message || 'Unknown error' 
    }, { status: 500 })
  }
}