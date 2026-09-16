import { useCallback, useState } from 'react'
import type { InvestigationService } from '../evidence/service'
import { useResource } from '../evidence/useResource'

export function TimelineEventDetails({ api, id }: { api: InvestigationService; id: string }) {
  const [attempt, setAttempt] = useState(0)
  const load = useCallback((signal: AbortSignal) => api.timelineDetails(id, signal), [api, id, attempt])
  const state = useResource(load)
  return <section><a href="#timeline">Back to timeline</a>
    {state.loading && <p role="status">Loading observation…</p>}
    {state.error && <p role="alert">{state.error} <button onClick={() => setAttempt(v => v + 1)}>Retry observation</button></p>}
    {state.data && <><h1>{state.data.title}</h1><p>{state.data.origin === 'investigator' ? 'Investigator observation — not an automatically verified finding.' : 'Legacy record — evidence provenance was not inferred.'}</p>
      <dl className="metadata-grid">
        <div><dt>Occurrence time</dt><dd>{new Date(state.data.occurred_at).toISOString()} (UTC)</dd></div>
        <div><dt>Reported timestamp</dt><dd>{state.data.reported_time || 'Not captured'}</dd></div>
        <div><dt>Recording time</dt><dd>{new Date(state.data.created_at).toISOString()} (UTC)</dd></div>
        <div><dt>Recorded by</dt><dd>{state.data.recorded_by_label || 'Historical name not captured'} ({state.data.recorded_by_id})</dd></div>
        <div><dt>Source</dt><dd>{state.data.source}</dd></div><div><dt>Source locator</dt><dd>{state.data.source_locator || 'Not supplied'}</dd></div>
        <div><dt>Event ID</dt><dd>{state.data.id}</dd></div><div><dt>Submission ID</dt><dd>{state.data.submission_id || 'Not captured'}</dd></div>
      </dl><p className="plain-text">{state.data.description}</p>
      <p><a href={`#timeline/${state.data.incident_id}`}>View this incident timeline</a></p>
      {state.data.evidence_id ? <p><a href={`#evidence/${state.data.evidence_id}`}>View source evidence</a></p> : <p>No evidence link recorded.</p>}
      <p className="muted">Observations cannot be edited or deleted through this API.</p>
    </>}
  </section>
}
