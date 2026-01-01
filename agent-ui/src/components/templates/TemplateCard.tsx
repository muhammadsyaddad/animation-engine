'use client'
import React, { useState, useMemo } from 'react'
import { TemplateSchema } from '@/types/templates'
import { useStore } from '@/store'

interface TemplateCardProps {
  template: TemplateSchema
  isSelected: boolean
  onSelect: (template: TemplateSchema) => void
}

// Simple category icons as SVG paths
const categoryIconPaths: Record<string, string> = {
  ranking: 'M3 3v18h18M7 16h2v-4H7v4zm4 0h2V8h-2v8zm4 0h2v-6h-2v6z',
  correlation:
    'M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0M6 6m-1 0a1 1 0 1 0 2 0a1 1 0 1 0-2 0M18 18m-1 0a1 1 0 1 0 2 0a1 1 0 1 0-2 0',
  trend: 'M3 3v18h18M7 14l4-4 4 4 5-6',
  distribution: 'M3 21h18M6 21V10M10 21V6M14 21V8M18 21V4',
  dashboard: 'M3 3h7v7H3zM14 3h7v4h-7zM14 10h7v11h-7zM3 13h7v8H3z',
  categorical: 'M12 2l9 4-9 4-9-4 9-4zM3 10l9 4 9-4M3 14l9 4 9-4',
  comparison: 'M3 3v18h18M7 17h3v-6H7v6zm5 0h3V7h-3v10zm5 0h3v-4h-3v4z',
  general: 'M3 3v18h18M9 17V9M15 17v-4'
}

type ImageState = 'loading' | 'loaded' | 'error'

const TemplateCard: React.FC<TemplateCardProps> = ({
  template,
  isSelected,
  onSelect
}) => {
  const [imageState, setImageState] = useState<ImageState>('loading')
  const selectedEndpoint = useStore((s) => s.selectedEndpoint)

  const resolveUrl = (url: string | null | undefined): string | null => {
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
  }

  const resolvedPreviewUrl = useMemo(
    () => resolveUrl(template.preview_url),
    [template.preview_url, selectedEndpoint]
  )
  const resolvedFallbackUrl = useMemo(
    () => resolveUrl(template.preview_fallback_url),
    [template.preview_fallback_url, selectedEndpoint]
  )

  const iconPath =
    categoryIconPaths[template.category] || categoryIconPaths.general
  const requiredAxes = template.axes.filter((a) => a.required)

  const handleImageLoad = () => setImageState('loaded')
  const handleImageError = () => setImageState('error')

  const renderPlaceholder = () => (
    <div className="flex h-full w-full flex-col items-center justify-center rounded bg-secondary/60">
      <svg
        className="h-10 w-10 text-muted/40"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
      </svg>
    </div>
  )

  return (
    <button
      type="button"
      onClick={() => onSelect(template)}
      className={`group relative w-full rounded-lg border text-left transition-all duration-150 ${
        isSelected
          ? 'border-primary/50 bg-primary/5'
          : 'border-border bg-secondary/20 hover:border-primary/30 hover:bg-secondary/40'
      }`}
    >
      {/* Selected indicator */}
      {isSelected && (
        <div className="absolute right-2 top-2 z-10 flex h-5 w-5 items-center justify-center rounded-full bg-primary">
          <svg
            className="h-3 w-3 text-primaryAccent"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
      )}

      {/* Preview */}
      <div className="relative h-28 overflow-hidden rounded-t-lg bg-black/10">
        {resolvedPreviewUrl && imageState !== 'error' && (
          <>
            <img
              src={resolvedPreviewUrl}
              alt={template.display_name}
              className={`h-full w-full object-cover transition-opacity duration-200 ${
                imageState === 'loaded'
                  ? 'opacity-90 group-hover:opacity-100'
                  : 'opacity-0'
              }`}
              onLoad={handleImageLoad}
              onError={handleImageError}
            />
            {imageState === 'loading' && (
              <div className="absolute inset-0 flex items-center justify-center bg-secondary/40">
                <div className="h-5 w-5 animate-spin rounded-full border border-muted border-t-transparent" />
              </div>
            )}
          </>
        )}

        {(!resolvedPreviewUrl || imageState === 'error') &&
          resolvedFallbackUrl && (
            <img
              src={resolvedFallbackUrl}
              alt={`${template.display_name} preview`}
              className="h-full w-full object-cover opacity-90"
            />
          )}

        {(!resolvedPreviewUrl || imageState === 'error') &&
          !resolvedFallbackUrl && (
            <div className="absolute inset-0">{renderPlaceholder()}</div>
          )}
      </div>

      {/* Content */}
      <div className="p-3">
        {/* Category */}
        <span className="text-[10px] font-medium uppercase tracking-wider text-muted/60">
          {template.category}
        </span>

        {/* Title */}
        <h3 className="mt-1 text-sm font-medium text-primary">
          {template.display_name}
        </h3>

        {/* Description */}
        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted">
          {template.description}
        </p>

        {/* Required axes */}
        <div className="mt-2 flex flex-wrap gap-1">
          {requiredAxes.slice(0, 3).map((axis) => (
            <span
              key={axis.name}
              className="rounded bg-secondary px-1.5 py-0.5 text-[10px] text-muted"
              title={axis.description || axis.label}
            >
              {axis.name.replace('_column', '').replace('_', ' ')}
            </span>
          ))}
          {requiredAxes.length > 3 && (
            <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] text-muted/60">
              +{requiredAxes.length - 3}
            </span>
          )}
        </div>

        {/* Axes count */}
        <div className="mt-2 text-[10px] text-muted/50">
          {requiredAxes.length} required
          {template.axes.length > requiredAxes.length && (
            <span>
              {' '}
              · {template.axes.length - requiredAxes.length} optional
            </span>
          )}
        </div>
      </div>
    </button>
  )
}

export default TemplateCard
