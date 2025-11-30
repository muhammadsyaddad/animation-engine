'use client'

import { useEffect } from 'react'
import { useStore } from '@/store'

type AuthUser = {
  id: string
  email: string
  display_name?: string | null
  avatar_url?: string | null
}

/**
 * HeaderUserBadge
 *
 * - On mount, fetches `/api/auth/me` once if `authUser` is not yet in the store.
 * - Sets `authUser` in the zustand store when the cookie is valid.
 * - Renders a tiny badge with the user's email if available; renders nothing otherwise.
 *
 * Usage:
 *   import HeaderUserBadge from '@/components/layout/HeaderUserBadge'
 *   ...
 *   <HeaderUserBadge />
 */
export default function HeaderUserBadge() {
  const authUser = useStore((s) => s.authUser)
  const setAuthUser = useStore((s) => s.setAuthUser)

  useEffect(() => {
    let cancelled = false
    if (authUser) return

    const hydrateUser = async () => {
      try {
        const res = await fetch('/api/auth/me', { method: 'GET', cache: 'no-store' })
        if (!res.ok) return
        const data = (await res.json()) as { user?: AuthUser } | null
        if (!cancelled && data?.user) {
          setAuthUser({
            id: data.user.id,
            email: data.user.email,
            display_name: data.user.display_name ?? null,
            avatar_url: data.user.avatar_url ?? null
          })
        }
      } catch {
        // Silently ignore; middleware will gate protected routes anyway.
      }
    }

    void hydrateUser()
    return () => {
      cancelled = true
    }
  }, [authUser, setAuthUser])

  if (!authUser) return null

  return (
    <div className="inline-flex items-center gap-2 rounded-md border border-primary/10 bg-muted px-2 py-1 text-xs text-foreground/80">
      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary/20 text-[10px] font-semibold text-primary">
        {authUser.email?.[0]?.toUpperCase() || 'U'}
      </span>
      <span className="truncate max-w-[180px]">{authUser.email}</span>
    </div>
  )
}
