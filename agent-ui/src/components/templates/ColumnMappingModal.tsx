'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { DatasetSummary, TemplateSuggestion } from '@/types/os'
import Icon from '@/components/ui/icon'

// Template column requirements configuration
interface ColumnConfig {
  key: string
  label: string
  description: string
  required: boolean
  columnType: 'any' | 'numeric' | 'categorical' | 'time'
}

interface TemplateColumnRequirements {
  templateId: string
  displayName: string
  description: string
  columns: ColumnConfig[]
}

// Define column requirements for each template
const TEMPLATE_COLUMN_CONFIGS: Record<string, TemplateColumnRequirements> = {
  line_evolution: {
    templateId: 'line_evolution',
    displayName: 'Line Evolution',
    description: 'Animated line chart showing values over time',
    columns: [
      {
        key: 'time_col',
        label: 'Time / X-Axis Column',
        description: 'Column for the horizontal axis (e.g., year, date, month)',
        required: true,
        columnType: 'any'
      },
      {
        key: 'value_col',
        label: 'Value / Y-Axis Column',
        description: 'Numeric column for the vertical axis values',
        required: true,
        columnType: 'numeric'
      },
      {
        key: 'group_col',
        label: 'Group / Series Column',
        description:
          'Optional column to create multiple lines (e.g., category)',
        required: false,
        columnType: 'categorical'
      }
    ]
  },
  bar_race: {
    templateId: 'bar_race',
    displayName: 'Bar Race',
    description: 'Animated bar chart race over time',
    columns: [
      {
        key: 'time_col',
        label: 'Time Column',
        description: 'Column for time progression (e.g., year, date)',
        required: true,
        columnType: 'any'
      },
      {
        key: 'value_col',
        label: 'Value Column',
        description: 'Numeric column for bar heights',
        required: true,
        columnType: 'numeric'
      },
      {
        key: 'category_col',
        label: 'Entity / Category Column',
        description: 'Column representing each bar (e.g., country, product)',
        required: true,
        columnType: 'categorical'
      }
    ]
  },
  count_bar: {
    templateId: 'count_bar',
    displayName: 'Count Bar Chart',
    description: 'Animated bar chart showing counts of categories',
    columns: [
      {
        key: 'count_column',
        label: 'Category Column',
        description: 'Column to count occurrences of (e.g., gender, status)',
        required: true,
        columnType: 'categorical'
      }
    ]
  },
  single_numeric: {
    templateId: 'single_numeric',
    displayName: 'Single Numeric Chart',
    description: 'Bar chart showing numeric values by category',
    columns: [
      {
        key: 'category_column',
        label: 'Category Column',
        description: 'Column for categories (e.g., product, country)',
        required: true,
        columnType: 'categorical'
      },
      {
        key: 'value_column',
        label: 'Value Column',
        description: 'Numeric column for bar values',
        required: true,
        columnType: 'numeric'
      }
    ]
  },
  bubble: {
    templateId: 'bubble',
    displayName: 'Bubble Chart',
    description: 'Animated bubble/scatter chart with optional time animation',
    columns: [
      {
        key: 'x_col',
        label: 'X-Axis Column',
        description: 'Numeric column for horizontal position',
        required: true,
        columnType: 'numeric'
      },
      {
        key: 'y_col',
        label: 'Y-Axis Column',
        description: 'Numeric column for vertical position',
        required: true,
        columnType: 'numeric'
      },
      {
        key: 'r_col',
        label: 'Size Column',
        description: 'Numeric column for bubble size',
        required: false,
        columnType: 'numeric'
      },
      {
        key: 'entity_col',
        label: 'Entity Column',
        description: 'Column identifying each bubble (e.g., country, item)',
        required: true,
        columnType: 'categorical'
      },
      {
        key: 'time_col',
        label: 'Time Column',
        description: 'Optional column for time animation',
        required: false,
        columnType: 'any'
      },
      {
        key: 'group_col',
        label: 'Group / Color Column',
        description: 'Optional column for grouping/coloring bubbles',
        required: false,
        columnType: 'categorical'
      }
    ]
  },
  distribution: {
    templateId: 'distribution',
    displayName: 'Distribution Chart',
    description: 'Animated histogram/distribution visualization',
    columns: [
      {
        key: 'value_col',
        label: 'Value Column',
        description: 'Numeric column to show distribution of',
        required: true,
        columnType: 'numeric'
      },
      {
        key: 'group_col',
        label: 'Group Column',
        description: 'Optional column to compare distributions',
        required: false,
        columnType: 'categorical'
      }
    ]
  },
  bento_grid: {
    templateId: 'bento_grid',
    displayName: 'Bento Grid',
    description: 'Multi-chart dashboard layout',
    columns: [
      {
        key: 'primary_col',
        label: 'Primary Column',
        description: 'Main column for analysis (numeric or categorical)',
        required: false,
        columnType: 'any'
      },
      {
        key: 'secondary_col',
        label: 'Secondary Column',
        description: 'Secondary column for comparison',
        required: false,
        columnType: 'any'
      }
    ]
  }
}

interface ColumnMappingModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (columnMapping: Record<string, string | null>) => void
  template: TemplateSuggestion
  datasetSummary: DatasetSummary | null
  isLoading?: boolean
}

const ColumnMappingModal: React.FC<ColumnMappingModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  template,
  datasetSummary,
  isLoading = false
}) => {
  const [columnMapping, setColumnMapping] = useState<
    Record<string, string | null>
  >({})
  const [error, setError] = useState<string | null>(null)

  // Get column configuration for the selected template
  const templateConfig = useMemo(() => {
    return TEMPLATE_COLUMN_CONFIGS[template.template_id] || null
  }, [template.template_id])

  // Get available columns from dataset summary
  const availableColumns = useMemo(() => {
    if (!datasetSummary?.columns) return []
    return datasetSummary.columns
  }, [datasetSummary])

  const numericColumns = useMemo(() => {
    return datasetSummary?.numeric_columns || []
  }, [datasetSummary])

  const categoricalColumns = useMemo(() => {
    return datasetSummary?.categorical_columns || []
  }, [datasetSummary])

  // Get columns filtered by type
  const getColumnsForType = (
    columnType: ColumnConfig['columnType']
  ): string[] => {
    switch (columnType) {
      case 'numeric':
        return numericColumns.length > 0 ? numericColumns : availableColumns
      case 'categorical':
        return categoricalColumns.length > 0
          ? categoricalColumns
          : availableColumns
      case 'time':
        // Time columns could be in either, or detected separately
        return datasetSummary?.time_column
          ? [
              datasetSummary.time_column,
              ...availableColumns.filter(
                (c) => c !== datasetSummary.time_column
              )
            ]
          : availableColumns
      case 'any':
      default:
        return availableColumns
    }
  }

  // Auto-fill best guesses when modal opens
  useEffect(() => {
    if (!isOpen || !templateConfig) return

    const autoMapping: Record<string, string | null> = {}

    templateConfig.columns.forEach((col) => {
      const candidates = getColumnsForType(col.columnType)

      // Try to find a smart default
      let defaultValue: string | null = null

      // Special handling for known column types
      if (col.key.includes('time') && datasetSummary?.time_column) {
        defaultValue = datasetSummary.time_column
      } else if (col.key.includes('value') && numericColumns.length > 0) {
        defaultValue = numericColumns[0]
      } else if (col.key === 'x_col' && numericColumns.length > 0) {
        defaultValue = numericColumns[0]
      } else if (col.key === 'y_col' && numericColumns.length > 1) {
        defaultValue = numericColumns[1]
      } else if (col.key === 'r_col' && numericColumns.length > 2) {
        defaultValue = numericColumns[2]
      } else if (
        (col.key.includes('category') ||
          col.key.includes('entity') ||
          col.key.includes('group') ||
          col.key.includes('count')) &&
        categoricalColumns.length > 0
      ) {
        defaultValue = categoricalColumns[0]
      } else if (col.columnType === 'numeric' && numericColumns.length > 0) {
        // Find first unused numeric column
        const usedCols = Object.values(autoMapping).filter(Boolean)
        defaultValue =
          numericColumns.find((c) => !usedCols.includes(c)) || numericColumns[0]
      } else if (
        col.columnType === 'categorical' &&
        categoricalColumns.length > 0
      ) {
        // Find first unused categorical column
        const usedCols = Object.values(autoMapping).filter(Boolean)
        defaultValue =
          categoricalColumns.find((c) => !usedCols.includes(c)) ||
          categoricalColumns[0]
      } else if (candidates.length > 0 && col.required) {
        // Fall back to first available
        defaultValue = candidates[0]
      }

      autoMapping[col.key] = defaultValue
    })

    setColumnMapping(autoMapping)
    setError(null)
  }, [
    isOpen,
    templateConfig,
    datasetSummary,
    numericColumns,
    categoricalColumns
  ])

  // Handle column selection change
  const handleColumnChange = (key: string, value: string) => {
    setColumnMapping((prev) => ({
      ...prev,
      [key]: value || null
    }))
    setError(null)
  }

  // Validate and confirm
  const handleConfirm = () => {
    if (!templateConfig) return

    // Check required columns
    const missingRequired = templateConfig.columns
      .filter((col) => col.required && !columnMapping[col.key])
      .map((col) => col.label)

    if (missingRequired.length > 0) {
      setError(`Please select: ${missingRequired.join(', ')}`)
      return
    }

    onConfirm(columnMapping)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-md overflow-hidden rounded-lg border border-border bg-background shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <h2 className="text-base font-medium text-primary">
              {template.display_name}
            </h2>
            {templateConfig && (
              <p className="mt-0.5 text-xs text-muted">
                {templateConfig.description}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1.5 text-muted transition-colors hover:bg-secondary hover:text-primary"
            disabled={isLoading}
          >
            <Icon type="x" size="sm" />
          </button>
        </div>

        {/* Content */}
        <div className="max-h-[60vh] overflow-y-auto px-5 py-4">
          {/* Dataset info */}
          {datasetSummary && (
            <div className="mb-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
              <span className="font-medium text-primary/80">
                {datasetSummary.filename}
              </span>
              {datasetSummary.row_count && (
                <span>{datasetSummary.row_count.toLocaleString()} rows</span>
              )}
              {datasetSummary.column_count && (
                <span>{datasetSummary.column_count} columns</span>
              )}
            </div>
          )}

          {/* Column mappings */}
          {templateConfig ? (
            <div className="space-y-3">
              {templateConfig.columns.map((col) => {
                const candidates = getColumnsForType(col.columnType)

                return (
                  <div key={col.key}>
                    <label className="mb-1 block">
                      <span className="text-xs font-medium text-primary">
                        {col.label}
                        {!col.required && (
                          <span className="ml-1.5 text-muted/60">optional</span>
                        )}
                      </span>
                    </label>
                    <select
                      value={columnMapping[col.key] || ''}
                      onChange={(e) =>
                        handleColumnChange(col.key, e.target.value)
                      }
                      className="w-full rounded border border-border bg-secondary px-3 py-2 text-sm text-primary transition-colors focus:border-primary/40 focus:outline-none"
                      disabled={isLoading}
                    >
                      <option value="">
                        {col.required ? 'Select...' : 'None'}
                      </option>
                      {candidates.map((column) => (
                        <option key={column} value={column}>
                          {column}
                        </option>
                      ))}
                    </select>
                    <p className="mt-1 text-[11px] text-muted/70">
                      {col.description}
                    </p>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="py-6 text-center text-sm text-muted">
              Columns will be auto-detected.
            </div>
          )}

          {/* Error message - subtle, not red */}
          {error && (
            <div className="mt-4 rounded border border-border bg-secondary/60 px-3 py-2 text-xs text-muted">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded px-3 py-1.5 text-sm text-muted transition-colors hover:bg-secondary hover:text-primary"
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            className="flex items-center gap-1.5 rounded bg-primary px-3 py-1.5 text-sm font-medium text-primaryAccent transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <div className="h-3 w-3 animate-spin rounded-full border border-primaryAccent border-t-transparent" />
                <span>Generating...</span>
              </>
            ) : (
              <span>Generate</span>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ColumnMappingModal
export { TEMPLATE_COLUMN_CONFIGS }
export type { ColumnConfig, TemplateColumnRequirements }
