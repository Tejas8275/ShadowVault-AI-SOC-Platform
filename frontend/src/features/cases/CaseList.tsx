import { useCallback, useId, useState } from 'react'
import type { InvestigationService } from '../evidence/service'
import { useResource } from '../evidence/useResource'
import { CaseForm } from './CaseForm'

export function CaseList({ api }: { api: InvestigationService }) {
  const severityId=useId()
  const [severity,setSeverity]=useState('')
  const [q,setQ]=useState(''), [status,setStatus]=useState(''), [filters,setFilters]=useState<Record<string,string>>({})
  const [cursor,setCursor]=useState<string>(), [previous,setPrevious]=useState<(string|undefined)[]>([])
  const [attempt,setAttempt]=useState(0), [creating,setCreating]=useState(false)
  const load=useCallback((signal:AbortSignal)=>api.cases(filters,cursor,signal),[api,filters,cursor,attempt])
  const state=useResource(load)
  return <section><h1>Cases</h1><p>Find your investigations by title, description, status, or severity. Open a case to review its evidence and history.</p>
    <form className="filter-panel case-filters" onSubmit={e=>{e.preventDefault();setFilters({q,status,severity});setCursor(undefined);setPrevious([])}}>
      <div className="case-filter-grid"><label>Case search<input maxLength={200} value={q} onChange={e=>setQ(e.target.value)} /></label>
      <label>Filter case status<select value={status} onChange={e=>setStatus(e.target.value)}><option value="">All</option>{['open','investigating','closed'].map(v=><option key={v}>{v}</option>)}</select></label>
      <div><label htmlFor={severityId}>Filter case severity</label><select id={severityId} value={severity} onChange={e=>setSeverity(e.target.value)}><option value="">All</option>{['low','medium','high','critical'].map(v=><option key={v}>{v}</option>)}</select></div></div>
      <button>Search cases</button>
    </form>
    <button onClick={()=>setCreating(v=>!v)}>{creating?'Hide creation form':'New case'}</button>
    {creating && <CaseForm api={api} onSaved={record=>{window.location.hash=`#cases/${record.id}`}} onReload={()=>{setCreating(false);setAttempt(v=>v+1)}} />}
    {state.loading && <p role="status">Loading cases…</p>}{state.error && <p role="alert">{state.error}</p>}
    {state.data && <><p role="status">{state.data.total} matching cases</p>{!state.data.items.length && <p>No cases match these filters.</p>}
      {state.data.items.map(record=><article className="case-card" key={record.id}><h2><a href={`#cases/${record.id}`}>{record.title}</a></h2><div className="actions"><span className={`badge status-${record.status}`}>{record.status}</span><span className={`badge severity-${record.severity}`}>{record.severity}</span></div>
        <p className="case-description">{record.description || 'No description provided.'}</p>
        <p className="muted">Last updated: {record.updated_at ? `${new Date(record.updated_at).toISOString()} (UTC)` : 'Unknown'}</p>
        <p className="record-id">Case ID: {record.id}</p></article>)}
      <div className="actions"><button disabled={!previous.length} onClick={()=>{setCursor(previous.at(-1));setPrevious(v=>v.slice(0,-1))}}>Previous cases</button>
      <button disabled={!state.data.next_cursor} onClick={()=>{setPrevious(v=>[...v,cursor]);setCursor(state.data!.next_cursor!)}}>Next cases</button></div></>}
    <button onClick={()=>setAttempt(v=>v+1)}>Refresh cases</button>
  </section>
}
