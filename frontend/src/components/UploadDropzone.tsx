import { useRef, useState } from 'react'
import { api } from '../api/client'
import { Card } from './ui/Card'

interface UploadResult {
  filename: string
  status: 'uploading' | 'done' | 'duplicate' | 'error'
  detail?: string
}

export function UploadDropzone({ onUploaded }: { onUploaded: () => void }) {
  const [dragActive, setDragActive] = useState(false)
  const [results, setResults] = useState<UploadResult[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  async function uploadFiles(files: FileList | File[]) {
    const list = Array.from(files)
    setResults(list.map((f) => ({ filename: f.name, status: 'uploading' })))
    for (const [i, file] of list.entries()) {
      try {
        const res = await api.uploadDocument(file)
        setResults((prev) =>
          prev.map((r, idx) => (idx === i ? { filename: file.name, status: res.is_duplicate ? 'duplicate' : 'done', detail: res.ingestion_status } : r)),
        )
      } catch (e) {
        setResults((prev) => prev.map((r, idx) => (idx === i ? { filename: file.name, status: 'error', detail: (e as Error).message } : r)))
      }
    }
    onUploaded()
  }

  return (
    <Card
      className="border-2 border-dashed p-6 text-center"
      onDragOver={(e) => {
        e.preventDefault()
        setDragActive(true)
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragActive(false)
        if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files)
      }}
      style={{ borderColor: dragActive ? 'var(--series-1)' : 'var(--border)', backgroundColor: dragActive ? 'color-mix(in srgb, var(--series-1) 6%, var(--surface-1))' : 'var(--surface-1)' }}
    >
      <input ref={inputRef} type="file" multiple hidden onChange={(e) => e.target.files && uploadFiles(e.target.files)} />
      <p className="text-sm font-medium">Drop heterogeneous documents here</p>
      <p className="mt-1 text-xs text-[var(--text-muted)]">PDF, DOCX, XLSX, PPTX, HTML, TXT, Markdown, CSV, EML — routed through detect → extract → classify → chunk → embed → index</p>
      <button
        onClick={() => inputRef.current?.click()}
        className="mt-3 rounded-lg px-4 py-1.5 text-sm font-medium text-white"
        style={{ backgroundColor: 'var(--series-1)' }}
      >
        Choose files
      </button>

      {results.length > 0 && (
        <div className="mt-4 space-y-1 text-left text-xs">
          {results.map((r, i) => (
            <div key={i} className="flex items-center justify-between rounded-md px-2 py-1" style={{ backgroundColor: 'var(--surface-2)' }}>
              <span className="truncate">{r.filename}</span>
              <span
                style={{
                  color:
                    r.status === 'done' ? 'var(--status-good)' : r.status === 'duplicate' ? 'var(--status-neutral)' : r.status === 'error' ? 'var(--status-critical)' : 'var(--status-info)',
                }}
              >
                {r.status === 'uploading' ? 'Processing…' : r.status === 'done' ? r.detail : r.status === 'duplicate' ? 'Duplicate — skipped' : r.detail}
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
