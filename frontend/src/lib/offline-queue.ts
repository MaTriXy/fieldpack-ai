import { uploadImageBase64, createObservation } from './api'

const QUEUE_KEY = 'fieldpack_offline_queue'

export interface QueuedObservation {
  id: string
  type: string
  details: string
  location: string | null
  image_base64: string | null
  image_format: string | null
  created_at: string
}

export interface QueuedChatMessage {
  id: string
  content: string
  image_base64: string | null
  image_format: string | null
  created_at: string
}

interface OfflineQueue {
  observations: QueuedObservation[]
  chat_messages: QueuedChatMessage[]
}

function getQueue(): OfflineQueue {
  try {
    const raw = localStorage.getItem(QUEUE_KEY)
    if (!raw) return { observations: [], chat_messages: [] }
    const parsed = JSON.parse(raw) as OfflineQueue
    if (!parsed.chat_messages) parsed.chat_messages = []
    return parsed
  } catch {
    return { observations: [], chat_messages: [] }
  }
}

function setQueue(queue: OfflineQueue): void {
  try {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue))
  } catch {
    throw new Error('Storage full — connect to the server and sync before adding more offline data.')
  }
  // Notify same-tab listeners (native storage event only fires cross-tab)
  window.dispatchEvent(new Event('storage'))
}

export function enqueueObservation(
  obs: Omit<QueuedObservation, 'id' | 'created_at'>,
): QueuedObservation {
  const full: QueuedObservation = {
    ...obs,
    id: crypto.randomUUID(),
    created_at: new Date().toISOString(),
  }
  const queue = getQueue()
  queue.observations.push(full)
  setQueue(queue)
  return full
}

export function dequeueObservation(id: string): void {
  const queue = getQueue()
  queue.observations = queue.observations.filter(o => o.id !== id)
  setQueue(queue)
}

export function getQueuedObservations(): QueuedObservation[] {
  return getQueue().observations
}

export function getQueuedObservationCount(): number {
  return getQueue().observations.length
}

// ── Chat message queue ──

export function enqueueChatMessage(
  msg: Omit<QueuedChatMessage, 'id' | 'created_at'>,
): QueuedChatMessage {
  const full: QueuedChatMessage = {
    ...msg,
    id: crypto.randomUUID(),
    created_at: new Date().toISOString(),
  }
  const queue = getQueue()
  queue.chat_messages.push(full)
  setQueue(queue)
  return full
}

export function dequeueChatMessage(id: string): void {
  const queue = getQueue()
  queue.chat_messages = queue.chat_messages.filter(m => m.id !== id)
  setQueue(queue)
}

export function getQueuedChatMessages(): QueuedChatMessage[] {
  return getQueue().chat_messages
}

export function clearChatMessageQueue(): void {
  const queue = getQueue()
  queue.chat_messages = []
  setQueue(queue)
}

export function getQueuedChatMessageCount(): number {
  return getQueue().chat_messages.length
}

// ── Observation queue flush ──

let flushing = false

export async function flushObservationQueue(
  onProgress?: (synced: number, total: number) => void,
): Promise<{ synced: number; failed: number }> {
  if (flushing) return { synced: 0, failed: 0 }
  flushing = true
  try {
    return await _doFlush(onProgress)
  } finally {
    flushing = false
  }
}

async function _doFlush(
  onProgress?: (synced: number, total: number) => void,
): Promise<{ synced: number; failed: number }> {
  const queue = getQueue()
  if (queue.observations.length === 0) return { synced: 0, failed: 0 }

  let synced = 0
  let failed = 0
  const total = queue.observations.length

  for (const obs of queue.observations) {
    try {
      let imagePath: string | undefined
      if (obs.image_base64) {
        imagePath = await uploadImageBase64(obs.image_base64, obs.image_format || 'jpeg')
      }
      await createObservation({
        type: obs.type,
        details: obs.details,
        location: obs.location || undefined,
        image_path: imagePath,
      })
      dequeueObservation(obs.id)
      synced++
    } catch {
      failed++
    }
    onProgress?.(synced, total)
  }
  return { synced, failed }
}
