import { useState } from 'react'
import type { InvestigationService } from '../evidence/service'
import { ApiError } from '../../services/http'
import { prepareSubmission } from './contracts'
import type { TimelineDraft, TimelineEvent, TimelineSubmission } from './contracts'

export function TimelineEventForm({ api, evidenceId, incidentId, onCreated }: { api: InvestigationService; evidenceId: string; incidentId: string; onCreated: () => void }) {
  const [draft, setDraft] = useState<TimelineDraft>({ occurred_at: '', title: '', description: '', source: '', source_locator: '' })
  const [submissionId, setSubmissionId] = useState(() => crypto.randomUUID())
  const [pending, setPending] = useState<TimelineSubmission | null>(null)
  const [saved, setSaved] = useState<TimelineEvent | null>(null)
  const [recent, setRecent] = useState<TimelineEvent[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit() {
    if (busy) return
    let payload: TimelineSubmission
    try { payload = pending || prepareSubmission(draft, submissionId) }
    catch (problem) { setError((problem as Error).message); return }
    setPending(payload); setBusy(true); setError('')
    try {
      const result = await api.createTimeline(evidenceId, payload)
      setSaved(result); setPending(null); setDraft({ occurred_at: '', title: '', description: '', source: '', source_locator: '' })
      setSubmissionId(crypto.randomUUID()); onCreated()
    } catch (problem) {
      if (problem instanceof ApiError && problem.status === 422) {
        setPending(null); setError('Submission rejected. Check the timestamp and field limits before resubmitting.')
      } else setError('Submission not confirmed. Review the incident timeline, then retry this unchanged submission if needed. Its ID and contents are retained; do not create a replacement for the same observation.')
    } finally { setBusy(false) }
  }
  return <section className="evidence-panel"><h2>Add timeline observation</h2>
    <p>This records your observation about this evidence. It does not automatically establish a forensic finding.</p>
    {!pending && <p><a href={`#timeline/${incidentId}`}>View incident timeline</a></p>}
    <form onSubmit={e => { e.preventDefault(); void submit() }}><fieldset disabled={busy || pending !== null}>
      <label htmlFor="observation-time">Occurrence time (ISO timestamp with offset)</label>
      <input id="observation-time" value={draft.occurred_at} required maxLength={64} placeholder="2026-09-06T12:30:00+05:30" onChange={e => setDraft(v => ({ ...v, occurred_at: e.target.value }))} />
      <p className="muted">Enter the reported event time explicitly. Upload and verification times are not substituted.</p>
      <label htmlFor="observation-title">Observation title</label><input id="observation-title" value={draft.title} required maxLength={200} onChange={e => setDraft(v => ({ ...v, title: e.target.value }))} />
      <label htmlFor="observation-description">Observation description</label><textarea id="observation-description" rows={4} maxLength={10000} value={draft.description} onChange={e => setDraft(v => ({ ...v, description: e.target.value }))} />
      <label htmlFor="observation-source">Observation source</label><input id="observation-source" required maxLength={200} value={draft.source} onChange={e => setDraft(v => ({ ...v, source: e.target.value }))} />
      <label htmlFor="observation-locator">Source locator (optional)</label><input id="observation-locator" maxLength={512} value={draft.source_locator} onChange={e => setDraft(v => ({ ...v, source_locator: e.target.value }))} />
      <button>Record observation</button></fieldset></form>
    {error && <p role="alert">{error}</p>}
    {pending && !busy && <><p>Retained submission ID: <code>{submissionId}</code>. Leaving this detail or reloading discards the in-memory draft and retry ID.</p>
      <div className="actions"><button onClick={async () => {
        try { const page = await api.timelineSearch({ incident_id: incidentId, evidence_id: evidenceId, sort: 'newest' }); setRecent(page.items) }
        catch { setError('Could not load existing observations. Keep this unchanged submission for a safe retry.') }
      }}>Review current observations</button><button onClick={() => void submit()}>Retry unchanged submission</button></div></>}
    {recent && pending && <div><p>Latest occurrence-time page for this evidence. An absent record does not prove the submission failed.</p><ul>{recent.map(event => <li key={event.id}>{event.title} — submission {event.submission_id || 'legacy'}</li>)}</ul></div>}
    {busy && <p role="status">Recording observation…</p>}
    {saved && <p role="status">Observation recorded. <a href={`#timeline-event/${saved.id}`}>View recorded observation</a></p>}
  </section>
}
