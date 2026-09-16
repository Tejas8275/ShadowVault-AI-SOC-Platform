import { useId, useState } from 'react'
import type { InvestigationService } from '../evidence/service'
import { transitions, type CaseRecord, type CaseSeverity, type CaseStatus } from './contracts'

export function CaseForm({ api, record, onSaved, onReload }: { api: InvestigationService; record?: CaseRecord; onSaved: (record: CaseRecord) => void; onReload: () => void }) {
  const statusId = useId()
  const [title, setTitle] = useState(record?.title || '')
  const [description, setDescription] = useState(record?.description || '')
  const [severity, setSeverity] = useState<CaseSeverity>(record?.severity || 'medium')
  const [status, setStatus] = useState<CaseStatus>(record?.status || 'open')
  const [busy, setBusy] = useState(false), [blocked, setBlocked] = useState(false), [error, setError] = useState('')
  return <section className="evidence-panel"><h2>{record ? 'Edit case' : 'Create case'}</h2>
    <form onSubmit={async event => {
      event.preventDefault(); if (busy || blocked) return
      if (!title.trim()) { setError('Enter a case title.'); return }
      setBusy(true); setError('')
      const payload = { title: title.trim(), description: description.trim(), severity }
      try {
        const saved = record ? await api.updateCase(record.id, { ...payload, status, expected_revision: record.revision }) : await api.createCase(payload)
        onSaved(saved)
      } catch {
        setBlocked(true); setError(record ? 'Save not confirmed or case changed. Reload the case before saving again.' : 'Creation not confirmed. Review the case list before creating again; a case may already exist.')
      } finally { setBusy(false) }
    }}>
      <label>Case title<input required maxLength={200} value={title} disabled={busy || blocked} onChange={e => setTitle(e.target.value)} /></label>
      <label>Case description<textarea maxLength={10000} value={description} disabled={busy || blocked} onChange={e => setDescription(e.target.value)} /></label>
      <label>Case severity<select value={severity} disabled={busy || blocked} onChange={e => setSeverity(e.target.value as CaseSeverity)}>{['low','medium','high','critical'].map(v => <option key={v}>{v}</option>)}</select></label>
      {record && <><label htmlFor={statusId}>Case status</label><select id={statusId} value={status} disabled={busy || blocked} onChange={e => setStatus(e.target.value as CaseStatus)}>{transitions[record.status].map(v => <option key={v}>{v}</option>)}</select></>}
      <p>New cases start open. Lifecycle: open → investigating → closed; closed cases can explicitly reopen to investigating. Case status does not cancel collection or restrict evidence workflows.</p>
      <button disabled={busy || blocked}>{record ? 'Save case' : 'Create case'}</button>
      {error && <p role="alert">{error}</p>}
      {blocked && <button type="button" onClick={onReload}>{record ? 'Reload case and discard draft' : 'Review cases and discard draft'}</button>}
    </form>
  </section>
}
