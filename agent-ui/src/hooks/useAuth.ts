import { useCallback, useEffect, useMemo } from 'react'
import { useStore } from '@/store'

/**
 * useAuth
 *
 * Abstraction layer over the auth slice in the zustand store providing:
 * - Reactive user & token access
 * - Derived authentication status
 * - Token payload decoding (exp, iat)
 * - Login / register integration helper (expects caller to supply AuthResponse)
 * - Logout helper (clears store, localStorage, cookie)
 * - Automatic persistence (localStorage + auth cookie for middleware)
 *
 * This hook intentionally does NOT perform network requests directly.
 * You still call the API functions (loginAPI, registerAPI, meAPI) externally,
 * then feed their results into loginFromResponse().
 *
 * If future migration to Supabase/Auth provider happens, only this hook and the
 * store slice need adjustment, minimizing refactors across components.
 */

/* -------------------------------------------------------------------------- */
/* Types                                                                      */
/* -------------------------------------------------------------------------- */

export interface DecodedToken {
  raw: string
  header?: Record<string, unknown>
  payload?: {
    sub?: string
    iat?: number
    exp?: number
    [key: string]: unknown
  }
  expiresInSeconds?: number
  isExpired: boolean
  valid: boolean
}

export interface AuthUser {
  id: string
  email: string
  display_name?: string | null
  avatar_url?: string | null
  created_at?: string | null
  last_login_at?: string | null
}

export interface AuthResponse {
  access_token: string
  refresh_token?: string
  token_type?: string
  user: AuthUser
}

export interface UseAuth {
  user: AuthUser | undefined
  accessToken: string | undefined
  isAuthenticated: boolean
  decoded: DecodedToken | null
  expiresInSeconds: number | null
  isExpired: boolean
  loginFromResponse: (resp: AuthResponse) => void
  logout: () => void
  setUser: (u: AuthUser | null) => void
  setAccessToken: (t: string | null) => void
}

/* -------------------------------------------------------------------------- */
/* Constants                                                                  */
/* -------------------------------------------------------------------------- */

const ACCESS_TOKEN_KEY = 'agentui_access_token'
const AUTH_USER_KEY = 'agentui_auth_user'
const AUTH_COOKIE_NAME = 'auth_token'
const COOKIE_DEFAULT_MAX_AGE = 900 // fallback if exp missing
const EXP_BUFFER_SECONDS = 5 // subtract small buffer to avoid race near expiry

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

/**
 * decodeJwt (no signature verification; client-side convenience only)
 */
function decodeJwt(token: string): DecodedToken {
  if (!token || typeof token !== 'string') {
    return { raw: token, isExpired: true, valid: false }
  }
  const parts = token.split('.')
  if (parts.length !== 3) {
    return { raw: token, isExpired: true, valid: false }
  }

  let header: Record<string, unknown> | undefined
  let payload: Record<string, unknown> | undefined

  try {
    const h = parts[0].replace(/-/g, '+').replace(/_/g, '/')
    const p = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    header = JSON.parse(atob(h))
    payload = JSON.parse(atob(p))
  } catch {
    return { raw: token, isExpired: true, valid: false }
  }

  let exp: number | undefined
  if (
    payload &&
    typeof payload === 'object' &&
    'exp' in payload &&
    typeof (payload as Record<string, unknown>).exp === 'number'
  ) {
    exp = (payload as Record<string, unknown>).exp as number
  } else {
    exp = undefined
  }
  const now = Math.floor(Date.now() / 1000)
  const isExpired = exp ? now >= exp : true
  const expiresInSeconds = exp ? Math.max(0, exp - now) : undefined

  return {
    raw: token,
    header,
    payload: payload as DecodedToken['payload'],
    expiresInSeconds,
    isExpired,
    valid: true
  }
}

/**
 * persistAuthLocally
 * Sync store values to localStorage + auth cookie (for middleware).
 */
function persistAuthLocally(token: string, user: AuthUser) {
  try {
    localStorage.setItem(ACCESS_TOKEN_KEY, token)
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
  } catch {
    /* ignore storage failures */
  }

  // Derive cookie max-age from exp claim (with buffer)
  let maxAge = COOKIE_DEFAULT_MAX_AGE
  const decoded = decodeJwt(token)
  if (decoded.valid && decoded.payload?.exp) {
    const now = Math.floor(Date.now() / 1000)
    const delta = decoded.payload.exp - now - EXP_BUFFER_SECONDS
    if (delta > 0) maxAge = delta
  }

  document.cookie = `${AUTH_COOKIE_NAME}=${token}; Path=/; Max-Age=${maxAge}; SameSite=Lax`
}

/**
 * clearAuthLocally
 * Remove token/user from localStorage and clear cookie.
 */
function clearAuthLocally() {
  try {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(AUTH_USER_KEY)
  } catch {
    /* ignore */
  }
  document.cookie = `${AUTH_COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax`
}

/* -------------------------------------------------------------------------- */
/* Hook                                                                       */
/* -------------------------------------------------------------------------- */

export function useAuth(): UseAuth {
  const user = useStore((s) => s.authUser)
  const accessToken = useStore((s) => s.accessToken)
  const setAuthUser = useStore((s) => s.setAuthUser)
  const setAccessToken = useStore((s) => s.setAccessToken)
  const logoutStore = useStore((s) => s.logout)

  // Derived decoded token
  const decoded = useMemo(
    () => (accessToken ? decodeJwt(accessToken) : null),
    [accessToken]
  )

  const isAuthenticated = Boolean(
    accessToken && user && decoded && decoded.valid && !decoded.isExpired
  )
  const expiresInSeconds = decoded?.expiresInSeconds ?? null
  const isExpired = decoded?.isExpired ?? true

  /**
   * loginFromResponse
   * Called after successful login/register API call.
   */
  const loginFromResponse = useCallback(
    (resp: AuthResponse) => {
      if (!resp || !resp.access_token || !resp.user) return
      setAccessToken(resp.access_token)
      setAuthUser({
        id: resp.user.id,
        email: resp.user.email,
        display_name: resp.user.display_name,
        avatar_url: resp.user.avatar_url
      })
      persistAuthLocally(resp.access_token, resp.user)
      // Broadcast
      window.dispatchEvent(
        new CustomEvent('auth:login', {
          detail: { token: resp.access_token, user: resp.user }
        })
      )
    },
    [setAccessToken, setAuthUser]
  )

  /**
   * logout
   * Clears store + local persistence + cookie.
   */
  const logout = useCallback(() => {
    logoutStore()
    clearAuthLocally()
    window.dispatchEvent(new CustomEvent('auth:logout'))
  }, [logoutStore])

  /**
   * Hydrate store from localStorage if empty (initial load / refresh).
   */
  useEffect(() => {
    if (accessToken || user) return
    try {
      const token = localStorage.getItem(ACCESS_TOKEN_KEY)
      const rawUser = localStorage.getItem(AUTH_USER_KEY)
      if (token) setAccessToken(token)
      if (rawUser) {
        const parsed = JSON.parse(rawUser) as AuthUser
        setAuthUser({
          id: parsed.id,
          email: parsed.email,
          display_name: parsed.display_name,
          avatar_url: parsed.avatar_url
        })
      }
    } catch {
      /* ignore */
    }
  }, [accessToken, user, setAccessToken, setAuthUser])

  return {
    user: user as AuthUser | undefined,
    accessToken,
    isAuthenticated,
    decoded,
    expiresInSeconds,
    isExpired,
    loginFromResponse,
    logout,
    setUser: (u: AuthUser | null) =>
      setAuthUser(
        u
          ? {
              id: u.id,
              email: u.email,
              display_name: u.display_name,
              avatar_url: u.avatar_url
            }
          : null
      ),
    setAccessToken: (t: string | null) => setAccessToken(t)
  }
}

/* -------------------------------------------------------------------------- */
/* Optional: Hook for auto-logout near expiry (example placeholder)           */
/* -------------------------------------------------------------------------- */
/*
import { useRef } from 'react'
export function useAutoLogout(thresholdSeconds = 5) {
  const { expiresInSeconds, logout, isAuthenticated } = useAuth()
  const triggeredRef = useRef(false)
  useEffect(() => {
    if (!isAuthenticated || triggeredRef.current) return
    if (expiresInSeconds != null && expiresInSeconds <= thresholdSeconds) {
      triggeredRef.current = true
      logout()
    }
  }, [expiresInSeconds, logout, isAuthenticated, thresholdSeconds])
}
*/
