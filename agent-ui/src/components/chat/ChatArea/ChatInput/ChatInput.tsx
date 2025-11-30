'use client'
import { useCallback, useRef, useState } from 'react'
import { toast } from 'sonner'
import { useQueryState } from 'nuqs'

import { TextArea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import Icon from '@/components/ui/icon'

import { useStore } from '@/store'
import useAIChatStreamHandler from '@/hooks/useAIStreamHandler'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'

type UploadResponse = {
  dataset: {
    dataset_id: string
    unified_rel_url?: string | null
    chart_type_hint?: string | null
  }
}

interface Attachment {
  name: string
  csvPath: string
}

const ChatInput = () => {
  const { chatInputRef } = useStore()
  const selectedEndpoint = useStore((s) => s.selectedEndpoint)
  const isStreaming = useStore((s) => s.isStreaming)
  const [selectedAgent] = useQueryState('agent')
  const [teamId] = useQueryState('team')

  const { handleStreamResponse } = useAIChatStreamHandler()

  const [inputMessage, setInputMessage] = useState('')
  const [attachment, setAttachment] = useState<Attachment | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const triggerFilePicker = useCallback(() => {
    if (isStreaming) return
    fileInputRef.current?.click()
  }, [isStreaming])

  const handleUploadFile = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      e.target.value = ''

      if (!file) return
      if (!/\.csv$/i.test(file.name)) {
        toast.error('Please select a CSV file')
        return
      }

      try {
        const endpointUrl = constructEndpointUrl(selectedEndpoint)
        const url = `${endpointUrl}/v1/datasets/upload`
        const fd = new FormData()
        fd.append('file', file, file.name)

        toast.loading('Uploading dataset...')
        const resp = await fetch(url, { method: 'POST', body: fd })
        if (!resp.ok) {
          let detail = ''
          try {
            const data = await resp.json()
            detail =
              typeof data === 'object' ? JSON.stringify(data) : String(data)
          } catch {
            detail = `${resp.status} ${resp.statusText}`
          }
          throw new Error(detail)
        }

        const json: UploadResponse = await resp.json()
        const csvPath = json?.dataset?.unified_rel_url
        if (!csvPath) {
          toast.error('Upload success, but csv_path missing')
          return
        }

        setAttachment({ name: file.name, csvPath })
        chatInputRef.current?.focus()
        toast.success('Dataset attached.')
      } catch (err) {
        toast.error(
          `Upload failed: ${err instanceof Error ? err.message : String(err)}`
        )
      } finally {
        toast.dismiss()
      }
    },
    [selectedEndpoint, chatInputRef]
  )

  const removeAttachment = useCallback(() => {
    setAttachment(null)
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!inputMessage.trim() && !attachment) return
    const formData = new FormData()

    // Build message; append dataset marker if attachment exists
    let messageText = inputMessage.trim() || '(no prompt)'
    if (attachment?.csvPath) {
      messageText = `${messageText}\n[dataset csv_path=${attachment.csvPath}]`
    }
    formData.append('message', messageText)

    if (attachment?.csvPath) {
      formData.append('csv_path', attachment.csvPath)
      // Optionally could set animate_data true automatically:
      // formData.append('animate_data', 'true')
    }

    setInputMessage('')

    try {
      await handleStreamResponse(formData)
    } catch (error) {
      toast.error(
        `Error in handleSubmit: ${
          error instanceof Error ? error.message : String(error)
        }`
      )
    } finally {
      // Clear attachment after sending
      setAttachment(null)
    }
  }, [handleStreamResponse, inputMessage, attachment])

  const canInteract = Boolean(selectedAgent || teamId)

  return (
    <div className="relative mx-auto mb-1 flex w-full max-w-2xl flex-col gap-y-2 font-geist">
      {attachment && (
        <div className="flex items-center gap-2 rounded-md px-3 py-2 text-xs text-primary">
          <span className="max-w-[140px] truncate">{attachment.name}</span>
          <button
            type="button"
            onClick={removeAttachment}
            aria-label="Remove attachment"
            className="text-muted hover:text-primary"
          >
            <Icon type="x" size="xs" />
          </button>
        </div>
      )}

      <div className="relative mx-auto mb-1 flex w-full max-w-2xl items-end justify-center gap-x-2 font-geist">
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={handleUploadFile}
        />
        <TextArea
          placeholder={'Ask anything'}
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={(e) => {
            if (
              e.key === 'Enter' &&
              !e.nativeEvent.isComposing &&
              !e.shiftKey &&
              !isStreaming
            ) {
              e.preventDefault()
              handleSubmit()
            }
          }}
          className="w-full border border-accent bg-primaryAccent px-4 text-sm text-primary focus:border-accent"
          disabled={!canInteract}
          ref={chatInputRef}
        />

        <Button
          type="button"
          onClick={triggerFilePicker}
          disabled={!canInteract || isStreaming}
          size="icon"
          className="rounded-xl bg-secondary p-5 text-primaryAccent"
          aria-label="Add dataset file"
          title="Add dataset file"
        >
          <Icon type="plus-icon" color="primaryAccent" />
        </Button>

        <Button
          type="button"
          onClick={handleSubmit}
          disabled={
            !canInteract || (!inputMessage.trim() && !attachment) || isStreaming
          }
          size="icon"
          className="rounded-xl bg-primary p-5 text-primaryAccent disabled:opacity-50"
          aria-label="Send"
          title="Send"
        >
          <Icon type="send" color="primaryAccent" />
        </Button>
      </div>
    </div>
  )
}

export default ChatInput
