import test from 'node:test'
import assert from 'node:assert/strict'
import { createInvestigationService } from '../src/features/evidence/service.ts'
const id='00000000-0000-0000-0000-000000000014'
const result={case_id:id,schema_version:1,kind:'ai_selected_metadata',prompt_version:'metadata-selection-v1',
  sources:[{citation:`incident:${id}`,fields:{title:'Recorded title'}}],limitations:['Selection only']}

test('briefing uses existing bearer authorization and fixed explicit computation body',async()=>{
  const calls=[]
  const api=createInvestigationService('http://localhost/api',()=>{},async(url,options)=>{calls.push({url,options});return Response.json(result)})
  await api.connect('sv_operator_test');await api.aiBriefing(id)
  assert.equal(calls[1].url,`http://localhost/api/incidents/${id}/ai-briefing`)
  assert.equal(calls[1].options.method,'POST')
  assert.deepEqual(JSON.parse(calls[1].options.body),{schema_version:1})
  assert.equal(calls[1].options.headers.Authorization,'Bearer sv_operator_test')
  assert.equal(calls[1].options.cache,'no-store');assert.equal(calls[1].options.credentials,'omit')
  assert.equal(calls[1].options.redirect,'error')
})

test('briefing unavailable, conflicts and malformed responses fail safely without retries',async()=>{
  for(const status of [401,404,409,413,429,501,503,504]){
    let calls=0
    const api=createInvestigationService('http://localhost/api',()=>{},async()=>++calls===1?Response.json({}):Response.json({detail:'PRIVATE'},{status}))
    await api.connect('sv_operator_test')
    await assert.rejects(api.aiBriefing(id),error=>error.status===status&&!error.message.includes('PRIVATE'))
    assert.equal(calls,2)
  }
})

test('briefing rejects wrong case, unsupported schema and unresolved citation shape',async()=>{
  for(const body of [{...result,case_id:'foreign'},{...result,schema_version:2},{...result,sources:[{citation:'invented',fields:{}}]}]){
    const api=createInvestigationService('http://localhost/api',()=>{},async()=>Response.json(body))
    await api.connect('sv_operator_test');await assert.rejects(api.aiBriefing(id),/scope or schema/)
  }
})

test('disconnect discards a delayed briefing response',async()=>{
  let calls=0,release
  const api=createInvestigationService('http://localhost/api',()=>{},async()=>{
    if(++calls>1)await new Promise(resolve=>{release=resolve})
    return Response.json(result)
  })
  await api.connect('sv_operator_test');const pending=api.aiBriefing(id)
  api.disconnect();release();await assert.rejects(pending,{name:'AbortError'})
})

test('usage denial makes one request and a subsequent attempt is explicit',async()=>{
  let calls=0
  const api=createInvestigationService('http://localhost/api',()=>{},async()=>{
    calls++
    return calls===2?Response.json({detail:'PRIVATE quota'},{status:429}):Response.json(result)
  })
  await api.connect('sv_operator_test')
  await assert.rejects(api.aiBriefing(id),error=>error.status===429&&!error.message.includes('PRIVATE'))
  assert.equal(calls,2)
  await api.aiBriefing(id)
  assert.equal(calls,3)
})

import { reviewGroups, reviewDestination, sourceEvidenceHref } from '../src/features/cases/briefing.ts'
const evidenceId='00000000-0000-0000-0000-000000000005'
const source=(kind,fields={},selection='model')=>({citation:`${kind}:${evidenceId}`,section:'Untrusted label',fields,selection,evidence_id:evidenceId})
test('review groups only returned metadata and retains complete correction context in every category',()=>{
  const rows=[source('evidence'),source('indicator',{superseded_by_id:id}),source('indicator',{supersedes_id:evidenceId},'correction_context'),source('timeline')]
  const before=JSON.stringify(rows)
  const groups=reviewGroups(rows,'evidence')
  assert.deepEqual(groups.map(g=>g.kind),['evidence','indicator'])
  assert.equal(groups[1].sources.length,2)
  assert.equal(groups[0].label,'Evidence records')
  assert.equal(JSON.stringify(rows),before)
  assert.deepEqual(reviewGroups([source('evidence')],'history'),[])
})
test('review destinations use fixed case sections and reject foreign case and unknown citations',()=>{
  assert.equal(reviewDestination({...source('incident'),citation:`incident:${id}`},id),'case')
  assert.equal(reviewDestination(source('incident'),id),undefined)
  for(const [kind,target] of [['timeline','timeline'],['indicator','indicators'],['history','history'],['custody','report']])assert.equal(reviewDestination(source(kind),id),target)
  assert.equal(reviewDestination({...source('timeline'),citation:'https://evil.example'},id),undefined)
  assert.equal(reviewDestination({...source('timeline'),citation:'timeline:../../other'},id),undefined)
})
test('review evidence links are local case routes and never interpret provider text or credentials',()=>{
  assert.equal(sourceEvidenceHref(source('evidence'),id),`#cases/${id}/evidence/${evidenceId}`)
  assert.equal(sourceEvidenceHref({...source('evidence'),evidence_id:id},id),undefined)
  assert.equal(sourceEvidenceHref({...source('timeline'),evidence_id:'https://evil.example'},id),undefined)
  assert.equal(sourceEvidenceHref(source('evidence'),'../../other'),undefined)
  assert.equal(sourceEvidenceHref(source('incident'),id),undefined)
})
