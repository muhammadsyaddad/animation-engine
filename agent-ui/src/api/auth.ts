import { toast } from 'sonner'

// Base URL helper ensures no trailing slash and consistent prefix
// NOTE: For auth, prefer routing through local Next.js API routes (/api/auth/*)
// so we can set HttpOnly cookies server-side for middleware to read securely.
const baseUrl = (endpoint: string) => `${endpoint.replace(/\/$/, '')}/v1/auth`

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
  refresh_token: string
  token_type: string
  user: AuthUser
}

interface RegisterParams {
  email: string
  password: string
  display_name?: string
}

interface LoginParams {
  email: string
  password: string
}

// Shared fetch options builder
function jsonOptions(method: string, body?: unknown): RequestInit {
  return {
    method,
    headers: {
      'Content-Type': 'application/json'
    },
    body: body ? JSON.stringify(body) : undefined
  }
}

async function parseJSON<T>(res: Response): Promise<T> {
  try {
    return (await res.json()) as T
  } catch {
    throw new Error('Invalid JSON response')
  }
}

/**
 * TODO: Migrate this client call to the local Next.js API route (/api/auth/register)
 * to set HttpOnly cookies server-side for better security and reliable middleware checks.
 * Current direct call to the backend should be phased out once the proxy route is in use.
 */
export async function registerAPI(
  endpoint: string,
  params: RegisterParams
): Promise<AuthResponse | null> {
  try {
    const res = await fetch(
      `${baseUrl(endpoint)}/register`,
      jsonOptions('POST', params)
    )
    if (!res.ok) {
      const text = await res.text()
      toast.error(`Register failed: ${text || res.status}`)
      return null
    }
    return await parseJSON<AuthResponse>(res)
  } catch (err) {
    toast.error(`Register error: ${(err as Error).message}`)
    return null
  }
}

/**
 * TODO: Migrate this client call to the local Next.js API route (/api/auth/login)
 * to set HttpOnly cookies server-side for better security and reliable middleware checks.
 * Current direct call to the backend should be phased out once the proxy route is in use.
 */
export async function loginAPI(
  endpoint: string,
  params: LoginParams
): Promise<AuthResponse | null> {
  try {
    const res = await fetch(
      `${baseUrl(endpoint)}/login`,
      jsonOptions('POST', params)
    )
    if (!res.ok) {
      if (res.status === 401) {
        toast.error('Invalid credentials')
      } else {
        toast.error(`Login failed: ${res.statusText}`)
      }
      return null
    }
    return await parseJSON<AuthResponse>(res)
  } catch (err) {
    toast.error(`Login error: ${(err as Error).message}`)
    return null
  }
}

export async function meAPI(
  endpoint: string,
  accessToken: string
): Promise<AuthUser | null> {
  if (!accessToken) return null
  try {
    const res = await fetch(`${baseUrl(endpoint)}/me`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${accessToken}`
      }
    })
    if (!res.ok) {
      if (res.status !== 401) {
        toast.error(`Failed to load profile: ${res.statusText}`)
      }
      return null
    }
    const data = await parseJSON<{ user: AuthUser }>(res)
    return data.user
  } catch (err) {
    toast.error(`Profile error: ${(err as Error).message}`)
    return null
  }
}

// Placeholder for future refresh token implementation
// export async function refreshAPI(endpoint: string, refreshToken: string): Promise<AuthResponse | null> { ... }
