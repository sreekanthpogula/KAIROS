import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import { Card, CardHeader } from '../components/ui/Card'
import { ConfidenceBadge, DomainBadge, Pill, SecurityBadge, StatusBadge } from '../components/ui/Badge'
import { LineageTree } from '../components/LineageTree'

const TABS = ['Overview', 'Classification', 'Sections & Chunks', 'Lineage', 'Processing History'] as const

export function DocumentDetail() {
  const { id } = useParams<{ id: string }>()
  const [tab, setTab] = useState<(typeof TABS)[number]>('Overview')
  const { data, loading, error } = useApi(() => api.getDocument(id!), [id])
  const { data: chunks } = useApi(() => api.getDocumentChunks(id!), [id])
  const { data: lineage } = useApi(() => api.getDocumentLineage(id!), [id])

  if (loading) return <p className="text-sm text-[var(--text-muted)]">Loading…</p>
  if (error || !data) return <p className="text-sm text-[var(--status-critical)]">Failed to load document: {error}</p>

  const { document: doc } = data

  return (
    <div className="space-y-5">
      <div>
        <Link to="/documents" className="text-xs text-[var(--text-muted)] hover:underline">
          ← Document Explorer
        </Link>
        <div className="mt-1 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">{doc.filename}</h1>
            <div className="mt-1.5 flex items-center gap-2">
              <StatusBadge status={doc.status} />
              <DomainBadge domain={doc.domain} />
              <SecurityBadge level={doc.security_level} />
              <ConfidenceBadge value={doc.classification_confidence} action={doc.confidence_action} />
            </div>
          </div>
        </div>
      </div>

      <div className="flex gap-1 border-b" style={{ borderColor: 'var(--border)' }}>
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="border-b-2 px-3 py-2 text-sm font-medium"
            style={{ borderColor: tab === t ? 'var(--series-1)' : 'transparent', color: tab === t ? 'var(--series-1)' : 'var(--text-secondary)' }}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Overview' && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader title="File Identity" />
            <dl className="grid grid-cols-2 gap-3 p-5 text-sm">
              <Field label="Original filename" value={doc.original_filename} />
              <Field label="MIME type" value={doc.mime_type} />
              <Field label="Size" value={`${(doc.size_bytes / 1024).toFixed(1)} KB`} />
              <Field label="Checksum" value={doc.checksum.slice(0, 16) + '…'} mono />
              <Field label="Source system" value={doc.source_system} />
              <Field label="Page count" value={doc.page_count?.toString() ?? '—'} />
            </dl>
          </Card>
          <Card>
            <CardHeader title="Versioning" subtitle="Preserved per-record so ontology changes never silently rewrite history" />
            <dl className="grid grid-cols-2 gap-3 p-5 text-sm">
              <Field label="Extractor" value={doc.extractor_version ?? '—'} />
              <Field label="Classifier" value={doc.classifier_version ?? '—'} />
              <Field label="Ontology" value={doc.ontology_version ?? '—'} />
              <Field label="Chunker" value={doc.chunker_version ?? '—'} />
              <Field label="Embedding model" value={doc.embedding_model ?? '—'} />
              <Field label="Chunks" value={String(data.chunk_count)} />
            </dl>
          </Card>
          <Card className="lg:col-span-2">
            <CardHeader title="Topics" subtitle="Normalized topic vocabulary matched across this document's chunks" />
            <div className="flex flex-wrap gap-2 p-5">
              {data.topics.length ? data.topics.map((t) => <Pill key={t}>{t.replace(/_/g, ' ')}</Pill>) : <span className="text-xs text-[var(--text-muted)]">None matched.</span>}
            </div>
          </Card>
          <Card className="lg:col-span-2">
            <CardHeader title="Entities" subtitle="Synthetic named entities extracted deterministically" />
            <div className="flex flex-wrap gap-2 p-5">
              {data.entities.length ? (
                data.entities.map((e, i) => (
                  <Pill key={i} tone="info">
                    {e.type}: {e.value}
                  </Pill>
                ))
              ) : (
                <span className="text-xs text-[var(--text-muted)]">None extracted.</span>
              )}
            </div>
          </Card>
        </div>
      )}

      {tab === 'Classification' && (
        <Card>
          <CardHeader title="Classification History" subtitle="Every attempt is preserved — is_current marks the active decision" />
          <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
            {data.classification_history.map((c) => (
              <div key={c.id} className="p-5" style={{ opacity: c.is_current ? 1 : 0.6 }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Pill tone={c.method === 'human' ? 'warning' : c.method.includes('llm') ? 'info' : 'neutral'}>{c.method}</Pill>
                    {c.is_current && <Pill tone="good">current</Pill>}
                    <span className="text-sm font-medium">
                      {c.document_type} / {c.document_subtype}
                    </span>
                  </div>
                  <ConfidenceBadge value={c.confidence} action={c.confidence_action} />
                </div>
                <p className="mt-1 text-xs text-[var(--text-muted)]">{new Date(c.created_at).toLocaleString()} · ontology: {c.ontology_id ?? 'none'}</p>
                <ul className="mt-2 space-y-0.5 text-xs text-[var(--text-secondary)]">
                  {c.reasoning_signals.map((s, i) => (
                    <li key={i}>✓ {s}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Card>
      )}

      {tab === 'Sections & Chunks' && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader title="Document Segments" subtitle={`${data.segments.length} structural segments`} />
            <ul className="divide-y text-sm" style={{ borderColor: 'var(--border)' }}>
              {data.segments.map((s) => (
                <li key={s.id} className="flex items-center justify-between px-5 py-2.5" style={{ paddingLeft: 20 + s.level * 14 }}>
                  <span>{s.title ?? s.segment_type}</span>
                  <span className="text-xs text-[var(--text-muted)]">{s.segment_type}</span>
                </li>
              ))}
            </ul>
          </Card>
          <Card>
            <CardHeader title="Chunks" subtitle={chunks ? `${chunks.length} chunks · chunker: ${chunks[0]?.chunker_type ?? '—'}` : ''} />
            <ul className="max-h-[480px] divide-y overflow-y-auto text-sm" style={{ borderColor: 'var(--border)' }}>
              {(chunks ?? []).map((c) => (
                <li key={c.chunk_id} className="px-5 py-3">
                  <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
                    <span>
                      #{c.chunk_index} · {c.section ?? 'no section'}
                    </span>
                    <span>{c.page_start ? `p.${c.page_start}${c.page_end && c.page_end !== c.page_start ? `-${c.page_end}` : ''}` : ''}</span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-[var(--text-secondary)]">{c.text}</p>
                  {c.topics.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {c.topics.map((t) => (
                        <Pill key={t}>{t.replace(/_/g, ' ')}</Pill>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}

      {tab === 'Lineage' && (
        <Card>
          <CardHeader title="Source → Document → Segment → Chunk" subtitle="Full traceability graph for this document" />
          <div className="p-5">{lineage ? <LineageTree lineage={lineage} /> : <p className="text-sm text-[var(--text-muted)]">Loading…</p>}</div>
        </Card>
      )}

      {tab === 'Processing History' && (
        <Card>
          <CardHeader title="Processing Events" subtitle="Append-only event log — the in-process stand-in for a Kafka topic" />
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs text-[var(--text-muted)]">
                {['Event', 'Stage', 'Status', 'Duration', 'Message', 'Time'].map((h) => (
                  <th key={h} className="px-5 py-2 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.processing_events.map((e) => (
                <tr key={e.id} className="border-t" style={{ borderColor: 'var(--border)' }}>
                  <td className="px-5 py-2">{e.event_type}</td>
                  <td className="px-5 py-2 text-[var(--text-secondary)]">{e.stage}</td>
                  <td className="px-5 py-2">
                    <Pill tone={e.status === 'SUCCESS' ? 'good' : 'critical'}>{e.status}</Pill>
                  </td>
                  <td className="px-5 py-2 tabular-nums text-[var(--text-muted)]">{e.duration_ms ? `${e.duration_ms.toFixed(0)}ms` : '—'}</td>
                  <td className="px-5 py-2 text-[var(--text-secondary)]">{e.message ?? ''}</td>
                  <td className="px-5 py-2 text-xs text-[var(--text-muted)]">{new Date(e.created_at).toLocaleTimeString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs text-[var(--text-muted)]">{label}</dt>
      <dd className={mono ? 'font-mono text-xs' : ''}>{value}</dd>
    </div>
  )
}
