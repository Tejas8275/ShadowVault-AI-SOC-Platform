import type { EvidenceIndicatorContext } from '../indicators/contracts'
import { CaseThreatIntelligence } from '../indicators/CaseThreatIntelligence'
import { useEffect, useRef, useState } from 'react'
import type { InvestigationService } from '../evidence/service'
import { ApiError } from '../../services/http'
import type { CaseRecord } from './contracts'
import { EvidenceSearch } from '../evidence/EvidenceSearch'
import { EvidenceDetailsPage } from '../evidence/EvidenceDetailsPage'
import { TimelinePanel } from '../timeline/TimelinePanel'
import type { Filters } from '../evidence/contracts'
import { CaseForm } from './CaseForm'
import { CaseIntelligencePanel } from './CaseIntelligencePanel'
import { CaseHistory } from './CaseHistory'
import { CaseReport } from './CaseReport'
import { CaseBriefing } from './CaseBriefing'
import type { ReviewTarget } from './briefing'

export function CaseWorkspace({ api, id, evidenceId }: { api: InvestigationService; id: string; evidenceId?: string }) {
  const [indicatorContext, setIndicatorContext] = useState<EvidenceIndicatorContext>()
  const [attempt, setAttempt] = useState(0)
  const [view, setView] = useState('evidence')
  const [evidencePivot, setEvidencePivot] = useState(0)
  const [filters, setFilters] = useState<Filters>({ incident_id: id })
  const [timelineFilters, setTimelineFilters] = useState<Filters>({ incident_id: id })
  const [review, setReview] = useState<{ target: ReviewTarget; citation?: string; sequence: number }>()
  const destinations = useRef<Partial<Record<ReviewTarget, HTMLDivElement | null>>>({})
  const focusedReview = useRef(0)

  // The authenticated parent keys this workspace by case ID and connection generation.
  // Retain mounted panels only within that boundary; never use browser persistence.
  const [state, setState] = useState<{ data?: CaseRecord; loading: boolean; error?: string }>({ loading: true })

  function reviewSection(target: ReviewTarget, citation?: string) {
    setReview(current => ({ target, citation, sequence: (current?.sequence || 0) + 1 }))
    if (target === 'timeline') setView('timeline')
    if (evidenceId && !['report', 'case'].includes(target)) window.location.hash = `#cases/${id}`
  }

  useEffect(() => {
    if (!review || state.loading || state.error || focusedReview.current === review.sequence) return
    const destination = destinations.current[review.target]
    if (!destination || destination.closest('[hidden]')) return
    destination.focus()
    destination.scrollIntoView({ block: 'start' })
    focusedReview.current = review.sequence
  }, [review, evidenceId, state.loading, state.error])

  const reference = (target: ReviewTarget) =>
    review?.target === target && (
      <p role="status">
        Review reference: <code>{review.citation || `incident:${id}`}</code>. Use this section's existing controls to inspect the recorded information.
      </p>
    )

  function refresh() {
    setState(current => ({ ...current, loading: true, error: undefined }))
    setAttempt(v => v + 1)
  }

  useEffect(() => {
    const controller = new AbortController()
    api.caseDetail(id, controller.signal).then(
      data => {
        if (controller.signal.aborted) return
        if (data.id !== id) {
          setIndicatorContext(undefined)
          setReview(undefined)
          focusedReview.current = 0
          setState({ loading: false, error: 'Case unavailable. Retained work has been cleared.' })
          return
        }
        setState({ data, loading: false })
      },
      error => {
        if (controller.signal.aborted) return
        const denied = error instanceof ApiError && [401, 403, 404].includes(error.status)
        if (denied) {
          setIndicatorContext(undefined)
          setReview(undefined)
          focusedReview.current = 0
        }
        setState(current => ({
          data: denied ? undefined : current.data,
          loading: false,
          error: denied
            ? 'Case unavailable. Retained work has been cleared.'
            : 'Unable to refresh case access. Retained work is hidden; use Refresh case to retry.',
        }))
      },
    )
    return () => controller.abort()
  }, [api, id, attempt])

  const riskScore = state.data
    ? state.data.severity === 'critical'
      ? 95
      : state.data.severity === 'high'
        ? 75
        : state.data.severity === 'medium'
          ? 50
          : 25
    : 0

  const riskColor = state.data
    ? state.data.severity === 'critical'
      ? '#ff385c'
      : state.data.severity === 'high'
        ? '#fb923c'
        : state.data.severity === 'medium'
          ? '#facc15'
          : '#38bdf8'
    : 'var(--muted)'

  return (
    <section>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <a href="#cases" className="back-link" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}>
          <span aria-hidden="true">← </span>Back to cases
        </a>
        <button className="secondary" disabled={state.loading} onClick={refresh}>
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
          Refresh case
        </button>
      </div>

      {state.loading && <p role="status">Loading case…</p>}
      {state.error && <p role="alert">{state.error}</p>}

      {state.data && (
        <div hidden={state.loading || !!state.error} inert={state.loading || !!state.error}>
          <div
            className="case-header"
            data-review-target="case"
            tabIndex={-1}
            ref={node => {
              destinations.current.case = node
            }}
          >
            {reference('case')}
            <p className="eyebrow">Case workspace</p>
            <h1>{state.data.title}</h1>
            <div className="actions">
              <span className={`badge severity-${state.data.severity}`}>Severity: {state.data.severity}</span>
              <span className={`badge status-${state.data.status}`}>{state.data.status}</span>
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                margin: '0.75rem 0',
                padding: '0.6rem 1rem',
                background: 'rgba(0, 0, 0, 0.35)',
                borderRadius: '6px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: riskColor }}>
                Threat Assessment: {riskScore}/100
              </span>
              <div style={{ flex: 1, height: '6px', background: 'var(--bg-void)', borderRadius: '3px', overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${riskScore}%`,
                    height: '100%',
                    background: riskColor,
                    borderRadius: '3px',
                    transition: 'width 0.4s ease',
                  }}
                />
              </div>
            </div>

            <p className="plain-text">{state.data.description || 'No description provided.'}</p>
            <p>
              Case ID: {id} · Status: {state.data.status} · Revision: {state.data.revision}
            </p>
            <p>
              Owner: {state.data.created_by_id} · Created: {new Date(state.data.created_at).toISOString()} (UTC)
            </p>
            <p>
              Last updated: {state.data.updated_at ? `${new Date(state.data.updated_at).toISOString()} (UTC)` : 'Unknown'}
            </p>
          </div>

          <CaseIntelligencePanel key={`intelligence-${attempt}-${state.data.revision}`} api={api} id={id} />

          <div
            data-review-target="report"
            tabIndex={-1}
            ref={node => {
              destinations.current.report = node
            }}
          >
            {reference('report')}
            <CaseReport key={`report-${id}`} api={api} id={id} />
          </div>

          <CaseBriefing key={`briefing-${id}`} api={api} id={id} onReview={reviewSection} />

          <div
            hidden={!!evidenceId}
            data-review-target="indicators"
            tabIndex={-1}
            ref={node => {
              destinations.current.indicators = node
            }}
          >
            {reference('indicators')}
            <CaseThreatIntelligence
              key={id}
              api={api}
              id={id}
              visible={!evidenceId}
              context={indicatorContext}
              onHash={sha256 => {
                setFilters({ incident_id: id, sha256 })
                setEvidencePivot(v => v + 1)
                setView('evidence')
              }}
            />
          </div>

          {evidenceId ? (
            <EvidenceDetailsPage
              key={evidenceId}
              api={api}
              id={evidenceId}
              caseId={id}
              onIndicators={(evidence, action) => {
                setIndicatorContext(current => ({ ...evidence, action, sequence: (current?.sequence || 0) + 1 }))
                window.location.hash = `#cases/${id}`
              }}
            />
          ) : (
            <>
              <div className="case-work-grid">
                <div className="case-investigation">
                  <div className="actions workspace-tabs" aria-label="Case investigation sections">
                    <button aria-pressed={view === 'evidence'} onClick={() => setView('evidence')}>
                      <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                      </svg>
                      Case evidence
                    </button>
                    <button aria-pressed={view === 'timeline'} onClick={() => setView('timeline')}>
                      <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12 6 12 12 16 14" />
                      </svg>
                      Case timeline
                    </button>
                  </div>
                  {view === 'evidence' ? (
                    <EvidenceSearch
                      key={evidencePivot}
                      api={api}
                      filters={filters}
                      setFilters={value => setFilters({ ...value, incident_id: id })}
                      lockedIncidentId={id}
                      evidenceHref={eid => `#cases/${id}/evidence/${eid}`}
                    />
                  ) : (
                    <div
                      data-review-target="timeline"
                      tabIndex={-1}
                      ref={node => {
                        destinations.current.timeline = node
                      }}
                    >
                      {reference('timeline')}
                      <TimelinePanel
                        api={api}
                        filters={timelineFilters}
                        setFilters={value => setTimelineFilters({ ...value, incident_id: id })}
                        lockedIncidentId={id}
                      />
                    </div>
                  )}
                </div>
                <aside className="case-management" aria-label="Case management">
                  <CaseForm
                    key={`${attempt}-${state.data.revision}`}
                    api={api}
                    record={state.data}
                    onSaved={refresh}
                    onReload={refresh}
                  />
                  <div
                    data-review-target="history"
                    tabIndex={-1}
                    ref={node => {
                      destinations.current.history = node
                    }}
                  >
                    {reference('history')}
                    <CaseHistory
                      key={`history-${attempt}-${state.data.revision}`}
                      api={api}
                      id={id}
                    />
                  </div>
                </aside>
              </div>
            </>
          )}
        </div>
      )}
    </section>
  )
}
