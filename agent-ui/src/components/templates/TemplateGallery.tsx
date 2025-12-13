'use client'
import React, { useEffect, useState, useMemo } from 'react'
import { useStore } from '@/store'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'
import { APIRoutes } from '@/api/routes'
import { TemplateSchema, TemplateListResponse, TemplateCategory } from '@/types/templates'
import TemplateCard from './TemplateCard'

interface TemplateGalleryProps {
  onSelectTemplate: (template: TemplateSchema) => void
  selectedTemplateId?: string | null
}

const CATEGORY_ORDER: TemplateCategory[] = [
  'ranking',
  'trend',
  'correlation',
  'distribution',
  'comparison',
  'categorical',
  'dashboard',
  'general',
]

const CATEGORY_LABELS: Record<TemplateCategory, string> = {
  ranking: 'Rankings & Races',
  trend: 'Trends & Evolution',
  correlation: 'Correlations',
  distribution: 'Distributions',
  comparison: 'Comparisons',
  categorical: 'Categorical',
  dashboard: 'Dashboards',
  general: 'General',
}

const TemplateGallery: React.FC<TemplateGalleryProps> = ({
  onSelectTemplate,
  selectedTemplateId,
}) => {
  const selectedEndpoint = useStore((s) => s.selectedEndpoint)
  const [templates, setTemplates] = useState<TemplateSchema[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterCategory, setFilterCategory] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch templates on mount
  useEffect(() => {
    const fetchTemplates = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const endpointUrl = constructEndpointUrl(selectedEndpoint)
        const url = APIRoutes.GetTemplates(endpointUrl)
        const resp = await fetch(url)
        if (!resp.ok) {
          throw new Error(`Failed to fetch templates: ${resp.status}`)
        }
        const data: TemplateListResponse = await resp.json()
        setTemplates(data.templates)
      } catch (err: any) {
        setError(err?.message || 'Failed to load templates')
      } finally {
        setIsLoading(false)
      }
    }

    fetchTemplates()
  }, [selectedEndpoint])

  // Get unique categories from templates
  const categories = useMemo(() => {
    const cats = new Set(templates.map((t) => t.category))
    return CATEGORY_ORDER.filter((c) => cats.has(c))
  }, [templates])

  // Filter and search templates
  const filteredTemplates = useMemo(() => {
    return templates.filter((t) => {
      // Category filter
      if (filterCategory && t.category !== filterCategory) {
        return false
      }
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        return (
          t.display_name.toLowerCase().includes(query) ||
          t.description.toLowerCase().includes(query) ||
          t.template_id.toLowerCase().includes(query)
        )
      }
      return true
    })
  }, [templates, filterCategory, searchQuery])

  // Group templates by category for display
  const groupedTemplates = useMemo(() => {
    const groups: Record<string, TemplateSchema[]> = {}
    for (const t of filteredTemplates) {
      if (!groups[t.category]) {
        groups[t.category] = []
      }
      groups[t.category].push(t)
    }
    return groups
  }, [filteredTemplates])

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <p className="text-sm text-muted">Loading templates...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="mb-4 rounded-full bg-red-500/20 p-3">
          <svg
            className="h-6 w-6 text-red-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <p className="mb-2 text-sm font-medium text-red-400">
          Failed to load templates
        </p>
        <p className="text-xs text-muted">{error}</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-primary">
          Choose a Template
        </h2>
        <span className="text-xs text-muted">
          {templates.length} templates available
        </span>
      </div>

      {/* Search and Filter */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        {/* Search input */}
        <div className="relative flex-1">
          <input
            type="text"
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-accent/30 bg-secondary/40 px-4 py-2 pl-10 text-sm text-primary placeholder-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/50"
          />
          <svg
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        {/* Category filter */}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setFilterCategory(null)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filterCategory === null
                ? 'bg-primary text-primaryAccent'
                : 'bg-secondary text-muted hover:bg-secondary/80 hover:text-primary'
            }`}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setFilterCategory(cat)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                filterCategory === cat
                  ? 'bg-primary text-primaryAccent'
                  : 'bg-secondary text-muted hover:bg-secondary/80 hover:text-primary'
              }`}
            >
              {CATEGORY_LABELS[cat] || cat}
            </button>
          ))}
        </div>
      </div>

      {/* Templates grid */}
      {filteredTemplates.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12">
          <p className="text-sm text-muted">No templates found</p>
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="mt-2 text-xs text-primary hover:underline"
            >
              Clear search
            </button>
          )}
        </div>
      ) : filterCategory ? (
        // Single category view (flat grid)
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredTemplates.map((template) => (
            <TemplateCard
              key={template.template_id}
              template={template}
              isSelected={selectedTemplateId === template.template_id}
              onSelect={onSelectTemplate}
            />
          ))}
        </div>
      ) : (
        // Grouped by category view
        <div className="space-y-6">
          {CATEGORY_ORDER.filter((cat) => groupedTemplates[cat]?.length > 0).map(
            (category) => (
              <div key={category}>
                <h3 className="mb-3 text-sm font-medium text-muted">
                  {CATEGORY_LABELS[category] || category}
                </h3>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {groupedTemplates[category].map((template) => (
                    <TemplateCard
                      key={template.template_id}
                      template={template}
                      isSelected={selectedTemplateId === template.template_id}
                      onSelect={onSelectTemplate}
                    />
                  ))}
                </div>
              </div>
            )
          )}
        </div>
      )}
    </div>
  )
}

export default TemplateGallery
