import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Send, Camera, Mic, Check, ChevronDown, Menu } from 'lucide-react'
import TopBar from '../components/layout/TopBar'
import ChatSidebar from '../components/ChatSidebar'
import { useSwipeToOpen } from '../hooks/useSwipeToOpen'
import {
  listConversations,
  createConversation,
  getConversation,
  saveConversation,
  type ConversationSummary,
  type MessageData,
} from '../lib/api'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  image?: string
  diagnosis?: DiagnosisPreview
  sources?: { name: string; score: number }[]
  suggestions?: string[]
}

interface DiagnosisPreview {
  disease: string
  confidence: number
  severity: 'High' | 'Medium' | 'Low'
  pathogen: string
}

const PIPELINE_STEPS = ['Classifying', 'Routing', 'Searching', 'Reranking', 'Generating']

function deriveTitle(firstMessage: string): string {
  const cleaned = firstMessage.replace(/\n/g, ' ').trim()
  if (cleaned.length <= 50) return cleaned
  const truncated = cleaned.slice(0, 50)
  const lastSpace = truncated.lastIndexOf(' ')
  return (lastSpace > 20 ? truncated.slice(0, lastSpace) : truncated) + '...'
}

function messagesToApi(messages: Message[]): MessageData[] {
  return messages.map((m) => ({
    role: m.role,
    content: m.content,
    image_path: m.image || null,
    metadata:
      m.diagnosis || m.sources || m.suggestions
        ? { diagnosis: m.diagnosis, sources: m.sources, suggestions: m.suggestions }
        : null,
  }))
}

function apiToMessages(data: MessageData[]): Message[] {
  return data.map((m, i) => {
    const meta = m.metadata as Record<string, unknown> | null
    return {
      id: String(i),
      role: m.role,
      content: m.content,
      image: (m.image_path as string) || undefined,
      diagnosis: (meta?.diagnosis as DiagnosisPreview) || undefined,
      sources: (meta?.sources as { name: string; score: number }[]) || undefined,
      suggestions: (meta?.suggestions as string[]) || undefined,
    }
  })
}

export default function FieldChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [pipelineStep, setPipelineStep] = useState(0)
  const [isStreaming, setIsStreaming] = useState(false)
  const [showSources, setShowSources] = useState<string | null>(null)

  // Conversation state
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [sidebarLoading, setSidebarLoading] = useState(false)

  const bottomRef = useRef<HTMLDivElement>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const skipNextSave = useRef(false)
  const navigate = useNavigate()
  const location = useLocation()

  const openSidebar = useCallback(() => setSidebarOpen(true), [])
  useSwipeToOpen(openSidebar)

  // Fetch conversations when sidebar opens
  useEffect(() => {
    if (!sidebarOpen) return
    setSidebarLoading(true)
    listConversations('field').then((convs) => {
      setConversations(convs)
      setSidebarLoading(false)
    })
  }, [sidebarOpen])

  // Pick up prefilled input from diagnosis card navigation
  useEffect(() => {
    const prefill = (location.state as { prefill?: string })?.prefill
    if (prefill) {
      setInput(prefill)
      window.history.replaceState({}, '')
    }
  }, [location.state])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Cleanup all timers on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    }
  }, [])

  // Auto-save after messages change (debounced — only when we have a conversation and messages)
  useEffect(() => {
    if (!conversationId || messages.length === 0 || isStreaming) return
    if (skipNextSave.current) {
      skipNextSave.current = false
      return
    }
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    saveTimeoutRef.current = setTimeout(() => {
      const firstUserMsg = messages.find((m) => m.role === 'user')
      const title = firstUserMsg ? deriveTitle(firstUserMsg.content) : 'New conversation'
      saveConversation(conversationId, 'field', messagesToApi(messages), title)
    }, 500)
    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    }
  }, [conversationId, messages, isStreaming])

  const handleNewChat = async () => {
    try {
      const conv = await createConversation('field')
      setConversationId(conv.id)
      setMessages([])
      setInput('')
      setSidebarOpen(false)
    } catch {
      // If pack not loaded, just clear locally
      setConversationId(null)
      setMessages([])
      setInput('')
      setSidebarOpen(false)
    }
  }

  const handleSelectConversation = async (id: string) => {
    try {
      const conv = await getConversation(id, 'field')
      skipNextSave.current = true
      setConversationId(conv.id)
      setMessages(apiToMessages(conv.messages))
      setSidebarOpen(false)
    } catch {
      // Conversation may have been deleted
    }
  }

  const handleSend = () => {
    if (!input.trim() || isStreaming) return

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input.trim() }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsStreaming(true)

    // Auto-create conversation if none active (fire-and-forget, auto-save handles persistence)
    if (!conversationId) {
      createConversation('field', deriveTitle(userMsg.content))
        .then((conv) => setConversationId(conv.id))
        .catch(() => {})
    }
    setPipelineStep(0)

    let step = 0
    intervalRef.current = setInterval(() => {
      step++
      if (step >= PIPELINE_STEPS.length - 1) {
        if (intervalRef.current) clearInterval(intervalRef.current)
        intervalRef.current = null
        setPipelineStep(PIPELINE_STEPS.length - 1)

        timeoutRef.current = setTimeout(() => {
          timeoutRef.current = null
          setIsStreaming(false)
          setMessages((prev) => [
            ...prev,
            {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: 'Based on your question, here is what I found in the knowledge base...',
              suggestions: ['Tell me more', 'What about prevention?', 'Show related diseases'],
            },
          ])
        }, 1500)
      } else {
        setPipelineStep(step)
      }
    }, 800)
  }

  const severityColor = (s: string) =>
    s === 'High'
      ? 'bg-tertiary/10 text-tertiary'
      : s === 'Medium'
        ? 'bg-secondary/10 text-secondary'
        : 'bg-primary/10 text-primary'

  return (
    <div className="flex flex-col h-[calc(100dvh-4rem)]">
      <ChatSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        conversations={conversations}
        activeId={conversationId}
        onSelect={handleSelectConversation}
        onNewChat={handleNewChat}
        isLoading={sidebarLoading}
      />

      <TopBar
        title="Field Assistant"
        backTo="/"
        back
        badge={{ label: 'Offline', variant: 'offline' }}
        leftAction={
          <button
            onClick={openSidebar}
            className="text-white/70 p-1 hover:text-white transition-colors"
            aria-label="Open chat history"
          >
            <Menu size={20} />
          </button>
        }
        rightAction={
          <span className="text-xs text-white/60 flex items-center gap-1">
            <Check size={12} />
            Casamance
          </span>
        }
      />

      {/* Pipeline status */}
      {isStreaming && (
        <div className="bg-primary-dark px-4 py-1.5">
          <div className="max-w-lg mx-auto flex items-center gap-2">
            <span className="text-xs text-white/70">{PIPELINE_STEPS[pipelineStep]}...</span>
            <div className="flex gap-1 ml-auto">
              {PIPELINE_STEPS.map((_, i) => (
                <span
                  key={i}
                  className={`w-1.5 h-1.5 rounded-full ${
                    i < pipelineStep
                      ? 'bg-primary-light'
                      : i === pipelineStep
                        ? 'bg-secondary animate-pulse'
                        : 'bg-white/20'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Chat */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 bg-surface">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full text-text-muted text-sm gap-2">
            <p className="font-heading font-semibold text-base text-text">Ask about your crops</p>
            <p className="text-center text-xs max-w-[250px]">
              Describe symptoms, upload a photo, or ask about farming practices in Casamance.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-primary text-white rounded-br-sm'
                  : 'bg-card text-text border-l-[3px] border-primary shadow-sm rounded-bl-sm'
              }`}
            >
              {msg.image && (
                <div className="mb-2 rounded-lg overflow-hidden bg-surface-dark h-32 flex items-center justify-center">
                  <Camera size={24} className="text-text-muted" />
                  <span className="ml-2 text-xs text-text-muted">Photo attached</span>
                </div>
              )}

              <p>{msg.content}</p>

              {msg.diagnosis && (
                <div className="mt-3 bg-surface rounded-lg p-3 space-y-1.5">
                  <p className="font-heading font-bold text-sm">{msg.diagnosis.disease}</p>
                  <div className="flex gap-1.5 flex-wrap">
                    <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-semibold">
                      {msg.diagnosis.confidence}% Confidence
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-semibold ${severityColor(msg.diagnosis.severity)}`}
                    >
                      {msg.diagnosis.severity} Severity
                    </span>
                  </div>
                  <p className="text-xs text-text-muted">{msg.diagnosis.pathogen}</p>
                  <button
                    onClick={() => navigate('/field/diagnosis')}
                    className="mt-2 text-xs font-semibold bg-secondary text-primary-dark px-3 py-1.5 rounded-lg hover:bg-secondary-light transition-colors"
                  >
                    View Full Diagnosis &rarr;
                  </button>
                </div>
              )}

              {msg.sources && (
                <div className="mt-2">
                  <button
                    onClick={() => setShowSources(showSources === msg.id ? null : msg.id)}
                    className="flex items-center gap-1 text-xs text-text-muted hover:text-text"
                  >
                    <ChevronDown
                      size={12}
                      className={showSources === msg.id ? 'rotate-180 transition-transform' : 'transition-transform'}
                    />
                    {msg.sources.length} sources
                  </button>
                  {showSources === msg.id && (
                    <div className="mt-1.5 space-y-1">
                      {msg.sources.map((s) => (
                        <div key={s.name} className="flex items-center justify-between text-xs text-text-muted">
                          <span>{s.name}</span>
                          <span className="font-mono">{s.score.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {msg.suggestions && (
                <div className="mt-3 flex gap-1.5 flex-wrap">
                  {msg.suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => setInput(s)}
                      className="text-xs bg-surface text-text px-3 py-1.5 rounded-full border border-surface-dark hover:bg-surface-dark transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isStreaming && (
          <div className="flex justify-start">
            <div className="bg-card rounded-xl px-4 py-3 text-sm border-l-[3px] border-primary shadow-sm">
              <div className="flex items-center gap-2 text-text-muted">
                <div className="w-2 h-2 bg-secondary rounded-full animate-pulse" />
                <span className="text-xs">{PIPELINE_STEPS[pipelineStep]}...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="bg-card border-t border-surface-dark px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center gap-2">
          <button className="text-text-muted p-2 hover:text-primary transition-colors" aria-label="Attach photo">
            <Camera size={20} />
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about your crops..."
            className="flex-1 bg-surface rounded-lg px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button className="text-text-muted p-2 hover:text-primary transition-colors" aria-label="Voice input">
            <Mic size={20} />
          </button>
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="bg-primary text-white p-2.5 rounded-lg disabled:opacity-40 hover:bg-primary-light transition-colors"
            aria-label="Send message"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}
