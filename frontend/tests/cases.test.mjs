import test from 'node:test'
import assert from 'node:assert/strict'
import { createInvestigationService } from '../src/features/evidence/service.ts'
import { transitions } from '../src/features/cases/contracts.ts'

test('case reads accept historical null, current and absent update timestamps',async()=>{
  for(const record of [{id:'id',updated_at:null},{id:'id',updated_at:'2030-01-01T00:00:00Z'},{id:'id'}]){
    const api=createInvestigationService('http://localhost/api',()=>{},async()=>Response.json(record))
    await api.connect('sv_operator_fixture')
    assert.deepEqual(await api.caseDetail('id'),record)
  }
})

test('case methods share token boundary and preserve revision on explicit updates', async()=>{
  const calls=[]
  const api=createInvestigationService('http://localhost/api/v2/investigation',()=>{},async(url,options)=>{calls.push({url,options});return Response.json({})})
  await api.connect('sv_operator_fixture')
  await api.cases({q:' %_ ',status:'open',severity:' high '},'next+/=')
  await api.caseDetail('id')
  await api.createCase({title:'Case',description:'',severity:'medium'})
  await api.updateCase('id',{title:'Case',description:'updated',severity:'high',status:'investigating',expected_revision:7})
  assert.equal(new URL(calls[1].url).searchParams.get('cursor'),'next+/=')
  assert.equal(new URL(calls[1].url).searchParams.get('q'),'%_')
  assert.equal(new URL(calls[1].url).searchParams.get('severity'),'high')
  assert.equal(calls[3].options.method,'POST');assert.equal(calls[4].options.method,'PATCH')
  assert.equal(JSON.parse(calls[4].options.body).expected_revision,7)
  assert.equal(calls[4].options.headers.Authorization,'Bearer sv_operator_fixture')
  api.disconnect();await assert.rejects(api.caseDetail('id'),{status:401})
})

test('case writes never retry conflicts, validation errors or uncertain failures',async()=>{
  for(const status of [409,422,503]){
    let calls=0
    const api=createInvestigationService('http://localhost/api',()=>{},async()=>++calls===1?Response.json({}):Response.json({detail:'private'},{status}))
    await api.connect('sv_operator_fixture')
    await assert.rejects(api.updateCase('id',{title:'x',description:'',severity:'medium',status:'closed',expected_revision:1}),error=>error.status===status&&!error.message.includes('private'))
    assert.equal(calls,2)
  }
})

test('case 401 clears the shared evidence and timeline connection',async()=>{
  let calls=0,expired=0
  const api=createInvestigationService('http://localhost/api',()=>expired++,async()=>++calls===1?Response.json({}):Response.json({},{status:401}))
  await api.connect('sv_operator_fixture');await assert.rejects(api.caseDetail('id'),{status:401})
  assert.equal(expired,1);await assert.rejects(api.timelineDetails('event'),{status:401});await assert.rejects(api.details('evidence'),{status:401})
})

test('case lifecycle options are explicit and do not allow skipping investigation',()=>{
  assert.deepEqual(transitions.open,['open','investigating'])
  assert.deepEqual(transitions.investigating,['investigating','closed'])
  assert.deepEqual(transitions.closed,['closed','investigating'])
})
