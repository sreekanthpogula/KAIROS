import type { ReactNode } from 'react'

// CSS custom properties can't take a hex-alpha suffix (`var(--x)1a` isn't
// valid CSS — the trailing chars silently invalidate the whole value).
// color-mix() is the correct way to tint a var() reference.
function tint(color: string, pct: number): string {
  return `color-mix(in srgb, ${color} ${pct}%, transparent)`
}

const STATUS_COLOR: Record<string, string> = {
  READY: 'var(--status-good)',
  AUTO_ACCEPT: 'var(--status-good)',
  SECONDARY_VALIDATION: 'var(--status-warning)',
  REVIEW_REQUIRED: 'var(--status-serious)',
  FAILED: 'var(--status-critical)',
  DUPLICATE: 'var(--status-neutral)',
  PENDING: 'var(--status-warning)',
  APPROVED: 'var(--status-good)',
  CORRECTED: 'var(--status-info)',
  REJECTED: 'var(--status-critical)',
}

const IN_PROGRESS = new Set(['RECEIVED', 'VALIDATED', 'EXTRACTING', 'EXTRACTED', 'CLASSIFYING', 'CLASSIFIED', 'ONTOLOGY_MAPPED', 'ENRICHED', 'SEGMENTED', 'CHUNKED', 'EMBEDDING', 'INDEXED'])

export function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLOR[status] ?? (IN_PROGRESS.has(status) ? 'var(--status-info)' : 'var(--status-neutral)')
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ backgroundColor: tint(color, 16), color }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {status.replace(/_/g, ' ')}
    </span>
  )
}

const DOMAIN_COLOR: Record<string, string> = {
  clinical: 'var(--series-1)',
  administrative: 'var(--series-2)',
  financial: 'var(--series-3)',
  legal: 'var(--series-4)',
  technical: 'var(--series-5)',
}

export function DomainBadge({ domain }: { domain: string | null }) {
  if (!domain) return <span className="text-xs text-[var(--text-muted)]">—</span>
  const color = DOMAIN_COLOR[domain] ?? 'var(--text-muted)'
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium capitalize" style={{ backgroundColor: tint(color, 16), color }}>
      {domain}
    </span>
  )
}

const SECURITY_COLOR: Record<string, string> = {
  public: 'var(--security-public)',
  internal: 'var(--security-internal)',
  confidential: 'var(--security-confidential)',
  restricted: 'var(--security-restricted)',
}

export function SecurityBadge({ level }: { level: string }) {
  const color = SECURITY_COLOR[level] ?? 'var(--text-muted)'
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium capitalize" style={{ borderColor: tint(color, 55), color }}>
      {level}
    </span>
  )
}

export function ConfidenceBadge({ value, action }: { value: number | null; action?: string | null }) {
  if (value === null) return <span className="text-xs text-[var(--text-muted)]">—</span>
  const color = value >= 0.9 ? 'var(--confidence-high)' : value >= 0.7 ? 'var(--confidence-medium)' : 'var(--confidence-low)'
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium" style={{ color }} title={action ?? undefined}>
      <span className="relative h-1.5 w-16 overflow-hidden rounded-full bg-[var(--gridline)]">
        <span className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${Math.round(value * 100)}%`, backgroundColor: color }} />
      </span>
      {(value * 100).toFixed(0)}%
    </span>
  )
}

export function Pill({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'info' | 'good' | 'warning' | 'critical' }) {
  const color = { neutral: 'var(--text-muted)', info: 'var(--status-info)', good: 'var(--status-good)', warning: 'var(--status-warning)', critical: 'var(--status-critical)' }[tone]
  return (
    <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium" style={{ backgroundColor: tint(color, 16), color }}>
      {children}
    </span>
  )
}
