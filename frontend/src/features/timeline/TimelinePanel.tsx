import { useCallback, useState } from 'react'
import type { InvestigationService } from '../evidence/service'
import type { Filters } from '../evidence/contracts'
import { useResource } from '../evidence/useResource'

export function TimelinePanel({ api, filters, setFilters, lockedIncidentId }: { api: InvestigationService; filters: Filters; setFilters: (value: Filters) => void; lockedIncidentId?: string }) {
  const [draft, setDraft] = useState(filters)
  const [cursor, setCursor] = useState<string>()
  const [previous, setPrevious] = useState<(string | undefined)[]>([])
  const [attempt, setAttempt] = useState(0)
  const [error, setError] = useState('')
  const load = useCallback((signal: AbortSignal) => filters.incident_id ? api.timelineSearch(filters, cursor, signal) : Promise.resolve(null), [api, filters, cursor, attempt])
  const state = useResource(load)
  const field = (key: string, value: string) => setDraft(current => ({ ...current, [key]: value }))
  return <section><h1>Incident timeline</h1><p>Investigator observations and legacy records, ordered by occurrence time. Select an evidence record to add an observation.</p>
    <form className="filter-panel" onSubmit={e => {
      e.preventDefault()
      for (const key of ['occurred_from', 'occurred_to']) {
        if (draft[key] && (!/(Z|[+-]\d{2}:\d{2})$/.test(draft[key]) || !Number.isFinite(Date.parse(draft[key])))) { setError('Date filters require an ISO timestamp with a timezone offset.'); return }
      }
      if (draft.occurred_from && draft.occurred_to && Date.parse(draft.occurred_from) > Date.parse(draft.occurred_to)) { setError('Range start must not exceed range end.'); return }
      setError(''); setCursor(undefined); setPrevious([]); setFilters({ ...draft })
    }}><div className="filter-grid">
      {[['incident_id', 'Timeline incident ID'], ['evidence_id', 'Filter evidence ID'], ['q', 'Timeline text'], ['occurred_from', 'Occurrence from (with offset)'], ['occurred_to', 'Occurrence to (with offset)']].map(([key, label]) => <label key={key}>{label}<input disabled={key === 'incident_id' && !!lockedIncidentId} required={key === 'incident_id'} maxLength={key === 'q' ? 200 : 64} value={draft[key] || ''} onChange={e => field(key, e.target.value)} /></label>)}
      <label>Timeline origin<select value={draft.origin || ''} onChange={e => field('origin', e.target.value)}><option value="">All</option><option value="investigator">Investigator observation</option><option value="legacy">Legacy</option></select></label>
      <label>Timeline sort<select value={draft.sort || 'oldest'} onChange={e => field('sort', e.target.value)}><option value="oldest">Oldest first</option><option value="newest">Newest first</option></select></label>
    </div><button>Search timeline</button>{error && <p role="alert">{error}</p>}</form>
    {!filters.incident_id && <p>Enter an incident ID to load its authorized timeline.</p>}
    {state.loading && filters.incident_id && <p role="status">Loading timeline…</p>}
    {state.error && <p role="alert">{state.error} <button onClick={() => setAttempt(v => v + 1)}>Retry timeline</button></p>}
    {state.data && <><p role="status">{state.data.total} matching timeline observations</p><ol className="history-list timeline-list">{state.data.items.map(event => <li key={event.id}>
      <p className="eyebrow">Occurrence</p><h2><a href={`#timeline-event/${event.id}`}>{event.title}</a></h2><p>{new Date(event.occurred_at).toISOString()} (UTC) · {event.origin === 'investigator' ? 'Investigator observation' : 'Legacy record'}</p>
      <p>{event.recorded_by_label || 'Historical name not captured'} · Recorded {new Date(event.created_at).toISOString()} (UTC)</p>
      <p className="muted">Source: {event.source || 'Not recorded'}</p>
      {event.evidence_id ? <a href={`#evidence/${event.evidence_id}`}>Source evidence</a> : <p>No evidence link recorded.</p>}
    </li>)}</ol>{!state.data.items.length && <div className="empty-state"><p>No timeline observations match these filters.</p><p>Select a source evidence record and add a timeline observation. Creating a case does not create forensic events.</p><a href={filters.incident_id ? `#cases/${filters.incident_id}` : '#cases'}>Open case evidence</a></div>}
      <div className="actions"><button disabled={!previous.length} onClick={() => { setCursor(previous.at(-1)); setPrevious(v => v.slice(0, -1)) }}>Previous observations</button>
        <button disabled={!state.data.next_cursor} onClick={() => { setPrevious(v => [...v, cursor]); setCursor(state.data!.next_cursor!) }}>Next observations</button><button onClick={() => setAttempt(v => v + 1)}>Refresh timeline</button></div>
      <p className="muted">This is a live view. Observations are reported accounts, not automatically verified facts.</p></>}
  </section>
}
