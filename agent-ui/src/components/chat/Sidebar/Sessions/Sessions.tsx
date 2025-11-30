'use client'

/**
 * Sessions.tsx
 *
 * Sidebar list component for persisted chat sessions (backend /v1/chat).
 * Rewired to use useChatSession() which manages:
 *  - Loading sessions (listChatSessions)
 *  - Selecting a session (getChatSession + messages)
 *  - SessionItem now provides rename & delete actions (kebab menu).
 *
 * Lifecycle:
 *  - On mount (and whenever endpoint changes + store hydrated): loadSessions()
 *  - If ?session query param exists: selectSession(sessionId)
 *  - Clicking a session row: selectSession(id) + updates query param
 *
 * Visual:
 *  - Skeleton loaders while fetching
 *  - Blank state if no sessions
 *  - Scroll container with subtle scrollbar behavior
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { useQueryState } from 'nuqs'
import { useStore } from '@/store'
import { useChatSession } from '../../../../hooks/useChatSession'
import SessionBlankState from './SessionBlankState'
import SessionItem from './SessionItem'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

/* ------------------------------ Skeleton List ------------------------------ */

function SkeletonList({ count }: { count: number }) {
  const items = useMemo(
    () => Array.from({ length: count }, (_, i) => i),
    [count]
  )
  return (
    <>
      {items.map((k, idx) => (
        <Skeleton
          key={k}
          className={cn(
            'mb-1 h-11 rounded-lg px-3 py-2',
            idx > 0 && 'bg-background-secondary'
          )}
        />
      ))}
    </>
  )
}

/* --------------------------------- Component ------------------------------- */

export default function Sessions() {
  const {
    hydrated,
    selectedEndpoint,
    isEndpointLoading,
    isEndpointActive,
    sessionsData,
    setSessionsData,
    isSessionsLoading,
    setIsSessionsLoading
  } = useStore()

  const { loadSessions, selectSession, currentSessionId } = useChatSession()

  const [querySessionId] = useQueryState('session')
  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [isScrollbarHidden, setIsScrollbarHidden] = useState(false)

  /* ------------------------------ Scroll Behavior ------------------------------ */

  const handleScroll = () => {
    setIsScrollbarHidden(true)
    if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current)
    scrollTimeoutRef.current = setTimeout(() => {
      setIsScrollbarHidden(false)
    }, 1200)
  }

  useEffect(
    () => () => {
      if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current)
    },
    []
  )

  /* ------------------------------- Load Sessions ------------------------------- */

  useEffect(() => {
    if (!hydrated) return
    if (!selectedEndpoint || isEndpointLoading) return
    setSessionsData([])
    setIsSessionsLoading(true)
    loadSessions({ userOnly: true })
      .catch((e) => {
        // errors already toasted in hook
        console.debug('loadSessions error', e)
      })
      .finally(() => setIsSessionsLoading(false))
  }, [
    hydrated,
    selectedEndpoint,
    isEndpointLoading,
    loadSessions,
    setIsSessionsLoading,
    setSessionsData
  ])

  /* ----------------------------- Select via Query ----------------------------- */

  useEffect(() => {
    if (
      hydrated &&
      selectedEndpoint &&
      !isEndpointLoading &&
      querySessionId &&
      sessionsData &&
      sessionsData.length > 0
    ) {
      selectSession(querySessionId).catch(() => {
        /* already toasted in hook */
      })
    }
  }, [
    hydrated,
    selectedEndpoint,
    isEndpointLoading,
    querySessionId,
    sessionsData,
    selectSession
  ])

  /* --------------------------------- Render ---------------------------------- */

  if (isSessionsLoading || isEndpointLoading) {
    return (
      <div className="w-full">
        <div className="mb-2 text-xs font-medium uppercase">Sessions</div>
        <div className="mt-4 h-[calc(100vh-325px)] w-full overflow-y-auto">
          <SkeletonList count={5} />
        </div>
      </div>
    )
  }

  return (
    <div className="w-full">
      <div className="mb-2 w-full text-xs font-medium uppercase">Sessions</div>
      <div
        className={cn(
          'h-[calc(100vh-345px)] overflow-y-auto pr-1 font-geist transition-all duration-300',
          '[&::-webkit-scrollbar]:w-1',
          isScrollbarHidden
            ? '[&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-background [&::-webkit-scrollbar]:opacity-0'
            : '[&::-webkit-scrollbar]:opacity-100'
        )}
        onScroll={handleScroll}
        onMouseOver={() => setIsScrollbarHidden(true)}
        onMouseLeave={handleScroll}
      >
        {!isEndpointActive ||
        (!isSessionsLoading && (!sessionsData || sessionsData.length === 0)) ? (
          <SessionBlankState />
        ) : (
          <div className="flex flex-col gap-y-1">
            {sessionsData?.map((entry) => (
              <SessionItem
                key={entry.session_id}
                isSelected={currentSessionId === entry.session_id}
                onSessionClick={() => {
                  // select handled inside item if needed
                }}
                session_id={entry.session_id}
                session_name={entry.session_name}
                created_at={entry.created_at}
                updated_at={entry.updated_at}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
