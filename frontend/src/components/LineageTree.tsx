import type { ReactNode } from 'react'
import type { LineageResponse } from '../api/types'

const TYPE_COLOR: Record<string, string> = {
  source: 'var(--text-muted)',
  document: 'var(--series-1)',
  segment: 'var(--series-4)',
  chunk: 'var(--series-3)',
}

export function LineageTree({ lineage }: { lineage: LineageResponse }) {
  const children = new Map<string, string[]>()
  const byId = new Map(lineage.nodes.map((n) => [n.id, n]))
  for (const edge of lineage.edges) {
    children.set(edge.source, [...(children.get(edge.source) ?? []), edge.target])
  }
  const roots = lineage.nodes.filter((n) => n.type === 'source').map((n) => n.id)

  function renderNode(id: string, depth: number): ReactNode {
    const node = byId.get(id)
    if (!node) return null
    const kids = children.get(id) ?? []
    return (
      <div key={id} style={{ marginLeft: depth * 18 }}>
        <div className="flex items-center gap-2 py-1">
          <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide" style={{ color: TYPE_COLOR[node.type], backgroundColor: `color-mix(in srgb, ${TYPE_COLOR[node.type]} 14%, transparent)` }}>
            {node.type}
          </span>
          <span className="text-sm">{node.label}</span>
          {typeof node.metadata.text_preview === 'string' && (
            <span className="truncate text-xs text-[var(--text-muted)]">— {node.metadata.text_preview.slice(0, 60)}…</span>
          )}
        </div>
        {kids.map((k) => renderNode(k, depth + 1))}
      </div>
    )
  }

  return <div className="text-[var(--text-secondary)]">{roots.map((id) => renderNode(id, 0))}</div>
}
