import { useEffect, useState } from 'react'
import type { InvestigationService } from '../evidence/service'
import type { CaseHistoryEvent, CaseHistoryPage } from './contracts'

export function CaseHistory({ api, id }: { api: InvestigationService; id: string }) {
  const [after,setAfter]=useState<number>(), [attempt,setAttempt]=useState(0)
  const [items,setItems]=useState<CaseHistoryEvent[]>([])
  const [page,setPage]=useState<CaseHistoryPage>(), [loading,setLoading]=useState(true), [error,setError]=useState(false)
  useEffect(()=>{
    const controller=new AbortController()
    setLoading(true);setError(false)
    api.caseHistory(id,after,controller.signal).then(result=>{
      if(controller.signal.aborted)return
      setItems(current=>after===undefined?result.items:[...current,...result.items.filter(item=>!current.some(old=>old.id===item.id))])
      setPage(result);setLoading(false)
    },()=>{if(!controller.signal.aborted){setError(true);setLoading(false)}})
    return ()=>controller.abort()
  },[api,id,after,attempt])
  return <section className="evidence-panel" aria-label="Case history"><h2>Case history</h2>
    <p>Case management changes only. Evidence custody and forensic timeline observations are separate.</p>
    {loading && <p role="status">Loading case history…</p>}
    {error && <p role="alert">Unable to load case history. <button onClick={()=>setAttempt(v=>v+1)}>Retry case history</button></p>}
    {page && <p>{page.tracking_started?`Tracking starts at revision ${page.tracking_started_revision}. Earlier changes are not reconstructed.`:'Case history tracking is unavailable; this does not mean no changes occurred.'}</p>}
    <ol className="history-list" tabIndex={0} aria-label="Case history entries">{items.map(event=><li key={event.id}>
      <h3>Revision {event.revision}: {event.event_type==='baseline_registered'?'Migration baseline':event.event_type==='case_created'?'Case created':Object.keys(event.changes).length?'Case updated':'Case saved — no field changes'}</h3>
      <p>{event.actor_label} · {event.source} · {new Date(event.recorded_at).toISOString()} (UTC)</p>
      {event.event_type==='baseline_registered' && <p>Snapshot when tracking began; earlier history is unavailable.</p>}
      {Object.entries(event.changes).map(([field,change])=><details key={field}><summary>{field}: {event.event_type==='case_updated'?'changed':'snapshot'}</summary>
        {event.event_type==='case_updated' && <><p>Before</p><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{change.before}</pre></>}
        <p>{event.event_type==='case_updated'?'After':'Recorded value'}</p><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{change.after}</pre>
      </details>)}
    </li>)}</ol>
    <button disabled={loading || error || page?.next_revision==null} onClick={()=>setAfter(page!.next_revision!)}>Load more case history</button>
    <button onClick={()=>{setAfter(undefined);setItems([]);setPage(undefined);setAttempt(v=>v+1)}}>Refresh case history</button>
  </section>
}
