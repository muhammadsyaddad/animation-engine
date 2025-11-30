'use client'

import Link from 'next/link'

import LoginPanel from '@/components/auth/LoginPanel'
import { Button } from '@/components/ui/button'
import { useStore } from '@/store'

/**
 * /auth Page
 *
 * Dedicated authentication page separated from the main chat + sidebar layout.
 * Renders the LoginPanel standalone, centered on the screen.
 *
 * Behavior:
 * - Shows a simple header and the LoginPanel.
 * - If the user is already authenticated (detected via localStorage token),
 *   optionally offers navigation back to the main app (/).
 *
 * Note:
 * - Current LoginPanel maintains its own local auth state and syncs with localStorage.
 * - If later you move auth state to a global store (zustand), you can enhance this page
 *   to redirect automatically when logged in.
 */

export default function AuthPage() {
  const authUser = useStore((s) => s.authUser)
  // removed local token state (cookie-only auth)

  /* removed legacy localStorage token check (cookie-only auth) */

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-8">
      <div className="mb-6 flex flex-col items-center gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">
          Authentication
        </h1>
        <p className="max-w-sm text-center text-sm text-muted">
          Sign in or create an account to use protected features and have your
          runs & datasets attributed to you.
        </p>
        {authUser && (
          <Link
            href="/"
            className="rounded bg-positive/10 px-3 py-1 text-xs text-positive hover:underline"
          >
            Go to App
          </Link>
        )}
      </div>

      <div className="w-full max-w-sm">
        <LoginPanel />
      </div>

      <div className="mt-6 flex gap-2 text-xs">
        <Link href="/" className="text-primary hover:underline">
          Back to App
        </Link>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            // Manual refresh if needed
            location.reload()
          }}
        >
          Refresh
        </Button>
      </div>
    </div>
  )
}
