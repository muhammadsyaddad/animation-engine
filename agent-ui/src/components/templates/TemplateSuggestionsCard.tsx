'use client'

import React, { useState, useCallback, useMemo } from 'react'
import { TemplateSuggestion, DatasetSummary, VideoData } from '@/types/os'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'
import { useStore } from '@/store'
import Icon from '@/components/ui/icon'
import { APIRoutes } from '@/api/routes'
import ColumnMappingModal from './ColumnMappingModal'

interface TemplateSuggestionsCardProps {
  suggestions: TemplateSuggestion[]
  runId: string
  sessionId?: string | null
  message?: string
  datasetSummary?: DatasetSummary | null
  onTemplateSelected?: (templateId: string) => void
  onVideosReceived?: (videos: VideoData[]) => void
}

const TemplateSuggestionsCard: React.FC<TemplateSuggestionsCardProps> = ({
  suggestions,
  runId,
  sessionId,
  message = 'Select a template',
  datasetSummary,
  onTemplateSelected,
  onVideosReceived
}) => {
  const selectedEndpoint = useStore((s) => s.selectedEndpoint)
  const setMessages = useStore((s) => s.setMessages)
  const [selectedTemplate, setSelectedTemplate] =
    useState<TemplateSuggestion | null>(null)
  const [showColumnModal, setShowColumnModal] = useState(false)
  const [progressMessage, setProgressMessage] = useState<string | null>(null)

  const resolveUrl = useCallback(
    (url: string | null | undefined): string | null => {
      if (!url) return null
      try {
        if (/^(https?:|data:)/.test(url)) return url
        if (url.startsWith('/')) {
          const base = (selectedEndpoint || '').replace(/\/$/, '')
          return `${base}${url}`
        }
        const base = selectedEndpoint || ''
        return new URL(url, base.endsWith('/') ? base : base + '/').toString()
      } catch {
        return url
      }
    },
    [selectedEndpoint]
  )

  const resolvedSuggestions = useMemo(
    () =>
      suggestions.map((s) => ({
        ...s,
        resolvedPreviewUrl: resolveUrl(s.preview_url),
        resolvedFallbackUrl: resolveUrl(s.preview_fallback_url)
      })),
    [suggestions, resolveUrl]
  )

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isCompleted, setIsCompleted] = useState(false)
  const [receivedVideos, setReceivedVideos] = useState<VideoData[]>([])

  const parseSSEEvents = useCallback(
    async (reader: ReadableStreamDefaultReader<Uint8Array>) => {
      const decoder = new TextDecoder()
      let buffer = ''

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          const events = buffer.split('\n\n')
          buffer = events.pop() || ''

          for (const event of events) {
            if (!event.trim()) continue

            const dataMatch = event.match(/^data:\s*(.+)$/m)
            if (!dataMatch) continue

            try {
              const data = JSON.parse(dataMatch[1])

              if (data.event === 'RunContent' && data.content) {
                setProgressMessage(data.content)
              }

              if (data.videos && Array.isArray(data.videos)) {
                const videos: VideoData[] = data.videos.map(
                  (v: { id?: number; url?: string; eta?: number } | string) => {
                    if (typeof v === 'string') {
                      return { id: Date.now().toString(), url: v }
                    }
                    return {
                      id: v.id?.toString() || Date.now().toString(),
                      url: v.url || ''
                    }
                  }
                )

                const resolvedVideos = videos.map((v) => ({
                  ...v,
                  url: resolveUrl(v.url) || v.url
                }))

                setReceivedVideos(resolvedVideos)
                onVideosReceived?.(resolvedVideos)

                setMessages((prevMessages) => {
                  const newMessages = [...prevMessages]
                  const lastMessage = newMessages[newMessages.length - 1]
                  if (lastMessage && lastMessage.role === 'agent') {
                    return newMessages.map((msg, idx) =>
                      idx === newMessages.length - 1
                        ? { ...msg, videos: resolvedVideos }
                        : msg
                    )
                  }
                  return newMessages
                })
              }

              if (data.event === 'RunCompleted') {
                setProgressMessage('Animation completed!')
              }

              if (data.event === 'RunError') {
                setError(data.content || 'Animation generation failed')
                setIsLoading(false)
              }
            } catch {
              // Ignore JSON parse errors
            }
          }
        }
      } catch (err) {
        console.error('Error reading SSE stream:', err)
      }
    },
    [resolveUrl, onVideosReceived, setMessages]
  )

  const handleTemplateClick = useCallback(
    (suggestion: TemplateSuggestion) => {
      if (isLoading || isCompleted) return
      setSelectedTemplate(suggestion)
      setShowColumnModal(true)
      setError(null)
    },
    [isLoading, isCompleted]
  )

  const handleModalClose = useCallback(() => {
    setShowColumnModal(false)
    setSelectedTemplate(null)
  }, [])

  const handleColumnMappingConfirm = useCallback(
    async (columnMapping: Record<string, string | null>) => {
      if (!selectedTemplate || isLoading || isCompleted) return

      setIsLoading(true)
      setError(null)
      setProgressMessage('Starting animation generation...')

      try {
        const endpointUrl = constructEndpointUrl(selectedEndpoint)
        const url = APIRoutes.SelectTemplate(endpointUrl, runId)

        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            template_id: selectedTemplate.template_id,
            session_id: sessionId,
            column_mapping: columnMapping
          })
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}))
          let errorMessage = `Request failed (${response.status})`

          if (errorData.detail) {
            if (typeof errorData.detail === 'string') {
              errorMessage = errorData.detail
            } else if (typeof errorData.detail === 'object') {
              const detail = errorData.detail
              if (
                detail.errors &&
                Array.isArray(detail.errors) &&
                detail.errors.length > 0
              ) {
                errorMessage = detail.errors[0]
              } else if (detail.message) {
                errorMessage = detail.message
              }
            }
          }

          throw new Error(errorMessage)
        }

        setIsCompleted(true)
        setShowColumnModal(false)
        onTemplateSelected?.(selectedTemplate.template_id)

        if (response.body) {
          const reader = response.body.getReader()
          await parseSSEEvents(reader)
        }
      } catch (err: unknown) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to select template'
        setError(errorMessage)
        setShowColumnModal(false)
        setSelectedTemplate(null)
      } finally {
        setIsLoading(false)
      }
    },
    [
      runId,
      sessionId,
      selectedEndpoint,
      selectedTemplate,
      isLoading,
      isCompleted,
      onTemplateSelected,
      parseSSEEvents
    ]
  )

  const recommendedTemplate = suggestions.find((s) => s.is_recommended)

  // Completed state - minimal success indicator
  if (isCompleted) {
    return (
      <div className="mt-4 rounded-lg border border-border bg-secondary/30 p-4">
        <div className="flex items-center gap-2 text-primary">
          <Icon type="check" size="sm" />
          <span className="text-sm font-medium">
            {selectedTemplate?.display_name}
          </span>
        </div>
        {progressMessage && (
          <p className="mt-1.5 text-xs text-muted">{progressMessage}</p>
        )}
        {isLoading && !receivedVideos.length && (
          <div className="mt-3 flex items-center gap-2 text-xs text-muted">
            <div className="h-3 w-3 animate-spin rounded-full border border-muted border-t-transparent" />
            <span>Generating animation...</span>
          </div>
        )}
        {error && <p className="mt-2 text-xs text-muted opacity-80">{error}</p>}
      </div>
    )
  }

  return (
    <>
      <div className="mt-4 rounded-lg border border-border bg-secondary/20 p-4">
        {/* Header */}
        <div className="mb-4">
          <h3 className="text-sm font-medium text-primary">{message}</h3>
          {datasetSummary && (
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
              <span className="font-medium text-primary/80">
                {datasetSummary.filename}
              </span>
              {datasetSummary.row_count && (
                <span>{datasetSummary.row_count.toLocaleString()} rows</span>
              )}
              {datasetSummary.column_count && (
                <span>{datasetSummary.column_count} columns</span>
              )}
              {datasetSummary.time_column && (
                <span>Time: {datasetSummary.time_column}</span>
              )}
            </div>
          )}
        </div>

        {/* Error message - subtle, not red */}
        {error && (
          <div className="mb-4 rounded border border-border bg-secondary/40 px-3 py-2 text-xs text-muted">
            <span className="opacity-70">{error}</span>
          </div>
        )}

        {/* Template grid */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {resolvedSuggestions.map((suggestion) => {
            const isSelected =
              selectedTemplate?.template_id === suggestion.template_id
            const isRecommended = suggestion.is_recommended

            return (
              <button
                key={suggestion.template_id}
                type="button"
                onClick={() => handleTemplateClick(suggestion)}
                disabled={isLoading}
                className={`group relative flex flex-col overflow-hidden rounded-lg border text-left transition-all duration-150 ${isSelected ? 'border-primary/60 bg-primary/5' : 'border-border bg-secondary/30 hover:border-primary/30 hover:bg-secondary/50'} ${isLoading ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'} `}
              >
                {/* Recommended indicator - subtle */}
                {isRecommended && (
                  <div className="absolute right-2 top-2 z-10 rounded bg-primary/10 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wider text-primary/80">
                    Recommended
                  </div>
                )}

                {/* Preview image */}
                {(suggestion.resolvedPreviewUrl ||
                  suggestion.resolvedFallbackUrl) && (
                  <div className="relative h-28 w-full overflow-hidden bg-black/10">
                    <img
                      src={
                        suggestion.resolvedPreviewUrl ||
                        suggestion.resolvedFallbackUrl ||
                        ''
                      }
                      alt={suggestion.display_name}
                      className="h-full w-full object-cover opacity-90 transition-opacity group-hover:opacity-100"
                      onError={(e) => {
                        if (
                          suggestion.resolvedFallbackUrl &&
                          e.currentTarget.src !== suggestion.resolvedFallbackUrl
                        ) {
                          e.currentTarget.src = suggestion.resolvedFallbackUrl
                        }
                      }}
                    />
                  </div>
                )}

                {/* Content */}
                <div className="flex flex-1 flex-col p-3">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="text-sm font-medium text-primary">
                      {suggestion.display_name}
                    </h4>
                    {suggestion.confidence_score > 0 && (
                      <span className="shrink-0 rounded bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-muted">
                        {Math.round(suggestion.confidence_score * 100)}%
                      </span>
                    )}
                  </div>

                  <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-muted">
                    {suggestion.description}
                  </p>

                  {/* Reasons - simplified */}
                  {suggestion.reasons && suggestion.reasons.length > 0 && (
                    <div className="mt-2 space-y-0.5">
                      {suggestion.reasons.slice(0, 2).map((reason, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-1.5 text-[10px] text-muted/70"
                        >
                          <span className="mt-0.5 opacity-50">•</span>
                          <span className="line-clamp-1">{reason}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Loading indicator */}
                  {isSelected && isLoading && (
                    <div className="mt-2 flex items-center gap-2 text-xs text-muted">
                      <div className="h-3 w-3 animate-spin rounded-full border border-muted border-t-transparent" />
                      <span>Generating...</span>
                    </div>
                  )}
                </div>
              </button>
            )
          })}
        </div>

        {/* Footer hint */}
        <p className="mt-4 text-center text-[11px] text-muted/60">
          Select a template to configure and generate your animation
        </p>
      </div>

      {/* Column Mapping Modal */}
      {selectedTemplate && (
        <ColumnMappingModal
          isOpen={showColumnModal}
          onClose={handleModalClose}
          onConfirm={handleColumnMappingConfirm}
          template={selectedTemplate}
          datasetSummary={datasetSummary || null}
          isLoading={isLoading}
        />
      )}
    </>
  )
}

export default TemplateSuggestionsCard
