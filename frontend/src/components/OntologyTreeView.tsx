import { useState } from 'react'
import type { OntologyTreeNode } from '../api/types'
import { domainColor } from '../lib/colors'

function TreeNode({ node, depth, selectedId, onSelect }: { node: OntologyTreeNode; depth: number; selectedId: string | null; onSelect: (id: string) => void }) {
  const [open, setOpen] = useState(depth < 2)
  const hasChildren = node.children.length > 0
  const isDomain = depth === 0
  const color = isDomain ? domainColor(node.id) : undefined

  return (
    <div>
      <button
        onClick={() => {
          onSelect(node.id)
          if (hasChildren) setOpen((o) => !o)
        }}
        className="flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-left text-sm hover:bg-[var(--surface-2)]"
        style={{ marginLeft: depth * 16, backgroundColor: selectedId === node.id ? 'var(--surface-2)' : undefined }}
      >
        {hasChildren ? <span className="w-3 text-[var(--text-muted)]">{open ? '▾' : '▸'}</span> : <span className="w-3" />}
        <span className="flex-1 truncate" style={{ color, fontWeight: isDomain ? 600 : 400 }}>
          {node.name}
        </span>
        <span className="text-xs text-[var(--text-muted)]">{node.document_count}</span>
      </button>
      {open && hasChildren && node.children.map((c) => <TreeNode key={c.id} node={c} depth={depth + 1} selectedId={selectedId} onSelect={onSelect} />)}
    </div>
  )
}

export function OntologyTreeView({ root, selectedId, onSelect }: { root: OntologyTreeNode; selectedId: string | null; onSelect: (id: string) => void }) {
  return (
    <div>
      {root.children.map((domain) => (
        <TreeNode key={domain.id} node={domain} depth={0} selectedId={selectedId} onSelect={onSelect} />
      ))}
    </div>
  )
}
