interface BarItem {
  label: string
  value: number
  color?: string
}

export function HorizontalBarList({ items, valueFormatter }: { items: BarItem[]; valueFormatter?: (v: number) => string }) {
  const max = Math.max(...items.map((i) => i.value), 1)
  const fmt = valueFormatter ?? ((v: number) => String(v))

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-3">
          <div className="w-32 flex-none truncate text-xs text-[var(--text-secondary)] capitalize" title={item.label}>
            {item.label}
          </div>
          <div className="relative h-2 flex-1 overflow-hidden rounded-full" style={{ backgroundColor: 'var(--gridline)' }}>
            <div
              className="absolute inset-y-0 left-0 rounded-full transition-[width]"
              style={{ width: `${(item.value / max) * 100}%`, backgroundColor: item.color ?? 'var(--series-1)' }}
            />
          </div>
          <div className="w-10 flex-none text-right text-xs font-medium tabular-nums text-[var(--text-primary)]">{fmt(item.value)}</div>
        </div>
      ))}
      {items.length === 0 && <p className="text-xs text-[var(--text-muted)]">No data yet.</p>}
    </div>
  )
}
