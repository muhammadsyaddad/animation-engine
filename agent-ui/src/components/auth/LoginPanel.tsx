'use client'

import { useEffect, useMemo, useState, useCallback } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import type { AuthUser } from '@/api/auth'
import { useStore } from '@/store'

type Mode = 'login' | 'register'

export default function LoginPanel() {
  const selectedEndpoint = useStore((s) => s.selectedEndpoint)
  const authUser = useStore((s) => s.authUser)

  const setAuthUserStore = useStore((s) => s.setAuthUser)

  const logoutStore = useStore((s) => s.logout)

  const [mode, setMode] = useState<Mode>('login')
  const [loading, setLoading] = useState(false)

  // Form fields
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')

  const endpoint = useMemo(
    () => selectedEndpoint?.replace(/\/$/, ''),
    [selectedEndpoint]
  )

  useEffect(() => {
    let mounted = true

    const loadSession = async () => {
      try {
        const resp = await fetch('/api/auth/me')
        if (!resp.ok) return
        const data = await resp.json().catch(() => null)
        if (!mounted || !data) return

        if (data.user) {
          const user = data.user as AuthUser
          setAuthUserStore({
            id: user.id,
            email: user.email,
            display_name: user.display_name,
            avatar_url: user.avatar_url
          })
        }
      } catch (err) {
        console.error('loadSession error', err)
      }
    }
    void loadSession()
    return () => {
      mounted = false
    }
  }, [setAuthUserStore])

  // Define clearAuthState before effects that reference it
  const clearAuthState = useCallback(() => {
    logoutStore()
    window.dispatchEvent(new CustomEvent('auth:logout'))
  }, [logoutStore])

  const storeUser = (user: AuthUser) => {
    setAuthUserStore({
      id: user.id,
      email: user.email,
      display_name: user.display_name,
      avatar_url: user.avatar_url
    })
  }

  // clearAuthState moved above

  const handleSubmit = async () => {
    if (!email || !password) return

    setLoading(true)
    try {
      if (mode === 'login') {
        const resp = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, endpoint })
        })
        if (!resp.ok) {
          const data = await resp.json().catch(() => null)
          toast.error(
            data?.error
              ? String(data.error)
              : `Login failed: ${resp.statusText}`
          )
          return
        }
        const res = (await resp.json()) as {
          access_token: string
          user: AuthUser
        }
        storeUser(res.user)
        // Persist access token (for direct backend calls needing Bearer)
        try {
          localStorage.setItem('agentui_access_token', res.access_token)
        } catch {}
        toast.success('Logged in')
      } else {
        const resp = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email,
            password,
            display_name: displayName || undefined,
            endpoint
          })
        })
        if (!resp.ok) {
          const data = await resp.json().catch(() => null)
          toast.error(
            data?.error
              ? String(data.error)
              : `Register failed: ${resp.statusText}`
          )
          return
        }
        const res = (await resp.json()) as {
          access_token: string
          user: AuthUser
        }
        storeUser(res.user)
        // Persist access token after registration
        try {
          localStorage.setItem('agentui_access_token', res.access_token)
        } catch {}
        toast.success('Registered & logged in')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' })
    clearAuthState()
    // Remove persisted token
    try {
      localStorage.removeItem('agentui_access_token')
    } catch {}
    toast.success('Logged out')
  }

  if (authUser) {
    return (
      <div className="space-y-2 border border-primary/15 bg-accent p-3 text-xs">
        <div className="text-primary">Account</div>
        <div className="flex flex-col gap-0.5">
          <div className="font-medium">{authUser.email}</div>
          {authUser.display_name ? (
            <div className="italic text-muted">{authUser.display_name}</div>
          ) : null}
        </div>
        <Button
          variant="secondary"
          size="sm"
          className="w-full"
          onClick={handleLogout}
        >
          Logout
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-3 rounded-xl border border-primary/15 bg-accent p-3 text-xs">
      <div className="flex items-center justify-between">
        <div className="text-primary">Auth</div>
        <div className="flex gap-1">
          <button
            type="button"
            className={`rounded px-2 py-1 ${mode === 'login' ? 'bg-primary text-background' : 'bg-background/30 text-muted'}`}
            onClick={() => setMode('login')}
          >
            Login
          </button>
          <button
            type="button"
            className={`rounded px-2 py-1 ${mode === 'register' ? 'bg-primary text-background' : 'bg-background/30 text-muted'}`}
            onClick={() => setMode('register')}
          >
            Register
          </button>
        </div>
      </div>

      <div className="space-y-2">
        <input
          type="email"
          className="w-full rounded-xl border border-primary/15 bg-background px-3 py-2 text-xs"
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
        />
        <input
          type="password"
          className="w-full rounded-xl border border-primary/15 bg-background px-3 py-2 text-xs"
          placeholder="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
        />
        {mode === 'register' && (
          <input
            className="w-full rounded-xl border border-primary/15 bg-background px-3 py-2 text-xs"
            placeholder="display name (optional)"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            autoComplete="nickname"
          />
        )}
      </div>

      <Button
        size="sm"
        className="w-full text-black"
        disabled={loading || !email || !password}
        onClick={handleSubmit}
      >
        {loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Register'}
      </Button>
    </div>
  )
}
