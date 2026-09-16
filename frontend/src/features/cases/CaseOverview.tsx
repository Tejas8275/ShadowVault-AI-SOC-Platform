import { useCallback, useState } from 'react'
import type { InvestigationService } from '../evidence/service'
import { useResource } from '../evidence/useResource'
import { loadCaseOverview } from './overview'

export function CaseOverview({ api }: { api: InvestigationService }) {
  const [attempt, setAttempt] = useState(0)
  const load = useCallback((signal: AbortSignal) => loadCaseOverview(api, signal), [api, attempt])
  const state = useResource(load)

  const totalSeverities = state.data
    ? state.data.severities.reduce((acc, curr) => acc + curr.total, 0)
    : 0

  return (
    <section aria-label="Authorized case overview">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Your investigation portfolio</p>
          <h2>Case overview</h2>
        </div>
        <button
          className="secondary"
          disabled={state.loading}
          onClick={() => setAttempt(v => v + 1)}
        >
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
          Refresh overview
        </button>
      </div>

      {state.loading && (
        <p role="status" className="empty-state">
          Loading authorized case overview…
        </p>
      )}

      {state.error && (
        <p role="alert" className="empty-state">
          Case overview unavailable. Check your connection and access, then refresh. Counts are not available.
        </p>
      )}

      {state.data && (
        <>
          <div className="metric-grid">
            <article className="metric">
              <span>Authorized cases</span>
              <strong>{state.data.total}</strong>
              <a href="#cases">Browse cases →</a>
            </article>
            {state.data.statuses.map(item => (
              <article className="metric" key={item.name}>
                <span className={`status-${item.name}`}>{item.name}</span>
                <strong>{item.total}</strong>
                <span className="muted">Cases by status</span>
              </article>
            ))}
          </div>

          <div className="severity-strip" aria-label="Case severity totals">
            <span className="eyebrow" style={{ marginRight: '0.5rem', marginBottom: 0 }}>
              Risk Profile:
            </span>
            {state.data.severities.map(item => (
              <div key={item.name}>
                <span className={`badge severity-${item.name}`}>{item.name}</span>
                <strong>{item.total}</strong>
              </div>
            ))}
            {totalSeverities > 0 && (
              <div
                style={{
                  width: '100%',
                  height: '6px',
                  borderRadius: '3px',
                  display: 'flex',
                  overflow: 'hidden',
                  marginTop: '0.5rem',
                  background: 'var(--bg-void)',
                  boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.5)',
                }}
                title="Severity distribution"
              >
                {state.data.severities.map(item => {
                  const pct = totalSeverities > 0 ? (item.total / totalSeverities) * 100 : 0
                  if (pct === 0) return null
                  const color =
                    item.name === 'critical'
                      ? '#ff385c'
                      : item.name === 'high'
                        ? '#fb923c'
                        : item.name === 'medium'
                          ? '#facc15'
                          : '#38bdf8'
                  return (
                    <div
                      key={item.name}
                      style={{
                        width: `${pct}%`,
                        background: color,
                        transition: 'width 0.3s ease',
                      }}
                      title={`${item.name}: ${item.total} (${Math.round(pct)}%)`}
                    />
                  )
                })}
              </div>
            )}
          </div>

          <p className="footnote">
            Live, owner-authorized counts. Concurrent case changes may affect totals between requests. Refresh manually for updated results.
          </p>

          <div className="section-heading">
            <h2>Newest cases</h2>
            <a href="#cases">Open case workspace →</a>
          </div>
          <p className="muted">
            Up to five cases, ordered by creation time. Open a case for its recorded history; this is not a global activity feed.
          </p>

          {!state.data.recent.length ? (
            <div className="empty-state">
              <svg
                aria-hidden="true"
                width="36"
                height="36"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--muted)"
                strokeWidth="1.5"
                style={{ margin: '0 auto 0.75rem', display: 'block' }}
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M12 2a10 10 0 0 1 10 10" />
                <path d="M12 12 19 5" />
              </svg>
              <h3>No cases yet</h3>
              <p>Create your first case to organize evidence and observations.</p>
              <a className="button-link" href="#cases">Go to cases</a>
            </div>
          ) : (
            <div className="case-grid">
              {state.data.recent.map(record => (
                <article className="case-card" key={record.id}>
                  <div className="actions">
                    <span className={`badge severity-${record.severity}`}>{record.severity}</span>
                    <span className={`badge status-${record.status}`}>{record.status}</span>
                  </div>
                  <h3>
                    <a href={`#cases/${record.id}`}>{record.title}</a>
                  </h3>
                  <p>
                    Created: <time dateTime={record.created_at}>{new Date(record.created_at).toISOString()} (UTC)</time>
                  </p>
                  <p className="muted">
                    Last updated: {record.updated_at ? `${new Date(record.updated_at).toISOString()} (UTC)` : 'Unknown'}
                  </p>
                </article>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )
}
