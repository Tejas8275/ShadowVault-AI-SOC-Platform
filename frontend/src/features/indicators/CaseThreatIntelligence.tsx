import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import type { InvestigationService } from '../evidence/service'
import { useResource } from '../evidence/useResource'
import { ApiError } from '../../services/http'
import type { EvidenceIndicatorContext, IndicatorFilters, IndicatorKind, IndicatorObservation, IndicatorSubmission } from './contracts'

export function CaseThreatIntelligence({api, id, onHash, visible=true, context}: {api:InvestigationService; id:string; onHash:(value:string)=>void; visible?:boolean; context?:EvidenceIndicatorContext}) {
 const kindId=useId(), sourceId=useId(), filterKindId=useId(), messageId=useId()
 const heading=useRef<HTMLHeadingElement>(null), formDetails=useRef<HTMLDetailsElement>(null), evidenceInput=useRef<HTMLInputElement>(null)
 const [cursor,setCursor]=useState<string>(), [previous,setPrevious]=useState<(string|undefined)[]>([]), [attempt,setAttempt]=useState(0)
 const [filters,setFilters]=useState<IndicatorFilters>({}), [draft,setDraft]=useState<IndicatorFilters>({}), [filterError,setFilterError]=useState('')
 const load=useCallback((signal:AbortSignal)=>api.indicators(id,cursor,signal,filters),[api,id,cursor,attempt,filters])
 const state=useResource(load)
 const [evidence,setEvidence]=useState(''), [evidenceName,setEvidenceName]=useState(''), [kind,setKind]=useState<IndicatorKind>('sha256')
 const [source,setSource]=useState<IndicatorSubmission['source_kind']>('manual')
 const [value,setValue]=useState(''), [locator,setLocator]=useState(''), [supersedes,setSupersedes]=useState('')
 const [pending,setPending]=useState<{evidence:string;payload:IndicatorSubmission}>()
 const [receipt,setReceipt]=useState<IndicatorObservation>()
 const [saving,setSaving]=useState(false), [message,setMessage]=useState(''), [failed,setFailed]=useState(false), [discard,setDiscard]=useState(false)
 const active=useRef<AbortController | null>(null), appliedContext=useRef(0)
 useEffect(()=>()=>active.current?.abort(),[])
 function applyFilters(next:IndicatorFilters){setFilters(next);setDraft(next);setCursor(undefined);setPrevious([]);setFilterError('')}
 function refresh(){setCursor(undefined);setPrevious([]);setAttempt(v=>v+1)}
 function focusForm(){if(formDetails.current)formDetails.current.open=true;requestAnimationFrame(()=>evidenceInput.current?.focus())}
 function locate(observation_id:string){applyFilters({observation_id});heading.current?.focus()}
 useEffect(()=>{
  if(!visible || !context || appliedContext.current===context.sequence)return
  appliedContext.current=context.sequence
  applyFilters({evidence_id:context.id})
  if(context.action==='add'){
   if(pending || saving){setFailed(true);setMessage('Finish or explicitly discard the pending submission before changing evidence.');focusForm()}
   else {setEvidence(context.id);setEvidenceName(context.filename);setSupersedes('');setValue('');setLocator('');setMessage('');focusForm()}
  } else heading.current?.focus()
 },[visible,context,pending,saving])
 function correct(item:IndicatorObservation){
  if(pending || saving)return
  setEvidence(item.evidence_id);setEvidenceName('');setKind(item.kind);setSource('manual');setValue(item.raw_value);setLocator(item.source_locator||'');setSupersedes(item.id);setMessage('Correction appends a new observation. The original remains unchanged.');setFailed(false);focusForm()
 }
 async function submit(event:FormEvent){
  event.preventDefault();if(active.current)return
  const request=pending || {evidence:evidence.trim(),payload:{kind,source_kind:source,submission_id:crypto.randomUUID(),
   ...(source==='manual'?{raw_value:value,...(locator.trim()?{source_locator:locator.trim()}:{})}:{}),...(supersedes.trim()?{supersedes_id:supersedes.trim()}:{})}}
  const controller=new AbortController();active.current=controller
  let sent=false
  setSaving(true);setFailed(false);setMessage('');setDiscard(false)
  try {
   const record=await api.details(request.evidence,controller.signal)
   if(record.incident_id!==id)throw new ApiError(404,'Evidence does not belong to this case.')
   setEvidenceName(record.filename);setPending(request);sent=true
   const result=await api.addIndicator(request.evidence,request.payload,controller.signal)
   if(controller.signal.aborted)return
   if(result.incident_id!==id || result.evidence_id!==request.evidence)throw new Error('Unexpected observation response')
   setReceipt(result);setPending(undefined);setValue('');setLocator('');setSupersedes('');setMessage('Indicator observation recorded.');refresh()
  } catch(error){
   if(controller.signal.aborted)return
   setFailed(true)
   if(error instanceof ApiError && error.status===422){setPending(undefined);setMessage('Validation failed. Check the evidence/observation IDs and value format: SHA-256 uses 64 hex characters; IP uses one address; domain uses an ASCII name; file uses a filename only.')}
   else if(error instanceof ApiError && error.status===404){setPending(undefined);setMessage('Evidence or correction is unavailable in this case. Check the source before submitting.')}
   else if(error instanceof ApiError && error.status===409){setMessage('Submission conflict. Refresh indicators and inspect the correction history. Retry the same submission only to resolve a concurrent save; a changed payload needs an explicit new submission.')}
   else if(sent || pending)setMessage('Save not confirmed. Retry the unchanged submission; it may already have been recorded.')
   else setMessage('Could not verify source evidence. No indicator submission was sent. Check the connection and try again.')
  } finally {if(active.current===controller)active.current=null;if(!controller.signal.aborted)setSaving(false)}
 }
 return <section className="evidence-panel" aria-label="Case Threat Intelligence">
  <div className="section-heading"><h2 ref={heading} tabIndex={-1}>Case Threat Intelligence</h2><button className="secondary" onClick={refresh} disabled={state.loading}>Refresh indicators</button></div>
  <p>Investigator-recorded candidate observations, not threat verdicts. Every observation references authorized evidence in this case.</p>
  {receipt && <section aria-label="Last saved indicator" className="evidence-panel"><h3>Saved observation</h3><p>{receipt.kind}: {receipt.normalized_value}</p><p>Saved observation ID: {receipt.id}</p><a href={`#cases/${id}/evidence/${receipt.evidence_id}`}>Saved source evidence {receipt.evidence_id}</a><button className="secondary" onClick={()=>locate(receipt.id)}>View saved observation</button><p>This save receipt is retained even if the list cannot refresh. It is not a current correction-status check.</p></section>}
  <form className="filter-panel" aria-label="Indicator filters" onSubmit={event=>{event.preventDefault();if(draft.value?.trim()&&!draft.kind){setFilterError('Select an indicator kind for exact-value filtering.');return}applyFilters({...draft,observation_id:undefined})}}>
   <div className="filter-grid"><div><label htmlFor={filterKindId}>Filter indicator kind</label><select id={filterKindId} value={draft.kind||''} onChange={e=>setDraft({...draft,kind:e.target.value as IndicatorKind|''})}><option value="">All kinds</option><option value="sha256">SHA-256 hash</option><option value="ip">IP address</option><option value="domain">Domain</option><option value="filename">Filename</option></select></div>
    <label>Exact indicator value<input maxLength={255} value={draft.value||''} onChange={e=>setDraft({...draft,value:e.target.value})} /></label>
    <label>Filter indicator evidence ID<input maxLength={36} value={draft.evidence_id||''} onChange={e=>setDraft({...draft,evidence_id:e.target.value})} /></label>
   </div>{filters.observation_id && <p>Showing observation {filters.observation_id}. Clear filters to return to the case list.</p>}
   <div className="actions"><button type="submit">Filter indicators</button><button type="button" className="secondary" onClick={()=>applyFilters({})}>Clear indicator filters</button></div>
   {filterError && <p role="alert">{filterError}</p>}
  </form>
  {state.loading && <p role="status">Loading indicators…</p>}
  {state.error && <p role="alert">Indicators unavailable. Refresh to retry; this does not mean there are no observations.</p>}
  {!state.loading && !state.error && state.data && <>
   {state.data.items.length===0 && <p>No indicator observations on this page.</p>}
   <ol className="history-list" aria-label="Indicator observations">{state.data.items.filter(item=>item.incident_id===id).map(item=><li key={item.id}>
    <h3>{item.kind}: <span style={{overflowWrap:'anywhere'}}>{item.normalized_value}</span></h3>
    {item.superseded_by_id ? <p><strong>Corrected — original retained.</strong> <button className="secondary" onClick={()=>locate(item.superseded_by_id!)}>View correction {item.superseded_by_id}</button></p> : <p>{item.superseded_by_id===null?'No later correction recorded in this response.':'Correction status unavailable; refresh with the current backend.'}</p>}
    {item.raw_value!==item.normalized_value && <p>Recorded value: {item.raw_value}</p>}
    <p>{item.source_kind==='manual'?'Manual assertion — not independently verified':`Stored evidence metadata: ${item.source_kind==='evidence_sha256'?'SHA-256':'filename'}`}</p>
    <p>{item.actor_label} · Recorded at <time dateTime={item.created_at}>{new Date(item.created_at).toISOString()} (UTC)</time> · Local normalization v{item.schema_version}</p>
    <p><a href={`#cases/${id}/evidence/${item.evidence_id}`}>Source evidence {item.evidence_id}</a></p>
    <button className="secondary" onClick={()=>applyFilters({evidence_id:item.evidence_id})}>Show indicators for this evidence</button>
    {item.source_locator && <p>Source citation: {item.source_locator}</p>}
    <p>Observation ID: {item.id}</p>
    {item.supersedes_id && <><p>Corrects observation: {item.supersedes_id}. The original record remains preserved.</p><button className="secondary" onClick={()=>locate(item.supersedes_id!)}>View original {item.supersedes_id}</button></>}
    <div className="actions"><button className="secondary" disabled={saving || !!pending || item.superseded_by_id!==null} onClick={()=>correct(item)}>Correct observation {item.id}</button>
    {item.kind==='sha256' && <button className="secondary" onClick={()=>onHash(item.normalized_value)}>Find matching SHA-256 in this case</button>}</div>
   </li>)}</ol>
   <div className="actions"><button disabled={!cursor} onClick={()=>{setCursor(undefined);setPrevious([])}}>First indicator page</button><button disabled={!previous.length} onClick={()=>{setCursor(previous.at(-1));setPrevious(v=>v.slice(0,-1))}}>Previous indicators</button><button disabled={!state.data.next_cursor} onClick={()=>{setPrevious(v=>[...v,cursor]);setCursor(state.data!.next_cursor!)}}>Next indicators</button></div>
  </>}
  <details ref={formDetails}><summary>Add indicator observation</summary>
   <p>Use an evidence-context action or copy an Evidence ID from this case. No file paths, external lookups or content extraction. Source citations are investigator-supplied references.</p>
   {evidenceName && <p>Selected evidence: {evidenceName} · {evidence}</p>}
   <form onSubmit={submit} aria-describedby={message?messageId:undefined}>
    <fieldset disabled={saving || !!pending}><legend>Observation details</legend>
     <label>Indicator evidence ID<input ref={evidenceInput} required maxLength={36} value={evidence} onChange={e=>{setEvidence(e.target.value);setEvidenceName('')}} /></label>
     <label htmlFor={kindId}>Indicator kind</label><select id={kindId} value={kind} onChange={e=>{setKind(e.target.value as IndicatorKind);setSource('manual')}}><option value="sha256">SHA-256 hash</option><option value="ip">IP address</option><option value="domain">Domain</option><option value="filename">Filename</option></select>
     <label htmlFor={sourceId}>Indicator source</label><select id={sourceId} value={source} onChange={e=>setSource(e.target.value as IndicatorSubmission['source_kind'])}><option value="manual">Manual observation</option>{kind==='sha256'&&<option value="evidence_sha256">Use stored evidence SHA-256</option>}{kind==='filename'&&<option value="evidence_filename">Use stored evidence filename</option>}</select>
     {source==='manual' && <><label>Indicator value<input required maxLength={255} value={value} onChange={e=>setValue(e.target.value)} /></label><label>Source citation (optional)<input maxLength={512} value={locator} onChange={e=>setLocator(e.target.value)} /></label></>}
     <label>Corrects observation ID (optional)<input maxLength={36} value={supersedes} onChange={e=>setSupersedes(e.target.value)} /></label>
    </fieldset>
    <button disabled={saving} type="submit">{saving?'Recording indicator…':pending?'Retry unchanged indicator':'Record indicator'}</button>
    {pending && !saving && <><p>An earlier submission may have succeeded. Retry it first to avoid duplicate observations. Navigation and metadata refresh within this case preserve it; reloading the tab or leaving the case clears this memory.</p><button type="button" className="secondary" onClick={()=>setDiscard(true)}>Start a new submission</button>{discard && <><p>Discard this pending retry identity? Check the saved observations first; the server may already have recorded it.</p><button type="button" onClick={()=>{setPending(undefined);setDiscard(false);setFailed(false);setMessage('New submission selected. Check existing observations before saving again.')}}>Confirm new submission</button><button type="button" onClick={()=>setDiscard(false)}>Keep pending submission</button></>}</>}
   </form>
   {message && <p id={messageId} role={failed?'alert':'status'}>{message}</p>}
  </details>
 </section>
}
