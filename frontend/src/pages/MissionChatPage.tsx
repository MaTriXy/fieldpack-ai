import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, Menu, Leaf, FileText } from 'lucide-react'
import MarkdownContent from '../components/MarkdownContent'
import ThinkingBubble from '../components/ThinkingBubble'
import TopBar from '../components/layout/TopBar'
import ChatSidebar from '../components/ChatSidebar'
import { useSwipeToOpen } from '../hooks/useSwipeToOpen'
import { useAndroidBack } from '../hooks/useAndroidBack'
import { isNative, getMissionChatWsUrl } from '../lib/config'
import { getLanguage } from '../lib/settings'
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
  scaleEstimate?: string
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
  const haptic = (style: string = 'Medium') =>
    isNative() && import('@capacitor/haptics').then(m =>
      m.Haptics.impact({ style: m.ImpactStyle[style as keyof typeof m.ImpactStyle] })
    ).catch(() => {})

  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES)
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [editing, setEditing] = useState(false)
  const [currentStep, setCurrentStep] = useState<string | null>(null)

  // Conversation state
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [sidebarLoading, setSidebarLoading] = useState(false)

  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const skipNextSave = useRef(false)
  const chatWsRef = useRef<WebSocket | null>(null)
  const navigate = useNavigate()

  const openSidebar = useCallback(() => setSidebarOpen(true), [])
  useSwipeToOpen(openSidebar)
  useAndroidBack([
    () => { if (sidebarOpen) { setSidebarOpen(false); return true } return false },
  ])

  // Auto-focus textarea on mount so keyboard users can type immediately
  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

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

  // Cleanup save timer and chat WebSocket on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
      chatWsRef.current?.close()
      chatWsRef.current = null
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
      setEditing(false)
      setSidebarOpen(false)
    } catch {
      // Conversation may have been deleted
    }
  }

  const handleSend = async () => {
    if (!input.trim() || isTyping) return

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input.trim() }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsTyping(true)
    setCurrentStep(null)

    // Auto-create conversation if none active
    if (!conversationId) {
      createConversation('mission', deriveTitle(userMsg.content))
        .then((conv) => setConversationId(conv.id))
        .catch(() => {})
    }

    try {
      const allMessages = [...messages, userMsg]
      const history = messagesToApi(allMessages).slice(0, -1).map((m) => ({
        role: m.role,
        content: m.content,
      }))

      const ws = new WebSocket(getMissionChatWsUrl())
      chatWsRef.current = ws

      await new Promise<void>((resolve, reject) => {
        let handled = false

        ws.onopen = () => {
          ws.send(JSON.stringify({
            message: userMsg.content,
            language: getLanguage() || undefined,
            conversation_history: history,
          }))
        }

        ws.onmessage = (event) => {
          let data: Record<string, unknown>
          try {
            data = JSON.parse(event.data)
          } catch {
            return
          }

          if (data.type === 'status') {
            setCurrentStep(data.step as string)
          } else if (data.type === 'done') {
            handled = true
            const reply = data.reply as string
            const card = data.mission_card as {
              region: string
              crops: string[]
              season: string
              focus_areas: string[]
              scale_estimate?: string
            } | null

            const assistantMsg: Message = {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: reply,
            }

            if (card) {
              assistantMsg.missionCard = {
                region: card.region,
                crops: card.crops,
                season: card.season,
                focusAreas: card.focus_areas,
                scaleEstimate: card.scale_estimate || undefined,
              }
              assistantMsg.actions = [
                { label: 'Dispatch Agents \u2192', variant: 'primary' },
                { label: 'Edit details', variant: 'secondary' },
              ]
              setEditing(false)
            }

            setMessages((prev) => [...prev, assistantMsg])
            ws.close()
            resolve()
          } else if (data.type === 'error') {
            handled = true
            const message = (data.message as string) || 'Unknown error'
            setMessages((prev) => [
              ...prev,
              {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: `I couldn't process that request. ${message}`,
              },
            ])
            ws.close()
            resolve()
          }
        }

        ws.onerror = () => {
          handled = true
          reject(new Error('WebSocket connection failed'))
        }

        ws.onclose = () => {
          chatWsRef.current = null
          if (!handled) {
            setMessages((prev) => [
              ...prev,
              {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: 'Connection lost. Please try again.',
              },
            ])
          }
          resolve()
        }
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `I couldn't process that request. ${message}`,
        },
      ])
    } finally {
      setIsTyping(false)
      setCurrentStep(null)
    }
  }

  const handleAction = async (label: string) => {
    if (label.includes('Dispatch')) {
      haptic('Heavy')
      const latestCard = [...messages].reverse().find(m => m.missionCard)?.missionCard
      if (!latestCard) return
      navigate('/mission/progress', {
        state: {
          missionCard: {
            region: latestCard.region,
            crops: latestCard.crops,
            season: latestCard.season,
            focusAreas: latestCard.focusAreas,
            scaleEstimate: latestCard.scaleEstimate,
            description: `${latestCard.region} — ${latestCard.crops.join(', ')}`,
          },
        },
      })
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

  const lastActionMsgId = [...messages].reverse().find(m => m.actions)?.id

  return (
    <div
      className="flex flex-col h-[calc(100dvh-4rem-env(safe-area-inset-bottom,0px))]"
      onKeyDown={(e) => { if (e.key === 'Escape' && sidebarOpen) setSidebarOpen(false) }}
    >
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
        subtitle="Gemma 4 · 31B orchestrator + 26B agents"
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
      <div role="log" aria-label="Chat messages" aria-live="polite" className="flex-1 overflow-y-auto overscroll-none px-4 py-4 space-y-4 bg-surface">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start gap-2'}`}>
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-1">
                <Leaf size={14} className="text-primary" />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-primary text-white rounded-br-sm animate-slideInRight'
                  : 'bg-card text-text shadow-sm rounded-bl-sm animate-slideInLeft'
              }`}
            >
              {msg.role === 'user' ? (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              ) : (
                <MarkdownContent content={msg.content} />
              )}

              {/* Suggestion chips on the initial welcome message only */}
              {msg.id === '1' && messages.filter((m) => m.role === 'user').length === 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {[
                    { label: 'Casamance, Senegal', icon: '📍' },
                    { label: 'Huambo Province, Angola', icon: '📍' },
                    { label: 'Kano State, Nigeria', icon: '📍' },
                  ].map((chip) => (
                    <button
                      key={chip.label}
                      onClick={() => setInput(chip.label)}
                      className="flex items-center gap-1.5 text-xs bg-surface border border-surface-dark text-text-muted px-3 py-2 rounded-full hover:border-primary/40 hover:text-primary hover:bg-primary/5 transition-all whitespace-nowrap min-h-[36px]"
                    >
                      <span>{chip.icon}</span>
                      <span>{chip.label}</span>
                    </button>
                  ))}
                </div>
              )}

              {msg.missionCard && (
                <div className="mt-3 bg-surface rounded-lg p-3 space-y-2 text-xs">
                  <div className="flex items-center gap-1.5 pb-1 border-b border-surface-dark mb-1">
                    <FileText size={12} className="text-primary" />
                    <span className="font-heading font-bold text-[11px] text-text-muted uppercase tracking-wider">Mission Brief</span>
                  </div>
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
                  {msg.missionCard.scaleEstimate && (
                    <div className="flex items-center gap-2 pt-1.5 border-t border-surface-dark">
                      <span className="font-semibold text-text-muted">Scale:</span>
                      <span className="text-text">{msg.missionCard.scaleEstimate}</span>
                    </div>
                  )}
                </div>
              )}

              {msg.actions && (
                <div className="mt-3 flex flex-col gap-2">
                  <div className="flex gap-2 flex-wrap">
                    {msg.actions.map((a) => (
                      <button
                        key={a.label}
                        onClick={() => handleAction(a.label)}
                        disabled={msg.id !== lastActionMsgId}
                        className={`text-xs font-semibold px-4 py-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                          a.variant === 'primary'
                            ? 'bg-primary text-white hover:bg-primary-light min-h-[44px]'
                            : 'border border-text-muted text-text-muted hover:bg-surface-dark min-h-[44px]'
                        }`}
                      >
                        {a.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex justify-start gap-2">
            <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-1">
              <Leaf size={14} className="text-primary" />
            </div>
            <div className="bg-card text-text-muted rounded-xl rounded-bl-sm px-4 py-3 shadow-sm animate-fadeIn">
              <ThinkingBubble
                step={currentStep}
                mode="quick"
                insights={[]}
                stepLabels={{
                  planning: 'Planning your mission',
                  fallback: 'Switching to local model',
                }}
              />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="bg-card border-t border-surface-dark px-4 py-3">
        <div className="max-w-lg mx-auto flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder={editing ? 'Tell me what to change...' : 'Describe your mission...'}
            rows={1}
            className="flex-1 bg-surface rounded-lg px-4 py-2.5 text-base outline-none focus:ring-2 focus:ring-primary/30 resize-none leading-normal"
            style={{ maxHeight: '120px' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="bg-primary text-white p-2.5 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg disabled:opacity-40 hover:bg-primary-light transition-colors shrink-0 shadow-md disabled:shadow-none"
            aria-label="Send message"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}
