import type { HTMLAttributes, ReactNode } from 'react'
import clsx from 'clsx'

export function Card({ children, className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx('rounded-xl border shadow-sm', className)}
      style={{ backgroundColor: 'var(--surface-1)', borderColor: 'var(--border)' }}
      {...rest}
    >
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b px-5 py-4" style={{ borderColor: 'var(--border)' }}>
      <div>
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-[var(--text-secondary)]">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function StatTile({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: string; tone?: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs font-medium text-[var(--text-muted)]">{label}</p>
      <p className="mt-1.5 text-2xl font-semibold tracking-tight" style={{ color: tone ?? 'var(--text-primary)' }}>
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-[var(--text-secondary)]">{hint}</p>}
    </Card>
  )
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 py-16 text-center">
      <p className="text-sm font-medium text-[var(--text-secondary)]">{title}</p>
      {description && <p className="max-w-sm text-xs text-[var(--text-muted)]">{description}</p>}
    </div>
  )
}
