export interface BriefingSource {
  citation: string; section: string; evidence_id: string | null;
  fields: Record<string, string | number | null>;
  selection: 'model' | 'correction_context';
}
export interface CaseBriefingResult {
  schema_version: 1; kind: 'ai_selected_metadata'; case_id: string; case_title: string;
  case_revision: number; snapshot_at: string; context_sha256: string;
  prompt_version: 'metadata-selection-v1'; sources: BriefingSource[]; limitations: string[];
}

export const reviewCategories = {
  incident: 'Case metadata', evidence: 'Evidence records', timeline: 'Timeline observations',
  indicator: 'Recorded indicators', custody: 'Evidence custody records', history: 'Case history',
} as const
export type ReviewTarget = 'case' | 'report' | 'timeline' | 'indicators' | 'history'
const uuid = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
export function citationKind(citation: string) {
  return new RegExp(`^(incident|evidence|timeline|indicator|custody|history):${uuid}$`).exec(citation)?.[1]
}
export function reviewDestination(source: BriefingSource, caseId: string): ReviewTarget | undefined {
  switch (citationKind(source.citation)) {
    case 'incident': return source.citation === `incident:${caseId}` ? 'case' : undefined
    case 'timeline': return 'timeline'
    case 'indicator': return 'indicators'
    case 'history': return 'history'
    case 'custody': return 'report'
    default: return undefined
  }
}
export function sourceEvidenceHref(source: BriefingSource, caseId: string): string | undefined {
  if (!citationKind(source.citation) || !new RegExp(`^${uuid}$`).test(caseId)
      || !source.evidence_id || !new RegExp(`^${uuid}$`).test(source.evidence_id)) return undefined
  if (citationKind(source.citation) === 'incident') return undefined
  if (citationKind(source.citation) === 'evidence' && source.citation !== `evidence:${source.evidence_id}`) return undefined
  return `#cases/${caseId}/evidence/${source.evidence_id}`
}
export function reviewGroups(sources: BriefingSource[], category = 'all') {
  const visible = sources.filter(source => category === 'all' || citationKind(source.citation) === category
    || source.selection === 'correction_context' || !!source.fields.supersedes_id || !!source.fields.superseded_by_id)
  return [...Object.entries(reviewCategories), ['unknown', 'Other recorded metadata']].map(([kind, label]) => ({
    kind, label, sources: visible.filter(source => (citationKind(source.citation) || 'unknown') === kind),
  })).filter(group => group.sources.length > 0)
}
