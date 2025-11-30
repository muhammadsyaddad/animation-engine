import { toast } from 'sonner'

/**
 * chat.ts
 * Lightweight client wrapper for backend /v1/chat endpoints.
 *
 * Endpoints (FastAPI):
 *  - POST   /v1/chat/sessions
 *  - GET    /v1/chat/sessions
 *  - GET    /v1/chat/sessions/{session_id}
 *  - PATCH  /v1/chat/sessions/{session_id}
 *  - DELETE /v1/chat/sessions/{session_id}
 *
 *  - POST   /v1/chat/sessions/{session_id}/messages
 *  - GET    /v1/chat/sessions/{session_id}/messages
 *  - DELETE /v1/chat/messages/{message_id}
 *
 * Conventions:
 *  - Caller supplies the base Agent API endpoint (e.g., http://localhost:8000)
 *  - Access token (local dev) is read from localStorage key 'agentui_access_token'
 *  - Functions throw on non-2xx HTTP or network errors
 */

/* -------------------------------------------------------------------------- */
/* Types (mirror backend Pydantic models)                                     */
/* -------------------------------------------------------------------------- */

export interface ChatSession {
  id: string
  user_id: string
  name: string | null
  created_at: string | null
  updated_at: string | null
}

export type ChatRole = 'user' | 'agent' | 'system' | 'tool'

export interface ChatMessage {
  id: string
  session_id: string
  role: ChatRole
  content: string
  user_id?: string | null
  extra_json?: Record<string, unknown> | null
  created_at: string | null
}

export interface CreateSessionRequest {
  name?: string | null
}

export interface CreateSessionResponse {
  session: ChatSession
}

export interface SessionListResponse {
  sessions: ChatSession[]
}

export interface RenameSessionRequest {
  name: string | null
}

export interface CreateMessageRequest {
  role: ChatRole
  content: string
  extra_json?: Record<string, unknown>
}

export interface CreateMessageResponse {
  message: ChatMessage
}

export interface MessageListResponse {
  messages: ChatMessage[]
}

export interface ListSessionsParams {
  user_only?: boolean
  limit?: number
  offset?: number
}

export interface ListMessagesParams {
  limit?: number
  offset?: number
  ascending?: boolean
}

/* -------------------------------------------------------------------------- */
/* Internal helpers                                                           */
/* -------------------------------------------------------------------------- */

const ACCESS_TOKEN_KEY = 'agentui_access_token'

function base(endpoint: string): string {
  return `${endpoint.replace(/\/$/, '')}/v1/chat`
}

function authHeaders(): Record<string, string> {
  try {
    const token =
      typeof window !== 'undefined'
        ? localStorage.getItem(ACCESS_TOKEN_KEY)
        : null
    return token ? { Authorization: `Bearer ${token}` } : {}
  } catch {
    return {}
  }
}

async function parseJson<T>(res: Response): Promise<T> {
  try {
    return (await res.json()) as T
  } catch {
    throw new Error('Invalid JSON response')
  }
}

function toastAndThrow(res: Response, body?: unknown): never {
  let detail: string | undefined
  if (body && typeof body === 'object' && body !== null) {
    const anyBody = body as Record<string, unknown>
    if (typeof anyBody.detail === 'string') detail = anyBody.detail
  }
  const message =
    detail ||
    (res.status === 401
      ? 'Unauthorized'
      : `${res.status} ${res.statusText || 'Error'}`)
  toast.error(message)
  throw new Error(message)
}

/* -------------------------------------------------------------------------- */
/* Sessions                                                                   */
/* -------------------------------------------------------------------------- */

/**
 * Create a new chat session for the authenticated user.
 */
export async function createChatSession(
  endpoint: string,
  req: CreateSessionRequest = {}
): Promise<ChatSession> {
  const res = await fetch(`${base(endpoint)}/sessions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders()
    },
    body: JSON.stringify(req)
  })
  const body = await parseJson<CreateSessionResponse | Record<string, unknown>>(
    res
  )
  if (!res.ok) {
    toastAndThrow(res, body)
  }
  return (body as CreateSessionResponse).session
}

/**
 * List chat sessions (defaults to user_only=true).
 */
export async function listChatSessions(
  endpoint: string,
  params: ListSessionsParams = {}
): Promise<ChatSession[]> {
  const url = new URL(`${base(endpoint)}/sessions`)
  if (params.user_only !== undefined)
    url.searchParams.set('user_only', String(params.user_only))
  if (params.limit !== undefined)
    url.searchParams.set('limit', String(params.limit))
  if (params.offset !== undefined)
    url.searchParams.set('offset', String(params.offset))

  const res = await fetch(url.toString(), {
    method: 'GET',
    headers: { ...authHeaders() }
  })
  const body = await parseJson<SessionListResponse | Record<string, unknown>>(
    res
  )
  if (!res.ok) {
    toastAndThrow(res, body)
  }
  if (
    body &&
    typeof body === 'object' &&
    'sessions' in body &&
    Array.isArray((body as SessionListResponse).sessions)
  ) {
    return (body as SessionListResponse).sessions
  }
  return []
}

/**
 * Get a single session by id.
 */
export async function getChatSession(
  endpoint: string,
  sessionId: string
): Promise<ChatSession> {
  const res = await fetch(
    `${base(endpoint)}/sessions/${encodeURIComponent(sessionId)}`,
    {
      method: 'GET',
      headers: { ...authHeaders() }
    }
  )
  const body = await parseJson<ChatSession | Record<string, unknown>>(res)
  if (!res.ok) {
    toastAndThrow(res, body)
  }
  return body as ChatSession
}

/**
 * Rename (or clear name with null) a session.
 */
export async function renameChatSession(
  endpoint: string,
  sessionId: string,
  name: string | null
): Promise<ChatSession> {
  const res = await fetch(
    `${base(endpoint)}/sessions/${encodeURIComponent(sessionId)}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders()
      },
      body: JSON.stringify({ name } as RenameSessionRequest)
    }
  )
  const body = await parseJson<ChatSession | Record<string, unknown>>(res)
  if (!res.ok) {
    toastAndThrow(res, body)
  }
  return body as ChatSession
}

/**
 * Delete a session (and its messages).
 */
export async function deleteChatSession(
  endpoint: string,
  sessionId: string
): Promise<boolean> {
  const res = await fetch(
    `${base(endpoint)}/sessions/${encodeURIComponent(sessionId)}`,
    {
      method: 'DELETE',
      headers: { ...authHeaders() }
    }
  )
  if (!res.ok) {
    let body: unknown = null
    try {
      body = await res.json()
    } catch {
      /* ignore */
    }
    toastAndThrow(res, body)
  }
  return true
}

/* -------------------------------------------------------------------------- */
/* Messages                                                                   */
/* -------------------------------------------------------------------------- */

/**
 * Append a message to a session.
 */
export async function createChatMessage(
  endpoint: string,
  sessionId: string,
  req: CreateMessageRequest
): Promise<ChatMessage> {
  const res = await fetch(
    `${base(endpoint)}/sessions/${encodeURIComponent(sessionId)}/messages`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders()
      },
      body: JSON.stringify(req)
    }
  )
  const body = await parseJson<CreateMessageResponse | Record<string, unknown>>(
    res
  )
  if (!res.ok) {
    toastAndThrow(res, body)
  }
  return (body as CreateMessageResponse).message
}

/**
 * List messages in a session (chronological by default).
 */
export async function listChatMessages(
  endpoint: string,
  sessionId: string,
  params: ListMessagesParams = {}
): Promise<ChatMessage[]> {
  const url = new URL(
    `${base(endpoint)}/sessions/${encodeURIComponent(sessionId)}/messages`
  )
  if (params.limit !== undefined)
    url.searchParams.set('limit', String(params.limit))
  if (params.offset !== undefined)
    url.searchParams.set('offset', String(params.offset))
  if (params.ascending !== undefined)
    url.searchParams.set('ascending', String(params.ascending))

  const res = await fetch(url.toString(), {
    method: 'GET',
    headers: { ...authHeaders() }
  })
  const body = await parseJson<MessageListResponse | Record<string, unknown>>(
    res
  )
  if (!res.ok) {
    toastAndThrow(res, body)
  }
  if (
    body &&
    typeof body === 'object' &&
    'messages' in body &&
    Array.isArray((body as MessageListResponse).messages)
  ) {
    return (body as MessageListResponse).messages
  }
  return []
}

/**
 * Delete a single message.
 */
export async function deleteChatMessage(
  endpoint: string,
  messageId: string
): Promise<boolean> {
  const res = await fetch(
    `${base(endpoint)}/messages/${encodeURIComponent(messageId)}`,
    {
      method: 'DELETE',
      headers: { ...authHeaders() }
    }
  )
  if (!res.ok) {
    let body: unknown = null
    try {
      body = await res.json()
    } catch {
      /* ignore */
    }
    toastAndThrow(res, body)
  }
  return true
}

/* -------------------------------------------------------------------------- */
/* Convenience helpers                                                        */
/* -------------------------------------------------------------------------- */

/**
 * Ensure a chat session exists (create if missing) and return its record.
 * Useful for "lazy session" behavior on first user message.
 */
export async function ensureChatSession(
  endpoint: string,
  sessionId: string | null | undefined,
  opts?: CreateSessionRequest
): Promise<ChatSession> {
  if (sessionId) {
    try {
      return await getChatSession(endpoint, sessionId)
    } catch {
      // If not found or no access, create new below
    }
  }
  return createChatSession(endpoint, opts ?? {})
}

/**
 * Append a user message and (optionally) an agent reply in one call.
 * Intended for simple cases; streaming flows should use dedicated logic.
 */
export async function createUserAndAgentMessages(
  endpoint: string,
  sessionId: string,
  userContent: string,
  agentContent?: string
): Promise<{ user: ChatMessage; agent?: ChatMessage }> {
  const userMsg = await createChatMessage(endpoint, sessionId, {
    role: 'user',
    content: userContent
  })
  let agentMsg: ChatMessage | undefined
  if (agentContent) {
    agentMsg = await createChatMessage(endpoint, sessionId, {
      role: 'agent',
      content: agentContent
    })
  }
  return { user: userMsg, agent: agentMsg }
}
