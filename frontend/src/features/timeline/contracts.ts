export interface TimelineEvent {
  id: string; incident_id: string; evidence_id: string | null; recorded_by_id: string
  recorded_by_label: string | null; occurred_at: string; reported_time: string | null; created_at: string
  title: string; description: string; source: string; source_locator: string | null
  origin: 'legacy' | 'investigator'; submission_id: string | null
}
export interface TimelinePage { items: TimelineEvent[]; total: number; next_cursor: string | null }
export interface TimelineDraft { occurred_at: string; title: string; description: string; source: string; source_locator: string }
export interface TimelineSubmission extends Omit<TimelineDraft, 'source_locator'> { source_locator: string | null; submission_id: string }
export function prepareSubmission(draft: TimelineDraft, submission_id: string): TimelineSubmission {
  const occurred_at = draft.occurred_at.trim()
  if (!/^\d{4}-\d{2}-\d{2}T.+(?:Z|[+-]\d{2}:\d{2})$/.test(occurred_at) || !Number.isFinite(Date.parse(occurred_at))) {
    throw new Error('Enter an ISO occurrence timestamp with Z or an explicit offset, such as 2026-09-06T12:30:00+05:30.')
  }
  if (!draft.title.trim() || !draft.source.trim()) throw new Error('Title and source are required.')
  return { occurred_at, title: draft.title.trim(), description: draft.description.trim(), source: draft.source.trim(),
    source_locator: draft.source_locator.trim() || null, submission_id }
}
