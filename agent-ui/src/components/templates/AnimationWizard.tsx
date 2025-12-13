'use client'
import React, { useState, useCallback } from 'react'
import { toast } from 'sonner'
import { useStore } from '@/store'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'
import { APIRoutes } from '@/api/routes'
import {
  TemplateSchema,
  ColumnAnalysis,
  ColumnMappings,
  UploadResponse,
} from '@/types/templates'
import TemplateGallery from './TemplateGallery'
import ColumnMappingDialog from './ColumnMappingDialog'
import useAnimationGenerate from '@/hooks/useAnimationGenerate'

type WizardStep = 'upload' | 'template' | 'mapping' | 'generating' | 'complete'

interface AnimationWizardProps {
  onClose?: () => void
  onComplete?: (videoUrl: string) => void
  initialDatasetId?: string
  initialColumns?: ColumnAnalysis[]
}

const AnimationWizard: React.FC<AnimationWizardProps> = ({
  onClose,
  onComplete,
  initialDatasetId,
  initialColumns,
}) => {
  const selectedEndpoint = useStore((s) => s.selectedEndpoint)

  // Wizard state
  const [step, setStep] = useState<WizardStep>(
    initialDatasetId ? 'template' : 'upload'
  )
  const [datasetId, setDatasetId] = useState<string | null>(
    initialDatasetId || null
  )
  const [columns, setColumns] = useState<ColumnAnalysis[]>(
    initialColumns || []
  )
  const [selectedTemplate, setSelectedTemplate] =
    useState<TemplateSchema | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)

  // Upload state
  const [isUploading, setIsUploading] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)

  // Animation generation hook
  const {
    generate,
    isGenerating,
    progress,
    error: generateError,
    abort,
  } = useAnimationGenerate({
    onComplete: (url) => {
      setVideoUrl(url)
      setStep('complete')
      onComplete?.(url)
    },
    onError: (err) => {
      toast.error(`Generation failed: ${err}`)
    },
  })

  // Handle file upload
  const handleFileUpload = useCallback(
    async (file: File) => {
      setIsUploading(true)
      setUploadedFile(file)

      try {
        const endpointUrl = constructEndpointUrl(selectedEndpoint)
        const url = APIRoutes.UploadDataset(endpointUrl)

        const formData = new FormData()
        formData.append('file', file, file.name)

        const response = await fetch(url, {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          let detail = `HTTP ${response.status}`
          try {
            const errorData = await response.json()
            detail = errorData.detail || JSON.stringify(errorData)
          } catch {
            detail = response.statusText
          }
          throw new Error(detail)
        }

        const data: UploadResponse = await response.json()

        setDatasetId(data.dataset.dataset_id)
        setColumns(data.column_analysis || [])
        setStep('template')

        toast.success('Dataset uploaded successfully')
      } catch (err: any) {
        toast.error(`Upload failed: ${err?.message || String(err)}`)
      } finally {
        setIsUploading(false)
      }
    },
    [selectedEndpoint]
  )

  // Handle template selection
  const handleSelectTemplate = useCallback((template: TemplateSchema) => {
    setSelectedTemplate(template)
    setStep('mapping')
  }, [])

  // Handle column mapping submission
  const handleMappingSubmit = useCallback(
    async (mappings: ColumnMappings) => {
      if (!datasetId || !selectedTemplate) return

      setStep('generating')

      await generate(datasetId, selectedTemplate.template_id, mappings, {
        quality: 'medium',
        aspectRatio: '16:9',
      })
    },
    [datasetId, selectedTemplate, generate]
  )

  // Handle going back
  const handleBack = useCallback(() => {
    switch (step) {
      case 'template':
        if (!initialDatasetId) {
          setStep('upload')
        }
        break
      case 'mapping':
        setSelectedTemplate(null)
        setStep('template')
        break
      case 'generating':
        abort()
        setStep('mapping')
        break
      case 'complete':
        setVideoUrl(null)
        setStep('template')
        break
    }
  }, [step, initialDatasetId, abort])

  // Handle file drop
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      const file = e.dataTransfer.files[0]
      if (file && file.name.endsWith('.csv')) {
        handleFileUpload(file)
      } else {
        toast.error('Please upload a CSV file')
      }
    },
    [handleFileUpload]
  )

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-accent/30 bg-background shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-accent/20 bg-secondary/30 px-6 py-4">
          <div className="flex items-center gap-4">
            {/* Step indicator */}
            <div className="flex items-center gap-2">
              <StepIndicator
                stepNumber={1}
                label="Upload"
                isActive={step === 'upload'}
                isComplete={!!datasetId}
              />
              <div className="h-px w-4 bg-accent/30" />
              <StepIndicator
                stepNumber={2}
                label="Template"
                isActive={step === 'template'}
                isComplete={!!selectedTemplate}
              />
              <div className="h-px w-4 bg-accent/30" />
              <StepIndicator
                stepNumber={3}
                label="Columns"
                isActive={step === 'mapping'}
                isComplete={step === 'generating' || step === 'complete'}
              />
              <div className="h-px w-4 bg-accent/30" />
              <StepIndicator
                stepNumber={4}
                label="Generate"
                isActive={step === 'generating' || step === 'complete'}
                isComplete={step === 'complete'}
              />
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
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

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Step 1: Upload */}
          {step === 'upload' && (
            <div className="flex flex-col items-center justify-center py-12">
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                className="w-full max-w-md cursor-pointer rounded-xl border-2 border-dashed border-accent/40 bg-secondary/20 p-8 text-center transition-colors hover:border-primary/50 hover:bg-secondary/40"
              >
                {isUploading ? (
                  <div className="flex flex-col items-center gap-4">
                    <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                    <p className="text-sm text-primary">
                      Uploading {uploadedFile?.name}...
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="mb-4 flex justify-center">
                      <div className="rounded-full bg-primary/10 p-4">
                        <svg
                          className="h-10 w-10 text-primary"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={1.5}
                            d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                          />
                        </svg>
                      </div>
                    </div>
                    <h3 className="mb-2 text-lg font-semibold text-primary">
                      Upload your dataset
                    </h3>
                    <p className="mb-4 text-sm text-muted">
                      Drag and drop a CSV file here, or click to browse
                    </p>
                    <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primaryAccent hover:bg-primary/90">
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
                          d="M12 4v16m8-8H4"
                        />
                      </svg>
                      Choose file
                      <input
                        type="file"
                        accept=".csv"
                        className="hidden"
                        onChange={(e) => {
                          const file = e.target.files?.[0]
                          if (file) handleFileUpload(file)
                        }}
                      />
                    </label>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Step 2: Template Selection */}
          {step === 'template' && (
            <div>
              {/* Dataset info */}
              {datasetId && columns.length > 0 && (
                <div className="mb-6 rounded-lg border border-accent/20 bg-secondary/20 p-4">
                  <div className="mb-2 text-sm font-medium text-primary">
                    Your Dataset
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {columns.map((col) => (
                      <span
                        key={col.name}
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs ${
                          col.inferred_type === 'numeric'
                            ? 'bg-blue-500/20 text-blue-400'
                            : col.inferred_type === 'temporal'
                              ? 'bg-purple-500/20 text-purple-400'
                              : 'bg-green-500/20 text-green-400'
                        }`}
                      >
                        {col.name}
                        <span className="opacity-60">({col.inferred_type})</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <TemplateGallery
                onSelectTemplate={handleSelectTemplate}
                selectedTemplateId={selectedTemplate?.template_id}
              />
            </div>
          )}

          {/* Step 3: Column Mapping (handled by dialog) */}
          {step === 'mapping' && selectedTemplate && (
            <ColumnMappingDialog
              template={selectedTemplate}
              columns={columns}
              onSubmit={handleMappingSubmit}
              onCancel={handleBack}
              isSubmitting={false}
            />
          )}

          {/* Step 4: Generating */}
          {step === 'generating' && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="mb-6 h-16 w-16 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <h3 className="mb-4 text-lg font-semibold text-primary">
                Generating your animation...
              </h3>

              {/* Progress log */}
              <div className="w-full max-w-lg rounded-lg border border-accent/20 bg-secondary/20 p-4">
                <div className="max-h-48 space-y-2 overflow-y-auto">
                  {progress.map((msg, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-2 text-sm text-muted"
                    >
                      <span className="mt-1 text-primary">→</span>
                      <span>{msg}</span>
                    </div>
                  ))}
                  {isGenerating && (
                    <div className="flex items-center gap-2 text-sm text-primary">
                      <div className="h-2 w-2 animate-pulse rounded-full bg-primary" />
                      <span>Processing...</span>
                    </div>
                  )}
                </div>
              </div>

              {generateError && (
                <div className="mt-4 rounded-lg bg-red-500/10 px-4 py-2 text-sm text-red-400">
                  {generateError}
                </div>
              )}

              <button
                type="button"
                onClick={abort}
                className="mt-6 rounded-lg border border-accent/30 bg-secondary px-4 py-2 text-sm text-muted hover:bg-secondary/80 hover:text-primary"
              >
                Cancel
              </button>
            </div>
          )}

          {/* Step 5: Complete */}
          {step === 'complete' && videoUrl && (
            <div className="flex flex-col items-center justify-center py-8">
              <div className="mb-4 rounded-full bg-green-500/20 p-4">
                <svg
                  className="h-10 w-10 text-green-400"
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
              <h3 className="mb-2 text-lg font-semibold text-primary">
                Animation Ready!
              </h3>
              <p className="mb-6 text-sm text-muted">
                Your animation has been generated successfully.
              </p>

              {/* Video preview */}
              <div className="mb-6 w-full max-w-2xl overflow-hidden rounded-xl border border-accent/30 bg-black">
                <video
                  src={videoUrl}
                  controls
                  autoPlay
                  className="w-full"
                />
              </div>

              <div className="flex gap-3">
                <a
                  href={videoUrl}
                  download
                  className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primaryAccent hover:bg-primary/90"
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
                      d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                    />
                  </svg>
                  Download
                </a>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedTemplate(null)
                    setVideoUrl(null)
                    setStep('template')
                  }}
                  className="flex items-center gap-2 rounded-lg border border-accent/30 bg-secondary px-4 py-2 text-sm font-medium text-primary hover:bg-secondary/80"
                >
                  Create another
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer with back button */}
        {step !== 'upload' && step !== 'generating' && step !== 'mapping' && (
          <div className="border-t border-accent/20 bg-secondary/30 px-6 py-4">
            <button
              type="button"
              onClick={handleBack}
              className="flex items-center gap-2 text-sm text-muted hover:text-primary"
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
                  d="M15 19l-7-7 7-7"
                />
              </svg>
              Back
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// Step indicator component
interface StepIndicatorProps {
  stepNumber: number
  label: string
  isActive: boolean
  isComplete: boolean
}

const StepIndicator: React.FC<StepIndicatorProps> = ({
  stepNumber,
  label,
  isActive,
  isComplete,
}) => {
  return (
    <div className="flex items-center gap-2">
      <div
        className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
          isComplete
            ? 'bg-green-500 text-white'
            : isActive
              ? 'bg-primary text-primaryAccent'
              : 'bg-secondary text-muted'
        }`}
      >
        {isComplete ? (
          <svg
            className="h-3 w-3"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={3}
              d="M5 13l4 4L19 7"
            />
          </svg>
        ) : (
          stepNumber
        )}
      </div>
      <span
        className={`text-xs ${isActive ? 'text-primary' : 'text-muted'}`}
      >
        {label}
      </span>
    </div>
  )
}

export default AnimationWizard
