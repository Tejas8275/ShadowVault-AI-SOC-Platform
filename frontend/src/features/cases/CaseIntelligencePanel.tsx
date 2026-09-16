import { useCallback, useState } from 'react'
import type { InvestigationService } from '../evidence/service'
import { useResource } from '../evidence/useResource'

export function CaseIntelligencePanel({ api, id }: { api: InvestigationService; id: string }) {
  const [attempt, setAttempt] = useState(0)
  const load = useCallback((signal: AbortSignal) => api.caseIntelligence(id, signal), [api, id, attempt])
  const state = useResource(load)
  const record = state.data?.id === id ? state.data : undefined
  const summary = record?.intelligence

  return (
    <section className="evidence-panel" aria-label="Case investigation overview">
      <div className="section-heading">
        <h2>Investigation overview</h2>
        <button className="secondary" disabled={state.loading} onClick={() => setAttempt(v => v + 1)}>
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
          Refresh investigation overview
        </button>
      </div>

      {state.loading && <p role="status">Loading investigation overview…</p>}

      {!state.loading && (state.error || !summary) && (
        <p role="alert">Investigation overview unavailable. Refresh to retry; unavailable counts are not zero.</p>
      )}

      {!state.loading && !state.error && summary && record && (
        <>
          <div className="metric-grid">
            <article className="metric">
              <span>Evidence records</span>
              <strong>{summary.evidence_count}</strong>
            </article>
            <article className="metric">
              <span>Timeline observations</span>
              <strong>{summary.timeline_count}</strong>
            </article>
            <article className="metric">
              <span>Recorded history revisions</span>
              <strong>{summary.history_revision_count}</strong>
            </article>
            <article className="metric">
              <span>Investigation status</span>
              <strong className={`status-${record.status}`} style={{ fontSize: '1.2rem' }}>
                {record.status}
              </strong>
              <span className={`badge severity-${record.severity}`}>{record.severity} severity</span>
            </article>
          </div>

          <p style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span className="pulse-dot" style={{ color: 'var(--accent)' }} />
            Latest recorded activity:{' '}
            <time dateTime={summary.latest_activity_at} style={{ fontFamily: 'var(--font-mono)' }}>
              {new Date(summary.latest_activity_at).toISOString()} (UTC)
            </time>
          </p>

          <p className="muted">
            Includes case creation/updates, evidence registration, timeline recording, and evidence custody activity. It is not the latest forensic occurrence time or proof of download delivery.
          </p>

          <p className="muted">
            Case revision {record.revision}.{' '}
            {summary.history_started_revision == null
              ? 'History tracking has not started.'
              : `History tracking starts at revision ${summary.history_started_revision}; the count includes any baseline and creation record, not reconstructed earlier changes.`}
          </p>

          {summary.evidence_count === 0 && <p>No evidence has been registered for this case within your authorized scope.</p>}

          <p className="footnote">
            Read-only live summary. Refresh after investigation activity; separate views can change between requests. Status and severity are investigator-assigned, not automated conclusions.
          </p>
        </>
      )}
    </section>
  )
}
