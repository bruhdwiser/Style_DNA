import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { api } from '@/lib/api'
import { usePageTracking } from '@/lib/tracking'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export default function AiStylistPage() {
  usePageTracking()
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: 'Tell me where you’re going, what you want to wear, or the piece you can’t quite place. I’ll pull options from the rack.' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const parseLinks = (content: string) => {
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g
    const parts: (string | { text: string; url: string })[] = []
    let lastIndex = 0
    let match
    while ((match = linkRegex.exec(content)) !== null) {
      if (match.index > lastIndex) parts.push(content.substring(lastIndex, match.index))
      parts.push({ text: match[1], url: match[2] })
      lastIndex = match.index + match[0].length
    }
    if (lastIndex < content.length) parts.push(content.substring(lastIndex))
    return parts.length ? parts : [content]
  }

  const handleSend = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!input.trim() || loading) return
    const prompt = input.trim()
    const nextMessages = [...messages, { id: Date.now().toString(), role: 'user' as const, content: prompt }]
    setMessages(nextMessages)
    setInput('')
    setLoading(true)
    try {
      const history = messages.map((message) => `${message.role}: ${message.content}`).join('\n')
      const response = await api.ai.chat(prompt, history)
      setMessages((previous) => [...previous, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message || 'Here are a few pieces that could work. Take a look at the rack.',
      }])
    } catch (error) {
      console.error('Second opinion request failed:', error)
      setMessages((previous) => [...previous, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'I couldn’t reach the fitting room just now. You can still [browse the rack](/shop).',
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-shell opinion-page">
      <Navigation />
      <main className="page-main opinion-main">
        <div className="opinion-intro">
          <p className="eyebrow">STYLESENSE / A SECOND OPINION</p>
          <h1>Describe<br /><em>the plan.</em></h1>
          <div>
            <p>Tell us the occasion, weather, or the one piece you want to wear. We’ll find a way in.</p>
            <span className="opinion-disclosure">SUGGESTIONS COME FROM THE STYLESENSE RACK.</span>
          </div>
        </div>

        <section className="opinion-workspace" aria-label="Styling conversation">
          <div className="opinion-messages" aria-live="polite">
            {messages.map((message) => (
              <article key={message.id} className={`opinion-message ${message.role}`}>
                <span className="opinion-message-label">{message.role === 'user' ? 'YOU' : 'STYLESENSE NOTES'}</span>
                <div>
                  {message.role === 'assistant'
                    ? parseLinks(message.content).map((part, index) => typeof part === 'string'
                      ? <span key={index}>{part}</span>
                      : <Link key={index} to={part.url}>{part.text} →</Link>)
                    : message.content}
                </div>
              </article>
            ))}
            {loading && <p className="opinion-loading">PULLING A FEW OPTIONS…</p>}
          </div>

          <div className="opinion-prompt-list">
            <span className="eyebrow">START WITH</span>
            {[
              'A relaxed look for a humid afternoon',
              'One shirt, three ways to wear it',
              'Something for dinner, no heels',
            ].map((prompt) => (
              <button type="button" key={prompt} onClick={() => setInput(prompt)}>{prompt}<span>↗</span></button>
            ))}
          </div>

          <form onSubmit={handleSend} className="opinion-form">
            <label htmlFor="opinion-input" className="eyebrow">YOUR NOTE</label>
            <div>
              <textarea
                id="opinion-input"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="A rooftop dinner, warm weather, and the blue shirt I never wear…"
                rows={2}
                disabled={loading}
              />
              <button type="submit" disabled={loading || !input.trim()}>{loading ? 'ONE MOMENT…' : 'SEND NOTE →'}</button>
            </div>
          </form>
        </section>
      </main>
      <Footer />
    </div>
  )
}
