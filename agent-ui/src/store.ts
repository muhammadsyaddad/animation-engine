import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

import {
  AgentDetails,
  SessionEntry,
  TeamDetails,
  type ChatMessage
} from '@/types/os'

interface Store {
  hydrated: boolean
  setHydrated: () => void
  streamingErrorMessage: string
  setStreamingErrorMessage: (streamingErrorMessage: string) => void
  endpoints: {
    endpoint: string
    id__endpoint: string
  }[]
  setEndpoints: (
    endpoints: {
      endpoint: string
      id__endpoint: string
    }[]
  ) => void
  isStreaming: boolean
  setIsStreaming: (isStreaming: boolean) => void
  isEndpointActive: boolean
  setIsEndpointActive: (isActive: boolean) => void
  isEndpointLoading: boolean
  setIsEndpointLoading: (isLoading: boolean) => void
  messages: ChatMessage[]
  setMessages: (
    messages: ChatMessage[] | ((prevMessages: ChatMessage[]) => ChatMessage[])
  ) => void
  chatInputRef: React.RefObject<HTMLTextAreaElement | null>
  selectedEndpoint: string
  setSelectedEndpoint: (selectedEndpoint: string) => void
  agents: AgentDetails[]
  setAgents: (agents: AgentDetails[]) => void
  teams: TeamDetails[]
  setTeams: (teams: TeamDetails[]) => void
  selectedModel: string
  setSelectedModel: (model: string) => void
  mode: 'agent' | 'team'
  setMode: (mode: 'agent' | 'team') => void
  sessionsData: SessionEntry[] | null
  setSessionsData: (
    sessionsData:
      | SessionEntry[]
      | ((prevSessions: SessionEntry[] | null) => SessionEntry[] | null)
  ) => void
  isSessionsLoading: boolean
  setIsSessionsLoading: (isSessionsLoading: boolean) => void
  currentSessionId: string | null
  currentSessionName: string | null
  setCurrentSessionId: (id: string | null) => void
  setCurrentSessionName: (name: string | null) => void
  resetSession: () => void
  isMessagesLoading: boolean
  setIsMessagesLoading: (isLoading: boolean) => void
  upsertSessionEntry: (entry: SessionEntry) => void
  removeSessionEntry: (sessionId: string) => void
  renameSessionEntry: (sessionId: string, name: string | null) => void

  authUser?: {
    id: string
    email: string
    display_name?: string | null
    avatar_url?: string | null
  }
  setAuthUser: (user: Store['authUser'] | null) => void
  logout: () => void
}

export const useStore = create<Store>()(
  persist(
    (set) => ({
      hydrated: false,
      setHydrated: () => set({ hydrated: true }),
      streamingErrorMessage: '',
      setStreamingErrorMessage: (streamingErrorMessage) =>
        set(() => ({ streamingErrorMessage })),
      endpoints: [],
      setEndpoints: (endpoints) => set(() => ({ endpoints })),
      isStreaming: false,
      setIsStreaming: (isStreaming) => set(() => ({ isStreaming })),
      isEndpointActive: false,
      setIsEndpointActive: (isActive) =>
        set(() => ({ isEndpointActive: isActive })),
      isEndpointLoading: true,
      setIsEndpointLoading: (isLoading) =>
        set(() => ({ isEndpointLoading: isLoading })),
      messages: [],
      setMessages: (messages) =>
        set((state) => ({
          messages:
            typeof messages === 'function' ? messages(state.messages) : messages
        })),
      chatInputRef: { current: null },
      selectedEndpoint: 'http://localhost:8000',
      setSelectedEndpoint: (selectedEndpoint) =>
        set(() => ({ selectedEndpoint })),
      agents: [],
      setAgents: (agents) => set({ agents }),
      teams: [],
      setTeams: (teams) => set({ teams }),
      selectedModel: '',
      setSelectedModel: (selectedModel) => set(() => ({ selectedModel })),
      mode: 'agent',
      setMode: (mode) => set(() => ({ mode })),
      sessionsData: null,
      setSessionsData: (sessionsData) =>
        set((state) => ({
          sessionsData:
            typeof sessionsData === 'function'
              ? sessionsData(state.sessionsData)
              : sessionsData
        })),
      isSessionsLoading: false,
      setIsSessionsLoading: (isSessionsLoading) =>
        set(() => ({ isSessionsLoading })),
      currentSessionId: null,
      currentSessionName: null,
      setCurrentSessionId: (currentSessionId) =>
        set(() => ({ currentSessionId })),
      setCurrentSessionName: (currentSessionName) =>
        set(() => ({ currentSessionName })),
      resetSession: () =>
        set(() => ({
          currentSessionId: null,
          currentSessionName: null,
          messages: []
        })),
      isMessagesLoading: false,
      setIsMessagesLoading: (isMessagesLoading) =>
        set(() => ({ isMessagesLoading })),
      upsertSessionEntry: (entry) =>
        set((state) => ({
          sessionsData: [
            entry,
            ...(state.sessionsData?.filter(
              (s) => s.session_id !== entry.session_id
            ) ?? [])
          ]
        })),
      removeSessionEntry: (sessionId) =>
        set((state) => ({
          sessionsData: (state.sessionsData ?? []).filter(
            (s) => s.session_id !== sessionId
          )
        })),
      renameSessionEntry: (sessionId, name) =>
        set((state) => ({
          sessionsData: (state.sessionsData ?? []).map((s) =>
            s.session_id === sessionId ? { ...s, session_name: name ?? '-' } : s
          )
        })),
      authUser: undefined,

      setAuthUser: (authUser) => set(() => ({ authUser })),
      logout: () =>
        set(() => ({
          authUser: undefined,

          messages: [],
          currentSessionId: null,
          currentSessionName: null
        }))
    }),
    {
      name: 'endpoint-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        selectedEndpoint: state.selectedEndpoint,
        authUser: state.authUser,
        currentSessionId: state.currentSessionId,
        currentSessionName: state.currentSessionName
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated?.()
      }
    }
  )
)
