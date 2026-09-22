import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useApi } from '../hooks/useApi'
import { Card, CardHeader, EmptyState } from '../components/ui/Card'
import { OntologyTreeView } from '../components/OntologyTreeView'
import { ConfidenceBadge, Pill, StatusBadge } from '../components/ui/Badge'

export function Ontology() {
  const { data: tree, loading } = useApi(() => api.getOntologyTree(), [])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { data: stats } = useApi(() => (selectedId ? api.getOntologyNode(selectedId) : Promise.resolve(null)), [selectedId])

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Ontology Explorer</h1>
        <p className="text-sm text-[var(--text-secondary)]">Healthcare v1.0 — the controlled vocabulary every classification must resolve into</p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader title="Healthcare" subtitle={tree ? `${tree.document_count} documents · ${tree.chunk_count} chunks` : ''} />
          <div className="max-h-[600px] overflow-y-auto p-3">
            {loading || !tree ? <p className="p-3 text-sm text-[var(--text-muted)]">Loading…</p> : <OntologyTreeView root={tree} selectedId={selectedId} onSelect={setSelectedId} />}
          </div>
        </Card>

        <div className="lg:col-span-2">
          {!stats ? (
            <Card>
              <EmptyState title="Select a node" description="Click any domain, category, or type in the tree to see its documents, entities, and topics." />
            </Card>
          ) : (
            <div className="space-y-4">
              <Card>
                <CardHeader title={stats.path.join(' / ')} subtitle={`level: ${stats.level}`} />
                <div className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-2">
                  <div>
                    <p className="text-xs text-[var(--text-muted)]">Documents</p>
                    <p className="text-2xl font-semibold">{stats.document_count}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-muted)]">Chunks</p>
                    <p className="text-2xl font-semibold">{stats.chunk_count}</p>
                  </div>
                </div>
              </Card>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Card>
                  <CardHeader title="Top Entities" />
                  <div className="flex flex-wrap gap-2 p-5">
                    {stats.top_entities.length ? stats.top_entities.map((e) => <Pill key={e.value}>{e.value} ({e.count})</Pill>) : <span className="text-xs text-[var(--text-muted)]">None yet.</span>}
                  </div>
                </Card>
                <Card>
                  <CardHeader title="Top Topics" />
                  <div className="flex flex-wrap gap-2 p-5">
                    {stats.top_topics.length ? (
                      stats.top_topics.map((t) => (
                        <Pill key={t.topic} tone="info">
                          {t.topic.replace(/_/g, ' ')} ({t.count})
                        </Pill>
                      ))
                    ) : (
                      <span className="text-xs text-[var(--text-muted)]">None yet.</span>
                    )}
                  </div>
                </Card>
              </div>

              <Card>
                <CardHeader title="Recent Documents" />
                {stats.recent_documents.length === 0 ? (
                  <EmptyState title="No documents classified into this node yet" />
                ) : (
                  <ul className="divide-y text-sm" style={{ borderColor: 'var(--border)' }}>
                    {stats.recent_documents.map((d) => (
                      <li key={d.id} className="flex items-center justify-between px-5 py-2.5">
                        <Link to={`/documents/${d.id}`} className="hover:underline" style={{ color: 'var(--series-1)' }}>
                          {d.filename}
                        </Link>
                        <div className="flex items-center gap-3">
                          <ConfidenceBadge value={d.confidence} />
                          <StatusBadge status={d.status} />
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
