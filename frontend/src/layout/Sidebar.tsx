import { NavLink } from 'react-router-dom'
import clsx from 'clsx'
import {
  IconClassification, IconConnectors, IconDashboard, IconDocuments, IconHealth, IconIngestion,
  IconOntology, IconRag, IconReview, IconScale, IconSearch,
} from './icons'

const NAV = [
  { to: '/', label: 'Dashboard', icon: IconDashboard },
  { to: '/documents', label: 'Documents', icon: IconDocuments },
  { to: '/ingestion', label: 'Ingestion', icon: IconIngestion },
  { to: '/connectors', label: 'Connectors', icon: IconConnectors },
  { to: '/classification', label: 'Classification', icon: IconClassification },
  { to: '/ontology', label: 'Ontology', icon: IconOntology },
  { to: '/search', label: 'Search', icon: IconSearch },
  { to: '/rag', label: 'RAG', icon: IconRag },
  { to: '/reviews', label: 'Review Queue', icon: IconReview },
  { to: '/scale-simulator', label: 'Scale Simulator', icon: IconScale },
  { to: '/system-health', label: 'System Health', icon: IconHealth },
]

export function Sidebar() {
  return (
    <aside className="flex h-full w-60 flex-none flex-col border-r" style={{ backgroundColor: 'var(--surface-1)', borderColor: 'var(--border)' }}>
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg text-sm font-bold text-white" style={{ backgroundColor: 'var(--series-1)' }}>
          E
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight">KAIROS</p>
          <p className="text-[11px] leading-tight text-[var(--text-muted)]">Content Intelligence</p>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 px-3">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive ? 'text-white' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
              )
            }
            style={({ isActive }) => (isActive ? { backgroundColor: 'var(--series-1)' } : undefined)}
          >
            <Icon className="flex-none" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t px-4 py-3 text-[11px] text-[var(--text-muted)]" style={{ borderColor: 'var(--border)' }}>
        Enterprise Content Intelligence Platform
      </div>
    </aside>
  )
}
