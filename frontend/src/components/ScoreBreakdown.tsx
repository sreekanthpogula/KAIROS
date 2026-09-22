const ROWS: { key: 'semantic_score' | 'lexical_score' | 'ontology_score' | 'metadata_score' | 'final_score'; label: string; color: string }[] = [
  { key: 'semantic_score', label: 'Semantic', color: 'var(--series-1)' },
  { key: 'lexical_score', label: 'Lexical', color: 'var(--series-3)' },
  { key: 'ontology_score', label: 'Ontology', color: 'var(--series-4)' },
  { key: 'metadata_score', label: 'Metadata', color: 'var(--series-2)' },
]

interface Scores {
  semantic_score: number
  lexical_score: number
  ontology_score: number
  metadata_score: number
  final_score: number
}

export function ScoreBreakdown({ scores }: { scores: Scores }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
      {ROWS.map((r) => (
        <div key={r.key}>
          <p className="text-[10px] text-[var(--text-muted)]">{r.label}</p>
          <div className="mt-0.5 flex items-center gap-1.5">
            <div className="relative h-1.5 flex-1 overflow-hidden rounded-full" style={{ backgroundColor: 'var(--gridline)' }}>
              <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${Math.min(scores[r.key] * 100, 100)}%`, backgroundColor: r.color }} />
            </div>
            <span className="w-9 text-right text-[11px] tabular-nums">{scores[r.key].toFixed(2)}</span>
          </div>
        </div>
      ))}
      <div>
        <p className="text-[10px] font-semibold text-[var(--text-secondary)]">Final</p>
        <p className="mt-0.5 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
          {scores.final_score.toFixed(3)}
        </p>
      </div>
    </div>
  )
}
