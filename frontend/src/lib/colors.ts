export function cssVar(name: string): string {
  if (typeof window === 'undefined') return '#888888'
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#888888'
}

export const DOMAIN_VAR: Record<string, string> = {
  clinical: '--series-1',
  administrative: '--series-2',
  financial: '--series-3',
  legal: '--series-4',
  technical: '--series-5',
}

export function domainColor(domain: string): string {
  return cssVar(DOMAIN_VAR[domain] ?? '--text-muted')
}
