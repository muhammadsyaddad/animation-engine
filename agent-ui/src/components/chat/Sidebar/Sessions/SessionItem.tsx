'use client'

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQueryState } from 'nuqs'
import { toast } from 'sonner'

import { SessionEntry } from '@/types/os'
import { useChatSession } from '../../../../hooks/useChatSession'
import { Button } from '../../../ui/button'
import Icon from '@/components/ui/icon'
import { cn } from '@/lib/utils'
import DeleteSessionModal from './DeleteSessionModal'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'

type SessionItemProps = SessionEntry & {
  isSelected: boolean
  onSessionClick: () => void
}

export default function SessionItem({
  session_name: title,
  session_id,
  isSelected,
  onSessionClick
}: SessionItemProps) {
  const [, setSessionIdQuery] = useQueryState('session')

  const {
    selectSession,
    deleteCurrentSession,
    renameCurrentSession,
    currentSessionId,
    clearLocalSession
  } = useChatSession()

  // kebab menu
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)

  // rename dialog
  const [renameOpen, setRenameOpen] = useState(false)
  const [renameValue, setRenameValue] = useState(title ?? '')
  const [isRenaming, setIsRenaming] = useState(false)

  // delete dialog
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const isActive = useMemo(
    () => currentSessionId === session_id,
    [currentSessionId, session_id]
  )

  useEffect(() => {
    setRenameValue(title ?? '')
  }, [title])

  // Close kebab on outside click
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!menuOpen) return
      const target = e.target as Node
      if (menuRef.current && !menuRef.current.contains(target)) {
        setMenuOpen(false)
      }
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onEsc)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onEsc)
    }
  }, [menuOpen])

  const handleOpenSession = useCallback(async () => {
    onSessionClick()
    try {
      await selectSession(session_id)
      setSessionIdQuery(session_id)
    } catch (e) {
      toast.error(
        `Failed to open session: ${e instanceof Error ? e.message : String(e)}`
      )
    }
  }, [onSessionClick, selectSession, session_id, setSessionIdQuery])

  const handleStartRename = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      setMenuOpen(false)
      setRenameValue(title ?? '')
      setRenameOpen(true)
    },
    [title]
  )

  const handleConfirmRename = useCallback(async () => {
    const newName = renameValue.trim()
    setIsRenaming(true)
    try {
      // ensure active
      if (!isActive) {
        await selectSession(session_id)
        setSessionIdQuery(session_id)
      }
      const ok = await renameCurrentSession(newName.length > 0 ? newName : null)
      if (ok) {
        toast.success('Session renamed')
        setRenameOpen(false)
      } else {
        toast.error('Failed to rename session')
      }
    } catch (e) {
      toast.error(
        `Failed to rename session: ${e instanceof Error ? e.message : String(e)}`
      )
    } finally {
      setIsRenaming(false)
    }
  }, [
    isActive,
    selectSession,
    session_id,
    setSessionIdQuery,
    renameCurrentSession,
    renameValue
  ])

  const handleStartDelete = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    setMenuOpen(false)
    setDeleteOpen(true)
  }, [])

  const handleConfirmDelete = useCallback(async () => {
    setIsDeleting(true)
    try {
      // ensure active
      if (!isActive) {
        await selectSession(session_id)
        setSessionIdQuery(session_id)
      }
      const ok = await deleteCurrentSession()
      if (ok) {
        // clear local state if we just deleted the active session
        clearLocalSession()
        toast.success('Session deleted')
      } else {
        toast.error('Failed to delete session')
      }
    } catch (e) {
      toast.error(
        `Failed to delete session: ${e instanceof Error ? e.message : String(e)}`
      )
    } finally {
      setDeleteOpen(false)
      setIsDeleting(false)
    }
  }, [
    isActive,
    selectSession,
    session_id,
    setSessionIdQuery,
    deleteCurrentSession,
    clearLocalSession
  ])

  return (
    <>
      <div
        className={cn(
          'group relative flex h-11 w-full items-center justify-between rounded-lg px-3 py-2 transition-colors duration-200',
          isSelected
            ? 'cursor-default bg-primary/10'
            : 'cursor-pointer bg-background-secondary hover:bg-background-secondary/80'
        )}
        onClick={handleOpenSession}
      >
        <div className="flex min-w-0 flex-col gap-1">
          <h4
            className={cn(
              'truncate text-sm font-medium',
              isSelected && 'text-primary'
            )}
            title={title ?? '-'}
          >
            {title ?? '-'}
          </h4>
        </div>

        {/* Kebab button */}
        <div className="relative" ref={menuRef}>
          <Button
            variant="ghost"
            size="icon"
            className="opacity-0 transition-opacity duration-200 group-hover:opacity-100"
            onClick={(e) => {
              e.stopPropagation()
              setMenuOpen((v) => !v)
            }}
            aria-label="Open menu"
          >
            {/* Use simple glyph for kebab to avoid icon dependency */}
            <span className="text-lg leading-none">⋯</span>
          </Button>

          {/* Context menu */}
          {menuOpen && (
            <div
              className="absolute right-0 z-10 mt-2 w-36 rounded-md border border-border bg-background p-1 shadow-md"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-xs hover:bg-accent"
                onClick={handleStartRename}
                type="button"
              >
                <Icon type="edit" size="xxs" />
                Rename
              </button>
              <button
                className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-xs text-destructive hover:bg-destructive/10"
                onClick={handleStartDelete}
                type="button"
              >
                <Icon type="trash" size="xs" />
                Delete
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Rename dialog */}
      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent className="font-geist">
          <DialogHeader>
            <DialogTitle>Rename session</DialogTitle>
            <DialogDescription>
              Enter a new name for this session.
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <input
              type="text"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              placeholder="Session name"
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              className="rounded-xl border-border font-geist"
              onClick={() => setRenameOpen(false)}
              disabled={isRenaming}
            >
              CANCEL
            </Button>
            <Button
              onClick={handleConfirmRename}
              disabled={isRenaming}
              className="rounded-xl font-geist"
            >
              {isRenaming ? 'RENAMING...' : 'RENAME'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation */}
      <DeleteSessionModal
        isOpen={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        onDelete={handleConfirmDelete}
        isDeleting={isDeleting}
      />
    </>
  )
}
