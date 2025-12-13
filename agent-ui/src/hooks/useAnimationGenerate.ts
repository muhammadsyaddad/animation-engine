import { useState, useCallback } from 'react'
import { useStore } from '@/store'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'
import { APIRoutes } from '@/api/routes'
import {
  GenerateAnimationRequest,
  ColumnMappings,
  AnimationEvent,
} from '@/types/templates'

interface UseAnimationGenerateOptions {
  onProgress?: (event: AnimationEvent) => void
  onComplete?: (videoUrl: string) => void
  onError?: (error: string) => void
}

interface UseAnimationGenerateReturn {
  generate: (
    datasetId: string,
    templateId: string,
    columnMappings: ColumnMappings,
    options?: {
      title?: string
      topN?: number
      aspectRatio?: '16:9' | '9:16' | '1:1'
      quality?: 'low' | 'medium' | 'high'
      sessionId?: string
    }
  ) => Promise<void>
  isGenerating: boolean
  progress: string[]
  error: string | null
  videoUrl: string | null
  runId: string | null
  abort: () => void
}

export function useAnimationGenerate(
  options: UseAnimationGenerateOptions = {}
): UseAnimationGenerateReturn {
  const { onProgress, onComplete, onError } = options
  const selectedEndpoint = useStore((s) => s.selectedEndpoint)

  const [isGenerating, setIsGenerating] = useState(false)
  const [progress, setProgress] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [runId, setRunId] = useState<string | null>(null)
  const [abortController, setAbortController] =
    useState<AbortController | null>(null)

  const abort = useCallback(() => {
    if (abortController) {
      abortController.abort()
      setAbortController(null)
      setIsGenerating(false)
    }
  }, [abortController])

  const generate = useCallback(
    async (
      datasetId: string,
      templateId: string,
      columnMappings: ColumnMappings,
      opts?: {
        title?: string
        topN?: number
        aspectRatio?: '16:9' | '9:16' | '1:1'
        quality?: 'low' | 'medium' | 'high'
        sessionId?: string
      }
    ) => {
      // Reset state
      setIsGenerating(true)
      setProgress([])
      setError(null)
      setVideoUrl(null)
      setRunId(null)

      // Create abort controller
      const controller = new AbortController()
      setAbortController(controller)

      try {
        const endpointUrl = constructEndpointUrl(selectedEndpoint)
        const url = APIRoutes.GenerateAnimation(endpointUrl)

        const requestBody: GenerateAnimationRequest = {
          dataset_id: datasetId,
          template_id: templateId,
          column_mappings: columnMappings,
          title: opts?.title,
          top_n: opts?.topN,
          aspect_ratio: opts?.aspectRatio || '16:9',
          quality: opts?.quality || 'medium',
          session_id: opts?.sessionId,
        }

        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
          signal: controller.signal,
        })

        if (!response.ok) {
          let errorDetail = `HTTP ${response.status}`
          try {
            const errorData = await response.json()
            errorDetail = errorData.detail || JSON.stringify(errorData)
          } catch {
            errorDetail = response.statusText
          }
          throw new Error(errorDetail)
        }

        // Handle SSE stream
        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error('No response body')
        }

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()

          if (done) {
            break
          }

          buffer += decoder.decode(value, { stream: true })

          // Process complete SSE events
          const lines = buffer.split('\n')
          buffer = lines.pop() || '' // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const jsonStr = line.slice(6).trim()
              if (!jsonStr) continue

              try {
                const event: AnimationEvent = JSON.parse(jsonStr)

                // Store run ID
                if (event.run_id && !runId) {
                  setRunId(event.run_id)
                }

                // Handle different event types
                switch (event.event) {
                  case 'RunContent':
                    setProgress((prev) => [...prev, event.content])
                    onProgress?.(event)
                    break

                  case 'RunCompleted':
                    if (event.videos && event.videos.length > 0) {
                      const url = event.videos[0]
                      setVideoUrl(url)
                      onComplete?.(url)
                    }
                    setProgress((prev) => [...prev, event.content])
                    onProgress?.(event)
                    break

                  case 'RunError':
                    setError(event.content)
                    onError?.(event.content)
                    break
                }
              } catch (parseError) {
                console.warn('Failed to parse SSE event:', jsonStr, parseError)
              }
            }
          }
        }
      } catch (err: any) {
        if (err.name === 'AbortError') {
          setError('Generation aborted')
          onError?.('Generation aborted')
        } else {
          const errorMsg = err?.message || String(err)
          setError(errorMsg)
          onError?.(errorMsg)
        }
      } finally {
        setIsGenerating(false)
        setAbortController(null)
      }
    },
    [selectedEndpoint, onProgress, onComplete, onError]
  )

  return {
    generate,
    isGenerating,
    progress,
    error,
    videoUrl,
    runId,
    abort,
  }
}

export default useAnimationGenerate
