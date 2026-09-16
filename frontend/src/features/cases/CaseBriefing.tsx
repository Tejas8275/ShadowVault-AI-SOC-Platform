import { useEffect, useRef, useState } from 'react'
import type { InvestigationService } from '../evidence/service'
import { ApiError } from '../../services/http'
import { reportLabel, reportValue } from './report'
import type { CaseBriefingResult } from './briefing'
import { reviewCategories, reviewGroups, reviewDestination, sourceEvidenceHref, type ReviewTarget } from './briefing'

export function CaseBriefing({ api, id, onReview }: { api: InvestigationService; id: string; onReview: (target: ReviewTarget, citation?: string) => void }) {
  const [result, setResult] = useState<CaseBriefingResult>()
  const [category, setCategory] = useState('all')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [previous, setPrevious] = useState(false)
  const active = useRef<AbortController | null>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const action = useRef<HTMLButtonElement>(null)
  const returnFocus = useRef(false)

  useEffect(() => () => active.current?.abort(), [api, id])
  useEffect(() => {
    if (result) heading.current?.focus()
  }, [result])
  useEffect(() => {
    if (!busy && returnFocus.current) {
      returnFocus.current = false
      action.current?.focus()
    }
  }, [busy])

  async function generate() {
    if (active.current) return
    const controller = new AbortController()
    active.current = controller
    setBusy(true)
    setError('')
    setPrevious(!!result)
    try {
      const next = await api.aiBriefing(id, controller.signal)
      if (!controller.signal.aborted) {
        setResult(next)
        setPrevious(false)
        setCategory('all')
      }
    } catch (reason) {
      if (controller.signal.aborted) return
      const status = reason instanceof ApiError ? reason.status : 0
      if ([401, 403, 404].includes(status)) {
        setResult(undefined)
        setPrevious(false)
      }
      const messages: Record<number, string> = {
        401: 'Operator access was rejected. Reconnect to continue.',
        403: 'Briefing access unavailable. Retained briefing cleared.',
        404: 'Case or source access unavailable. Retained briefing cleared.',
        409: 'Case metadata changed during preparation. Retry explicitly for a new snapshot.',
        413: 'This case exceeds briefing limits. Use the existing case report; no partial briefing was created.',
        422: 'Metadata requires sensitive-content review or the request is invalid. No briefing was created.',
        429: 'AI capacity or usage limit reached. Wait before retrying manually; a run budget may require administrator review.',
        501: 'AI is not configured. A reviewed provider must be explicitly configured by your administrator. Existing investigation tools remain available.',
        504: 'AI preparation timed out. Retry manually; no new briefing was created.',
      }
      setError(messages[status] || 'AI briefing unavailable or response invalid. Retry manually; investigation records are unchanged.')
    } finally {
      if (active.current === controller) {
        active.current = null
        setBusy(false)
      }
    }
  }

  function cancel() {
    active.current?.abort()
    active.current = null
    returnFocus.current = true
    setBusy(false)
    setError('Briefing preparation cancelled. No new briefing was displayed.')
  }

  return (
    <section className="evidence-panel" aria-label="AI Briefing">
      <details>
        <summary style={{ fontSize: '1.05rem', fontWeight: 600 }}>AI Briefing — cited case metadata</summary>
        <p>
          Case: <code>{id}</code>
        </p>
        <p>
          An AI-generated selection of recorded metadata, with source values resolved by the server. No raw evidence files, threat verdicts or automatic investigation actions.
        </p>
        <div className="advisory-notice">
          <span className="pulse-dot" style={{ color: 'var(--status-warning)' }} />
          <span>AI output is advisory and is not a threat verdict.</span>
        </div>
        <h3>Guided cited case review</h3>
        <ol className="briefing-steps">
          <li>Inspect the recorded sources; a citation establishes traceability, not truth.</li>
          <li>Compare occurrence and recording times, and review indicator corrections.</li>
          <li>Compare this non-exhaustive selection with the complete case report.</li>
        </ol>
        <button className="secondary" onClick={() => onReview('report')}>
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          Review case report
        </button>
        <p className="muted">
          Navigation opens existing case views. It does not generate a report, download evidence or change records.
        </p>
        <p className="muted">
          Requires an explicitly configured, reviewed provider. Metadata may contain sensitive text. No provider is installed by default. Generate only under your approved deployment policy.
        </p>
        <div className="actions">
          <button ref={action} disabled={busy} onClick={generate}>
            <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
            Generate AI Briefing
          </button>
          {busy && (
            <button className="secondary" onClick={cancel}>
              Cancel AI preparation
            </button>
          )}
        </div>
        {busy && <p role="status">Preparing cited case briefing…</p>}
        {error && <p role="alert">{error}</p>}
        {error && !busy && <p>Use Generate AI Briefing to retry explicitly. Requests are never retried automatically.</p>}
        {result && (
          <article style={{ marginTop: '1.5rem' }}>
            <h2 ref={heading} tabIndex={-1}>
              AI briefing — {result.case_title}
            </h2>
            <p role="status">
              {previous ? 'Previous successful briefing retained; the new attempt has not replaced it.' : 'AI briefing ready for investigator review.'}
            </p>
            <p>
              AI-generated selection, not AI interpretation. The recorded assertions below may be incomplete or incorrect; citations do not certify truth.
            </p>
            <p>
              Case revision: {result.case_revision} · Snapshot (UTC): <time dateTime={result.snapshot_at}>{result.snapshot_at}</time>
            </p>
            <p>This snapshot is not a live view. Later changes may not be reflected; generate again explicitly when needed.</p>
            <p className="muted">
              Context digest (not an evidence hash): <code>{result.context_sha256}</code>
            </p>
            <p>
              {result.sources.filter(source => source.selection === 'model').length} AI-selected sources ·{' '}
              {result.sources.filter(source => source.selection === 'correction_context').length} server-added correction sources. These are selection counts, not case totals.
            </p>
            <label>
              Review source category
              <select value={category} onChange={event => setCategory(event.target.value)}>
                <option value="all">All returned sources</option>
                {Object.entries(reviewCategories).map(([kind, label]) => (
                  <option key={kind} value={kind}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <p className="muted">
              This filter changes only displayed results, not provider input. Correction-linked sources remain visible in every category.
            </p>
            {!reviewGroups(result.sources, category).length && (
              <p role="status">No returned sources in this category. This does not mean the case has no such records.</p>
            )}
            {reviewGroups(result.sources, category).map(group => (
              <section key={group.kind} aria-label={`Briefing ${group.label}`} style={{ marginTop: '1.25rem' }}>
                <h3>
                  {group.label} — {group.sources.length} displayed
                </h3>
                {group.sources.map(source => (
                  <section className="report-source" key={source.citation}>
                    <h4>{group.label} — recorded metadata</h4>
                    <p>
                      Source citation: <code>{source.citation}</code>
                    </p>
                    {source.selection === 'correction_context' && (
                      <p>Correction context included by the server; original observation retained.</p>
                    )}
                    {(source.fields.supersedes_id || source.fields.superseded_by_id) && (
                      <p>Correction-linked observation retained across category filters.</p>
                    )}
                    {sourceEvidenceHref(source, id) && <a href={sourceEvidenceHref(source, id)}>Open source evidence {source.evidence_id}</a>}
                    {reviewDestination(source, id) && (
                      <button className="secondary" onClick={() => onReview(reviewDestination(source, id)!, source.citation)}>
                        Review {reviewDestination(source, id)} section
                      </button>
                    )}
                    {!sourceEvidenceHref(source, id) && !reviewDestination(source, id) && (
                      <p>No supported review destination for this citation.</p>
                    )}
                    <dl className="report-fields">
                      {Object.entries(source.fields).map(([key, value]) => (
                        <div key={key}>
                          <dt>{reportLabel(key)}</dt>
                          <dd>{reportValue(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  </section>
                ))}
              </section>
            ))}
            <h3 style={{ marginTop: '1.5rem' }}>Uncertainty and limitations</h3>
            <ul style={{ paddingLeft: '1.25rem', color: 'var(--muted)', fontSize: '0.88rem' }}>
              {result.limitations.map(text => (
                <li key={text} style={{ margin: '0.35rem 0' }}>
                  {text}
                </li>
              ))}
            </ul>
          </article>
        )}
        <p className="muted" style={{ marginTop: '1.5rem' }}>
          Briefings stay in this case workspace’s memory. Leaving the case, disconnecting or reloading clears them. Existing reports and evidence remain separate.
        </p>
      </details>
    </section>
  )
}
