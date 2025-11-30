import { NextRequest, NextResponse } from 'next/server'

/**
 * Logout endpoint
 *
 * Clears HttpOnly authentication cookies so middleware treats the user
 * as unauthenticated on subsequent requests.
 *
 * Usage:
 * fetch('/api/auth/logout', { method: 'POST' })
 */
function buildLogoutResponse() {
  const isProd = process.env.NODE_ENV === 'production'
  const res = NextResponse.json({ ok: true }, { status: 200 })

  // Clear primary auth token
  res.cookies.set({
    name: 'auth_token',
    value: '',
    httpOnly: true,
    sameSite: 'lax',
    secure: isProd,
    path: '/',
    maxAge: 0,
    expires: new Date(0)
  })

  // Optional: clear refresh token if you also set it in your login/register routes
  res.cookies.set({
    name: 'refresh_token',
    value: '',
    httpOnly: true,
    sameSite: 'lax',
    secure: isProd,
    path: '/',
    maxAge: 0,
    expires: new Date(0)
  })

  return res
}

export async function POST(_req: NextRequest) {
  return buildLogoutResponse()
}

// Optional convenience: allow GET to logout as well (useful for link-based sign-out)
export async function GET(_req: NextRequest) {
  return buildLogoutResponse()
}
