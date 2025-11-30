import { NextRequest, NextResponse } from 'next/server'

// Default backend Agent API base URL
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

type MeResponse = {
  user: AuthUser
}

function getBaseUrl(req: NextRequest): string {
  // Allow overriding via header
  const headerOverride = req.headers.get('x-agent-endpoint')
  if (headerOverride && typeof headerOverride === 'string') {
    return headerOverride.replace(/\/$/, '')
  }
  // Or query param (useful for local testing)
  const url = new URL(req.url)
  const queryOverride = url.searchParams.get('endpoint')
  if (queryOverride) {
    return queryOverride.replace(/\/$/, '')
  }
  return DEFAULT_AGENT_API.replace(/\/$/, '')
}

export async function GET(req: NextRequest) {
  // Read HttpOnly cookie set by /api/auth/login
  const token = req.cookies.get('auth_token')?.value
  if (!token) {
    return NextResponse.json({ error: 'Unauthenticated' }, { status: 401 })
  }

  const endpoint = getBaseUrl(req)
  const url = `${endpoint}/v1/auth/me`

  try {
    const upstream = await fetch(url, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`
      },
      // Ensure we never cache auth-sensitive responses
      cache: 'no-store'
    })

    if (upstream.status === 401) {
      return NextResponse.json({ error: 'Unauthenticated' }, { status: 401 })
    }

    if (!upstream.ok) {
      // Pass through backend detail if available, else generic error
      let detail: unknown = null
      try {
        detail = await upstream.json()
      } catch {
        /* ignore parse error */
      }
      const message =
        (detail &&
          typeof detail === 'object' &&
          'detail' in detail &&
          typeof (detail as { detail?: unknown }).detail !== 'undefined' &&
          String((detail as { detail?: unknown }).detail)) ||
        upstream.statusText ||
        'Failed to fetch profile'
      return NextResponse.json(
        { error: message, status: upstream.status },
        { status: 502 }
      )
    }

    const data = (await upstream.json()) as MeResponse
    return NextResponse.json(data, { status: 200 })
  } catch (err) {
    return NextResponse.json(
      { error: (err as Error).message || 'Unexpected error' },
      { status: 500 }
    )
  }
}
