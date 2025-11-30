'use client'

import { memo, useEffect, useState } from 'react'
import { toast } from 'sonner'

import { type VideoData } from '@/types/os'
import Icon from '@/components/ui/icon'
import { useStore } from '@/store'

const VideoItem = memo(({ video }: { video: VideoData }) => {
  const [failed, setFailed] = useState(false)
  const [retryKey, setRetryKey] = useState(0)
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
  const videoUrl = resolveUrl(video.url)

  useEffect(() => {
    // Reset failure state when the URL changes so the component will try again.
    setFailed(false)
    setRetryKey((k) => k + 1)
  }, [videoUrl])

  const handleDownload = async () => {
    try {
      toast.loading('Downloading video...')
      const response = await fetch(videoUrl)
      if (!response.ok) throw new Error('Network response was not ok')

      const blob = await response.blob()
      const fileExtension = videoUrl.split('.').pop() ?? 'mp4'
      const fileName = `video-${Date.now()}.${fileExtension}`

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName

      document.body.appendChild(a)
      a.click()

      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.dismiss()
      toast.success('Video downloaded successfully')
    } catch (err) {
      toast.dismiss()
      toast.error('Failed to download video')
    }
  }

  if (failed) {
    return (
      <div className="w-full max-w-xl">
        <div className="flex h-40 flex-col items-center justify-center gap-2 rounded-md bg-secondary/50 px-3 text-muted">
          <p className="text-primary">Video unavailable</p>
          <a
            href={videoUrl}
            target="_blank"
            rel="noreferrer"
            className="w-full truncate p-2 text-center text-xs text-primary underline"
          >
            {videoUrl}
          </a>
          <div className="mt-2 flex gap-2">
            <button
              onClick={() => {
                setFailed(false)
                setRetryKey((k) => k + 1)
              }}
              className="rounded bg-primary px-3 py-1 text-xs text-white"
            >
              Retry
            </button>
            <button
              onClick={handleDownload}
              className="rounded border px-3 py-1 text-xs"
            >
              <span className="flex items-center gap-2">
                <Icon type="download" size="xs" />
                Download
              </span>
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="group relative w-full max-w-xl">
        <video
          key={retryKey}
          src={videoUrl}
          autoPlay
          muted
          loop
          controls
          className="w-full rounded-lg bg-black"
          style={{ aspectRatio: '16 / 9' }}
          onError={() => setFailed(true)}
        />
        <button
          type="button"
          onClick={handleDownload}
          className="absolute right-2 top-2 flex items-center justify-center rounded-sm bg-secondary/80 p-1.5 opacity-0 transition-opacity duration-200 hover:bg-secondary group-hover:opacity-100"
          aria-label="Download video"
        >
          <Icon type="download" size="xs" />
        </button>
      </div>
    </div>
  )
})

VideoItem.displayName = 'VideoItem'

const Videos = memo(({ videos }: { videos: VideoData[] }) => (
  <div className="flex flex-col gap-4">
    {videos.map((video) => (
      <VideoItem key={video.id ?? video.url} video={video} />
    ))}
  </div>
))

Videos.displayName = 'Videos'

export default Videos
