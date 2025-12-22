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
  message = 'Please select a template for your animation:',
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

  // Resolve relative URLs to full URLs using the API endpoint
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

  // Pre-resolve all suggestion URLs
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

  // Parse SSE events from the stream
  const parseSSEEvents = useCallback(
    async (reader: ReadableStreamDefaultReader<Uint8Array>) => {
      const decoder = new TextDecoder()
      let buffer = ''

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // Process complete SSE events (separated by double newlines)
          const events = buffer.split('\n\n')
          buffer = events.pop() || '' // Keep incomplete event in buffer

          for (const event of events) {
            if (!event.trim()) continue

            // Extract data from SSE format: "data: {...}"
            const dataMatch = event.match(/^data:\s*(.+)$/m)
            if (!dataMatch) continue

            try {
              const data = JSON.parse(dataMatch[1])

              // Update progress message for RunContent events
              if (data.event === 'RunContent' && data.content) {
                setProgressMessage(data.content)
              }

              // Check for videos in the event
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

                // Resolve video URLs
                const resolvedVideos = videos.map((v) => ({
                  ...v,
                  url: resolveUrl(v.url) || v.url
                }))

                setReceivedVideos(resolvedVideos)
                onVideosReceived?.(resolvedVideos)

                // Update the last message in the store with the videos
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

              // Handle completion
              if (data.event === 'RunCompleted') {
                setProgressMessage('Animation completed!')
              }

              // Handle errors
              if (data.event === 'RunError') {
                setError(data.content || 'Animation generation failed')
                setIsLoading(false)
              }
            } catch {
              // Ignore JSON parse errors for malformed events
            }
          }
        }
      } catch (err) {
        console.error('Error reading SSE stream:', err)
      }
    },
    [resolveUrl, onVideosReceived, setMessages]
  )

  // Handle template card click - show column mapping modal
  const handleTemplateClick = useCallback(
    (suggestion: TemplateSuggestion) => {
      if (isLoading || isCompleted) return
      setSelectedTemplate(suggestion)
      setShowColumnModal(true)
      setError(null)
    },
    [isLoading, isCompleted]
  )

  // Handle modal close
  const handleModalClose = useCallback(() => {
    setShowColumnModal(false)
    setSelectedTemplate(null)
  }, [])

  // Handle confirm from column mapping modal
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

          // Handle structured error response from backend
          let errorMessage = `Failed to select template: ${response.status}`

          if (errorData.detail) {
            if (typeof errorData.detail === 'string') {
              errorMessage = errorData.detail
            } else if (typeof errorData.detail === 'object') {
              // Extract the message and errors from the structured response
              const detail = errorData.detail
              if (
                detail.errors &&
                Array.isArray(detail.errors) &&
                detail.errors.length > 0
              ) {
                // Show the first error as the main message
                errorMessage = detail.errors[0]
              } else if (detail.message) {
                errorMessage = detail.message
              } else {
                errorMessage = JSON.stringify(detail)
              }
            }
          }

          throw new Error(errorMessage)
        }

        setIsCompleted(true)
        setShowColumnModal(false)
        onTemplateSelected?.(selectedTemplate.template_id)

        // Read the SSE stream from the response to get video results
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

  // Find the recommended template
  const recommendedTemplate = suggestions.find((s) => s.is_recommended)

  if (isCompleted) {
    return (
      <div className="mt-4 rounded-lg border border-green-500/30 bg-green-500/10 p-4">
        <div className="flex items-center gap-2 text-green-400">
          <Icon type="check" size="sm" />
          <span className="font-medium">
            Template selected: {selectedTemplate?.display_name}
          </span>
        </div>
        {progressMessage && (
          <p className="mt-1 text-xs text-muted">{progressMessage}</p>
        )}
        {isLoading && !receivedVideos.length && (
          <div className="mt-2 flex items-center gap-2 text-xs text-muted">
            <div className="h-3 w-3 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <span>Generating animation...</span>
          </div>
        )}
        {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
      </div>
    )
  }

  return (
    <>
      <div className="mt-4 rounded-lg border border-accent/30 bg-secondary/40 p-4">
        {/* Header */}
        <div className="mb-4">
          <h3 className="text-sm font-medium text-primary">{message}</h3>
          {datasetSummary && (
            <div className="mt-2 rounded border border-accent/20 bg-secondary/60 px-3 py-2 text-xs text-muted">
              <span className="font-medium text-primary">
                {datasetSummary.filename}
              </span>
              {datasetSummary.row_count && (
                <span className="ml-2">
                  • {datasetSummary.row_count.toLocaleString()} rows
                </span>
              )}
              {datasetSummary.column_count && (
                <span className="ml-2">
                  • {datasetSummary.column_count} columns
                </span>
              )}
              {datasetSummary.time_column && (
                <span className="ml-2">
                  • Time: {datasetSummary.time_column}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-4 rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
            {error}
          </div>
        )}

        {/* Template grid */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {resolvedSuggestions.map((suggestion) => (
            <button
              key={suggestion.template_id}
              type="button"
              onClick={() => handleTemplateClick(suggestion)}
              disabled={isLoading}
              className={`relative flex flex-col overflow-hidden rounded-lg border text-left transition-all ${
                selectedTemplate?.template_id === suggestion.template_id
                  ? 'border-primary bg-primary/10'
                  : suggestion.is_recommended
                    ? 'border-primary/50 bg-secondary/80 hover:border-primary hover:bg-primary/5'
                    : 'border-accent/30 bg-secondary/60 hover:border-accent/50 hover:bg-secondary/80'
              } ${isLoading ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
            >
              {/* Recommended badge */}
              {suggestion.is_recommended && (
                <div className="absolute right-0 top-0 rounded-bl bg-primary px-2 py-0.5 text-[10px] font-semibold uppercase text-primaryAccent">
                  Recommended
                </div>
              )}

              {/* Preview image */}
              {(suggestion.resolvedPreviewUrl ||
                suggestion.resolvedFallbackUrl) && (
                <div className="relative h-24 w-full overflow-hidden bg-black/20">
                  <img
                    src={
                      suggestion.resolvedPreviewUrl ||
                      suggestion.resolvedFallbackUrl ||
                      ''
                    }
                    alt={suggestion.display_name}
                    className="h-full w-full object-cover"
                    onError={(e) => {
                      // Fallback to placeholder on error
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
                    <span
                      className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${
                        suggestion.confidence_score >= 0.8
                          ? 'bg-green-500/20 text-green-400'
                          : suggestion.confidence_score >= 0.5
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-gray-500/20 text-gray-400'
                      }`}
                    >
                      {Math.round(suggestion.confidence_score * 100)}% match
                    </span>
                  )}
                </div>

                <p className="mt-1 line-clamp-2 text-xs text-muted">
                  {suggestion.description}
                </p>

                {/* Reasons */}
                {suggestion.reasons && suggestion.reasons.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {suggestion.reasons.slice(0, 2).map((reason, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-1.5 text-[10px] text-muted"
                      >
                        <span className="mt-0.5 text-primary">•</span>
                        <span className="line-clamp-1">{reason}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Loading indicator */}
                {selectedTemplate?.template_id === suggestion.template_id &&
                  isLoading && (
                    <div className="mt-2 flex items-center gap-2 text-xs text-primary">
                      <div className="h-3 w-3 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                      <span>Generating...</span>
                    </div>
                  )}
              </div>
            </button>
          ))}
        </div>

        {/* Hint text */}
        <p className="mt-4 text-center text-xs text-muted">
          Click a template to configure columns and generate your animation
          {recommendedTemplate && (
            <>
              {' '}
              •{' '}
              <span className="text-primary">
                {recommendedTemplate.display_name}
              </span>{' '}
              is recommended based on your data
            </>
          )}
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
