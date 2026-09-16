import { useEffect, useRef, useState, type FormEvent } from 'react'
import { LoginPage } from '../../pages/LoginPage'
import { ApiError } from '../../services/http'
import type { Filters } from './contracts'
import { createInvestigationService } from './service'
import { EvidenceSearch } from './EvidenceSearch'
import { EvidenceDetailsPage } from './EvidenceDetailsPage'
import { TimelinePanel } from '../timeline/TimelinePanel'
import { TimelineEventDetails } from '../timeline/TimelineEventDetails'
import { DashboardPage } from '../../pages/DashboardPage'
import { CaseOverview } from '../cases/CaseOverview'
import { CaseList } from '../cases/CaseList'
import { CaseWorkspace } from '../cases/CaseWorkspace'

export function InvestigationWorkspace({ connectionOnly, overview, evidenceId, timeline, timelineIncidentId, timelineEventId, cases, caseId, caseEvidenceId }: {
  connectionOnly?: boolean; overview?: boolean; evidenceId?: string; timeline?: boolean; timelineIncidentId?: string; timelineEventId?: string; cases?: boolean; caseId?: string; caseEvidenceId?: string
}) {
  const focusConnection = useRef(false), submitting = useRef(false)
  const connectionStatus = useRef<HTMLSpanElement>(null)
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState<Filters>({})
  const [timelineFilters, setTimelineFilters] = useState<Filters>({})
  useEffect(() => {
    if (timelineIncidentId) setTimelineFilters(current => current.incident_id === timelineIncidentId ? current : { incident_id: timelineIncidentId })
  }, [timelineIncidentId])
  const [generation, setGeneration] = useState(0)
  const [api] = useState(() => createInvestigationService(
    import.meta.env.VITE_INVESTIGATION_API_BASE_URL || 'http://127.0.0.1:8000/api/v2/investigation',
    () => { focusConnection.current=true; setConnected(false); setFilters({}); setTimelineFilters({}); setGeneration(v => v + 1); setError('Operator connection expired or was rejected.') },
  ))
  useEffect(() => {
    if (!connecting && focusConnection.current) {
      focusConnection.current=false
      if (connected) connectionStatus.current?.focus()
      else document.getElementById('operator-token')?.focus()
    }
  }, [connected, connecting, error, generation])
  async function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting.current) return
    submitting.current=true
    const input=event.currentTarget.elements.namedItem('operator-token') as HTMLInputElement
    const value=input.value; input.value=''; setConnecting(true); setError('')
    try { await api.connect(value); setConnected(true) }
    catch (reason) {
      setError(reason instanceof ApiError && reason.status===401
        ? 'Operator connection rejected. Check your provisioned token and try again.'
        : reason instanceof Error && reason.message==='Enter a valid provisioned operator token.'
          ? 'Enter the provisioned operator token without quotes or surrounding spaces.'
          : 'Unable to verify operator access. Check backend availability and retry manually.')
    } finally { submitting.current=false; focusConnection.current=true; setConnecting(false) }
  }
  return <div>
    {overview && <DashboardPage />}
    {!connected ? <LoginPage pending={connecting} error={error} onSubmit={connect} /> : <><div className="connection-bar"><span ref={connectionStatus} tabIndex={-1} role="status">Operator connected</span><button className="secondary" onClick={() => { api.disconnect(); focusConnection.current=true; setConnected(false); setError(''); setFilters({}); setTimelineFilters({}); setGeneration(v => v + 1) }}>Disconnect operator</button></div>
      {connectionOnly ? <section className="operator-panel" aria-labelledby="connection-title"><p className="eyebrow">ShadowVault AI / Investigation access</p><h1 id="connection-title">Operator connection</h1><p>You are connected. Open your authorized cases to continue investigating.</p><a className="connection-open" href="#cases">Open cases</a><p className="operator-privacy">This connection lasts only in this tab. Disconnecting or reloading clears transient work; it does not revoke your token on other devices.</p></section> : overview ? <CaseOverview key={generation} api={api} /> : cases ? caseId ? <CaseWorkspace key={`${generation}-${caseId}`} api={api} id={caseId} evidenceId={caseEvidenceId} /> : <CaseList key={generation} api={api} /> : timelineEventId ? <TimelineEventDetails key={`${generation}-${timelineEventId}`} api={api} id={timelineEventId} /> : timeline ?
        <TimelinePanel key={`${generation}-${timelineFilters.incident_id || ''}`} api={api} filters={timelineFilters} setFilters={setTimelineFilters} /> :
        evidenceId ? <EvidenceDetailsPage key={`${generation}-${evidenceId}`} api={api} id={evidenceId} /> : <EvidenceSearch key={generation} api={api} filters={filters} setFilters={setFilters} />}
    </>}
  </div>
}
