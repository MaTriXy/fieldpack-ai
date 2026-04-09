import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { Send, Camera, ChevronDown, Menu, AlertCircle, X, Leaf, FileText, Square, Database, MapPin, ChevronRight, WifiOff, Wifi, Smartphone, Loader2 } from 'lucide-react'
import MarkdownContent from '../components/MarkdownContent'
import TopBar from '../components/layout/TopBar'
import ChatSidebar from '../components/ChatSidebar'
import { useSwipeToOpen } from '../hooks/useSwipeToOpen'
import {
  listConversations,
  createConversation,
  getConversation,
  saveConversation,
  uploadImageBase64,
  listPacks,
  loadPack,
  type ConversationSummary,
  type MessageData,
  type PackSummary,
} from '../lib/api'
import { getWsUrl, isNative } from '../lib/config'
import { useBackendReachable } from '../hooks/useBackendReachable'
import {
  enqueueChatMessage,
  getQueuedChatMessages,
  clearChatMessageQueue,
  type QueuedChatMessage,
} from '../lib/offline-queue'
import ServerSettings, { ServerSettingsButton } from '../components/ServerSettings'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  image?: string
  diagnosis?: DiagnosisPreview
  sources?: { name: string; score: number }[]
  suggestions?: string[]
  _queued?: boolean
}

interface DiagnosisPreview {
  disease: string
  confidence: number
  severity: 'High' | 'Medium' | 'Low'
  pathogen: string
}

const PHOTO_ANALYSIS_PHASES = [
  'Analyzing photo...',
  'Identifying symptoms...',
  'Checking knowledge base...',
  'Generating diagnosis...',
]

function PhotoAnalysisOverlay() {
  const [phase, setPhase] = useState(0)

  useEffect(() => {
    const id = setInterval(() => {
      setPhase((p) => (p + 1) % PHOTO_ANALYSIS_PHASES.length)
    }, 2000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="absolute inset-0 rounded-lg overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
      <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
        <div className="text-center px-3">
          <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-white text-xs font-medium leading-snug">
            {PHOTO_ANALYSIS_PHASES[phase]}
          </p>
        </div>
      </div>
    </div>
  )
}

// Maps backend step names to display labels
const STEP_LABELS: Record<string, string> = {
  classifying: 'Classifying',
  routing: 'Routing',
  evaluating: 'Evaluating',
  crafting: 'Crafting Query',
  searching: 'Searching',
  reranking: 'Reranking',
  expanding: 'Expanding Search',
  generating: 'Generating',
  saving: 'Saving Observation',
}

// Ordered steps for the progress dots
const STEP_ORDER = ['classifying', 'routing', 'searching', 'reranking', 'generating']

function deriveTitle(firstMessage: string): string {
  const cleaned = firstMessage.replace(/\n/g, ' ').trim()
  if (cleaned.length <= 50) return cleaned
  const truncated = cleaned.slice(0, 50)
  const lastSpace = truncated.lastIndexOf(' ')
  return (lastSpace > 20 ? truncated.slice(0, lastSpace) : truncated) + '...'
}

function messagesToApi(messages: Message[]): MessageData[] {
  return messages.filter((m) => !m._queued).map((m) => ({
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
  const haptic = (style: string = 'Medium') =>
    isNative() && import('@capacitor/haptics').then(m =>
      m.Haptics.impact({ style: m.ImpactStyle[style as keyof typeof m.ImpactStyle] })
    ).catch(() => {})

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [currentStep, setCurrentStep] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [showSources, setShowSources] = useState<string | null>(null)
  const [wsError, setWsError] = useState<string | null>(null)

  // Offline mode
  const { reachable } = useBackendReachable()
  const [offlineMode, setOfflineMode] = useState(false)
  const [queuedMessages, setQueuedMessages] = useState<QueuedChatMessage[]>([])
  const [showSendQueueBanner, setShowSendQueueBanner] = useState(false)
  const [sendingQueue, setSendingQueue] = useState(false)
  const prevReachable = useRef(false)
  const reachableRef = useRef(false)
  const pendingQueueBanner = useRef(false)

  // Conversation state
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [sidebarLoading, setSidebarLoading] = useState(false)

  // Pipeline context threaded back to backend on each turn
  const pipelineHistory = useRef<Record<string, unknown>[]>([])
  const pipelineSummary = useRef('')

  // Pack status
  const [packInfo, setPackInfo] = useState<{ name: string; region: string; crops: string[]; diseases_count: number } | null>(null)
  const [packLoading, setPackLoading] = useState(true)
  const [packError, setPackError] = useState<string | null>(null)
  const [availablePacks, setAvailablePacks] = useState<PackSummary[]>([])

  // Server settings modal (native only)
  const [showServerSettings, setShowServerSettings] = useState(false)

  // Pending photo to attach to next message
  const [pendingImage, setPendingImage] = useState<{ base64: string; format: string; preview: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const bottomRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const scrollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isStreamingRef = useRef(false)
  const skipNextSave = useRef(false)
  const pendingSourcesRef = useRef<{ name: string; score: number }[] | null>(null)
  const reconnectAttempts = useRef(0)
  const MAX_RECONNECT_ATTEMPTS = 5
  const navigate = useNavigate()
  const location = useLocation()

  const openSidebar = useCallback(() => setSidebarOpen(true), [])
  useSwipeToOpen(openSidebar)

  // Fetch pack status on mount
  useEffect(() => {
    listPacks().then(packs => {
      setAvailablePacks(packs)
      const loaded = packs.find(p => p.loaded)
      if (loaded) {
        setPackInfo({ name: loaded.name, region: loaded.region, crops: loaded.crops, diseases_count: loaded.diseases_count })
      }
      setPackLoading(false)
    }).catch(() => setPackLoading(false))
  }, [])

  // Keep reachableRef in sync so connectWs closure reads latest value
  useEffect(() => { reachableRef.current = reachable }, [reachable])

  // WebSocket connection management
  const connectWs = useCallback(() => {
    const rs = wsRef.current?.readyState
    if (rs === WebSocket.OPEN || rs === WebSocket.CONNECTING) return

    if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
      setWsError('Could not connect to server. Click to retry.')
      return
    }

    const ws = new WebSocket(getWsUrl())

    ws.onopen = () => {
      reconnectAttempts.current = 0
      setWsError(null)
      if (pendingQueueBanner.current) {
        pendingQueueBanner.current = false
        setShowSendQueueBanner(true)
      }
    }

    ws.onmessage = (event) => {
      let data: Record<string, unknown>
      try {
        data = JSON.parse(event.data)
      } catch {
        setWsError('Received invalid data from server')
        setStreamingContent('')
        setCurrentStep(null)
        isStreamingRef.current = false
        setIsStreaming(false)
        return
      }

      switch (data.type) {
        case 'status':
          setCurrentStep(data.step as string)
          break

        case 'token':
          setStreamingContent((prev) => prev + (data.content as string))
          break

        case 'sources':
          // Store sources — will attach to the assistant message on done
          pendingSourcesRef.current = ((data.sources as { title: string; score: number }[]) || []).map(
            (s) => ({ name: s.title, score: s.score })
          )
          break

        case 'answer_done':
          // Token stream complete — generating step done
          setCurrentStep(null)
          break

        case 'done': {
          // Thread conversation context for next turn
          pipelineHistory.current = (data.conversation_history as Record<string, unknown>[]) || []
          pipelineSummary.current = (data.conversation_summary as string) || ''

          const finalAnswer = (data.final_answer as string) || ''
          const observationStats = data.observation_stats as Record<string, unknown> | null

          // Build the assistant message
          let content = finalAnswer
          if (!content && observationStats) {
            content = `Observation saved. (${(observationStats as Record<string, unknown>).count || 1} total observations logged)`
          }
          if (!content) {
            content = 'I processed your request but could not generate a response. Please try again.'
          }

          const sources = pendingSourcesRef.current
          pendingSourcesRef.current = null

          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              role: 'assistant',
              content,
              sources: sources || undefined,
            },
          ])
          setStreamingContent('')
          setCurrentStep(null)
          isStreamingRef.current = false
          setIsStreaming(false)
          break
        }

        case 'error':
          setWsError(data.message as string)
          // Show error inline in chat if we were mid-stream
          if (isStreamingRef.current) {
            setMessages((prev) => [
              ...prev,
              {
                id: Date.now().toString(),
                role: 'assistant',
                content: `Error: ${data.message}`,
              },
            ])
          }
          setStreamingContent('')
          setCurrentStep(null)
          isStreamingRef.current = false
          setIsStreaming(false)
          break
      }
    }

    ws.onclose = () => {
      // If wsRef was already nulled (e.g. by stop button or unmount), skip reconnect
      if (wsRef.current !== ws) return
      wsRef.current = null
      // Auto-reconnect with exponential backoff
      reconnectAttempts.current += 1
      if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(2000 * Math.pow(2, reconnectAttempts.current - 1), 16000)
        setTimeout(() => {
          if (!wsRef.current) connectWs()
        }, delay)
      } else {
        if (!reachableRef.current) {
          setOfflineMode(true)
          setWsError(null)
          setQueuedMessages(getQueuedChatMessages())
        } else {
          setWsError('Could not connect to server. Click to retry.')
        }
      }
    }

    ws.onerror = () => {
      setWsError('Connection lost. Reconnecting...')
    }

    wsRef.current = ws
  }, [])

  // Connect WebSocket only after a pack is loaded, disconnect on unmount
  useEffect(() => {
    if (!packInfo) return
    connectWs()
    return () => {
      const ws = wsRef.current
      if (ws) {
        wsRef.current = null // prevent reconnect
        ws.close()
      }
    }
  }, [connectWs, packInfo])

  // Reconnect when backend becomes reachable again while in offline mode
  useEffect(() => {
    if (reachable && !prevReachable.current && offlineMode) {
      if (queuedMessages.length > 0) {
        pendingQueueBanner.current = true
      }
      setOfflineMode(false)
      reconnectAttempts.current = 0
      connectWs()
    }
    prevReachable.current = reachable
  }, [reachable, offlineMode, queuedMessages.length, connectWs])

  // Pre-warm the Capacitor camera module on native so first launch is instant
  useEffect(() => {
    if (isNative()) import('@capacitor/camera').catch(() => {})
  }, [])

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

  // Auto-scroll on new messages or streaming tokens (debounced to avoid layout thrash)
  useEffect(() => {
    if (scrollTimerRef.current) clearTimeout(scrollTimerRef.current)
    scrollTimerRef.current = setTimeout(() => {
      bottomRef.current?.scrollIntoView({ behavior: 'instant' })
    }, 80)
  }, [messages, streamingContent])

  // Cleanup save timer and scroll timer on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current)
      if (scrollTimerRef.current) clearTimeout(scrollTimerRef.current)
    }
  }, [])

  useEffect(() => {
    if (packInfo) textareaRef.current?.focus()
  }, [packInfo])

  // Auto-save after messages change (debounced)
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
      saveConversation(conversationId, 'field', messagesToApi(messages), title, pipelineSummary.current || undefined)
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
      pipelineHistory.current = []
      pipelineSummary.current = ''
      setSidebarOpen(false)
    } catch {
      setConversationId(null)
      setMessages([])
      setInput('')
      pipelineHistory.current = []
      pipelineSummary.current = ''
      setSidebarOpen(false)
    }
  }

  const handleSelectConversation = async (id: string) => {
    try {
      const conv = await getConversation(id, 'field')
      skipNextSave.current = true
      setConversationId(conv.id)
      setMessages(apiToMessages(conv.messages))
      // Reset pipeline context — loaded conversation starts fresh context
      pipelineHistory.current = []
      pipelineSummary.current = ''
      setSidebarOpen(false)
    } catch {
      // Conversation may have been deleted
    }
  }

  const handleCamera = async () => {
    if (isNative()) {
      // Capacitor native camera
      try {
        const { Camera: CapCamera, CameraResultType, CameraSource } = await import('@capacitor/camera')
        const photo = await CapCamera.getPhoto({
          quality: 80,
          allowEditing: false,
          resultType: CameraResultType.Base64,
          source: CameraSource.Camera,
          width: 1024, // Cap resolution to reduce payload size
          height: 1024,
        })
        if (photo.base64String) {
          setPendingImage({
            base64: photo.base64String,
            format: photo.format || 'jpeg',
            preview: `data:image/${photo.format || 'jpeg'};base64,${photo.base64String}`,
          })
        }
      } catch {
        // User cancelled or camera unavailable
      }
    } else {
      // Web fallback: trigger file input
      fileInputRef.current?.click()
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // Strip data:image/...;base64, prefix
      const base64 = result.split(',')[1]
      const format = file.type.split('/')[1] || 'jpeg'
      setPendingImage({ base64, format, preview: result })
    }
    reader.readAsDataURL(file)
    // Reset so same file can be selected again
    e.target.value = ''
  }

  const handleSend = async () => {
    if ((!input.trim() && !pendingImage) || isStreaming) return

    const messageText = input.trim() || (pendingImage ? 'What disease does this plant have?' : '')
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: messageText,
      image: pendingImage?.preview,
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    // ── OFFLINE PATH ──
    if (offlineMode || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      const queued = enqueueChatMessage({
        content: messageText,
        image_base64: pendingImage?.base64 || null,
        image_format: pendingImage?.format || null,
      })
      setQueuedMessages(prev => [...prev, queued])
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        _queued: true,
      }])
      setPendingImage(null)
      return
    }

    // ── ONLINE PATH ──
    isStreamingRef.current = true
    setIsStreaming(true)
    setWsError(null)
    setStreamingContent('')
    setCurrentStep(null)

    let imagePath: string | null = null
    if (pendingImage) {
      try {
        imagePath = await uploadImageBase64(pendingImage.base64, pendingImage.format)
      } catch {
        setWsError('Failed to upload image. Check server connection.')
        setMessages((prev) => prev.filter((m) => m.id !== userMsg.id))
        isStreamingRef.current = false
        setIsStreaming(false)
        return
      }
      setPendingImage(null)
    }

    if (!conversationId) {
      createConversation('field', deriveTitle(messageText))
        .then((conv) => setConversationId(conv.id))
        .catch(() => {})
    }

    wsRef.current.send(JSON.stringify({
      message: messageText,
      image_path: imagePath,
      conversation_history: pipelineHistory.current,
      conversation_summary: pipelineSummary.current,
      session_id: conversationId,
    }))
  }

  // ── Send queued messages as one bundled message ──
  const handleSendQueue = async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

    setSendingQueue(true)
    setShowSendQueueBanner(false)

    // Remove all queued sentinel messages
    setMessages(prev => prev.filter(m => !m._queued))

    // Upload first image if any
    let firstImagePath: string | null = null
    for (const msg of queuedMessages) {
      if (msg.image_base64 && !firstImagePath) {
        try {
          firstImagePath = await uploadImageBase64(msg.image_base64, msg.image_format || 'jpeg')
        } catch {
          // continue without image
        }
        break
      }
    }

    const combined = queuedMessages.map(q => q.content).join('\n\n---\n\n')
    const prefix = queuedMessages.length > 1
      ? `[I recorded these ${queuedMessages.length} observations/questions while offline. Please address each one:]\n\n`
      : ''

    wsRef.current.send(JSON.stringify({
      message: prefix + combined,
      image_path: firstImagePath,
      conversation_history: pipelineHistory.current,
      conversation_summary: pipelineSummary.current,
      session_id: conversationId,
    }))

    clearChatMessageQueue()
    setQueuedMessages([])
    setSendingQueue(false)
    isStreamingRef.current = true
    setIsStreaming(true)
  }

  // Compute which step index we're on for the progress dots
  const stepIndex = currentStep ? STEP_ORDER.indexOf(currentStep) : -1
  // Map non-standard steps (evaluating, crafting, expanding, saving) to nearest dot
  const effectiveStepIndex = stepIndex >= 0
    ? stepIndex
    : currentStep === 'evaluating' ? 1
    : currentStep === 'crafting' ? 2
    : currentStep === 'expanding' ? 2
    : currentStep === 'saving' ? 4
    : 0

  const severityColor = (s: string) =>
    s === 'High'
      ? 'bg-tertiary/10 text-tertiary'
      : s === 'Medium'
        ? 'bg-secondary/10 text-secondary'
        : 'bg-primary/10 text-primary'

  // ID of the most recent user message — used to show photo analysis overlay
  const lastUserMsgId = messages.findLast((m) => m.role === 'user')?.id

  // Find last assistant message's suggestions for chip display (avoid O(n) reverse per render)
  let lastSuggestions: string[] | undefined
  if (!isStreaming && messages.length > 0) {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'assistant' && messages[i].suggestions) {
        lastSuggestions = messages[i].suggestions
        break
      }
    }
  }

  if (!packInfo) {
    return (
      <div className="flex flex-col h-[calc(100dvh-4rem-env(safe-area-inset-bottom,0px))]">
        <TopBar title="Field AI" back backTo="/" />
        <div className="flex-1 flex flex-col items-center justify-center px-6 bg-surface animate-fadeIn">
          {packLoading ? (
            <>
              <div className="w-12 h-12 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-sm text-text-muted">Loading pack...</p>
            </>
          ) : (
            <>
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <Database size={28} className="text-primary" />
              </div>
              <h2 className="font-heading font-bold text-xl text-text text-center">Choose a Knowledge Pack</h2>
              <p className="text-sm text-text-muted text-center mt-2 max-w-[280px]">
                Select a region&rsquo;s offline field guide to start diagnosing crops
              </p>
              {packError && (
                <p className="text-xs text-tertiary mt-2">{packError}</p>
              )}
              <div className="mt-6 w-full max-w-sm space-y-3">
                {availablePacks.map(pack => (
                  <button
                    key={pack.pack_id}
                    disabled={packLoading}
                    onClick={async () => {
                      setPackLoading(true)
                      setPackError(null)
                      try {
                        const ok = await loadPack(pack.pack_id)
                        if (ok) {
                          setPackInfo({ name: pack.name, region: pack.region, crops: pack.crops, diseases_count: pack.diseases_count })
                        } else {
                          setPackError('Failed to load pack. Check that the server is running.')
                        }
                      } catch {
                        setPackError('Could not reach the server.')
                      }
                      setPackLoading(false)
                    }}
                    className="w-full bg-card rounded-xl p-4 border border-surface-dark shadow-sm text-left hover:border-primary/30 transition-colors disabled:opacity-50"
                  >
                    <div className="flex items-center gap-3">
                      <div className="bg-primary/10 rounded-lg p-2.5">
                        <MapPin size={18} className="text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-heading font-bold text-sm text-text">{pack.name}</p>
                        <p className="text-xs text-text-muted mt-0.5">{pack.region} · {pack.crops.length} crops · {pack.diseases_count} diseases</p>
                      </div>
                      <ChevronRight size={16} className="text-text-muted" />
                    </div>
                  </button>
                ))}
                {availablePacks.length === 0 && (
                  <div className="text-center py-8">
                    <p className="text-sm text-text-muted">No packs available.</p>
                    <Link to="/mission" className="text-sm text-primary font-semibold mt-2 inline-block">Create one &rarr;</Link>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    )
  }

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
        title="Field AI"
        subtitle="Agentic RAG · Gemma 4 E2B"
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
        rightAction={<ServerSettingsButton onClick={() => setShowServerSettings(true)} />}
      />

      {/* Pack context banner */}
      {packInfo && (
        <div className="bg-primary/5 border-b border-surface-dark px-4 py-2">
          <div className="max-w-lg mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <MapPin size={12} className="text-primary shrink-0" />
              <span className="text-xs font-medium text-text truncate">{packInfo.region}</span>
              <span className="text-xs text-text-muted">·</span>
              <span className="text-xs text-text-muted">{packInfo.crops.length} crops</span>
              <span className="text-xs text-text-muted">·</span>
              <span className="text-xs text-text-muted">{packInfo.diseases_count} diseases</span>
            </div>
            <Link to="/packs" className="text-xs text-primary font-medium hover:underline shrink-0">
              Change
            </Link>
          </div>
        </div>
      )}

      {/* Error banner */}
      {wsError && (
        <div className="bg-tertiary/10 border-b border-tertiary/20 px-4 py-2 flex items-center gap-2">
          <AlertCircle size={14} className="text-tertiary shrink-0" />
          <span className="text-xs text-tertiary">{wsError}</span>
          {reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS && (
            <button
              onClick={() => {
                reconnectAttempts.current = 0
                setWsError(null)
                connectWs()
              }}
              className="text-xs font-semibold text-tertiary underline hover:text-tertiary/80"
            >
              Retry
            </button>
          )}
          <button
            onClick={() => setWsError(null)}
            className="ml-auto text-xs text-tertiary/60 hover:text-tertiary"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Offline mode banner */}
      {offlineMode && (
        <div className="mx-4 mt-2 bg-surface-dark rounded-xl px-4 py-2.5 flex items-center gap-2">
          <WifiOff size={14} className="text-text-muted flex-shrink-0" />
          <div className="flex-1">
            <span className="text-xs font-medium text-text">Offline Mode</span>
            <span className="text-xs text-text-muted ml-1">— messages will send when connected</span>
          </div>
        </div>
      )}

      {/* Send queued messages banner */}
      {showSendQueueBanner && !sendingQueue && queuedMessages.length > 0 && (
        <div className="mx-4 mt-2 bg-secondary/10 border border-secondary/20 rounded-xl px-4 py-3 flex items-center justify-between animate-slideUp">
          <div className="flex items-center gap-2">
            <Wifi size={14} className="text-secondary" />
            <span className="text-xs font-medium text-text">
              {queuedMessages.length} message{queuedMessages.length !== 1 ? 's' : ''} ready to send
            </span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleSendQueue}
              className="text-xs font-semibold text-white bg-primary px-3 py-1.5 rounded-lg min-h-[32px]"
            >
              Send All
            </button>
            <button
              onClick={() => { clearChatMessageQueue(); setQueuedMessages([]); setMessages(prev => prev.filter(m => !m._queued)); setShowSendQueueBanner(false) }}
              className="text-xs font-medium text-text-muted px-2 py-1.5"
            >
              Discard
            </button>
          </div>
        </div>
      )}

      {/* Sending progress banner */}
      {sendingQueue && (
        <div className="mx-4 mt-2 bg-primary/10 border border-primary/20 rounded-xl px-4 py-3 flex items-center gap-2 animate-slideUp">
          <Loader2 size={14} className="animate-spin text-primary" />
          <span className="text-xs font-medium text-primary">Sending queued messages...</span>
        </div>
      )}

      {/* Pipeline status */}
      {isStreaming && currentStep && (
        <div className="bg-primary-dark">
          <div className="h-[3px] bg-white/10 w-full overflow-hidden">
            <div
              className="h-full bg-secondary transition-all duration-500 ease-out"
              style={{ width: `${Math.max(((effectiveStepIndex + 1) / STEP_ORDER.length) * 100, 10)}%` }}
            />
          </div>
          <div className="px-4 py-1.5">
            <div className="max-w-lg mx-auto flex items-center gap-2">
              <span className="text-xs text-white/85">
                {STEP_LABELS[currentStep] || currentStep}...
              </span>
              <span className="text-xs text-white/65 ml-auto">
                Step {effectiveStepIndex + 1}/{STEP_ORDER.length}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Chat */}
      <div role="log" aria-label="Chat messages" aria-live="polite" className="flex-1 overflow-y-auto overscroll-none px-4 py-4 space-y-4 bg-surface">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full gap-5 animate-fadeIn px-2">
            {/* Hero icon with layered gradient rings */}
            <div className="relative flex items-center justify-center">
              <div className="absolute w-28 h-28 rounded-full bg-primary/5" />
              <div className="absolute w-20 h-20 rounded-full bg-primary/8" />
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary to-primary-light flex items-center justify-center shadow-lg shadow-primary/20">
                <Leaf size={32} className="text-white" />
              </div>
            </div>
            <div className="text-center">
              <p className="font-heading font-bold text-xl text-text">Ask about your crops</p>
              <p className="text-sm text-text-muted mt-1.5 max-w-[280px] leading-relaxed">
                Describe symptoms, upload a photo, or ask about farming practices — works fully offline.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2.5 w-full max-w-[320px]">
              {[
                {
                  icon: '📸',
                  label: 'Diagnose a plant',
                  desc: 'Photo or symptom description',
                  prompt: 'What disease does this plant have?',
                  accent: 'border-l-4 border-l-primary',
                },
                {
                  icon: '🐛',
                  label: 'Pest control',
                  desc: 'Identify and treat infestations',
                  prompt: 'How do I control pests on my cassava?',
                  accent: 'border-l-4 border-l-tertiary',
                },
                {
                  icon: '🌱',
                  label: 'Planting guide',
                  desc: 'Timing and spacing advice',
                  prompt: 'When should I plant cassava in Casamance, Senegal?',
                  accent: 'border-l-4 border-l-secondary',
                },
                {
                  icon: '💧',
                  label: 'Irrigation advice',
                  desc: 'Water management methods',
                  prompt: 'What irrigation methods work best for rice in Casamance, Senegal?',
                  accent: 'border-l-4 border-l-primary-light',
                },
              ].map((card) => (
                <button
                  key={card.label}
                  onClick={() => { setInput(card.prompt); }}
                  className={`${card.accent} bg-card rounded-xl p-3.5 text-left shadow-sm border border-surface-dark hover:shadow-md hover:scale-[1.02] transition-all min-h-[44px]`}
                >
                  <span className="text-2xl">{card.icon}</span>
                  <p className="text-xs font-semibold text-text mt-1.5 leading-tight">{card.label}</p>
                  <p className="text-[11px] text-text-muted mt-0.5 leading-tight">{card.desc}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          msg._queued ? (
            <div key={msg.id} className="flex justify-start gap-2">
              <div className="w-7 h-7 rounded-full bg-secondary/10 flex items-center justify-center flex-shrink-0 mt-1">
                <Smartphone size={14} className="text-secondary" />
              </div>
              <div className="bg-surface text-text-muted rounded-xl rounded-bl-sm px-4 py-2.5 border border-dashed border-secondary/30 animate-slideInLeft">
                <span className="text-xs font-medium text-secondary">Queued</span>
                <span className="text-xs text-text-muted ml-1">— will send when connected</span>
              </div>
            </div>
          ) : (
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
              {msg.image && (
                <div className="mb-2 rounded-lg overflow-hidden relative">
                  {msg.image.startsWith('data:') ? (
                    <img src={msg.image} alt="Attached plant photo" className="max-h-48 rounded-lg object-cover w-full" />
                  ) : (
                    <div className="bg-surface-dark h-32 flex items-center justify-center rounded-lg">
                      <Camera size={24} className="text-text-muted" />
                      <span className="ml-2 text-xs text-text-muted">Photo attached</span>
                    </div>
                  )}
                  {isStreaming && msg.id === lastUserMsgId && (
                    <PhotoAnalysisOverlay />
                  )}
                </div>
              )}

              {msg.role === 'user' ? (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              ) : (
                <MarkdownContent content={msg.content} />
              )}

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
                    onClick={() => navigate('/field/diagnosis', { state: { image: msg.image } })}
                    className="mt-2 text-xs font-semibold bg-secondary text-white px-3 py-2.5 rounded-lg hover:bg-secondary-light transition-colors min-h-[44px]"
                  >
                    View Full Diagnosis →
                  </button>
                </div>
              )}

              {msg.sources && (
                <div className="mt-2">
                  <button
                    onClick={() => setShowSources(showSources === msg.id ? null : msg.id)}
                    className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text py-1"
                  >
                    <FileText size={12} className="shrink-0" />
                    <span>{msg.sources.length} sources consulted</span>
                    <ChevronDown
                      size={12}
                      className={`transition-transform ${showSources === msg.id ? 'rotate-180' : ''}`}
                    />
                  </button>
                  {showSources === msg.id && (
                    <div className="mt-1.5 space-y-1.5">
                      {msg.sources.map((s) => (
                        <div key={s.name} className="flex items-center gap-2 text-xs text-text-muted">
                          <FileText size={10} className="shrink-0" />
                          <span className="flex-1 truncate">{s.name}</span>
                          <span className={`w-2 h-2 rounded-full shrink-0 ${s.score >= 0.7 ? 'bg-primary' : s.score >= 0.4 ? 'bg-secondary' : 'bg-text-muted/30'}`} />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
          )))}

        {/* Streaming bubble — shows live tokens as they arrive */}
        {isStreaming && (
          <div className="flex justify-start gap-2">
            <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-1">
              <Leaf size={14} className="text-primary" />
            </div>
            <div className="max-w-[80%] bg-card rounded-xl rounded-bl-sm px-4 py-3 text-sm shadow-sm animate-fadeIn">
              {streamingContent ? (
                <div className="leading-relaxed">
                  <MarkdownContent content={streamingContent} />
                  <span className="inline-block w-0.5 h-4 bg-primary ml-0.5 animate-blink align-text-bottom" />
                </div>
              ) : (
                <div className="flex gap-1.5 items-center h-5">
                  <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounceTyping" />
                  <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounceTyping [animation-delay:0.15s]" />
                  <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounceTyping [animation-delay:0.3s]" />
                </div>
              )}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="bg-card border-t border-surface-dark px-4 py-3">
        <div className="max-w-lg mx-auto">
          {/* Suggestion chips from last assistant message */}
          {lastSuggestions && (
            <div className="mb-2 flex gap-2 overflow-x-auto scrollbar-hide pb-1">
              {lastSuggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => setInput(s)}
                  className="shrink-0 text-xs bg-surface text-text px-3 py-2.5 rounded-full border border-surface-dark hover:bg-surface-dark hover:border-primary/30 transition-colors whitespace-nowrap min-h-[44px]"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
          {/* Image preview */}
          {pendingImage && (
            <div className="mb-2 relative inline-block">
              <img src={pendingImage.preview} alt="Attached" className="h-20 rounded-lg object-cover" />
              <button
                onClick={() => setPendingImage(null)}
                className="absolute -top-1.5 -right-1.5 bg-tertiary text-white rounded-full p-0.5"
                aria-label="Remove photo"
              >
                <X size={14} />
              </button>
            </div>
          )}
          <div className="flex items-end gap-2">
            <button
              onClick={() => { haptic('Medium'); handleCamera() }}
              className="w-11 h-11 rounded-full bg-surface border border-surface-dark flex items-center justify-center text-text-muted hover:text-primary hover:border-primary/30 hover:bg-primary/5 transition-all shrink-0"
              aria-label="Attach photo"
            >
              <Camera size={20} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFileSelect}
              className="hidden"
            />
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                // Auto-grow
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder={pendingImage ? 'Describe the issue (optional)...' : 'Ask about your crops...'}
              rows={1}
              className="flex-1 bg-surface rounded-lg px-4 py-2.5 text-base outline-none focus:ring-2 focus:ring-primary/30 resize-none leading-normal"
              style={{ maxHeight: '120px' }}
            />
            {isStreaming ? (
              <button
                onClick={() => {
                  haptic('Medium')
                  // Save partial content as a message before stopping
                  if (streamingContent.trim()) {
                    const sources = pendingSourcesRef.current
                    pendingSourcesRef.current = null
                    setMessages((prev) => [
                      ...prev,
                      {
                        id: Date.now().toString(),
                        role: 'assistant',
                        content: streamingContent,
                        sources: sources || undefined,
                      },
                    ])
                  }
                  // Null the ref BEFORE closing — onclose checks wsRef !== ws and skips
                  const ws = wsRef.current
                  wsRef.current = null
                  ws?.close()
                  isStreamingRef.current = false
                  setIsStreaming(false)
                  setStreamingContent('')
                  setCurrentStep(null)
                  // Reconnect a fresh socket (onclose won't fire a competing reconnect)
                  reconnectAttempts.current = 0
                  setTimeout(() => connectWs(), 300)
                }}
                className="bg-tertiary text-white p-2.5 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg hover:bg-tertiary-light transition-colors shrink-0"
                aria-label="Stop generating"
              >
                <Square size={16} />
              </button>
            ) : offlineMode ? (
              <button
                onClick={() => { haptic('Light'); handleSend() }}
                disabled={!input.trim() && !pendingImage}
                className="bg-secondary text-white p-2.5 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg disabled:opacity-40 hover:bg-secondary-light transition-colors shrink-0 shadow-md disabled:shadow-none"
                aria-label="Queue message"
              >
                <Smartphone size={20} />
              </button>
            ) : (
              <button
                onClick={() => { haptic('Light'); handleSend() }}
                disabled={!input.trim() && !pendingImage}
                className="bg-primary text-white p-2.5 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg disabled:opacity-40 hover:bg-primary-light transition-colors shrink-0 shadow-md disabled:shadow-none"
                aria-label="Send message"
              >
                <Send size={18} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Server settings modal (native only) */}
      {showServerSettings && (
        <ServerSettings onClose={() => setShowServerSettings(false)} />
      )}
    </div>
  )
}
