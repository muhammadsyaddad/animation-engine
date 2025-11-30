import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Next.js Middleware for auth-based server-side redirects.
 *
 * Behavior:
 * - If no valid (non-expired) auth cookie and route is protected → redirect to /auth
 * - If has valid auth cookie and route is /auth → redirect to /
 *
 * Notes:
 * - Middleware runs on the Edge and can only read cookies/headers/URL (no localStorage).
 * - Ensure your login flow sets a cookie named AUTH_COOKIE (see constant below).
 * - JWT 'exp' is validated here; expired tokens are treated as unauthenticated.
 */

const AUTH_COOKIE = 'auth_token'

// Paths that should never be intercepted by auth checks
const PUBLIC_PATH_PREFIXES = [
  '/_next', // Next.js internal assets
  '/favicon.ico',
  '/robots.txt',
  '/sitemap.xml',
  '/manifest.webmanifest',
  '/images',
  '/assets',
  '/static' // static assets if any are served by the UI
]

// File extensions to ignore (static files)
const PUBLIC_EXTENSIONS = [
  'svg',
  'png',
  'jpg',
  'jpeg',
  'gif',
  'webp',
  'ico',
  'css',
  'js',
  'map',
  'txt',
  'xml',
  'json',
  'woff',
  'woff2',
  'ttf',
  'otf'
]

function isPublicPath(pathname: string): boolean {
  // Exclude Next internal/public prefixes
  if (PUBLIC_PATH_PREFIXES.some((p) => pathname.startsWith(p))) return true

  // Exclude static files by extension
  const lastDot = pathname.lastIndexOf('.')
  if (lastDot !== -1) {
    const ext = pathname.slice(lastDot + 1).toLowerCase()
    if (PUBLIC_EXTENSIONS.includes(ext)) return true
  }

  // Allow API routes to pass through (UI-side APIs if any)
  if (pathname.startsWith('/api')) return true

  return false
}

function isAuthPage(pathname: string): boolean {
  return pathname === '/auth' || pathname.startsWith('/auth/')
}

/**
 * Decode a base64url string to UTF-8.
 */
function base64UrlDecode(input: string): string {
  // Replace URL-safe chars
  let str = input.replace(/-/g, '+').replace(/_/g, '/')
  // Pad with '='
  const pad = str.length % 4
  if (pad) str += '='.repeat(4 - pad)
  // atob is available in Edge runtime
  try {
    return atob(str)
  } catch {
    return ''
  }
}

/**
 * Returns true if the JWT is expired or invalid.
 */
function isJwtExpired(token: string): boolean {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return true
    const payloadJson = base64UrlDecode(parts[1])
    if (!payloadJson) return true
    const payload = JSON.parse(payloadJson) as { exp?: number }
    if (typeof payload.exp !== 'number') {
      // If no exp, treat as invalid (unauthenticated)
      return true
    }
    const now = Math.floor(Date.now() / 1000)
    return payload.exp <= now
  } catch {
    return true
  }
}

export function middleware(req: NextRequest) {
  const { nextUrl } = req
  const { pathname } = nextUrl

  const token = req.cookies.get(AUTH_COOKIE)?.value
  const hasToken = Boolean(token)
  const expired = token ? isJwtExpired(token) : false
  const hasValidToken = hasToken && !expired

  // Skip public paths
  if (isPublicPath(pathname)) {
    return NextResponse.next()
  }

  // If user is authenticated (valid token) and tries to access /auth, redirect to home
  if (hasValidToken && isAuthPage(pathname)) {
    const url = nextUrl.clone()
    url.pathname = '/'
    return NextResponse.redirect(url)
  }

  // If user is not authenticated (no token or expired) and tries to access a protected route, redirect to /auth
  if (!hasValidToken && !isAuthPage(pathname)) {
    const url = nextUrl.clone()
    url.pathname = '/auth'
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

// Apply middleware to all routes except known static/image assets and api by using matcher.
// Note: We still re-check inside the middleware for robustness.
export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml|manifest.webmanifest|images|assets|static|api).*)'
  ]
}
