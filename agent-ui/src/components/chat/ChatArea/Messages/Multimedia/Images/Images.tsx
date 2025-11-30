import { memo, useEffect, useState } from 'react'

import { type ImageData } from '@/types/os'
import { cn } from '@/lib/utils'
import { useStore } from '@/store'

/**
 * ImageItem
 *
 * - Renders an image and handles transient 404s/non-loading by showing a non-destructive
 *   React fallback UI instead of replacing the DOM (which prevents React from re-rendering).
 * - Automatically resets failure state when `image.url` changes so the component will retry
 *   loading if the backend produces the file shortly after the initial request.
 */
const ImageItem = ({ image }: { image: ImageData }) => {
  const [failed, setFailed] = useState(false)
  const [retryKey, setRetryKey] = useState(0)

  // resolve base endpoint from store
  const selectedEndpoint = useStore((s) => s.selectedEndpoint)

  const resolveUrl = (url: string): string => {
    try {
      if (!url) return url
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
  }

  const resolvedUrl = resolveUrl(image.url)

  // Reset failure state and bump key when URL or endpoint changes so the <img> is re-requested.
  useEffect(() => {
    setFailed(false)
    setRetryKey((k) => k + 1)
  }, [image.url, selectedEndpoint])

  if (failed) {
    return (
      <div className="flex h-40 flex-col items-center justify-center gap-2 rounded-md bg-secondary/50 text-muted">
        <p className="text-primary">Image unavailable</p>
        <a
          href={resolvedUrl}
          target="_blank"
          rel="noreferrer"
          className="w-full max-w-md truncate p-2 text-center text-xs text-primary underline"
        >
          {resolvedUrl}
        </a>
        <div className="mt-2 flex gap-2">
          <button
            onClick={() => {
              // allow retry by resetting failure and bumping key (forces browser to re-request)
              setFailed(false)
              setRetryKey((k) => k + 1)
            }}
            className="rounded bg-primary px-3 py-1 text-xs text-white"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      key={retryKey}
      src={resolvedUrl}
      alt={image.revised_prompt || 'AI generated image'}
      className="w-full rounded-lg"
      onError={() => {
        // Mark as failed so we render the React fallback (non-destructive)
        setFailed(true)
      }}
    />
  )
}

const Images = ({ images }: { images: ImageData[] }) => (
  <div
    className={cn(
      'grid max-w-xl gap-4',
      images.length > 1 ? 'grid-cols-2' : 'grid-cols-1'
    )}
  >
    {images.map((image) => (
      <div key={image.url} className="group relative">
        <ImageItem image={image} />
      </div>
    ))}
  </div>
)

export default memo(Images)

Images.displayName = 'Images'
