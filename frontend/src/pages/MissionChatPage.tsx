import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, Menu } from 'lucide-react'
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
  missionCard?: MissionSummary
  actions?: { label: string; variant: 'primary' | 'secondary' }[]
}

interface MissionSummary {
  region: string
  crops: string[]
  season: string
  focusAreas: string[]
}

const INITIAL_MESSAGES: Message[] = [
  {
    id: '1',
    role: 'assistant',
    content:
      "Welcome! I'll help you prepare a Knowledge Pack for your deployment. Where are you headed and what crops will you be working with?",
  },
]

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
    metadata: m.missionCard || m.actions ? { missionCard: m.missionCard, actions: m.actions } : null,
  }))
}

function apiToMessages(data: MessageData[]): Message[] {
  return data.map((m, i) => {
    const meta = m.metadata as Record<string, unknown> | null
    return {
      id: String(i),
      role: m.role,
      content: m.content,
      missionCard: (meta?.missionCard as MissionSummary) || undefined,
      actions: (meta?.actions as { label: string; variant: 'primary' | 'secondary' }[]) || undefined,
    }
  })
}

export default function MissionChatPage() {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES)
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [missionReady, setMissionReady] = useState(false)
  const [editing, setEditing] = useState(false)

  // Conversation state
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [sidebarLoading, setSidebarLoading] = useState(false)

  const bottomRef = useRef<HTMLDivElement>(null)
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const skipNextSave = useRef(false)
  const navigate = useNavigate()

  const openSidebar = useCallback(() => setSidebarOpen(true), [])
  useSwipeToOpen(openSidebar)

  // Fetch conversations when sidebar opens
  useEffect(() => {
    if (!sidebarOpen) return
    setSidebarLoading(true)
    listConversations('mission').then((convs) => {
      setConversations(convs)
      setSidebarLoading(false)
    })
  }, [sidebarOpen])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Cleanup save timer on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    }
  }, [])

  // Auto-save after messages change
  useEffect(() => {
    if (!conversationId || messages.length <= 1 || isTyping) return
    if (skipNextSave.current) {
      skipNextSave.current = false
      return
    }
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    saveTimeoutRef.current = setTimeout(() => {
      const firstUserMsg = messages.find((m) => m.role === 'user')
      const title = firstUserMsg ? deriveTitle(firstUserMsg.content) : 'New mission'
      saveConversation(conversationId, 'mission', messagesToApi(messages), title)
    }, 500)
    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
    }
  }, [conversationId, messages, isTyping])

  const handleNewChat = async () => {
    try {
      const conv = await createConversation('mission')
      setConversationId(conv.id)
    } catch {
      setConversationId(null)
    }
    setMessages(INITIAL_MESSAGES)
    setMissionReady(false)
    setEditing(false)
    setInput('')
    setSidebarOpen(false)
  }

  const handleSelectConversation = async (id: string) => {
    try {
      const conv = await getConversation(id, 'mission')
      skipNextSave.current = true
      setConversationId(conv.id)
      setMessages(apiToMessages(conv.messages))
      // Check if mission was already configured
      const hasMissionCard = conv.messages.some((m) => m.metadata && (m.metadata as Record<string, unknown>).missionCard)
      setMissionReady(hasMissionCard)
      setEditing(false)
      setSidebarOpen(false)
    } catch {
      // Conversation may have been deleted
    }
  }

  const handleSend = () => {
    if (!input.trim() || isTyping) return

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input.trim() }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsTyping(true)

    // Auto-create conversation if none active (fire-and-forget)
    if (!conversationId) {
      createConversation('mission', deriveTitle(userMsg.content))
        .then((conv) => setConversationId(conv.id))
        .catch(() => {})
    }

    if (editing) {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: "Got it, I've updated the mission plan. Here's the revised version:",
            missionCard: {
              region: 'Casamance, Senegal',
              crops: ['Cassava', 'Rice'],
              season: 'Rainy (Jul\u2013Oct)',
              focusAreas: ['Disease ID', 'Treatment Protocols', 'Farming Calendar'],
            },
            actions: [
              { label: 'Dispatch Agents \u2192', variant: 'primary' },
              { label: 'Edit details', variant: 'secondary' },
            ],
          },
        ])
        setIsTyping(false)
        setEditing(false)
      }, 1000)
      return
    }

    if (missionReady) {
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content:
              "I can adjust the mission plan if needed. Just tell me what to change, or hit 'Dispatch Agents' above when you're ready!",
          },
        ])
        setIsTyping(false)
      }, 1000)
      return
    }

    // First substantive response -- show mission card
    setTimeout(() => {
      const response: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "Great \u2014 I'll focus on that region. Here's what I'll research for you:",
        missionCard: {
          region: 'Casamance, Senegal',
          crops: ['Cassava', 'Rice'],
          season: 'Rainy (Jul\u2013Oct)',
          focusAreas: ['Disease ID', 'Treatment Protocols', 'Farming Calendar'],
        },
        actions: [
          { label: 'Dispatch Agents \u2192', variant: 'primary' },
          { label: 'Edit details', variant: 'secondary' },
        ],
      }
      setMessages((prev) => [...prev, response])
      setIsTyping(false)
      setMissionReady(true)
    }, 1500)
  }

  const handleAction = (label: string) => {
    if (label.includes('Dispatch')) {
      navigate('/mission/progress')
    } else if (label.includes('Edit')) {
      setEditing(true)
      setInput('')
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 2).toString(),
          role: 'assistant',
          content: 'Sure! What would you like to change? You can adjust the region, crops, season, or focus areas.',
        },
      ])
    }
  }

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
        title="Plan Your Mission"
        badge={{ label: 'Online', variant: 'online' }}
        back
        backTo="/"
        leftAction={
          <button
            onClick={openSidebar}
            className="text-white/70 p-1 hover:text-white transition-colors"
            aria-label="Open chat history"
          >
            <Menu size={20} />
          </button>
        }
      />

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 bg-surface">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-primary text-white rounded-br-sm'
                  : 'bg-card text-text border-l-[3px] border-primary shadow-sm rounded-bl-sm'
              }`}
            >
              <p>{msg.content}</p>

              {msg.missionCard && (
                <div className="mt-3 bg-surface rounded-lg p-3 space-y-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-text-muted">Region:</span>
                    <span className="text-text">{msg.missionCard.region}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-text-muted">Crops:</span>
                    <div className="flex gap-1 flex-wrap">
                      {msg.missionCard.crops.map((c) => (
                        <span key={c} className="bg-primary/10 text-primary px-2 py-0.5 rounded-full text-xs font-medium">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-text-muted">Season:</span>
                    <span className="text-text">{msg.missionCard.season}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-text-muted">Focus:</span>
                    <div className="flex gap-1 flex-wrap">
                      {msg.missionCard.focusAreas.map((f) => (
                        <span key={f} className="bg-secondary/10 text-secondary px-2 py-0.5 rounded-full text-xs font-medium">
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {msg.actions && (
                <div className="mt-3 flex gap-2 flex-wrap">
                  {msg.actions.map((a) => (
                    <button
                      key={a.label}
                      onClick={() => handleAction(a.label)}
                      className={`text-xs font-semibold px-4 py-2 rounded-lg transition-colors ${
                        a.variant === 'primary'
                          ? 'bg-primary text-white hover:bg-primary-light'
                          : 'border border-text-muted text-text-muted hover:bg-surface-dark'
                      }`}
                    >
                      {a.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-card text-text-muted rounded-xl px-4 py-3 text-sm border-l-[3px] border-primary shadow-sm">
              <div className="flex gap-1">
                <span className="animate-bounce">.</span>
                <span className="animate-bounce [animation-delay:0.1s]">.</span>
                <span className="animate-bounce [animation-delay:0.2s]">.</span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="bg-card border-t border-surface-dark px-4 py-3">
        <div className="max-w-lg mx-auto flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder={editing ? 'Tell me what to change...' : 'Describe your mission...'}
            className="flex-1 bg-surface rounded-lg px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
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
