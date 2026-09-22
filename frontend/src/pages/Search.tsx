import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { SearchResponse } from '../api/types'
import { Card, EmptyState } from '../components/ui/Card'
import { DomainBadge, Pill, SecurityBadge } from '../components/ui/Badge'
import { ScoreBreakdown } from '../components/ScoreBreakdown'
import { useAppState } from '../state/AppContext'

const SUGGESTED = ['What are the provider termination requirements?', 'What reimbursement policies apply to providers?', 'What are the HIPAA breach notification requirements?']

export function Search() {
  const { actingAs } = useAppState()
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)

  async function runSearch(q: string) {
    setQuery(q)
    setLoading(true)
    try {
      setResult(await api.search({ query: q, requester_group: actingAs }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Hybrid Search</h1>
        <p className="text-sm text-[var(--text-secondary)]">
          query understanding → ontology/metadata filters → ACL filter → vector retrieval → lexical retrieval → fusion — acting as <strong className="capitalize">{actingAs}</strong>
        </p>
      </div>

      <Card className="p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (query.trim()) runSearch(query)
          }}
          className="flex gap-2"
        >
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about provider agreements, reimbursement, compliance…"
            className="flex-1 rounded-lg border bg-transparent px-4 py-2 text-sm outline-none"
            style={{ borderColor: 'var(--border)' }}
          />
          <button type="submit" className="rounded-lg px-5 py-2 text-sm font-medium text-white" style={{ backgroundColor: 'var(--series-1)' }}>
            Search
          </button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTED.map((s) => (
            <button key={s} onClick={() => runSearch(s)} className="rounded-full border px-3 py-1 text-xs text-[var(--text-secondary)] hover:bg-[var(--surface-2)]" style={{ borderColor: 'var(--border)' }}>
              {s}
            </button>
          ))}
        </div>
      </Card>

      {loading && <p className="text-sm text-[var(--text-muted)]">Searching…</p>}

      {result && !loading && (
        <>
          <Card className="p-4">
            <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--text-secondary)]">
              <span>{result.total_candidates} candidates</span>
              <span>·</span>
              <span>{result.excluded_by_acl} excluded by ACL</span>
              <span>·</span>
              <span>{result.latency_ms}ms</span>
              {result.understanding.domain && (
                <>
                  <span>·</span>
                  <span>
                    understood as <DomainBadge domain={result.understanding.domain} /> / {result.understanding.document_type}
                  </span>
                </>
              )}
              {result.understanding.topics.map((t) => (
                <Pill key={t} tone="info">
                  {t.replace(/_/g, ' ')}
                </Pill>
              ))}
            </div>
          </Card>

          {result.results.length === 0 ? (
            <Card>
              <EmptyState
                title="No accessible results"
                description={result.excluded_by_acl > 0 ? `${result.excluded_by_acl} documents matched but are outside "${actingAs}"'s access level.` : 'Try a different query.'}
              />
            </Card>
          ) : (
            <div className="space-y-3">
              {result.results.map((r) => (
                <Card key={r.chunk_id} className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <Link to={`/documents/${r.document_id}`} className="text-sm font-semibold hover:underline" style={{ color: 'var(--series-1)' }}>
                        {r.document_filename}
                      </Link>
                      <p className="text-xs text-[var(--text-muted)]">
                        {r.section ?? 'no section'} {r.page_start && `· p.${r.page_start}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <DomainBadge domain={r.domain} />
                      <SecurityBadge level={r.security_level} />
                    </div>
                  </div>
                  <p className="mt-2 text-sm text-[var(--text-secondary)]">{r.text.slice(0, 260)}{r.text.length > 260 ? '…' : ''}</p>
                  <div className="mt-3 border-t pt-3" style={{ borderColor: 'var(--border)' }}>
                    <ScoreBreakdown scores={r} />
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
