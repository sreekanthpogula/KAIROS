import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import { Card, EmptyState } from '../components/ui/Card'
import { ConfidenceBadge, DomainBadge, SecurityBadge, StatusBadge } from '../components/ui/Badge'
import { UploadDropzone } from '../components/UploadDropzone'

export function Documents() {
  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const { data, loading, refetch } = useApi(() => api.listDocuments({ q, status_filter: statusFilter }), [q, statusFilter])

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Document Explorer</h1>
          <p className="text-sm text-[var(--text-secondary)]">{data?.total ?? 0} documents ingested</p>
        </div>
      </div>

      <UploadDropzone onUploaded={refetch} />

      <Card>
        <div className="flex flex-wrap items-center gap-3 border-b p-4" style={{ borderColor: 'var(--border)' }}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search filename…"
            className="flex-1 min-w-[180px] rounded-md border bg-transparent px-3 py-1.5 text-sm outline-none"
            style={{ borderColor: 'var(--border)' }}
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border bg-transparent px-2 py-1.5 text-sm"
            style={{ borderColor: 'var(--border)' }}
          >
            <option value="">All statuses</option>
            {['READY', 'REVIEW_REQUIRED', 'FAILED', 'DUPLICATE'].map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <p className="p-6 text-sm text-[var(--text-muted)]">Loading…</p>
        ) : !data?.items.length ? (
          <EmptyState title="No documents match" description="Try clearing filters, or upload a document above." />
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs text-[var(--text-muted)]">
                {['Filename', 'Type', 'Domain', 'Confidence', 'Status', 'Security', 'Created'].map((h) => (
                  <th key={h} className="px-4 py-2 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.items.map((doc) => (
                <tr key={doc.id} className="border-t" style={{ borderColor: 'var(--border)' }}>
                  <td className="px-4 py-3">
                    <Link to={`/documents/${doc.id}`} className="font-medium hover:underline" style={{ color: 'var(--series-1)' }}>
                      {doc.filename}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-[var(--text-secondary)]">{doc.document_type?.replace(/_/g, ' ') ?? '—'}</td>
                  <td className="px-4 py-3">
                    <DomainBadge domain={doc.domain} />
                  </td>
                  <td className="px-4 py-3">
                    <ConfidenceBadge value={doc.classification_confidence} action={doc.confidence_action} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={doc.status} />
                  </td>
                  <td className="px-4 py-3">
                    <SecurityBadge level={doc.security_level} />
                  </td>
                  <td className="px-4 py-3 text-xs text-[var(--text-muted)]">{new Date(doc.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}
