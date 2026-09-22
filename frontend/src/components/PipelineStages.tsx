const STAGES = [
  'RECEIVED', 'VALIDATED', 'EXTRACTING', 'EXTRACTED', 'CLASSIFYING', 'CLASSIFIED',
  'ONTOLOGY_MAPPED', 'ENRICHED', 'SEGMENTED', 'CHUNKED', 'EMBEDDING', 'INDEXED', 'READY',
]

export function PipelineStages({ currentStatus }: { currentStatus?: string }) {
  const currentIndex = currentStatus ? STAGES.indexOf(currentStatus) : -1
  const isTerminalBranch = currentStatus === 'REVIEW_REQUIRED' || currentStatus === 'FAILED' || currentStatus === 'DUPLICATE'

  return (
    <div className="overflow-x-auto">
      <div className="flex min-w-max items-center">
        {STAGES.map((stage, i) => {
          const done = currentIndex >= 0 && i < currentIndex
          const active = i === currentIndex
          const color = active ? 'var(--series-1)' : done ? 'var(--status-good)' : 'var(--gridline)'
          return (
            <div key={stage} className="flex items-center">
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className="flex h-8 w-8 items-center justify-center rounded-full border-2 text-[10px] font-semibold"
                  style={{ borderColor: color, color: active || done ? color : 'var(--text-muted)', backgroundColor: active ? `color-mix(in srgb, ${color} 15%, transparent)` : 'transparent' }}
                >
                  {i + 1}
                </div>
                <span className="w-16 text-center text-[10px] leading-tight text-[var(--text-muted)]">{stage.replace(/_/g, ' ')}</span>
              </div>
              {i < STAGES.length - 1 && <div className="h-0.5 w-6" style={{ backgroundColor: done ? 'var(--status-good)' : 'var(--gridline)' }} />}
            </div>
          )
        })}
      </div>
      {isTerminalBranch && (
        <p className="mt-2 text-xs" style={{ color: currentStatus === 'FAILED' ? 'var(--status-critical)' : currentStatus === 'DUPLICATE' ? 'var(--text-muted)' : 'var(--status-serious)' }}>
          Branched to {currentStatus?.replace(/_/g, ' ')} — {currentStatus === 'REVIEW_REQUIRED' ? 'pipeline paused pending human review, resumes from SEGMENTED after resolution' : currentStatus === 'FAILED' ? 'see error message / retry' : 'checksum matched an existing document, no reprocessing'}
        </p>
      )}
    </div>
  )
}
