/**
 * TypeScript types for animation templates and generation
 */

// Axis requirement for a template
export interface AxisRequirement {
  name: string
  label: string
  required: boolean
  data_type: 'numeric' | 'categorical' | 'time' | 'any'
  description?: string
}

// Template schema returned by API
export interface TemplateSchema {
  template_id: string
  display_name: string
  description: string
  preview_url?: string | null
  preview_fallback_url?: string | null
  category: string
  axes: AxisRequirement[]
}

// Response from GET /v1/templates
export interface TemplateListResponse {
  templates: TemplateSchema[]
  total: number
}

// Column analysis from upload response
export interface ColumnAnalysis {
  name: string
  inferred_type: 'numeric' | 'categorical' | 'temporal'
  unique_count: number
  sample_values: string[]
}

// Column mappings for animation generation
export interface ColumnMappings {
  entity_column?: string | null
  value_column?: string | null
  time_column?: string | null
  group_column?: string | null
  x_column?: string | null
  y_column?: string | null
  size_column?: string | null
  label_column?: string | null
  category_column?: string | null
  change_column?: string | null
}

// Request for POST /v1/animations/generate
export interface GenerateAnimationRequest {
  dataset_id: string
  template_id: string
  column_mappings: ColumnMappings
  title?: string | null
  top_n?: number | null
  aspect_ratio?: '16:9' | '9:16' | '1:1'
  quality?: 'low' | 'medium' | 'high'
  session_id?: string | null
}

// SSE event types from animation generation
export type AnimationEventType = 'RunContent' | 'RunError' | 'RunCompleted'

export interface AnimationEvent {
  event: AnimationEventType
  content: string
  created_at: number
  run_id: string
  session_id?: string
  videos?: string[]
}

// Dataset metadata (extended with column_analysis)
export interface DatasetMeta {
  dataset_id: string
  created_at: number
  chart_type_hint?: string | null
  unified: boolean
  original_files: string[]
  unified_path?: string | null
  unified_rel_url?: string | null
  size_bytes?: number | null
  columns: string[]
  sha256?: string | null
}

// Upload response with column analysis
export interface UploadResponse {
  dataset: DatasetMeta
  column_analysis?: ColumnAnalysis[] | null
}

// Template category for grouping in UI
export type TemplateCategory =
  | 'ranking'
  | 'correlation'
  | 'trend'
  | 'distribution'
  | 'dashboard'
  | 'categorical'
  | 'comparison'
  | 'general'

// Helper type for column type matching
export type ColumnDataType =
  | 'numeric'
  | 'categorical'
  | 'temporal'
  | 'time'
  | 'any'

// Validation result for column mappings
export interface ColumnMappingValidation {
  isValid: boolean
  missingRequired: string[]
  typeMismatches: Array<{
    axis: string
    expectedType: ColumnDataType
    actualType: ColumnDataType
  }>
}
