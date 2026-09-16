import type { InvestigationService } from '../evidence/service.ts'

export const caseStatuses = ['open', 'investigating', 'closed'] as const
export const caseSeverities = ['critical', 'high', 'medium', 'low'] as const

// Use server totals, never the length of a paginated response. These requests
// share the existing operator boundary and are a live view, not a SQL snapshot.
export async function loadCaseOverview(api: Pick<InvestigationService, 'cases'>, signal: AbortSignal) {
  const [recent, ...counts] = await Promise.all([
    api.cases({ limit: '5' }, undefined, signal),
    ...caseStatuses.map(status => api.cases({ status, limit: '1' }, undefined, signal)),
    ...caseSeverities.map(severity => api.cases({ severity, limit: '1' }, undefined, signal)),
  ])
  return {
    total: recent.total,
    recent: recent.items,
    statuses: caseStatuses.map((name, index) => ({ name, total: counts[index].total })),
    severities: caseSeverities.map((name, index) => ({ name, total: counts[index + caseStatuses.length].total })),
  }
}
