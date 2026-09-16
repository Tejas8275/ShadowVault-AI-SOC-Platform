import { useCallback, useState } from 'react'
import type { InvestigationService } from './service'
import { useResource } from './useResource'
import type { EvidenceDetails } from './contracts'
import { AnnotationsPanel } from './AnnotationsPanel'
import { CustodyHistory } from './CustodyHistory'
import { IntegrityStatus } from './IntegrityStatus'
import { TimelineEventForm } from '../timeline/TimelineEventForm'
import { EvidenceDownload } from './EvidenceDownload'

export function utc(value: string | null) {
  return value ? `${new Date(value).toISOString()} (UTC)` : 'Not recorded'
}

function CopyValue({ label, value }: { label: string; value: string | null }) {
  const [message, setMessage] = useState('')
  return (
    <div>
      <dt>{label}</dt>
      <dd>
        {value || 'Not recorded'}{' '}
        {value && (
          <button
            className="secondary"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(value)
                setMessage('Copied')
              } catch {
                setMessage('Copy unavailable; select the value manually.')
              }
            }}
          >
            <svg aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
            Copy {label}
          </button>
        )}{' '}
        <span role="status" style={{ color: 'var(--status-nominal)', fontSize: '0.8rem' }}>
          {message}
        </span>
      </dd>
    </div>
  )
}

export function EvidenceDetailsPage({
  api,
  id,
  caseId,
  onIndicators,
}: {
  onIndicators?: (evidence: { id: string; filename: string }, action: 'view' | 'add') => void
  api: InvestigationService
  id: string
  caseId?: string
}) {
  const [version, setVersion] = useState(0)
  const load = useCallback((signal: AbortSignal) => api.details(id, signal), [api, id, version])
  const state = useResource(load)
  const [current, setCurrent] = useState<EvidenceDetails>()
  const [historyRefresh, setHistoryRefresh] = useState(0)
  const [refreshError, setRefreshError] = useState('')
  const evidence = current || state.data

  if (evidence && caseId && evidence.incident_id !== caseId)
    return <p role="alert">Evidence does not belong to this case.</p>

  return (
    <section>
      <div style={{ marginBottom: '1.25rem' }}>
        <a
          href={caseId ? `#cases/${caseId}` : '#evidence'}
          className="button-link secondary"
          style={{ background: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border)' }}
        >
          <span aria-hidden="true">← </span>Back to evidence results
        </a>
      </div>

      {state.loading && <p role="status">Loading evidence details…</p>}
      {state.error && (
        <p role="alert">
          {state.error} <button onClick={() => setVersion(v => v + 1)}>Retry details</button>
        </p>
      )}

      {evidence && (
        <>
          <p className="eyebrow">Evidence record</p>
          <h1>{evidence.display_title || evidence.filename}</h1>
          <div className="actions">
            <span className="badge">{evidence.size_bytes.toLocaleString()} bytes</span>
            <span className="badge">{evidence.review_state.replace('_', ' ')}</span>
          </div>

          <IntegrityStatus evidence={evidence} />

          <section className="evidence-panel">
            <h2>Acquisition metadata</h2>
            <p className="muted">Original acquisition fields are read-only.</p>
            <dl className="metadata-grid">
              <CopyValue label="Evidence ID" value={evidence.id} />
              <CopyValue label="Incident ID" value={evidence.incident_id} />
              <CopyValue label="SHA-256" value={evidence.sha256} />
              <CopyValue label="Collection job ID" value={evidence.collection_job_id} />
              <CopyValue label="Agent ID" value={evidence.agent_id} />
              <CopyValue label="Collection item ID" value={evidence.collection_item_id} />
              <div>
                <dt>Filename</dt>
                <dd style={{ wordBreak: 'break-all' }}>{evidence.filename}</dd>
              </div>
              <div>
                <dt>Source path</dt>
                <dd style={{ wordBreak: 'break-all' }}>{evidence.source_path || 'Not recorded'}</dd>
              </div>
              <div>
                <dt>Size</dt>
                <dd>{evidence.size_bytes.toLocaleString()} bytes</dd>
              </div>
              <div>
                <dt>Media type</dt>
                <dd>{evidence.media_type}</dd>
              </div>
              <div>
                <dt>Collected</dt>
                <dd>{utc(evidence.collected_at)}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{utc(evidence.created_at)}</dd>
              </div>
              <CopyValue label="Collected by user ID" value={evidence.collected_by_user_id} />
              <CopyValue label="Requested by user ID" value={evidence.requested_by_user_id} />
            </dl>
          </section>

          {onIndicators && (
            <section className="evidence-panel" aria-label="Evidence indicators">
              <h2>Indicator observations</h2>
              <p>Use this authorized evidence as the source. These actions do not read its contents.</p>
              <div className="actions">
                <button onClick={() => onIndicators(evidence, 'view')}>
                  <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                  View indicators for this evidence
                </button>
                <button onClick={() => onIndicators(evidence, 'add')}>
                  <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                  Record indicator for this evidence
                </button>
              </div>
            </section>
          )}

          <AnnotationsPanel api={api} evidence={evidence} onUpdated={setCurrent} />
          <EvidenceDownload key={id} api={api} id={id} size={evidence.size_bytes} onAttempt={() => setHistoryRefresh(v => v + 1)} />
          <TimelineEventForm
            api={api}
            evidenceId={id}
            incidentId={evidence.incident_id}
            onCreated={() => {
              setHistoryRefresh(v => v + 1)
              api.details(id).then(
                value => {
                  setCurrent(value)
                  setRefreshError('')
                },
                () => setRefreshError('Observation recorded, but evidence details could not refresh. Reopen this evidence to refresh.'),
              )
            }}
          />
          {refreshError && <p role="status">{refreshError}</p>}
          <CustodyHistory api={api} id={id} revision={evidence.metadata_revision} refreshKey={historyRefresh} />
        </>
      )}
    </section>
  )
}
