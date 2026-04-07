import { apiUrl } from './config'

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
  const res = await fetch(apiUrl('/upload/image/base64'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: base64Data, format }),
  })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  const result = await res.json()
  return result.image_path
}
