import type { SVGProps } from 'react'

const base = (props: SVGProps<SVGSVGElement>) => ({
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.75,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  ...props,
})

export const IconDashboard = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></svg>
)
export const IconDocuments = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M7 3h7l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" /><path d="M14 3v4h4" /><path d="M9 12h6M9 16h6" /></svg>
)
export const IconIngestion = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M12 3v12" /><path d="M7 10l5 5 5-5" /><path d="M4 19h16" /></svg>
)
export const IconConnectors = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M9 2v4M15 2v4" /><rect x="4" y="6" width="16" height="7" rx="2" /><path d="M9 13v3a3 3 0 0 0 3 3h0a3 3 0 0 0 3-3v-3" /><circle cx="12" cy="21" r="1.5" /></svg>
)
export const IconClassification = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><circle cx="12" cy="12" r="3.2" /><circle cx="5" cy="5" r="2" /><circle cx="19" cy="5" r="2" /><circle cx="5" cy="19" r="2" /><circle cx="19" cy="19" r="2" /><path d="M9.3 9.9 6.4 6.4M14.7 9.9l2.9-3.5M9.3 14.1l-2.9 3.5M14.7 14.1l2.9 3.5" /></svg>
)
export const IconOntology = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><circle cx="12" cy="4.5" r="2" /><circle cx="5" cy="19" r="2" /><circle cx="12" cy="19" r="2" /><circle cx="19" cy="19" r="2" /><path d="M12 6.5v6M12 12.5 6 17M12 12.5v6M12 12.5l6 4.5" /></svg>
)
export const IconSearch = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
)
export const IconRag = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M4 4h11l5 5v11H4Z" /><path d="M9 12h6M9 16h4" /><path d="M9 8h1" /></svg>
)
export const IconReview = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><circle cx="12" cy="12" r="9" /><path d="M8.5 12.5l2.3 2.3L16 9.5" /></svg>
)
export const IconScale = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M12 3v18M7 7l-4 8a4 4 0 0 0 8 0Zm10 0-4 8a4 4 0 0 0 8 0Z" /><path d="M5 21h14" /></svg>
)
export const IconHealth = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M20 12a8 8 0 1 1-8-8" /><path d="M4 12h4l2-4 3 8 2-4h5" /></svg>
)
export const IconSun = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
)
export const IconMoon = (p: SVGProps<SVGSVGElement>) => (
  <svg {...base(p)}><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5Z" /></svg>
)
