import { Plus, MessageSquare, X } from 'lucide-react'
import type { ConversationSummary } from '../lib/api'

interface ChatSidebarProps {
  isOpen: boolean
  onClose: () => void
  conversations: ConversationSummary[]
  activeId: string | null
  onSelect: (id: string) => void
  onNewChat: () => void
  isLoading: boolean
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  if (isNaN(diff)) return iso
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days}d ago`
  return new Date(iso).toLocaleDateString()
}

export default function ChatSidebar({
  isOpen,
  onClose,
  conversations,
  activeId,
  onSelect,
  onNewChat,
  isLoading,
}: ChatSidebarProps) {
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') onClose()
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-[60] bg-black/40 transition-opacity duration-300 ${
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        className={`fixed top-0 left-0 bottom-0 z-[60] w-72 bg-card shadow-xl flex flex-col transition-transform duration-300 ease-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        role="dialog"
        aria-modal="true"
        aria-label="Chat history"
        onKeyDown={handleKeyDown}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-dark">
          <h2 className="font-heading font-bold text-sm text-text">History</h2>
          <button onClick={onClose} className="p-3 text-text-muted hover:text-text" aria-label="Close sidebar">
            <X size={18} />
          </button>
        </div>

        {/* New Chat */}
        <button
          onClick={onNewChat}
          aria-label="Start new chat"
          className="mx-3 mt-3 flex items-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-primary/30 text-primary text-sm font-medium hover:bg-primary/5 transition-colors"
        >
          <Plus size={16} />
          New Chat
        </button>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto mt-2 px-2">
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-text-muted text-xs">Loading...</div>
          ) : conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-text-muted text-xs gap-1">
              <MessageSquare size={20} />
              <span>No conversations yet</span>
            </div>
          ) : (
            <div className="space-y-0.5">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => onSelect(conv.id)}
                  aria-current={conv.id === activeId ? 'true' : undefined}
                  className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                    conv.id === activeId
                      ? 'bg-primary/10 border-l-2 border-primary'
                      : 'hover:bg-surface-dark'
                  }`}
                >
                  <p className="text-sm text-text truncate leading-snug">{conv.title}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-text-muted">{relativeTime(conv.updated_at)}</span>
                    {conv.message_count > 0 && (
                      <span className="text-xs text-text-muted">
                        {conv.message_count} msg{conv.message_count !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
