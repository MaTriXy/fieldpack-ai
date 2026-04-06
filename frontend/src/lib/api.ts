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
  const res = await fetch(`/api/conversations?type=${type}`)
  if (!res.ok) return []
  return res.json()
}

export async function createConversation(type: 'field' | 'mission', title?: string): Promise<ConversationDetail> {
  const res = await fetch('/api/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, title: title || 'New conversation' }),
  })
  if (!res.ok) throw new Error(`Failed to create conversation: ${res.status}`)
  return res.json()
}

export async function getConversation(id: string, type: 'field' | 'mission'): Promise<ConversationDetail> {
  const res = await fetch(`/api/conversations/${id}?type=${type}`)
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
  await fetch(`/api/conversations/${id}?type=${type}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, title, summary }),
  })
}
