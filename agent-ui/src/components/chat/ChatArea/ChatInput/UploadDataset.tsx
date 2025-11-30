'use client'
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useStore } from '@/store'
import { toast } from 'sonner'
import Icon from '@/components/ui/icon'
import { constructEndpointUrl } from '@/lib/constructEndpointUrl'

type UploadedDataset = {
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

interface UploadResponse {
  dataset: UploadedDataset
}

type Mode = 'single' | 'bundle'

const readableSize = (bytes?: number | null) => {
  if (!bytes || bytes <= 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

const UploadDataset: React.FC = () => {
  const selectedEndpoint = useStore((s) => s.selectedEndpoint)
  const chatInputRef = useStore((s) => s.chatInputRef)
  const [mode, setMode] = useState<Mode>('single')

  const [singleFile, setSingleFile] = useState<File | null>(null)
  const [xFile, setXFile] = useState<File | null>(null)
  const [yFile, setYFile] = useState<File | null>(null)
  const [rFile, setRFile] = useState<File | null>(null)
  const [groupFile, setGroupFile] = useState<File | null>(null)

  const [chartTypeHint, setChartTypeHint] = useState<string>('auto')
  const [forceUnify, setForceUnify] = useState<boolean>(false)

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState<UploadedDataset | null>(null)

  const [open, setOpen] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  // Reset form when switching mode
  useEffect(() => {
    setResult(null)
    setSingleFile(null)
    setXFile(null)
    setYFile(null)
    setRFile(null)
    setGroupFile(null)
  }, [mode])

  const effectiveChartHint =
    chartTypeHint === 'auto' ? undefined : chartTypeHint

  const canSubmit = (() => {
    if (mode === 'single') return !!singleFile
    return !!(xFile && yFile && rFile)
  })()

  const handleInsertPath = useCallback(() => {
    if (!result?.unified_rel_url || !chatInputRef?.current) {
      toast.error('Nothing to insert')
      return
    }
    const insertion = ` csv_path=${result.unified_rel_url}`
    const ta = chatInputRef.current
    const start = ta.selectionStart || ta.value.length
    const end = ta.selectionEnd || ta.value.length
    const newValue = ta.value.slice(0, start) + insertion + ta.value.slice(end)
    ta.value = newValue
    ta.focus()
    ta.selectionStart = ta.selectionEnd = start + insertion.length
    toast.success('Inserted csv_path into prompt input')
  }, [result, chatInputRef])

  const handleCopyPath = useCallback(() => {
    if (!result?.unified_rel_url) {
      toast.error('No path to copy')
      return
    }
    navigator.clipboard
      .writeText(result.unified_rel_url)
      .then(() => toast.success('Copied path'))
      .catch(() => toast.error('Clipboard failed'))
  }, [result])

  const handleUpload = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      if (!canSubmit || isSubmitting) return
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      setIsSubmitting(true)
      setResult(null)
      toast.loading('Uploading dataset...')
      try {
        const endpointUrl = constructEndpointUrl(selectedEndpoint)
        const url = `${endpointUrl}/v1/datasets/upload`
        const fd = new FormData()
        if (mode === 'single') {
          if (singleFile) fd.append('file', singleFile, singleFile.name)
          if (forceUnify) fd.append('force_unify', 'true')
        } else {
          if (xFile) fd.append('x_file', xFile, xFile.name)
          if (yFile) fd.append('y_file', yFile, yFile.name)
          if (rFile) fd.append('r_file', rFile, rFile.name)
          if (groupFile) fd.append('group_file', groupFile, groupFile.name)
          if (forceUnify) fd.append('force_unify', 'true')
        }
        if (effectiveChartHint) fd.append('chart_type_hint', effectiveChartHint)
        const resp = await fetch(url, {
          method: 'POST',
          body: fd,
          signal: controller.signal
        })
        if (!resp.ok) {
          let detail = ''
          try {
            const data = await resp.json()
            detail =
              typeof data === 'object' ? JSON.stringify(data) : String(data)
          } catch {
            detail = `${resp.status} ${resp.statusText}`
          }
          throw new Error(detail)
        }
        const json: UploadResponse = await resp.json()
        setResult(json.dataset)
        toast.success('Dataset uploaded')
      } catch (err: any) {
        if (err?.name === 'AbortError') {
          toast.error('Upload aborted')
        } else {
          toast.error(`Upload failed: ${err?.message || String(err)}`)
        }
      } finally {
        setIsSubmitting(false)
        toast.dismiss()
      }
    },
    [
      canSubmit,
      isSubmitting,
      selectedEndpoint,
      singleFile,
      mode,
      xFile,
      yFile,
      rFile,
      groupFile,
      effectiveChartHint,
      forceUnify
    ]
  )

  const handleAbort = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return (
    <div className="w-full">
      <div className="mb-2 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-2 rounded-md border border-accent/40 bg-secondary px-3 py-1 text-xs text-primary hover:bg-secondary/80"
        >
          <Icon type="plus-icon" color="primary" className="h-3 w-3" />
          {open ? 'Close Dataset Upload' : 'Upload Dataset'}
        </button>
        {result?.unified_rel_url && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleInsertPath}
              className="rounded-md border border-accent/40 bg-primary px-3 py-1 text-xs text-primaryAccent hover:bg-primary/90"
            >
              Insert csv_path
            </button>
            <button
              type="button"
              onClick={handleCopyPath}
              className="rounded-md border border-accent/40 bg-secondary px-3 py-1 text-xs text-primary hover:bg-secondary/80"
            >
              Copy csv_path
            </button>
          </div>
        )}
      </div>
      {open && (
        <form
          onSubmit={handleUpload}
          className="mb-3 w-full rounded-lg border border-accent/30 bg-secondary/60 p-3 text-xs text-primary"
        >
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="mode"
                value="single"
                checked={mode === 'single'}
                onChange={() => setMode('single')}
              />
              Single CSV
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="mode"
                value="bundle"
                checked={mode === 'bundle'}
                onChange={() => setMode('bundle')}
              />
              Danim bundle (X,Y,R[,Group])
            </label>
            <label className="flex items-center gap-2">
              <span>Chart hint:</span>
              <select
                value={chartTypeHint}
                onChange={(e) => setChartTypeHint(e.target.value)}
                className="rounded border border-accent/40 bg-primaryAccent px-2 py-1 text-primary"
              >
                <option value="auto">auto</option>
                <option value="bubble">bubble</option>
                <option value="distribution">distribution</option>
              </select>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={forceUnify}
                onChange={(e) => setForceUnify(e.target.checked)}
              />
              force_unify
            </label>
          </div>

          {mode === 'single' && (
            <div className="mb-3 flex flex-col gap-2">
              <label className="flex flex-col gap-1">
                <span className="opacity-80">Unified CSV (long-form)</span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setSingleFile(e.target.files?.[0] || null)}
                  className="rounded border border-accent/40 bg-primaryAccent px-2 py-1 text-primaryAccent file:mr-2 file:rounded file:border-0 file:bg-primary file:px-2 file:py-1 file:text-xs file:font-medium file:text-primaryAccent"
                />
              </label>
              {singleFile && (
                <div className="text-[11px] text-muted">
                  {singleFile.name} • {readableSize(singleFile.size)}
                </div>
              )}
            </div>
          )}

          {mode === 'bundle' && (
            <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-2">
              <label className="flex flex-col gap-1">
                <span className="opacity-80">X.csv</span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setXFile(e.target.files?.[0] || null)}
                  className="rounded border border-accent/40 bg-primaryAccent px-2 py-1 text-primaryAccent file:mr-2 file:rounded file:border-0 file:bg-primary file:px-2 file:py-1 file:text-xs file:font-medium file:text-primaryAccent"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="opacity-80">Y.csv</span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setYFile(e.target.files?.[0] || null)}
                  className="rounded border border-accent/40 bg-primaryAccent px-2 py-1 text-primaryAccent file:mr-2 file:rounded file:border-0 file:bg-primary file:px-2 file:py-1 file:text-xs file:font-medium file:text-primaryAccent"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="opacity-80">R.csv</span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setRFile(e.target.files?.[0] || null)}
                  className="rounded border border-accent/40 bg-primaryAccent px-2 py-1 text-primaryAccent file:mr-2 file:rounded file:border-0 file:bg-primary file:px-2 file:py-1 file:text-xs file:font-medium file:text-primaryAccent"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="opacity-80">Group_lable.csv (optional)</span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setGroupFile(e.target.files?.[0] || null)}
                  className="rounded border border-accent/40 bg-primaryAccent px-2 py-1 text-primaryAccent file:mr-2 file:rounded file:border-0 file:bg-primary file:px-2 file:py-1 file:text-xs file:font-medium file:text-primaryAccent"
                />
              </label>
            </div>
          )}

          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={!canSubmit || isSubmitting}
              className="flex items-center gap-2 rounded-md bg-primary px-3 py-1 text-xs font-medium text-primaryAccent disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Icon
                type="plus-icon"
                color="primaryAccent"
                className="h-3 w-3"
              />
              {isSubmitting ? 'Uploading...' : 'Upload'}
            </button>
            {isSubmitting && (
              <button
                type="button"
                onClick={handleAbort}
                className="rounded-md bg-secondary px-3 py-1 text-xs text-primary hover:bg-secondary/70"
              >
                Abort
              </button>
            )}
          </div>

          {result && (
            <div className="mt-4 rounded-md border border-accent/30 bg-primaryAccent/10 p-3 text-[11px]">
              <div className="mb-1 font-semibold">Uploaded Dataset</div>
              <div className="grid grid-cols-1 gap-y-1 md:grid-cols-2">
                <div>
                  <span className="opacity-70">dataset_id:</span>{' '}
                  <code className="break-all">{result.dataset_id}</code>
                </div>
                <div>
                  <span className="opacity-70">chart_type_hint:</span>{' '}
                  {result.chart_type_hint || '—'}
                </div>
                <div>
                  <span className="opacity-70">unified:</span>{' '}
                  {result.unified ? 'yes' : 'no'}
                </div>
                <div>
                  <span className="opacity-70">size:</span>{' '}
                  {readableSize(result.size_bytes)}
                </div>
                <div className="md:col-span-2">
                  <span className="opacity-70">columns:</span>{' '}
                  {result.columns.length > 0 ? result.columns.join(', ') : '—'}
                </div>
                <div className="md:col-span-2">
                  <span className="opacity-70">csv_path:</span>{' '}
                  {result.unified_rel_url ? (
                    <code className="break-all">{result.unified_rel_url}</code>
                  ) : (
                    '—'
                  )}
                </div>
              </div>
              {!result.unified_rel_url && (
                <div className="mt-2 text-muted">
                  No unified_rel_url produced (unexpected). The upload may have
                  failed to write files correctly.
                </div>
              )}
              {result.unified_rel_url && (
                <div className="mt-2 text-[10px] italic text-muted">
                  Use in prompt: "Please animate my data (bubble). csv_path=
                  {result.unified_rel_url}"
                </div>
              )}
            </div>
          )}
        </form>
      )}
    </div>
  )
}

export default UploadDataset
