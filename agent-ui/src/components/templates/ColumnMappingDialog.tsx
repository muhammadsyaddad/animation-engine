'use client'
import React, { useState, useMemo, useCallback } from 'react'
import {
  TemplateSchema,
  AxisRequirement,
  ColumnAnalysis,
  ColumnMappings,
} from '@/types/templates'

interface ColumnMappingDialogProps {
  template: TemplateSchema
  columns: ColumnAnalysis[]
  onSubmit: (mappings: ColumnMappings) => void
  onCancel: () => void
  isSubmitting?: boolean
}

// Map axis data_type to column inferred_type
const typeCompatibility: Record<string, string[]> = {
  numeric: ['numeric'],
  categorical: ['categorical'],
  time: ['temporal', 'numeric'], // time can be temporal or numeric (year as number)
  any: ['numeric', 'categorical', 'temporal'],
}

const isTypeCompatible = (
  axisType: string,
  columnType: string
): boolean => {
  const compatible = typeCompatibility[axisType] || []
  return compatible.includes(columnType)
}

const getTypeColor = (type: string): string => {
  switch (type) {
    case 'numeric':
      return 'bg-blue-500/20 text-blue-400'
    case 'categorical':
      return 'bg-green-500/20 text-green-400'
    case 'temporal':
      return 'bg-purple-500/20 text-purple-400'
    default:
      return 'bg-gray-500/20 text-gray-400'
  }
}

const ColumnMappingDialog: React.FC<ColumnMappingDialogProps> = ({
  template,
  columns,
  onSubmit,
  onCancel,
  isSubmitting = false,
}) => {
  // Initialize mappings state with empty values
  const [mappings, setMappings] = useState<Record<string, string | null>>(() => {
    const initial: Record<string, string | null> = {}
    template.axes.forEach((axis) => {
      initial[axis.name] = null
    })
    return initial
  })

  // Get compatible columns for an axis
  const getCompatibleColumns = useCallback(
    (axis: AxisRequirement): ColumnAnalysis[] => {
      return columns.filter((col) =>
        isTypeCompatible(axis.data_type, col.inferred_type)
      )
    },
    [columns]
  )

  // Check if all required fields are filled
  const canSubmit = useMemo(() => {
    const requiredAxes = template.axes.filter((a) => a.required)
    return requiredAxes.every((axis) => mappings[axis.name])
  }, [template.axes, mappings])

  // Get missing required axes
  const missingRequired = useMemo(() => {
    return template.axes
      .filter((a) => a.required && !mappings[a.name])
      .map((a) => a.label)
  }, [template.axes, mappings])

  const handleMappingChange = (axisName: string, columnName: string | null) => {
    setMappings((prev) => ({
      ...prev,
      [axisName]: columnName,
    }))
  }

  const handleSubmit = () => {
    if (!canSubmit) return

    // Convert to ColumnMappings type
    const columnMappings: ColumnMappings = {}
    Object.entries(mappings).forEach(([key, value]) => {
      if (value) {
        ;(columnMappings as any)[key] = value
      }
    })

    onSubmit(columnMappings)
  }

  // Auto-suggest mappings based on column names
  const handleAutoSuggest = () => {
    const newMappings: Record<string, string | null> = { ...mappings }

    template.axes.forEach((axis) => {
      if (newMappings[axis.name]) return // Skip if already mapped

      const compatibleCols = getCompatibleColumns(axis)
      if (compatibleCols.length === 0) return

      // Try to find a matching column by name similarity
      const axisKeywords = axis.name
        .replace('_column', '')
        .replace('_', ' ')
        .toLowerCase()
        .split(' ')

      for (const col of compatibleCols) {
        const colLower = col.name.toLowerCase()
        const matches = axisKeywords.some(
          (kw) => colLower.includes(kw) || kw.includes(colLower)
        )
        if (matches) {
          newMappings[axis.name] = col.name
          break
        }
      }

      // If no match found and only one compatible column, use it
      if (!newMappings[axis.name] && compatibleCols.length === 1) {
        newMappings[axis.name] = compatibleCols[0].name
      }
    })

    setMappings(newMappings)
  }

  const handleClearAll = () => {
    const cleared: Record<string, string | null> = {}
    template.axes.forEach((axis) => {
      cleared[axis.name] = null
    })
    setMappings(cleared)
  }

  const requiredAxes = template.axes.filter((a) => a.required)
  const optionalAxes = template.axes.filter((a) => !a.required)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 max-h-[90vh] w-full max-w-2xl overflow-hidden rounded-2xl border border-accent/30 bg-background shadow-2xl">
        {/* Header */}
        <div className="border-b border-accent/20 bg-secondary/30 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-primary">
                Map Your Columns
              </h2>
              <p className="mt-1 text-sm text-muted">
                Template: <span className="text-primary">{template.display_name}</span>
              </p>
            </div>
            <button
              type="button"
              onClick={onCancel}
              className="rounded-lg p-2 text-muted hover:bg-accent/20 hover:text-primary"
            >
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="max-h-[60vh] overflow-y-auto px-6 py-4">
          {/* Quick actions */}
          <div className="mb-4 flex items-center gap-2">
            <button
              type="button"
              onClick={handleAutoSuggest}
              className="flex items-center gap-2 rounded-lg bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/20"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
              Auto-suggest
            </button>
            <button
              type="button"
              onClick={handleClearAll}
              className="flex items-center gap-2 rounded-lg bg-secondary px-3 py-1.5 text-xs font-medium text-muted hover:bg-secondary/80 hover:text-primary"
            >
              Clear all
            </button>
          </div>

          {/* Required mappings */}
          {requiredAxes.length > 0 && (
            <div className="mb-6">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-primary">
                <span className="flex h-5 w-5 items-center justify-center rounded bg-red-500/20 text-[10px] text-red-400">
                  *
                </span>
                Required
              </h3>
              <div className="space-y-3">
                {requiredAxes.map((axis) => (
                  <AxisMappingRow
                    key={axis.name}
                    axis={axis}
                    columns={columns}
                    selectedColumn={mappings[axis.name]}
                    compatibleColumns={getCompatibleColumns(axis)}
                    onChange={(col) => handleMappingChange(axis.name, col)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Optional mappings */}
          {optionalAxes.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-medium text-muted">Optional</h3>
              <div className="space-y-3">
                {optionalAxes.map((axis) => (
                  <AxisMappingRow
                    key={axis.name}
                    axis={axis}
                    columns={columns}
                    selectedColumn={mappings[axis.name]}
                    compatibleColumns={getCompatibleColumns(axis)}
                    onChange={(col) => handleMappingChange(axis.name, col)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-accent/20 bg-secondary/30 px-6 py-4">
          {/* Validation message */}
          {missingRequired.length > 0 && (
            <div className="mb-3 rounded-lg bg-yellow-500/10 px-3 py-2 text-xs text-yellow-400">
              Missing required: {missingRequired.join(', ')}
            </div>
          )}

          <div className="flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={isSubmitting}
              className="rounded-lg border border-accent/30 bg-secondary px-4 py-2 text-sm font-medium text-primary hover:bg-secondary/80 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canSubmit || isSubmitting}
              className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primaryAccent hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primaryAccent border-t-transparent" />
                  Generating...
                </>
              ) : (
                <>
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  Generate Animation
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Sub-component for individual axis mapping row
interface AxisMappingRowProps {
  axis: AxisRequirement
  columns: ColumnAnalysis[]
  selectedColumn: string | null
  compatibleColumns: ColumnAnalysis[]
  onChange: (columnName: string | null) => void
}

const AxisMappingRow: React.FC<AxisMappingRowProps> = ({
  axis,
  columns,
  selectedColumn,
  compatibleColumns,
  onChange,
}) => {
  const selectedColData = columns.find((c) => c.name === selectedColumn)

  return (
    <div className="rounded-lg border border-accent/20 bg-secondary/20 p-3">
      <div className="mb-2 flex items-start justify-between">
        <div>
          <label className="text-sm font-medium text-primary">
            {axis.label}
          </label>
          {axis.description && (
            <p className="mt-0.5 text-xs text-muted">{axis.description}</p>
          )}
        </div>
        <span
          className={`rounded px-2 py-0.5 text-[10px] font-medium ${getTypeColor(
            axis.data_type
          )}`}
        >
          {axis.data_type}
        </span>
      </div>

      <select
        value={selectedColumn || ''}
        onChange={(e) => onChange(e.target.value || null)}
        className="w-full rounded-lg border border-accent/30 bg-background px-3 py-2 text-sm text-primary focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/50"
      >
        <option value="">Select a column...</option>

        {/* Compatible columns first */}
        {compatibleColumns.length > 0 && (
          <optgroup label="Recommended">
            {compatibleColumns.map((col) => (
              <option key={col.name} value={col.name}>
                {col.name} ({col.inferred_type})
              </option>
            ))}
          </optgroup>
        )}

        {/* Other columns (not recommended but available) */}
        {columns.filter(
          (c) => !compatibleColumns.find((cc) => cc.name === c.name)
        ).length > 0 && (
          <optgroup label="Other columns">
            {columns
              .filter((c) => !compatibleColumns.find((cc) => cc.name === c.name))
              .map((col) => (
                <option key={col.name} value={col.name}>
                  {col.name} ({col.inferred_type})
                </option>
              ))}
          </optgroup>
        )}
      </select>

      {/* Show sample values if column is selected */}
      {selectedColData && selectedColData.sample_values.length > 0 && (
        <div className="mt-2 text-xs text-muted">
          <span className="opacity-70">Sample:</span>{' '}
          {selectedColData.sample_values.slice(0, 3).join(', ')}
          {selectedColData.sample_values.length > 3 && '...'}
        </div>
      )}
    </div>
  )
}

export default ColumnMappingDialog
