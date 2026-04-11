import { apiUrl } from './config'

/** Create an AbortController + timer that aborts after `ms` milliseconds. */
function withTimeout(ms: number): { signal: AbortSignal; clear: () => void } {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), ms)
  return { signal: controller.signal, clear: () => clearTimeout(timer) }
}

export interface ConversationSummary {
  id: string
  type: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface MessageData {
  role: 'user' | 'assistant'
  content: string
  image_path?: string | null
  metadata?: Record<string, unknown> | null
}

export interface ConversationDetail {
  id: string
  type: string
  title: string
  created_at: string
  updated_at: string
  messages: MessageData[]
  summary: string
}

export async function listConversations(type: 'field' | 'mission'): Promise<ConversationSummary[]> {
  const res = await fetch(apiUrl(`/conversations?type=${type}`))
  if (!res.ok) return []
  return res.json()
}

export async function createConversation(type: 'field' | 'mission', title?: string): Promise<ConversationDetail> {
  const res = await fetch(apiUrl('/conversations'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, title: title || 'New conversation' }),
  })
  if (!res.ok) throw new Error(`Failed to create conversation: ${res.status}`)
  return res.json()
}

export async function getConversation(id: string, type: 'field' | 'mission'): Promise<ConversationDetail> {
  const res = await fetch(apiUrl(`/conversations/${id}?type=${type}`))
  if (!res.ok) throw new Error(`Failed to get conversation: ${res.status}`)
  return res.json()
}

export async function saveConversation(
  id: string,
  type: 'field' | 'mission',
  messages: MessageData[],
  title?: string,
  summary?: string,
): Promise<void> {
  await fetch(apiUrl(`/conversations/${id}?type=${type}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, title, summary }),
  })
}

export interface PackSummary {
  pack_id: string
  name: string
  region: string
  crops: string[]
  diseases_count: number
  knowledge_entries: number
  sources: string[]
  loaded: boolean
}

export interface BrowseItem {
  id: string
  type: string
  title: string
  description: string
  badges: { label: string; color: string }[]
  details?: string[]
}

export interface BrowseResponse {
  count: number
  items: BrowseItem[]
}

export async function listPacks(): Promise<PackSummary[]> {
  const res = await fetch(apiUrl('/packs/'))
  if (!res.ok) return []
  return res.json()
}

export async function loadPack(packId: string): Promise<boolean> {
  const res = await fetch(apiUrl(`/packs/load/${packId}`), { method: 'POST' })
  return res.ok
}

export async function unloadPack(): Promise<boolean> {
  const res = await fetch(apiUrl('/packs/unload'), { method: 'POST' })
  return res.ok
}

export async function browseKnowledge(type: string = 'all', search: string = '', limit: number = 50): Promise<BrowseResponse> {
  const params = new URLSearchParams({ type, search, limit: String(limit) })
  const res = await fetch(apiUrl(`/packs/browse?${params}`))
  if (!res.ok) return { count: 0, items: [] }
  return res.json()
}

/** Upload a base64-encoded image and return the server file path. */
export async function uploadImageBase64(base64Data: string, format: string = 'jpeg'): Promise<string> {
  const timeout = withTimeout(15000)
  try {
    const res = await fetch(apiUrl('/upload/image/base64'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data: base64Data, format }),
      signal: timeout.signal,
    })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    const result = await res.json()
    return result.image_path
  } finally {
    timeout.clear()
  }
}

export interface MissionChatResponse {
  reply: string
  mission_card?: {
    region: string
    crops: string[]
    season: string
    focus_areas: string[]
    scale_estimate?: string
  }
}

export async function chatMission(message: string, conversationHistory: MessageData[], language?: string): Promise<MissionChatResponse> {
  const timeout = withTimeout(60000)
  try {
    const res = await fetch(apiUrl('/mission/chat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        language: language || undefined,
        conversation_history: conversationHistory.slice(0, -1).map(m => ({
          role: m.role,
          content: m.content,
        })),
      }),
      signal: timeout.signal,
    })
    if (!res.ok) throw new Error(`Mission chat failed: ${res.status}`)
    return res.json()
  } finally {
    timeout.clear()
  }
}

// ── Observations ────────────────────────────────────────────

export interface Observation {
  id: number
  timestamp: string
  type: 'disease_sighting' | 'crop_condition' | 'treatment_applied' | 'note'
  location: string | null
  details: string
  image_path: string | null
  synced: number
  crop_id: number | null
  severity_observed: string | null
}

export interface ObservationListResponse {
  observations: Observation[]
  total: number
  unsynced_count: number
}

export interface ObservationStats {
  total: number
  unsynced: number
  by_type: Record<string, number>
  recent: { type: string; details: string; timestamp: string }[]
}

export interface CreateObservationRequest {
  type: string
  details: string
  location?: string
  image_path?: string
}

export async function listObservations(type?: string, limit: number = 50): Promise<ObservationListResponse> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (type) params.set('type', type)
  const res = await fetch(apiUrl(`/observations/?${params}`))
  if (!res.ok) return { observations: [], total: 0, unsynced_count: 0 }
  return res.json()
}

export async function getObservationStats(): Promise<ObservationStats> {
  const res = await fetch(apiUrl('/observations/stats'))
  if (!res.ok) return { total: 0, unsynced: 0, by_type: {}, recent: [] }
  return res.json()
}

export async function summarizeObservations(limit: number = 20): Promise<{ summary: string; observation_count: number }> {
  const timeout = withTimeout(60000)
  try {
    const res = await fetch(apiUrl(`/observations/summary?limit=${limit}`), {
      method: 'POST',
      signal: timeout.signal,
    })
    if (!res.ok) throw new Error(`Summary failed: ${res.status}`)
    return res.json()
  } finally {
    timeout.clear()
  }
}

export async function saveConversationToJournal(
  messages: { role: string; content: string }[],
  imagePath: string | null = null,
): Promise<{ observation_id: number; summary: string }> {
  const timeout = withTimeout(60000)
  try {
    const res = await fetch(apiUrl('/chat/save-to-journal'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, image_path: imagePath }),
      signal: timeout.signal,
    })
    if (!res.ok) throw new Error(`Save to journal failed: ${res.status}`)
    return res.json()
  } finally {
    timeout.clear()
  }
}

export async function createObservation(data: CreateObservationRequest): Promise<{ observation_id: number; timestamp: string }> {
  const res = await fetch(apiUrl('/observations/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`Failed to create observation: ${res.status}`)
  return res.json()
}
