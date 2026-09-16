import { useEffect, useRef, useState } from 'react'
import type { InvestigationService } from '../evidence/service'
import { ApiError } from '../../services/http'
import { type CaseReportDraft, reportLabel, reportText, reportValue } from './report'

export function CaseReport({ api, id }: {api: InvestigationService; id: string}) {
  const [draft,setDraft]=useState<CaseReportDraft>()
  const [loading,setLoading]=useState(false), [error,setError]=useState(''), [visible,setVisible]=useState(false)
  const [saved,setSaved]=useState(false)
  const [previous,setPrevious]=useState(false)
  const active=useRef<AbortController | null>(null)
  const heading=useRef<HTMLHeadingElement>(null)
  const action=useRef<HTMLButtonElement>(null)
  const returnFocus=useRef(false)
  useEffect(()=>()=>{active.current?.abort()},[api,id])
  useEffect(()=>{if(visible && draft)heading.current?.focus()},[visible,draft])
  useEffect(()=>{
    if(!visible && !loading && returnFocus.current){returnFocus.current=false;action.current?.focus()}
  },[visible,loading])
  async function create() {
    if(active.current)return
    const controller=new AbortController();active.current=controller
    setLoading(true);setError('');setPrevious(!!draft);setSaved(false);setVisible(true)
    try {
      const result=await api.caseReport(id,controller.signal)
      if(!controller.signal.aborted){setDraft(result);setPrevious(false)}
    } catch(error) {
      if(!controller.signal.aborted){
        const denied=error instanceof ApiError && [401,403,404].includes(error.status)
        if(denied){setDraft(undefined);setPrevious(false)}
        setError(denied ? 'Report access unavailable. The retained draft has been cleared.'
          : error instanceof ApiError && error.status===413
            ? 'This case exceeds the complete report limit. No partial draft was created. Retry manually using Create report draft.'
            : draft ? 'Report replacement failed. The previous successful snapshot remains available. Retry manually using Create report draft.'
              : 'Report unavailable. No draft was created. Retry manually; existing investigation records are unchanged.')
      }
    } finally {if(active.current===controller){active.current=null;setLoading(false)}}
  }
  function close() {
    if(active.current && draft)setError('Report replacement cancelled. The previous successful snapshot remains available. Retry manually using Create report draft.')
    active.current?.abort();active.current=null;returnFocus.current=true;setLoading(false);setVisible(false)
  }
  function save() {
    if(!draft)return
    let url: string | undefined
    try {
      url=URL.createObjectURL(new Blob([reportText(draft)],{type:'text/plain;charset=utf-8'}))
      const link=document.createElement('a');link.href=url;link.download=`case-${id}-draft.txt`;link.click();setSaved(true)
    } catch {setError('Unable to start saving. The draft remains available; retry saving manually.')}
    finally {if(url)URL.revokeObjectURL(url)}
  }
  return <section className="evidence-panel case-report" aria-label="Case report">
    <div className="section-heading"><h2>Investigation report</h2><button ref={action} disabled={loading} onClick={create}>Create report draft</button></div>
    <p>Create a metadata-only draft for this case. No evidence files are read and no investigation records are changed.</p>
    <p className="muted">Drafts stay in this case workspace's memory through case refreshes. Leaving the case, disconnecting or reloading the tab clears them. No server-side report is saved. Limits: 2,000 source rows including tags, 2 MiB, five seconds.</p>
    {!visible && draft && <button className="secondary" onClick={()=>setVisible(true)}>View report draft</button>}
    {visible && <><button className="secondary" onClick={close}>{loading?'Cancel report preparation':'Close report view'}</button>
      {loading && <p role="status">Preparing authorized case report…</p>}
      {error && <p role="alert">{error}</p>}
      {draft && <article>
        <h2 ref={heading} tabIndex={-1}>Report draft — {draft.case.title}</h2>
        <p role="status">{previous?'Previous successful report retained. The timestamp below belongs to that snapshot, not the replacement attempt.':'Report draft ready. Review before sharing.'}</p>
        <p>Case citation: <code>incident:{draft.case.id}</code></p>
        <p>Status: {draft.status} · Schema: {draft.schema_version} · Generated (UTC): <time dateTime={draft.generated_at}>{draft.generated_at}</time></p>
        <p>{draft.scope}. This is a snapshot, not a live view.</p>
        <h3>Case details</h3><dl className="report-fields">{Object.entries(draft.case).map(([key,value])=><div key={key}><dt>{reportLabel(key)}</dt><dd>{reportValue(value)}</dd></div>)}</dl>
        <h3>Investigation summary</h3><p>Counts of recorded information, not threat counts or conclusions.</p>
        <dl className="report-fields">{Object.entries(draft.summary).map(([key,count])=><div key={key}><dt>{key}</dt><dd>{count}</dd></div>)}</dl>
        {draft.sections.map(section=><section key={section.title} aria-label={`Report ${section.title}`}>
          <h3>{section.title}</h3>
          {!section.records.length && <p>No authorized records recorded in this snapshot.</p>}
          {section.records.map(row=><details key={row.citation} className="report-source"><summary>Source citation: {row.citation}</summary>
            {row.evidence_id && <p><a href={`#cases/${id}/evidence/${row.evidence_id}`}>Source evidence {row.evidence_id}</a></p>}
            <dl className="report-fields">{Object.entries(row.fields).map(([key,value])=><div key={key}><dt>{reportLabel(key)}</dt><dd>{reportValue(value)}</dd></div>)}</dl>
          </details>)}
        </section>)}
        <h3>Scope and limitations</h3><ul>{draft.limitations.map(text=><li key={text}>{text}</li>)}</ul>
        <p>Review free text for sensitive information before saving. A local copy cannot be revoked when you disconnect.</p>
        <button onClick={save}>Save draft as text</button>
        {saved && <p role="status">Text download requested. Local saving is not confirmed by the server.</p>}
      </article>}
    </>}
  </section>
}
