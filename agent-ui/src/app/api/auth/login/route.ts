import { NextRequest, NextResponse } from 'next/server'

// Environment variable for backend Agent API base URL
// Example: http://localhost:8000 or https://api.example.com
const DEFAULT_AGENT_API =
  process.env.AGENT_API_ENDPOINT || 'http://localhost:8000'

type AuthUser = {
  id: string
  email: string
  display_name?: string | null
  avatar_url?: string | null
  created_at?: string | null
  last_login_at?: string | null
}

type AuthResponse = {
  access_token: string
  refresh_token: string
  token_type: string
  user: AuthUser
}

type LoginBody = {
  email?: string
  password?: string
  // Optional override if needed (use with caution)
  endpoint?: string
}

/**
 * Decode base64url string to JSON object
 */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const pad = base64.length % 4
    const padded = pad ? base64 + '='.repeat(4 - pad) : base64
    const json = Buffer.from(padded, 'base64').toString('utf-8')
    return JSON.parse(json)
  } catch {
    return null
  }
}

/**
 * Compute cookie maxAge from JWT exp (seconds) if available.
 * Fallback to 15 minutes.
 */
function maxAgeFromJwt(token: string, fallbackSeconds = 15 * 60): number {
  const payload = decodeJwtPayload(token)
  if (!payload) return fallbackSeconds
  const exp = typeof payload.exp === 'number' ? payload.exp : undefined
  if (!exp) return fallbackSeconds
  const now = Math.floor(Date.now() / 1000)
  const delta = exp - now - 5 // subtract small buffer
  return delta > 0 ? delta : 0
}

function getBaseUrl(req: NextRequest, override?: string): string {
  if (override && typeof override === 'string') {
    return override.replace(/\/$/, '')
  }
  const headerOverride = req.headers.get('x-agent-endpoint') || ''
  if (headerOverride) {
    return headerOverride.replace(/\/$/, '')
  }
  return DEFAULT_AGENT_API.replace(/\/$/, '')
}

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json()) as LoginBody
    const email = (body.email || '').trim()
    const password = (body.password || '').trim()
    const endpoint = getBaseUrl(req, body.endpoint)

    if (!email || !password) {
      return NextResponse.json(
        { error: 'Email and password are required' },
        { status: 400 }
      )
    }

    const url = `${endpoint}/v1/auth/login`
    const upstream = await fetch(url, {
      method: 'POST',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    })

    if (!upstream.ok) {
      let detail: unknown = null
      try {
        detail = await upstream.json()
      } catch {
        // ignore parse error
      }
      const message =
        (detail &&
          typeof detail === 'object' &&
          (detail as any).detail &&
          String((detail as any).detail)) ||
        upstream.statusText ||
        'Login failed'
      return NextResponse.json(
        { error: message, status: upstream.status },
        { status: upstream.status }
      )
    }

    const data = (await upstream.json()) as AuthResponse

    // Set HttpOnly cookie with access token for middleware consumption
    const isProd = process.env.NODE_ENV === 'production'
    const maxAge = maxAgeFromJwt(data.access_token)

    const res = NextResponse.json(
      {
        // Return same shape for compatibility; you can omit token fields on the client later
        access_token: data.access_token,
        refresh_token: data.refresh_token,
        token_type: data.token_type,
        user: data.user
      },
      { status: 200 }
    )

    res.cookies.set({
      name: 'auth_token',
      value: data.access_token,
      httpOnly: true,
      sameSite: 'lax',
      secure: isProd,
      path: '/',
      maxAge
    })

    // Optional: forward refresh token as httpOnly cookie too (commented out)
    // if (data.refresh_token) {
    //   res.cookies.set({
    //     name: 'refresh_token',
    //     value: data.refresh_token,
    //     httpOnly: true,
    //     sameSite: 'lax',
    //     secure: isProd,
    //     path: '/',
    //     // set an appropriate maxAge or rely on backend rotation policy
    //   })
    // }

    return res
  } catch (err) {
    return NextResponse.json(
      { error: (err as Error).message || 'Unexpected error' },
      { status: 500 }
    )
  }
}
