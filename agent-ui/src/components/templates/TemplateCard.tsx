'use client'
import React, { useState } from 'react'
import { TemplateSchema } from '@/types/templates'

interface TemplateCardProps {
  template: TemplateSchema
  isSelected: boolean
  onSelect: (template: TemplateSchema) => void
}

// Category icons as SVG paths
const categoryIconPaths: Record<string, string> = {
  ranking: 'M3 3v18h18M7 16h2v-4H7v4zm4 0h2V8h-2v8zm4 0h2v-6h-2v6z',
  correlation:
    'M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0-4 0M6 6m-1 0a1 1 0 1 0 2 0a1 1 0 1 0-2 0M18 18m-1 0a1 1 0 1 0 2 0a1 1 0 1 0-2 0M6 18m-1.5 0a1.5 1.5 0 1 0 3 0a1.5 1.5 0 1 0-3 0M18 6m-1 0a1 1 0 1 0 2 0a1 1 0 1 0-2 0',
  trend: 'M3 3v18h18M7 14l4-4 4 4 5-6',
  distribution: 'M3 21h18M6 21V10M10 21V6M14 21V8M18 21V4',
  dashboard: 'M3 3h7v7H3zM14 3h7v4h-7zM14 10h7v11h-7zM3 13h7v8H3z',
  categorical: 'M12 2l9 4-9 4-9-4 9-4zM3 10l9 4 9-4M3 14l9 4 9-4',
  comparison: 'M3 3v18h18M7 17h3v-6H7v6zm5 0h3V7h-3v10zm5 0h3v-4h-3v4z',
  general: 'M3 3v18h18M9 17V9M15 17v-4'
}

// Category colors for the badge
const categoryColors: Record<string, string> = {
  ranking: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  correlation: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  trend: 'bg-green-500/20 text-green-400 border-green-500/30',
  distribution: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  dashboard: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  categorical: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
  comparison: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  general: 'bg-gray-500/20 text-gray-400 border-gray-500/30'
}

// Placeholder gradient colors based on category
const placeholderGradients: Record<string, string> = {
  ranking: 'from-blue-900/40 to-blue-800/20',
  correlation: 'from-purple-900/40 to-purple-800/20',
  trend: 'from-green-900/40 to-green-800/20',
  distribution: 'from-orange-900/40 to-orange-800/20',
  dashboard: 'from-cyan-900/40 to-cyan-800/20',
  categorical: 'from-pink-900/40 to-pink-800/20',
  comparison: 'from-yellow-900/40 to-yellow-800/20',
  general: 'from-gray-900/40 to-gray-800/20'
}

type ImageState = 'loading' | 'loaded' | 'error'

const TemplateCard: React.FC<TemplateCardProps> = ({
  template,
  isSelected,
  onSelect
}) => {
  const [imageState, setImageState] = useState<ImageState>('loading')

  const categoryColor =
    categoryColors[template.category] || categoryColors.general
  const placeholderGradient =
    placeholderGradients[template.category] || placeholderGradients.general
  const iconPath =
    categoryIconPaths[template.category] || categoryIconPaths.general

  const requiredAxes = template.axes.filter((a) => a.required)

  const handleImageLoad = () => {
    setImageState('loaded')
  }

  const handleImageError = () => {
    setImageState('error')
  }

  const renderPlaceholder = () => (
    <div
      className={`flex h-full w-full flex-col items-center justify-center rounded-lg bg-gradient-to-br ${placeholderGradient}`}
    >
      <svg
        className="h-12 w-12 text-muted/60"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        strokeWidth={1.5}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
      </svg>
      <span className="mt-2 text-xs text-muted/60">Preview</span>
    </div>
  )

  const renderLoadingState = () => (
    <div
      className={`flex h-full w-full items-center justify-center rounded-lg bg-gradient-to-br ${placeholderGradient}`}
    >
      <div className="flex flex-col items-center gap-2">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted/30 border-t-primary/60" />
        <span className="text-xs text-muted/60">Loading...</span>
      </div>
    </div>
  )

  return (
    <button
      type="button"
      onClick={() => onSelect(template)}
      className={`group relative w-full rounded-xl border p-4 text-left transition-all duration-200 ${
        isSelected
          ? 'border-primary bg-primary/10 shadow-lg shadow-primary/10 ring-2 ring-primary/50'
          : 'border-accent/30 bg-secondary/40 hover:border-accent/60 hover:bg-secondary/60 hover:shadow-md'
      } `}
    >
      {/* Selected indicator */}
      {isSelected && (
        <div className="absolute right-3 top-3 z-10 flex h-6 w-6 items-center justify-center rounded-full bg-primary shadow-lg">
          <svg
            className="h-4 w-4 text-primaryAccent"
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

      {/* Preview container */}
      <div className="relative mb-3 h-28 overflow-hidden rounded-lg bg-accent/10">
        {template.preview_url && imageState !== 'error' && (
          <>
            {/* Hidden image for loading */}
            <img
              src={template.preview_url}
              alt={template.display_name}
              className={`absolute inset-0 h-full w-full rounded-lg object-cover transition-opacity duration-300 ${
                imageState === 'loaded' ? 'opacity-100' : 'opacity-0'
              }`}
              onLoad={handleImageLoad}
              onError={handleImageError}
            />
            {/* Loading state overlay */}
            {imageState === 'loading' && (
              <div className="absolute inset-0">{renderLoadingState()}</div>
            )}
          </>
        )}

        {/* Fallback to SVG placeholder when main preview fails or doesn't exist */}
        {(!template.preview_url || imageState === 'error') &&
          template.preview_fallback_url && (
            <img
              src={template.preview_fallback_url}
              alt={`${template.display_name} preview`}
              className="absolute inset-0 h-full w-full rounded-lg object-cover"
            />
          )}

        {/* Generic placeholder when no preview URLs available */}
        {(!template.preview_url || imageState === 'error') &&
          !template.preview_fallback_url && (
            <div className="absolute inset-0">{renderPlaceholder()}</div>
          )}

        {/* Hover overlay with play indicator for GIFs */}
        {template.preview_url &&
          imageState === 'loaded' &&
          template.preview_url.endsWith('.gif') && (
            <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-black/0 opacity-0 transition-all duration-200 group-hover:bg-black/30 group-hover:opacity-100">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/90 shadow-lg">
                <svg
                  className="ml-0.5 h-5 w-5 text-gray-800"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
            </div>
          )}
      </div>

      {/* Template info */}
      <div className="space-y-2">
        {/* Category badge */}
        <div className="flex items-center justify-between">
          <span
            className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${categoryColor}`}
          >
            <svg
              className="h-2.5 w-2.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
            </svg>
            {template.category}
          </span>
        </div>

        {/* Title */}
        <h3 className="text-sm font-semibold text-primary group-hover:text-primary/90">
          {template.display_name}
        </h3>

        {/* Description */}
        <p className="line-clamp-2 text-xs leading-relaxed text-muted">
          {template.description}
        </p>

        {/* Required axes preview */}
        <div className="pt-2">
          <div className="flex flex-wrap gap-1">
            {requiredAxes.slice(0, 3).map((axis) => (
              <span
                key={axis.name}
                className="inline-flex items-center rounded-md bg-accent/20 px-1.5 py-0.5 text-[10px] font-medium text-primary/80"
                title={axis.description || axis.label}
              >
                {axis.name.replace('_column', '').replace('_', ' ')}
              </span>
            ))}
            {requiredAxes.length > 3 && (
              <span className="inline-flex items-center rounded-md bg-accent/20 px-1.5 py-0.5 text-[10px] font-medium text-muted">
                +{requiredAxes.length - 3} more
              </span>
            )}
          </div>
        </div>

        {/* Axes count indicator */}
        <div className="flex items-center gap-2 pt-1 text-[10px] text-muted">
          <span className="flex items-center gap-1">
            <svg
              className="h-3 w-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            {requiredAxes.length} required
          </span>
          {template.axes.length > requiredAxes.length && (
            <span className="flex items-center gap-1">
              <svg
                className="h-3 w-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                />
              </svg>
              {template.axes.length - requiredAxes.length} optional
            </span>
          )}
        </div>
      </div>
    </button>
  )
}

export default TemplateCard
