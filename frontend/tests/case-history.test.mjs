import test from 'node:test'
import assert from 'node:assert/strict'
import { createInvestigationService } from '../src/features/evidence/service.ts'

test('history omits initial revision but preserves zero and uses shared token',async()=>{
  const calls=[]
  const api=createInvestigationService('http://localhost/api',()=>{},async(url,options)=>{calls.push({url,options});return Response.json({items:[]})})
  await api.connect('sv_operator_fixture');await api.caseHistory('id');await api.caseHistory('id',0)
  assert.equal(new URL(calls[1].url).searchParams.has('after_revision'),false)
  assert.equal(new URL(calls[2].url).searchParams.get('after_revision'),'0')
  assert.equal(calls[2].options.headers.Authorization,'Bearer sv_operator_fixture')
  assert.equal(calls[2].options.cache,'no-store')
})

test('history failures are sanitized and 401 clears shared connection',async()=>{
  let status=503,calls=0,expired=0
  const api=createInvestigationService('http://localhost/api',()=>expired++,async()=>++calls===1?Response.json({}):Response.json({detail:'private'},{status}))
  await api.connect('sv_operator_fixture')
  await assert.rejects(api.caseHistory('id'),e=>e.status===503&&!e.message.includes('private'))
  assert.equal(calls,2);status=401
  await assert.rejects(api.caseHistory('id'),{status:401});assert.equal(expired,1)
  await assert.rejects(api.caseDetail('id'),{status:401})
})
