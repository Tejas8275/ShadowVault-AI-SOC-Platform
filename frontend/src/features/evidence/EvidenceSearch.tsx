import { useCallback, useState } from 'react'
import type { Filters } from './contracts'
import type { InvestigationService } from './service'
import { validateFilters } from './service'
import { useResource } from './useResource'

const textFilters = [
  ['q', 'Text'],
  ['sha256', 'SHA-256'],
  ['incident_id', 'Incident ID'],
  ['collection_job_id', 'Collection job ID'],
  ['agent_id', 'Agent ID'],
  ['tags', 'Tags (comma-separated)'],
]

const dates = [
  ['created_from', 'Created from'],
  ['created_to', 'Created to'],
  ['collected_from', 'Collected from'],
  ['collected_to', 'Collected to'],
]

export function EvidenceSearch({
  api,
  filters,
  setFilters,
  lockedIncidentId,
  evidenceHref,
}: {
  api: InvestigationService
  filters: Filters
  setFilters: (value: Filters) => void
  lockedIncidentId?: string
  evidenceHref?: (id: string) => string
}) {
  const [draft, setDraft] = useState(filters)
  const [cursor, setCursor] = useState<string>()
  const [previous, setPrevious] = useState<(string | undefined)[]>([])
  const [attempt, setAttempt] = useState(0)
  const [error, setError] = useState('')
  const load = useCallback((signal: AbortSignal) => api.search(filters, cursor, signal), [api, filters, cursor, attempt])
  const state = useResource(load)

  const field = (key: string, value: string) => setDraft(current => ({ ...current, [key]: value }))

  function apply(values: Filters) {
    const problem = validateFilters(values)
    if (problem) {
      setError(problem)
      return
    }
    setError('')
    setCursor(undefined)
    setPrevious([])
    setFilters({ ...values })
  }

  return (
    <section aria-labelledby="evidence-title">
      <h1 id="evidence-title">Evidence investigation</h1>
      <p className="intro">Search evidence within your authorized investigations. Search values stay in this tab's memory.</p>

      <form
        className="filter-panel"
        onSubmit={event => {
          event.preventDefault()
          apply(draft)
        }}
      >
        <div className="filter-grid">
          {textFilters.map(([key, label]) => (
            <label key={key}>
              {label}
              <input
                disabled={key === 'incident_id' && !!lockedIncidentId}
                value={key === 'incident_id' && lockedIncidentId ? lockedIncidentId : draft[key] || ''}
                maxLength={key === 'q' ? 200 : key === 'tags' ? 1300 : 64}
                onChange={event => field(key, event.target.value)}
              />
            </label>
          ))}
        </div>

        <details style={{ margin: '1rem 0' }}>
          <summary style={{ cursor: 'pointer', fontWeight: 600 }}>Advanced filters</summary>
          <div className="filter-grid" style={{ marginTop: '0.75rem' }}>
            <label>
              Review state
              <select value={draft.review_state || ''} onChange={e => field('review_state', e.target.value)}>
                <option value="">All</option>
                <option value="unreviewed">Unreviewed</option>
                <option value="in_review">In review</option>
                <option value="reviewed">Reviewed</option>
              </select>
            </label>
            <label>
              Initial verification
              <select value={draft.verification_status || ''} onChange={e => field('verification_status', e.target.value)}>
                <option value="">All</option>
                <option value="legacy">Legacy</option>
                <option value="verified">Verified at upload</option>
              </select>
            </label>
            <label>
              Subsequent integrity
              <select value={draft.integrity_result || ''} onChange={e => field('integrity_result', e.target.value)}>
                <option value="">All</option>
                {['not_checked', 'matches', 'mismatch', 'missing', 'unavailable'].map(value => (
                  <option key={value} value={value}>
                    {value.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </label>
            {dates.map(([key, label]) => (
              <label key={key}>
                {label} (local time)
                <input type="datetime-local" value={draft[key] || ''} onChange={e => field(key, e.target.value)} />
              </label>
            ))}
            {['min_size', 'max_size'].map(key => (
              <label key={key}>
                {key === 'min_size' ? 'Minimum' : 'Maximum'} bytes
                <input type="number" min="0" step="1" value={draft[key] || ''} onChange={e => field(key, e.target.value)} />
              </label>
            ))}
          </div>
        </details>

        <div className="actions">
          <label style={{ display: 'inline-flex', flexDirection: 'row', alignItems: 'center', gap: '0.5rem' }}>
            <span>Sort</span>
            <select style={{ width: 'auto', margin: 0 }} value={draft.sort || 'newest'} onChange={e => field('sort', e.target.value)}>
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
          </label>
          <button type="submit">
            <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            Search
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setDraft({})
              apply({})
            }}
          >
            Clear filters
          </button>
        </div>
        {error && <p role="alert">{error}</p>}
      </form>

      {state.loading && <p role="status">Loading evidence…</p>}
      {state.error && (
        <p role="alert">
          {state.error} <button onClick={() => setAttempt(v => v + 1)}>Retry</button>
        </p>
      )}

      {state.data && (
        <>
          <p role="status" style={{ fontWeight: 600, color: 'var(--accent)' }}>
            {state.data.total} matching evidence records
          </p>
          {state.data.items.length === 0 ? (
            <div className="empty-state">
              <p>No evidence matches these filters.</p>
              <p className="muted">
                Clear optional filters or collect selected files into this case using the Windows collector. This workspace displays uploaded evidence; it does not collect files from your device.
              </p>
            </div>
          ) : (
            <div className="evidence-results">
              {state.data.items.map(item => (
                <article key={item.id} className="evidence-exhibit-card">
                  <h2>
                    <a href={evidenceHref ? evidenceHref(item.id) : `#evidence/${item.id}`}>
                      {item.display_title || item.filename}
                    </a>
                  </h2>
                  <p>
                    {item.filename} · {item.size_bytes.toLocaleString()} bytes · {item.review_state.replace('_', ' ')}
                  </p>
                  <p>
                    Collected: {item.collected_at ? new Date(item.collected_at).toISOString() + ' (UTC)' : 'Not recorded'}
                  </p>
                  <div className="actions">
                    <span className="badge">
                      {item.initial_verification_status === 'verified' ? 'Verified at upload' : 'Legacy acquisition'}
                    </span>
                    <span className={`badge integrity-${item.integrity_result}`}>
                      Subsequent integrity: {item.integrity_result.replace('_', ' ')}
                    </span>
                  </div>
                  <p>
                    Incident: <code>{item.incident_id}</code>
                  </p>
                  <div aria-label="Tags" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.5rem' }}>
                    {item.tags.map(tag => (
                      <span className="badge" key={tag}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
          <div className="actions" style={{ marginTop: '1.5rem' }}>
            <button
              disabled={!previous.length}
              onClick={() => {
                setCursor(previous.at(-1))
                setPrevious(v => v.slice(0, -1))
              }}
            >
              Previous page
            </button>
            <button
              disabled={!state.data.next_cursor}
              onClick={() => {
                setPrevious(v => [...v, cursor])
                setCursor(state.data!.next_cursor!)
              }}
            >
              Next page
            </button>
            <button className="secondary" onClick={() => setAttempt(v => v + 1)}>
              Refresh results
            </button>
          </div>
          <p className="muted">Results are a live view; totals may change as evidence is added or annotated.</p>
        </>
      )}
    </section>
  )
}
