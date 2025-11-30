import { useCallback } from 'react'

import { APIRoutes } from '@/api/routes'

import useChatActions from '@/hooks/useChatActions'
import { useStore } from '../store'
import { RunEvent, RunResponseContent, type RunResponse } from '@/types/os'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'
import useAIResponseStream from './useAIResponseStream'
import { ToolCall } from '@/types/os'
import { useQueryState } from 'nuqs'
import { getJsonMarkdown } from '@/lib/utils'
import { useChatSession } from '@/hooks/useChatSession'

const useAIChatStreamHandler = () => {
  const setMessages = useStore((state) => state.setMessages)
  const { addMessage, focusChatInput } = useChatActions()
  const [agentId] = useQueryState('agent')
  const [teamId] = useQueryState('team')
  const [sessionId, setSessionId] = useQueryState('session')
  const selectedEndpoint = useStore((state) => state.selectedEndpoint)
  const mode = useStore((state) => state.mode)
  const setStreamingErrorMessage = useStore(
    (state) => state.setStreamingErrorMessage
  )
  const setIsStreaming = useStore((state) => state.setIsStreaming)
  const setSessionsData = useStore((state) => state.setSessionsData)
  const { streamResponse } = useAIResponseStream()
  const { postUserMessage, postAgentMessage, setFromStreamSession } =
    useChatSession()

  const updateMessagesWithErrorState = useCallback(() => {
    setMessages((prevMessages) => {
      const newMessages = [...prevMessages]
      const lastMessage = newMessages[newMessages.length - 1]
      if (lastMessage && lastMessage.role === 'agent') {
        lastMessage.streamingError = true
      }
      return newMessages
    })
  }, [setMessages])

  /**
   * Processes a new tool call and adds it to the message
   * @param toolCall - The tool call to add
   * @param prevToolCalls - The previous tool calls array
   * @returns Updated tool calls array
   */
  const processToolCall = useCallback(
    (toolCall: ToolCall, prevToolCalls: ToolCall[] = []) => {
      const toolCallId =
        toolCall.tool_call_id || `${toolCall.tool_name}-${toolCall.created_at}`

      const existingToolCallIndex = prevToolCalls.findIndex(
        (tc) =>
          (tc.tool_call_id && tc.tool_call_id === toolCall.tool_call_id) ||
          (!tc.tool_call_id &&
            toolCall.tool_name &&
            toolCall.created_at &&
            `${tc.tool_name}-${tc.created_at}` === toolCallId)
      )
      if (existingToolCallIndex >= 0) {
        const updatedToolCalls = [...prevToolCalls]
        updatedToolCalls[existingToolCallIndex] = {
          ...updatedToolCalls[existingToolCallIndex],
          ...toolCall
        }
        return updatedToolCalls
      } else {
        return [...prevToolCalls, toolCall]
      }
    },
    []
  )

  /**
   * Processes tool calls from a chunk, handling both single tool object and tools array formats
   * @param chunk - The chunk containing tool call data
   * @param existingToolCalls - The existing tool calls array
   * @returns Updated tool calls array
   */
  const processChunkToolCalls = useCallback(
    (
      chunk: RunResponseContent | RunResponse,
      existingToolCalls: ToolCall[] = []
    ) => {
      let updatedToolCalls = [...existingToolCalls]
      // Handle new single tool object format
      if (chunk.tool) {
        updatedToolCalls = processToolCall(chunk.tool, updatedToolCalls)
      }
      // Handle legacy tools array format
      if (chunk.tools && chunk.tools.length > 0) {
        for (const toolCall of chunk.tools) {
          updatedToolCalls = processToolCall(toolCall, updatedToolCalls)
        }
      }

      return updatedToolCalls
    },
    [processToolCall]
  )

  const handleStreamResponse = useCallback(
    async (input: string | FormData) => {
      setIsStreaming(true)

      const formData = input instanceof FormData ? input : new FormData()
      if (typeof input === 'string') {
        formData.append('message', input)
      }

      setMessages((prevMessages) => {
        if (prevMessages.length >= 2) {
          const lastMessage = prevMessages[prevMessages.length - 1]
          const secondLastMessage = prevMessages[prevMessages.length - 2]
          if (
            lastMessage.role === 'agent' &&
            lastMessage.streamingError &&
            secondLastMessage.role === 'user'
          ) {
            return prevMessages.slice(0, -2)
          }
        }
        return prevMessages
      })

      // Build user-visible content; append dataset marker if csv_path present.
      const rawMessage = (formData.get('message') as string) || ''
      const csvPath = formData.get('csv_path') as string | null
      const userDisplay =
        csvPath && csvPath.length > 0
          ? `${rawMessage}\n[dataset csv_path=${csvPath}]`
          : rawMessage

      addMessage({
        role: 'user',
        content: userDisplay,
        // NOTE: If later we extend ChatMessage with attachments, we can pass csvPath metadata here.
        created_at: Math.floor(Date.now() / 1000)
      })

      addMessage({
        role: 'agent',
        content: '',
        tool_calls: [],
        streamingError: false,
        created_at: Math.floor(Date.now() / 1000) + 1
      })

      let lastContent = ''
      let userPersisted = false
      let newSessionId = sessionId
      try {
        const endpointUrl = constructEndpointUrl(selectedEndpoint)

        let RunUrl: string | null = null

        if (mode === 'team' && teamId) {
          RunUrl = APIRoutes.TeamRun(endpointUrl, teamId)
        } else if (mode === 'agent' && agentId) {
          RunUrl = APIRoutes.AgentRun(endpointUrl).replace(
            '{agent_id}',
            agentId
          )
        }

        if (!RunUrl) {
          updateMessagesWithErrorState()
          setStreamingErrorMessage('Please select an agent or team first.')
          setIsStreaming(false)
          return
        }

        const summarizeRaw = formData.get('summarize')
        const summarize =
          typeof summarizeRaw === 'string'
            ? ['true', '1', 'yes', 'on'].includes(summarizeRaw.toLowerCase())
            : Boolean(summarizeRaw)

        const fdHas = (key: string) =>
          formData instanceof FormData && formData.has(key)
        const fdGetString = (key: string): string | undefined => {
          if (!fdHas(key)) return undefined
          const v = formData.get(key)
          return typeof v === 'string' ? v : undefined
        }
        const fdGetBool = (key: string): boolean | undefined => {
          if (!fdHas(key)) return undefined
          const v = formData.get(key)
          if (typeof v === 'string')
            return ['true', '1', 'yes', 'on'].includes(v.toLowerCase())
          return Boolean(v)
        }
        const fdGetInt = (key: string): number | undefined => {
          if (!fdHas(key)) return undefined
          const v = formData.get(key)
          if (typeof v === 'string') {
            const n = parseInt(v, 10)
            return Number.isFinite(n) ? n : undefined
          }
          return undefined
        }
        const fdGetArray = (key: string): string[] | undefined => {
          if (!fdHas(key)) return undefined
          const v = formData.get(key)
          if (typeof v === 'string') {
            try {
              const parsed = JSON.parse(v)
              if (Array.isArray(parsed)) return parsed.map((x) => String(x))
            } catch {}
            return v
              .split(',')
              .map((s) => s.trim())
              .filter(Boolean)
          }
          return undefined
        }
        const csvPathValue = fdGetString('csv_path')

        const payload: Record<string, unknown> = {
          message: rawMessage,
          stream: true,
          session_id: sessionId ?? '',
          summarize,
          // Animation pipeline optional flags/params (included only if provided)
          animate_data: fdGetBool('animate_data'),
          chart_type: fdGetString('chart_type'),
          csv_path: csvPathValue,
          csv_dir: fdGetString('csv_dir'),
          preview_sample_every: fdGetInt('preview_sample_every'),
          preview_max_frames: fdGetInt('preview_max_frames'),
          aspect_ratio: fdGetString('aspect_ratio'),
          render_quality: fdGetString('render_quality'),
          // Codegen controls (forwarded to API if present)
          code_engine: fdGetString('code_engine'),
          code_model: fdGetString('code_model'),
          code_system_prompt: fdGetString('code_system_prompt'),
          // Export/Merge options (Phase 5)
          export_videos: fdGetArray('export_videos'),
          export_title_slug: fdGetString('export_title_slug')
        }

        await streamResponse({
          apiUrl: RunUrl,
          requestBody: payload,
          onChunk: (chunk: RunResponse) => {
            if (
              chunk.event === RunEvent.RunStarted ||
              chunk.event === RunEvent.TeamRunStarted ||
              chunk.event === RunEvent.ReasoningStarted ||
              chunk.event === RunEvent.TeamReasoningStarted
            ) {
              newSessionId = chunk.session_id as string
              setSessionId(chunk.session_id as string)
              if (
                chunk.event === RunEvent.RunStarted ||
                chunk.event === RunEvent.TeamRunStarted
              ) {
                if (chunk.session_id) {
                  setFromStreamSession(
                    chunk.session_id as string,
                    rawMessage,
                    chunk.created_at
                  )
                  if (!userPersisted) {
                    userPersisted = true
                    // Persist the user's message once the session_id is known,
                    // then reconcile UI to avoid duplicate unsaved/saved user messages
                    postUserMessage(userDisplay).then(() => {
                      setMessages((prev) => {
                        const len = prev.length
                        if (len >= 3) {
                          const thirdLast = prev[len - 3]
                          const secondLast = prev[len - 2]
                          const last = prev[len - 1]
                          // [..., user(unsaved), agent(placeholder), user(saved)] -> [..., user(saved), agent(placeholder)]
                          if (
                            thirdLast?.role === 'user' &&
                            secondLast?.role === 'agent' &&
                            last?.role === 'user'
                          ) {
                            return [...prev.slice(0, len - 3), last, secondLast]
                          }
                        }
                        return prev
                      })
                    })
                  }
                }
              }
              if (
                (!sessionId || sessionId !== chunk.session_id) &&
                chunk.session_id
              ) {
                const sessionData = {
                  session_id: chunk.session_id as string,
                  session_name: rawMessage,
                  created_at: chunk.created_at
                }
                setSessionsData((prevSessionsData) => {
                  const sessionExists = prevSessionsData?.some(
                    (session) => session.session_id === chunk.session_id
                  )
                  if (sessionExists) {
                    return prevSessionsData
                  }
                  return [sessionData, ...(prevSessionsData ?? [])]
                })
              }
            } else if (
              chunk.event === RunEvent.ToolCallStarted ||
              chunk.event === RunEvent.TeamToolCallStarted ||
              chunk.event === RunEvent.ToolCallCompleted ||
              chunk.event === RunEvent.TeamToolCallCompleted
            ) {
              setMessages((prevMessages) => {
                const newMessages = [...prevMessages]
                const lastMessage = newMessages[newMessages.length - 1]
                if (lastMessage && lastMessage.role === 'agent') {
                  lastMessage.tool_calls = processChunkToolCalls(
                    chunk,
                    lastMessage.tool_calls
                  )
                }
                return newMessages
              })
            } else if (
              chunk.event === RunEvent.RunContent ||
              chunk.event === RunEvent.TeamRunContent
            ) {
              setMessages((prevMessages) => {
                const newMessages = [...prevMessages]
                const lastMessage = newMessages[newMessages.length - 1]
                if (
                  lastMessage &&
                  lastMessage.role === 'agent' &&
                  typeof chunk.content === 'string'
                ) {
                  const uniqueContent = chunk.content.replace(lastContent, '')
                  lastMessage.content += uniqueContent
                  lastContent = chunk.content

                  // Handle tool calls streaming
                  lastMessage.tool_calls = processChunkToolCalls(
                    chunk,
                    lastMessage.tool_calls
                  )
                  if (chunk.extra_data?.reasoning_steps) {
                    lastMessage.extra_data = {
                      ...lastMessage.extra_data,
                      reasoning_steps: chunk.extra_data.reasoning_steps
                    }
                  }

                  if (chunk.extra_data?.references) {
                    lastMessage.extra_data = {
                      ...lastMessage.extra_data,
                      references: chunk.extra_data.references
                    }
                  }

                  lastMessage.created_at =
                    chunk.created_at ?? lastMessage.created_at
                  if (chunk.images) {
                    lastMessage.images = chunk.images
                  }
                  if (chunk.videos) {
                    lastMessage.videos = chunk.videos
                  }
                  if (chunk.audio) {
                    lastMessage.audio = chunk.audio
                  }
                } else if (
                  lastMessage &&
                  lastMessage.role === 'agent' &&
                  typeof chunk?.content !== 'string' &&
                  chunk.content !== null
                ) {
                  const jsonBlock = getJsonMarkdown(chunk?.content)

                  lastMessage.content += jsonBlock
                  lastContent = jsonBlock
                } else if (
                  chunk.response_audio?.transcript &&
                  typeof chunk.response_audio?.transcript === 'string'
                ) {
                  const transcript = chunk.response_audio.transcript
                  lastMessage.response_audio = {
                    ...lastMessage.response_audio,
                    transcript:
                      lastMessage.response_audio?.transcript + transcript
                  }
                }
                return newMessages
              })
            } else if (
              chunk.event === RunEvent.ReasoningStep ||
              chunk.event === RunEvent.TeamReasoningStep
            ) {
              setMessages((prevMessages) => {
                const newMessages = [...prevMessages]
                const lastMessage = newMessages[newMessages.length - 1]
                if (lastMessage && lastMessage.role === 'agent') {
                  const existingSteps =
                    lastMessage.extra_data?.reasoning_steps ?? []
                  const incomingSteps = chunk.extra_data?.reasoning_steps ?? []
                  lastMessage.extra_data = {
                    ...lastMessage.extra_data,
                    reasoning_steps: [...existingSteps, ...incomingSteps]
                  }
                }
                return newMessages
              })
            } else if (
              chunk.event === RunEvent.ReasoningCompleted ||
              chunk.event === RunEvent.TeamReasoningCompleted
            ) {
              setMessages((prevMessages) => {
                const newMessages = [...prevMessages]
                const lastMessage = newMessages[newMessages.length - 1]
                if (lastMessage && lastMessage.role === 'agent') {
                  if (chunk.extra_data?.reasoning_steps) {
                    lastMessage.extra_data = {
                      ...lastMessage.extra_data,
                      reasoning_steps: chunk.extra_data.reasoning_steps
                    }
                  }
                }
                return newMessages
              })
            } else if (
              chunk.event === RunEvent.RunError ||
              chunk.event === RunEvent.TeamRunError ||
              chunk.event === RunEvent.TeamRunCancelled
            ) {
              updateMessagesWithErrorState()
              const errorContent =
                (chunk.content as string) ||
                (chunk.event === RunEvent.TeamRunCancelled
                  ? 'Run cancelled'
                  : 'Error during run')
              setStreamingErrorMessage(errorContent)
              if (newSessionId) {
                setSessionsData(
                  (prevSessionsData) =>
                    prevSessionsData?.filter(
                      (session) => session.session_id !== newSessionId
                    ) ?? null
                )
              }
            } else if (
              chunk.event === RunEvent.UpdatingMemory ||
              chunk.event === RunEvent.TeamMemoryUpdateStarted ||
              chunk.event === RunEvent.TeamMemoryUpdateCompleted
            ) {
              // No-op for now; could surface a lightweight UI indicator in the future
            } else if (
              chunk.event === RunEvent.RunCompleted ||
              chunk.event === RunEvent.TeamRunCompleted
            ) {
              setMessages((prevMessages) => {
                const newMessages = prevMessages.map((message, index) => {
                  if (
                    index === prevMessages.length - 1 &&
                    message.role === 'agent'
                  ) {
                    let updatedContent: string
                    if (typeof chunk.content === 'string') {
                      updatedContent = chunk.content
                    } else {
                      try {
                        updatedContent = JSON.stringify(chunk.content)
                      } catch {
                        updatedContent = 'Error parsing response'
                      }
                    }
                    return {
                      ...message,
                      content:
                        updatedContent && updatedContent.length > 0
                          ? updatedContent
                          : message.content,
                      tool_calls: processChunkToolCalls(
                        chunk,
                        message.tool_calls
                      ),
                      images: chunk.images ?? message.images,
                      videos: chunk.videos ?? message.videos,
                      response_audio: chunk.response_audio,
                      created_at: chunk.created_at ?? message.created_at,
                      extra_data: {
                        reasoning_steps:
                          chunk.extra_data?.reasoning_steps ??
                          message.extra_data?.reasoning_steps,
                        references:
                          chunk.extra_data?.references ??
                          message.extra_data?.references
                      }
                    }
                  }
                  return message
                })
                return newMessages
              })
            }
          },
          onError: (error) => {
            updateMessagesWithErrorState()
            setStreamingErrorMessage(error.message)
            if (newSessionId) {
              setSessionsData(
                (prevSessionsData) =>
                  prevSessionsData?.filter(
                    (session) => session.session_id !== newSessionId
                  ) ?? null
              )
            }
          },
          onComplete: () => {
            // Fallback: persist user message if not already persisted and we have a session id
            if (!userPersisted && newSessionId) {
              userPersisted = true
              postUserMessage(userDisplay).then(() => {
                setMessages((prev) => {
                  const len = prev.length
                  if (len >= 3) {
                    const thirdLast = prev[len - 3]
                    const secondLast = prev[len - 2]
                    const last = prev[len - 1]
                    if (
                      thirdLast?.role === 'user' &&
                      secondLast?.role === 'agent' &&
                      last?.role === 'user'
                    ) {
                      return [...prev.slice(0, len - 3), last, secondLast]
                    }
                  }
                  return prev
                })
              })
            }

            // Persist the final agent message using the last agent message in the store
            const state = useStore.getState()
            const msgs = state.messages
            const last = msgs[msgs.length - 1]
            if (last && last.role === 'agent') {
              postAgentMessage(last.content || '', {
                tool_calls: last.tool_calls,
                images: last.images,
                videos: last.videos,
                audio: last.audio,
                response_audio: last.response_audio,
                extra_data: last.extra_data
              }).then(() => {
                // Remove agent placeholder duplicate: keep only persisted agent
                setMessages((prev) => {
                  const len = prev.length
                  if (len >= 2) {
                    const lastMsg = prev[len - 1]
                    const secondLast = prev[len - 2]
                    if (
                      lastMsg?.role === 'agent' &&
                      secondLast?.role === 'agent'
                    ) {
                      return [...prev.slice(0, len - 2), lastMsg]
                    }
                  }
                  return prev
                })
              })
            }
          }
        })
      } catch (error) {
        updateMessagesWithErrorState()
        setStreamingErrorMessage(
          error instanceof Error ? error.message : String(error)
        )
        if (newSessionId) {
          setSessionsData(
            (prevSessionsData) =>
              prevSessionsData?.filter(
                (session) => session.session_id !== newSessionId
              ) ?? null
          )
        }
      } finally {
        focusChatInput()
        setIsStreaming(false)
      }
    },
    [
      setMessages,
      addMessage,
      updateMessagesWithErrorState,
      selectedEndpoint,
      streamResponse,
      agentId,
      teamId,
      mode,
      setStreamingErrorMessage,
      setIsStreaming,
      focusChatInput,
      setSessionsData,
      sessionId,
      setSessionId,
      processChunkToolCalls,
      postUserMessage,
      postAgentMessage,
      setFromStreamSession
    ]
  )

  return { handleStreamResponse }
}

export default useAIChatStreamHandler
