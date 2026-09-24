import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import type { HealthResponse } from '../api/types'

export const GROUPS = ['employee', 'legal', 'provider-management', 'finance', 'clinical', 'engineering', 'executive'] as const
export type Group = (typeof GROUPS)[number]

interface AppState {
  theme: 'light' | 'dark'
  toggleTheme: () => void
  actingAs: Group
  setActingAs: (g: Group) => void
  health: HealthResponse | null
}

const AppCtx = createContext<AppState | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => (localStorage.getItem('kcip-theme') === 'light' ? 'light' : 'dark'))
  const [actingAs, setActingAs] = useState<Group>(() => (localStorage.getItem('kcip-group') as Group) || 'legal')
  const [health, setHealth] = useState<HealthResponse | null>(null)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('kcip-theme', theme)
  }, [theme])

  useEffect(() => {
    localStorage.setItem('kcip-group', actingAs)
  }, [actingAs])

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null))
  }, [])

  return (
    <AppCtx.Provider
      value={{
        theme,
        toggleTheme: () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')),
        actingAs,
        setActingAs,
        health,
      }}
    >
      {children}
    </AppCtx.Provider>
  )
}

export function useAppState() {
  const ctx = useContext(AppCtx)
  if (!ctx) throw new Error('useAppState must be used within AppProvider')
  return ctx
}
