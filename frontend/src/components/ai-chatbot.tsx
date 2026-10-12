import React, { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { X, Send, Bot, User, Sparkles, ExternalLink } from 'lucide-react'
import { api } from '@/lib/api'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface AiChatbotProps {
  isOpen: boolean
  onClose: () => void
  initialMessage?: string
}

export function AiChatbot({ isOpen, onClose, initialMessage }: AiChatbotProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content:
        "👋 Hi! I'm your Flashfits AI styling assistant! I can help you find the perfect outfits from our collection. What look are you going for today?",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (initialMessage && isOpen) {
      setInput(initialMessage)
    }
  }, [initialMessage, isOpen])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  const parseMessageContent = (content: string) => {
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g
    const parts: (string | { text: string; url: string })[] = []
    let lastIndex = 0
    let match

    while ((match = linkRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.substring(lastIndex, match.index))
      }
      parts.push({ text: match[1], url: match[2] })
      lastIndex = match.index + match[0].length
    }

    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex))
    }

    return parts.length > 0 ? parts : [content]
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    const promptText = input.trim()
    setInput('')
    setIsLoading(true)

    try {
      const historyStr = messages.map((m) => `${m.role}: ${m.content}`).join('\n')
      const response = await api.ai.chat(promptText, historyStr)

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message || "I found some great options for you!",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (err: any) {
      console.error('AI chat error:', err)
      const fallbackMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content:
          "I'm temporarily having trouble reaching the AI service. You can explore our collection directly on the [Shop Catalog](/shop)!",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, fallbackMsg])
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 w-[95vw] sm:w-[420px] max-w-lg shadow-2xl animate-in fade-in slide-in-from-bottom-6 duration-300">
      <Card className="border border-border/80 shadow-2xl backdrop-blur-xl bg-card/95 overflow-hidden flex flex-col h-[580px]">
        {/* Header */}
        <CardHeader className="bg-gradient-to-r from-primary to-accent text-primary-foreground p-4 flex flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <CardTitle className="text-base font-bold text-white">FlashFit AI Stylist</CardTitle>
              <p className="text-xs text-white/80">Personalized Fashion Recommendations</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="text-white hover:bg-white/20 h-8 w-8"
          >
            <X className="w-4 h-4" />
          </Button>
        </CardHeader>

        {/* Message list */}
        <ScrollArea className="flex-1 p-4 space-y-4">
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-2.5 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-full bg-primary/10 text-primary flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-xs ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground font-medium rounded-tr-xs'
                      : 'bg-muted/70 text-foreground border border-border/40 rounded-tl-xs'
                  }`}
                >
                  {message.role === 'assistant' ? (
                    <div>
                      {parseMessageContent(message.content).map((part, idx) => {
                        if (typeof part === 'string') {
                          return <span key={idx}>{part}</span>
                        }
                        return (
                          <Link
                            key={idx}
                            to={part.url}
                            onClick={onClose}
                            className="inline-flex items-center gap-1 text-primary font-semibold underline hover:opacity-80 mx-1"
                          >
                            {part.text}
                            <ExternalLink className="w-3 h-3 inline" />
                          </Link>
                        )
                      })}
                    </div>
                  ) : (
                    message.content
                  )}
                </div>
                {message.role === 'user' && (
                  <div className="w-7 h-7 rounded-full bg-accent text-accent-foreground flex items-center justify-center flex-shrink-0 mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-2.5 items-center text-muted-foreground text-xs italic">
                <Bot className="w-4 h-4 animate-spin text-primary" />
                Thinking & curating fashion looks...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Input area */}
        <CardContent className="p-3 bg-card border-t border-border flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                sendMessage()
              }
            }}
            placeholder="Ask about looks, colors, occasions..."
            className="text-sm"
            disabled={isLoading}
          />
          <Button
            size="icon"
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
            className="flex-shrink-0"
          >
            <Send className="w-4 h-4" />
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
