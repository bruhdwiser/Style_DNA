import React, { useState } from 'react'
import { Sparkles, Send, Bot, User, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Navigation } from '@/components/navigation'
import { Footer } from '@/components/footer'
import { Link } from 'react-router-dom'
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
    {
      id: '1',
      role: 'assistant',
      content:
        "Hello! I am your FlashFit AI Personal Stylist. Tell me about your upcoming plans, aesthetic preferences (e.g. minimalist, bold, vintage, chic), or a garment you want to style, and I will recommend outfits from our collection!",
    },
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
    return parts.length > 0 ? parts : [content]
  }

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
    }
    setMessages((prev) => [...prev, userMsg])
    const prompt = input.trim()
    setInput('')
    setLoading(true)

    try {
      const history = messages.map((m) => `${m.role}: ${m.content}`).join('\n')
      const res = await api.ai.chat(prompt, history)
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: res.message || "Here are some top picks that match your vibe!",
        },
      ])
    } catch (err) {
      console.error('Stylist chat error:', err)
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content:
            "I'm experiencing a brief connection delay with our AI engine. Feel free to browse our trending pieces on the [Shop](/shop) page!",
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navigation />

      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full flex flex-col">
        {/* Header */}
        <div className="text-center space-y-2 mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold uppercase">
            <Sparkles className="w-3.5 h-3.5" />
            Interactive Styling Studio
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-foreground tracking-tight">
            Meet Your FlashFit AI Stylist
          </h1>
          <p className="text-muted-foreground text-sm max-w-lg mx-auto">
            Get instant outfit recommendations grounded directly in our verified catalog inventory.
          </p>
        </div>

        {/* Chat Container */}
        <Card className="flex-1 border-border/80 shadow-xl overflow-hidden flex flex-col min-h-[500px]">
          <ScrollArea className="flex-1 p-6 space-y-4">
            <div className="space-y-4">
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {m.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center flex-shrink-0 mt-1">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}
                  <div
                    className={`max-w-[85%] rounded-2xl px-5 py-3 text-sm leading-relaxed ${
                      m.role === 'user'
                        ? 'bg-primary text-primary-foreground font-medium rounded-tr-xs shadow-md'
                        : 'bg-muted/60 text-foreground border border-border/40 rounded-tl-xs shadow-xs'
                    }`}
                  >
                    {m.role === 'assistant' ? (
                      <div>
                        {parseLinks(m.content).map((part, idx) => {
                          if (typeof part === 'string') return <span key={idx}>{part}</span>
                          return (
                            <Link
                              key={idx}
                              to={part.url}
                              className="inline-flex items-center gap-1 font-bold text-primary underline mx-1 hover:opacity-80"
                            >
                              {part.text}
                              <ArrowRight className="w-3.5 h-3.5 inline" />
                            </Link>
                          )
                        })}
                      </div>
                    ) : (
                      m.content
                    )}
                  </div>
                  {m.role === 'user' && (
                    <div className="w-8 h-8 rounded-full bg-accent text-accent-foreground flex items-center justify-center flex-shrink-0 mt-1">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex gap-3 items-center text-xs text-muted-foreground italic">
                  <Bot className="w-4 h-4 text-primary animate-spin" />
                  Stylist is selecting garments from our collection...
                </div>
              )}
            </div>
          </ScrollArea>

          {/* Quick Prompts */}
          <div className="px-6 py-2.5 bg-muted/20 border-t border-border flex items-center gap-2 overflow-x-auto text-xs scrollbar-none">
            <span className="text-muted-foreground whitespace-nowrap">Suggested:</span>
            {[
              'Casual summer linen outfit',
              'Smart formal blazer and trousers',
              'Monochrome luxury evening look',
            ].map((p) => (
              <button
                key={p}
                onClick={() => setInput(p)}
                className="px-2.5 py-1 rounded-full bg-background border border-border text-foreground hover:border-primary whitespace-nowrap cursor-pointer transition-colors"
              >
                {p}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <form onSubmit={handleSend} className="p-4 bg-card border-t border-border flex gap-3">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask your stylist: 'What should I wear to a rooftop gallery opening?'"
              className="text-sm"
              disabled={loading}
            />
            <Button type="submit" disabled={loading || !input.trim()} className="gap-2 px-5">
              <Send className="w-4 h-4" />
              Send
            </Button>
          </form>
        </Card>
      </main>

      <Footer />
    </div>
  )
}
