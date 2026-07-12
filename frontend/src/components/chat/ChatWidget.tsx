import { useState, useRef, useEffect } from 'react'
import { useStore } from '@/store'
import { streamChat } from '@/api/client'
import ReactMarkdown from 'react-markdown'

const QUICK_PROMPTS = [
  'What does this result mean?',
  'Is the safety factor acceptable?',
  'How can I reduce stress concentrations?',
  'Explain the boundary conditions I should use.',
]

export default function ChatWidget() {
  const { chatOpen, setChatOpen, currentProjectId, activeJobId } = useStore()
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([
    {
      role: 'assistant',
      content: "Hi! I'm your **CAE Assistant** 🔧\n\nI can help you:\n- Interpret analysis results\n- Set up boundary conditions\n- Understand material properties\n- Navigate solver settings\n\nUpload a CAD file and run an analysis to get started!",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text?: string) => {
    const msg = text || input.trim()
    if (!msg || loading) return
    setInput('')

    const userMsg = { role: 'user' as const, content: msg }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    // Optimistic assistant placeholder
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    try {
      await streamChat(
        currentProjectId || 'demo',
        msg,
        activeJobId || undefined,
        (token) => {
          setMessages(prev => {
            const copy = [...prev]
            copy[copy.length - 1] = {
              ...copy[copy.length - 1],
              content: copy[copy.length - 1].content + token,
            }
            return copy
          })
        },
        () => setLoading(false),
      )
    } catch {
      setMessages(prev => {
        const copy = [...prev]
        copy[copy.length - 1] = {
          ...copy[copy.length - 1],
          content: 'Sorry, I encountered an error. Please check your API configuration.',
        }
        return copy
      })
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="chat-widget">
      {chatOpen && (
        <div className="chat-panel">
          {/* Header */}
          <div className="chat-header">
            <div className="chat-title">
              <span className="chat-ai-dot" />
              CAE Assistant
            </div>
            <button
              className="btn btn-ghost btn-icon btn-sm"
              onClick={() => setChatOpen(false)}
              aria-label="Close chat"
            >
              ✕
            </button>
          </div>

          {/* Messages */}
          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className={`message ${m.role}`}>
                {m.role === 'assistant'
                  ? <ReactMarkdown>{m.content || (loading && i === messages.length - 1 ? '▋' : '')}</ReactMarkdown>
                  : m.content
                }
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Quick prompts (only if no project context yet) */}
          {messages.length <= 1 && (
            <div style={{ padding: '0 12px 8px', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {QUICK_PROMPTS.map((q) => (
                <button
                  key={q}
                  className="btn btn-ghost btn-sm"
                  style={{ fontSize: 11 }}
                  onClick={() => send(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="chat-input-area">
            <textarea
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your analysis…"
              rows={2}
              disabled={loading}
            />
            <button
              className="chat-send-btn"
              onClick={() => send()}
              disabled={!input.trim() || loading}
              aria-label="Send message"
            >
              {loading ? '…' : '↑'}
            </button>
          </div>
        </div>
      )}

      {/* Toggle button */}
      <button
        className="chat-toggle"
        onClick={() => setChatOpen(!chatOpen)}
        aria-label={chatOpen ? 'Close AI assistant' : 'Open AI assistant'}
        title="CAE AI Assistant"
      >
        {chatOpen ? '✕' : '🤖'}
      </button>
    </div>
  )
}
