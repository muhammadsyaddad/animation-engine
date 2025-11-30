'use client'

import { useCallback } from 'react'
import { useQueryState } from 'nuqs'
import { toast } from 'sonner'

import { useStore } from '@/store'
import type {
  ChatMessage as UIChatMessage,
  SessionEntry,
  ReasoningSteps,
  ReasoningMessage,
  ReferenceData,
  ImageData,
  VideoData,
  AudioData,
  ResponseAudio
} from '@/types/os'

import {
  createChatSession,
  listChatSessions,
  getChatSession,
  renameChatSession,
  deleteChatSession,
  listChatMessages,
  createChatMessage,
  type ChatMessage as APIChatMessage
} from '@/api/chat'

/**
 * useChatSession
 *
 * Hook untuk mengelola sesi chat yang dipersist ke backend (/v1/chat).
 * Fitur:
 * - Lazy-create session saat kirim pesan pertama
 * - Memuat daftar sesi, memilih sesi, memuat pesan sesi
 * - Rename / delete sesi (mengupdate store dan URL ?session)
 * - Persist user/agent messages ke backend
 *
 * Catatan:
 * - Mengandalkan auth token di localStorage (dev). Middleware Next.js cek cookie untuk SSR redirect.
 * - Integrasi streaming: setelah stream selesai, panggil postAgentMessage agar disimpan ke DB.
 */

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

function nowSeconds(): number {
  return Math.floor(Date.now() / 1000)
}

function parseTimestampToSeconds(ts?: string | null): number {
  if (!ts) return nowSeconds()
  const ms = Date.parse(ts)
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : nowSeconds()
}

/* Konversi payload extra_json dari backend ke bentuk ChatMessage UI */
interface PersistedExtra {
  tool_calls?: UIChatMessage['tool_calls']
  reasoning_steps?: ReasoningSteps[]
  reasoning_messages?: ReasoningMessage[]
  references?: ReferenceData[]
  images?: ImageData[]
  videos?: VideoData[]
  audio?: AudioData[]
  response_audio?: ResponseAudio
}

function toUIMessage(api: APIChatMessage): UIChatMessage {
  const createdAt = parseTimestampToSeconds(api.created_at)
  const extra: PersistedExtra = (api.extra_json ?? {}) as PersistedExtra

  const toolCalls: UIChatMessage['tool_calls'] | undefined = Array.isArray(
    extra.tool_calls
  )
    ? extra.tool_calls
    : undefined

  const hasExtraData =
    (extra.reasoning_steps && extra.reasoning_steps.length > 0) ||
    (extra.reasoning_messages && extra.reasoning_messages.length > 0) ||
    (extra.references && extra.references.length > 0)

  const extraData: UIChatMessage['extra_data'] | undefined = hasExtraData
    ? {
        reasoning_steps: extra.reasoning_steps,
        reasoning_messages: extra.reasoning_messages,
        references: extra.references
      }
    : undefined

  const msg: UIChatMessage = {
    role: api.role as UIChatMessage['role'],
    content: api.content ?? '',
    created_at: createdAt,
    tool_calls: toolCalls,
    extra_data: extraData
  }

  if (extra.images) msg.images = extra.images
  if (extra.videos) msg.videos = extra.videos
  if (extra.audio) msg.audio = extra.audio
  if (extra.response_audio) msg.response_audio = extra.response_audio

  return msg
}

/* Mengemas data dari UI agar bisa disimpan di extra_json untuk agent messages */
function toExtraJsonFromUI(
  msg: Partial<UIChatMessage>
): Record<string, unknown> | undefined {
  const extra: Record<string, unknown> = {}
  if (msg.tool_calls && msg.tool_calls.length > 0) extra.tool_calls = msg.tool_calls
  if (msg.extra_data?.reasoning_steps) extra.reasoning_steps = msg.extra_data.reasoning_steps
  if (msg.extra_data?.reasoning_messages) extra.reasoning_messages = msg.extra_data.reasoning_messages
  if (msg.extra_data?.references) extra.references = msg.extra_data.references
  if (msg.images) extra.images = msg.images
  if (msg.videos) extra.videos = msg.videos
  if (msg.audio) extra.audio = msg.audio
  if (msg.response_audio) extra.response_audio = msg.response_audio

  return Object.keys(extra).length > 0 ? extra : undefined
}

/* -------------------------------------------------------------------------- */
/* Types                                                                      */
/* -------------------------------------------------------------------------- */

export interface UseChatSession {
  currentSessionId: string | null
  currentSessionName: string | null
  isMessagesLoading: boolean

  // Session lifecycle
  ensureSession: (opts?: { name?: string | null }) => Promise<string | null>
  newSession: (name?: string | null) => Promise<string | null>
  selectSession: (sessionId: string) => Promise<void>
  renameCurrentSession: (name: string | null) => Promise<boolean>
  deleteCurrentSession: () => Promise<boolean>

  // Listing / loading
  loadSessions: (params?: {
    userOnly?: boolean
    limit?: number
    offset?: number
  }) => Promise<void>
  loadMessages: (sessionId?: string) => Promise<UIChatMessage[] | null>

  // Message persistence
  postUserMessage: (content: string) => Promise<boolean>
  postAgentMessage: (
    content: string,
    from?: Partial<UIChatMessage>
  ) => Promise<boolean>

  // Utilities
  setFromStreamSession: (
    sessionId: string,
    name?: string | null,
    createdAt?: number
  ) => void
  clearLocalSession: () => void
}

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

export function useChatSession(): UseChatSession {
  const selectedEndpoint = useStore((s) => s.selectedEndpoint)

  const currentSessionId = useStore((s) => s.currentSessionId)
  const currentSessionName = useStore((s) => s.currentSessionName)
  const setCurrentSessionId = useStore((s) => s.setCurrentSessionId)
  const setCurrentSessionName = useStore((s) => s.setCurrentSessionName)
  const resetSession = useStore((s) => s.resetSession)

  const setMessages = useStore((s) => s.setMessages)
  const isMessagesLoading = useStore((s) => s.isMessagesLoading)
  const setIsMessagesLoading = useStore((s) => s.setIsMessagesLoading)

  const setSessionsData = useStore((s) => s.setSessionsData)
  const upsertSessionEntry = useStore((s) => s.upsertSessionEntry)
  const removeSessionEntry = useStore((s) => s.removeSessionEntry)
  const renameSessionEntry = useStore((s) => s.renameSessionEntry)

  const [, setSessionQuery] = useQueryState('session')

  const requireEndpoint = useCallback((): string | null => {
    if (!selectedEndpoint) {
      toast.error('Please configure a valid backend endpoint')
      return null
    }
    return selectedEndpoint.replace(/\/$/, '')
  }, [selectedEndpoint])

  const ensureSession = useCallback(
    async (opts?: { name?: string | null }): Promise<string | null> => {
      const endpoint = requireEndpoint()
      if (!endpoint) return null
      if (currentSessionId) return currentSessionId

      try {
        const session = await createChatSession(endpoint, {
          name: opts?.name ?? null
        })
        const createdAt = parseTimestampToSeconds(session.created_at)
        const entry: SessionEntry = {
          session_id: session.id,
          session_name: session.name ?? '-',
          created_at: createdAt,
          updated_at: parseTimestampToSeconds(session.updated_at ?? session.created_at)
        }
        upsertSessionEntry(entry)
        setCurrentSessionId(session.id)
        setCurrentSessionName(session.name ?? '-')
        setSessionQuery(session.id)
        return session.id
      } catch (e) {
        toast.error(`Failed to create session: ${e instanceof Error ? e.message : String(e)}`)
        return null
      }
    },
    [
      requireEndpoint,
      currentSessionId,
      upsertSessionEntry,
      setCurrentSessionId,
      setCurrentSessionName,
      setSessionQuery
    ]
  )

  const newSession = useCallback(
    async (name?: string | null): Promise<string | null> => {
      resetSession()
      setSessionQuery(null)
      return ensureSession({ name: name ?? null })
    },
    [resetSession, setSessionQuery, ensureSession]
  )

  const selectSession = useCallback(
    async (sessionId: string): Promise<void> => {
      const endpoint = requireEndpoint()
      if (!endpoint) return

      try {
        const s = await getChatSession(endpoint, sessionId)
        setCurrentSessionId(s.id)
        setCurrentSessionName(s.name ?? '-')
        setSessionQuery(s.id)
        await loadMessagesInternal(endpoint, s.id, setIsMessagesLoading, setMessages)
      } catch (e) {
        toast.error(`Failed to open session: ${e instanceof Error ? e.message : String(e)}`)
      }
    },
    [
      requireEndpoint,
      setCurrentSessionId,
      setCurrentSessionName,
      setSessionQuery,
      setIsMessagesLoading,
      setMessages
    ]
  )

  const renameCurrentSession = useCallback(
    async (name: string | null): Promise<boolean> => {
      const endpoint = requireEndpoint()
      if (!endpoint || !currentSessionId) return false

      try {
        const s = await renameChatSession(endpoint, currentSessionId, name)
        setCurrentSessionName(s.name ?? '-')
        renameSessionEntry(s.id, s.name ?? '-')
        return true
      } catch (e) {
        toast.error(`Failed to rename session: ${e instanceof Error ? e.message : String(e)}`)
        return false
      }
    },
    [requireEndpoint, currentSessionId, setCurrentSessionName, renameSessionEntry]
  )

  const deleteCurrentSession = useCallback(async (): Promise<boolean> => {
    const endpoint = requireEndpoint()
    if (!endpoint || !currentSessionId) return false

    try {
      await deleteChatSession(endpoint, currentSessionId)
      removeSessionEntry(currentSessionId)
      resetSession()
      setSessionQuery(null)
      return true
    } catch (e) {
      toast.error(`Failed to delete session: ${e instanceof Error ? e.message : String(e)}`)
      return false
    }
  }, [
    requireEndpoint,
    currentSessionId,
    removeSessionEntry,
    resetSession,
    setSessionQuery
  ])

  const loadSessions = useCallback(
    async (params?: {
      userOnly?: boolean
      limit?: number
      offset?: number
    }) => {
      const endpoint = requireEndpoint()
      if (!endpoint) return

      try {
        const sessions = await listChatSessions(endpoint, {
          user_only: params?.userOnly ?? true,
          limit: params?.limit,
          offset: params?.offset
        })
        const entries: SessionEntry[] = sessions.map((s) => ({
          session_id: s.id,
          session_name: s.name ?? '-',
          created_at: parseTimestampToSeconds(s.created_at),
          updated_at: parseTimestampToSeconds(s.updated_at ?? s.created_at)
        }))
        setSessionsData(entries)
      } catch (e) {
        toast.error(`Failed to load sessions: ${e instanceof Error ? e.message : String(e)}`)
        setSessionsData([])
      }
    },
    [requireEndpoint, setSessionsData]
  )

  const loadMessages = useCallback(
    async (sessionIdArg?: string): Promise<UIChatMessage[] | null> => {
      const endpoint = requireEndpoint()
      if (!endpoint) return null

      const sid = sessionIdArg ?? currentSessionId
      if (!sid) return null
      return loadMessagesInternal(endpoint, sid, setIsMessagesLoading, setMessages)
    },
    [requireEndpoint, currentSessionId, setIsMessagesLoading, setMessages]
  )

  const postUserMessage = useCallback(
    async (content: string): Promise<boolean> => {
      if (!content || !content.trim()) return false
      const endpoint = requireEndpoint()
      if (!endpoint) return false

      const sid = (await ensureSession()) ?? null
      if (!sid) return false

      try {
        const saved = await createChatMessage(endpoint, sid, {
          role: 'user',
          content
        })
        const uiMsg = toUIMessage(saved)
        setMessages((prev) => [...prev, uiMsg])
        return true
      } catch (e) {
        toast.error(`Failed to save your message: ${e instanceof Error ? e.message : String(e)}`)
        return false
      }
    },
    [requireEndpoint, ensureSession, setMessages]
  )

  const postAgentMessage = useCallback(
    async (
      content: string,
      from?: Partial<UIChatMessage>
    ): Promise<boolean> => {
      const endpoint = requireEndpoint()
      if (!endpoint) return false
      const sid = currentSessionId ?? (await ensureSession())
      if (!sid) return false

      try {
        const saved = await createChatMessage(endpoint, sid, {
          role: 'agent',
          content,
          extra_json: toExtraJsonFromUI(from ?? {})
        })
        const uiMsg = toUIMessage(saved)
        setMessages((prev) => [...prev, uiMsg])
        return true
      } catch (e) {
        toast.error(`Failed to save agent message: ${e instanceof Error ? e.message : String(e)}`)
        return false
      }
    },
    [requireEndpoint, currentSessionId, ensureSession, setMessages]
  )

  const setFromStreamSession = useCallback(
    (sessionId: string, name?: string | null, createdAt?: number) => {
      setCurrentSessionId(sessionId)
      if (name != null) setCurrentSessionName(name || '-')
      if (sessionId) setSessionQuery(sessionId)
      if (sessionId && name) {
        upsertSessionEntry({
          session_id: sessionId,
          session_name: name || '-',
          created_at: createdAt ?? nowSeconds()
        })
      }
    },
    [setCurrentSessionId, setCurrentSessionName, setSessionQuery, upsertSessionEntry]
  )

  const clearLocalSession = useCallback(() => {
    resetSession()
    setSessionQuery(null)
  }, [resetSession, setSessionQuery])

  return {
    currentSessionId,
    currentSessionName,
    isMessagesLoading,
    ensureSession,
    newSession,
    selectSession,
    renameCurrentSession,
    deleteCurrentSession,
    loadSessions,
    loadMessages,
    postUserMessage,
    postAgentMessage,
    setFromStreamSession,
    clearLocalSession
  }
}

/* -------------------------------------------------------------------------- */
/* Internal helpers                                                           */
/* -------------------------------------------------------------------------- */

async function loadMessagesInternal(
  endpoint: string,
  sessionId: string,
  setIsMessagesLoading: (isLoading: boolean) => void,
  setMessages: (
    messages: UIChatMessage[] | ((prev: UIChatMessage[]) => UIChatMessage[])
  ) => void
): Promise<UIChatMessage[] | null> {
  setIsMessagesLoading(true)
  try {
    const res = await listChatMessages(endpoint, sessionId, { ascending: true })
    const ui = res.map(toUIMessage)
    setMessages(ui)
    return ui
  } catch (e) {
    toast.error(`Failed to load messages: ${e instanceof Error ? e.message : String(e)}`)
    setMessages([])
    return null
  } finally {
    setIsMessagesLoading(false)
  }
}
