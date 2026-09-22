import { GROUPS, useAppState } from '../state/AppContext'
import { IconMoon, IconSun } from './icons'

export function TopBar() {
  const { theme, toggleTheme, actingAs, setActingAs, health } = useAppState()

  return (
    <header className="flex h-14 flex-none items-center justify-between border-b px-6" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--surface-1)' }}>
      <div className="flex items-center gap-3">
        {health?.demo_mode && (
          <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold" style={{ backgroundColor: 'color-mix(in srgb, var(--series-4) 16%, transparent)', color: 'var(--series-4)' }}>
            <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: 'var(--series-4)' }} />
            Demo Mode
          </span>
        )}
        {health && (
          <span className="text-xs text-[var(--text-muted)]">
            {health.database} · {health.embedding_provider} embeddings · {health.llm_mode ? 'LLM mode' : 'deterministic'}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
          Acting as
          <select
            value={actingAs}
            onChange={(e) => setActingAs(e.target.value as (typeof GROUPS)[number])}
            className="rounded-md border bg-transparent px-2 py-1 text-xs font-medium capitalize"
            style={{ borderColor: 'var(--border)' }}
          >
            {GROUPS.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={toggleTheme}
          className="flex h-8 w-8 items-center justify-center rounded-lg border text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          style={{ borderColor: 'var(--border)' }}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <IconSun /> : <IconMoon />}
        </button>
      </div>
    </header>
  )
}
