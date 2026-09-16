import { useCallback, useEffect, useState } from 'react'
import type { InvestigationService } from './service'
import { useResource } from './useResource'

export function CustodyHistory({
  api,
  id,
  revision,
  refreshKey = 0,
}: {
  api: InvestigationService
  id: string
  revision: number
  refreshKey?: number
}) {
  const [after, setAfter] = useState(0)
  const [previous, setPrevious] = useState<number[]>([])
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    setAfter(0)
    setPrevious([])
  }, [revision, refreshKey])

  const load = useCallback((signal: AbortSignal) => api.custody(id, after, signal), [api, id, after, revision, refreshKey, attempt])
  const state = useResource(load)

  return (
    <section className="evidence-panel">
      <div className="section-heading" style={{ margin: '0 0 1rem', borderBottom: 'none' }}>
        <h2>Custody history</h2>
        {state.data?.tracking_started && (
          <span className="badge" style={{ fontFamily: 'var(--font-mono)' }}>
            Head Sequence: {state.data.head_sequence}
          </span>
        )}
      </div>
      <p className="muted">
        History display does not independently verify the chain. Tracking begins at migration registration, the first annotation, the first timeline observation, or the first retrieval; acquisition events before that point are not reconstructed.
      </p>

      {state.loading && <p role="status">Loading custody history…</p>}
      {state.error && (
        <p role="alert">
          {state.error} <button onClick={() => setAttempt(v => v + 1)}>Retry custody</button>
        </p>
      )}

      {state.data && (
        <>
          {!state.data.tracking_started ? (
            <p>Custody tracking has not started for this evidence.</p>
          ) : (
            <p>Stored head sequence: {state.data.head_sequence}</p>
          )}

          <ol className="history-list">
            {state.data.items.map(event => (
              <li key={event.id}>
                <h3>
                  {event.sequence}.{' '}
                  {event.event_type === 'baseline_registered'
                    ? event.system_actor === 'migration:0003'
                      ? 'Migration registration baseline'
                      : event.details.reason === 'tracking_started_at_first_retrieval'
                        ? 'Tracking started at first retrieval'
                        : event.details.reason === 'tracking_started_at_first_timeline_event'
                          ? 'Tracking started at first timeline observation'
                          : 'Tracking started at first annotation'
                    : event.event_type.replaceAll('_', ' ')}
                </h3>
                <p style={{ fontSize: '0.82rem', color: 'var(--muted)', fontFamily: 'var(--font-mono)' }}>
                  {event.actor_label} ({event.actor_type}) · {new Date(event.recorded_at).toISOString()} (UTC)
                </p>
                {event.event_type === 'baseline_registered' && (
                  <p>Registration only; this event does not claim acquisition or reverification at this time.</p>
                )}
                {event.details.changes && typeof event.details.changes === 'object' ? (
                  <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem' }}>
                    {Object.entries(event.details.changes).map(([field, change]) => {
                      const value = change as { before: unknown; after: unknown }
                      return (
                        <li key={field}>
                          <code>{field.replaceAll('_', ' ')}</code>: {JSON.stringify(value.before)} → {JSON.stringify(value.after)}
                        </li>
                      )
                    })}
                  </ul>
                ) : null}
                {event.event_type === 'note_added' && <p>Appended note: {String(event.details.note_id || '')}</p>}
                {event.event_type === 'evidence_retrieval_prepared' && (
                  <p>Verified copy prepared by the server. Delivery and local saving are not confirmed.</p>
                )}
                {event.event_type === 'timeline_observation_added' && (
                  <p>
                    <a href={`#timeline-event/${String(event.details.timeline_event_id || '')}`}>
                      View timeline observation →
                    </a>
                  </p>
                )}
                <details style={{ marginTop: '0.75rem' }}>
                  <summary style={{ fontSize: '0.8rem', color: 'var(--muted)', cursor: 'pointer' }}>
                    Event identifiers and hash linkage
                  </summary>
                  <dl className="metadata-grid" style={{ marginTop: '0.5rem' }}>
                    <div>
                      <dt>Event ID</dt>
                      <dd style={{ wordBreak: 'break-all' }}>{event.id}</dd>
                    </div>
                    <div>
                      <dt>Operation ID</dt>
                      <dd style={{ wordBreak: 'break-all' }}>{event.operation_id}</dd>
                    </div>
                    <div>
                      <dt>Actor reference</dt>
                      <dd>{event.actor_user_id || event.actor_agent_id || event.system_actor}</dd>
                    </div>
                    <div>
                      <dt>Schema version</dt>
                      <dd>{event.schema_version}</dd>
                    </div>
                    <div>
                      <dt>Previous hash</dt>
                      <dd style={{ wordBreak: 'break-all', fontFamily: 'var(--font-mono)' }}>
                        {event.previous_hash || 'First event'}
                      </dd>
                    </div>
                    <div>
                      <dt>Event hash</dt>
                      <dd style={{ wordBreak: 'break-all', fontFamily: 'var(--font-mono)' }}>{event.event_hash}</dd>
                    </div>
                    <div>
                      <dt>Source timestamp</dt>
                      <dd>{event.source_at || 'Not supplied'}</dd>
                    </div>
                  </dl>
                  <pre style={{ marginTop: '0.5rem' }}>{JSON.stringify(event.details, null, 2)}</pre>
                </details>
              </li>
            ))}
          </ol>

          <div className="actions">
            <button
              disabled={!previous.length}
              onClick={() => {
                setAfter(previous.at(-1)!)
                setPrevious(v => v.slice(0, -1))
              }}
            >
              Previous custody events
            </button>
            <button
              disabled={state.data.next_sequence === null}
              onClick={() => {
                setPrevious(v => [...v, after])
                setAfter(state.data!.next_sequence!)
              }}
            >
              Next custody events
            </button>
            <button className="secondary" onClick={() => setAttempt(v => v + 1)}>
              Refresh custody
            </button>
          </div>
        </>
      )}
    </section>
  )
}
