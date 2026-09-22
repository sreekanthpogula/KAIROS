import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { RAGQueryResponse } from '../api/types'
import { Card, CardHeader } from '../components/ui/Card'
import { Pill } from '../components/ui/Badge'
import { ScoreBreakdown } from '../components/ScoreBreakdown'
import { useAppState, type Group } from '../state/AppContext'

const DEMO_QUERIES: { query: string; group: Group; label: string }[] = [
  { query: 'What are the provider termination requirements?', group: 'legal', label: 'Demo 1 · Provider termination (as Legal)' },
  { query: 'What reimbursement policies apply to providers?', group: 'finance', label: 'Demo 2 · Reimbursement policy (as Finance)' },
  { query: 'What are the provider termination requirements?', group: 'engineering', label: 'ACL demo · Same question, as Engineering' },
]

const GROUNDEDNESS_COLOR: Record<string, string> = { high: 'var(--status-good)', medium: 'var(--status-warning)', low: 'var(--status-serious)', none: 'var(--status-critical)' }

export function RagPage() {
  const { actingAs, setActingAs } = useAppState()
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<RAGQueryResponse | null>(null)
  const [loading, setLoading] = useState(false)

  async function ask(q: string, group?: Group) {
    setQuery(q)
    if (group) setActingAs(group)
    setLoading(true)
    try {
      setResult(await api.ragQuery({ query: q, requester_group: group ?? actingAs }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Grounded Q&A (RAG)</h1>
        <p className="text-sm text-[var(--text-secondary)]">Deterministic extractive answers in Demo Mode — every sentence is traceable to a specific chunk</p>
      </div>

      <Card className="p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (query.trim()) ask(query)
          }}
          className="flex gap-2"
        >
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question grounded in the ingested corpus…"
            className="flex-1 rounded-lg border bg-transparent px-4 py-2 text-sm outline-none"
            style={{ borderColor: 'var(--border)' }}
          />
          <button type="submit" className="rounded-lg px-5 py-2 text-sm font-medium text-white" style={{ backgroundColor: 'var(--series-1)' }}>
            Ask
          </button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {DEMO_QUERIES.map((d) => (
            <button key={d.label} onClick={() => ask(d.query, d.group)} className="rounded-full border px-3 py-1 text-xs text-[var(--text-secondary)] hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--border)' }}>
              {d.label}
            </button>
          ))}
        </div>
      </Card>

      {loading && <p className="text-sm text-[var(--text-muted)]">Retrieving and composing an answer…</p>}

      {result && !loading && (
        <>
          <Card>
            <CardHeader
              title="Answer"
              action={
                <Pill tone={result.groundedness === 'high' ? 'good' : result.groundedness === 'medium' ? 'warning' : 'critical'}>
                  groundedness: {result.groundedness}
                </Pill>
              }
            />
            <div className="p-5">
              <p className="text-sm leading-relaxed">{result.answer}</p>
              <p className="mt-3 text-xs text-[var(--text-muted)]">
                mode: {result.mode} · {result.excluded_by_acl} documents excluded by ACL · {result.latency_ms}ms
              </p>
            </div>
          </Card>

          {result.citations.length > 0 && (
            <Card>
              <CardHeader title="Citations" subtitle="Answer → Chunk → Section → Document → Source" />
              <ul className="divide-y text-sm" style={{ borderColor: 'var(--border)' }}>
                {result.citations.map((c, i) => (
                  <li key={c.chunk_id} className="flex items-center justify-between px-5 py-3">
                    <div>
                      <span className="mr-2 text-xs font-semibold" style={{ color: 'var(--series-1)' }}>
                        [{i + 1}]
                      </span>
                      <Link to={`/documents/${c.document_id}`} className="hover:underline">
                        {c.document_filename}
                      </Link>
                      <span className="ml-2 text-xs text-[var(--text-muted)]">
                        {c.section} {c.page_start && `· p.${c.page_start}`}
                      </span>
                    </div>
                    <Link to={`/documents/${c.document_id}`} className="text-xs" style={{ color: 'var(--series-1)' }}>
                      View lineage →
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {result.scored_results.length > 0 && (
            <Card>
              <CardHeader title="Retrieval Explanation" subtitle="Full ranked candidate set behind this answer" />
              <div className="max-h-[360px] space-y-3 overflow-y-auto p-5">
                {result.scored_results.map((r) => (
                  <div key={r.chunk_id} className="border-b pb-3 last:border-0" style={{ borderColor: 'var(--border)' }}>
                    <p className="text-xs font-medium">{r.document_filename} — {r.section}</p>
                    <div className="mt-1.5">
                      <ScoreBreakdown scores={r} />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <p className="text-xs" style={{ color: GROUNDEDNESS_COLOR[result.groundedness] }}>
            {result.groundedness === 'none' && 'No relevant, accessible documents were found for this question.'}
          </p>
        </>
      )}
    </div>
  )
}
