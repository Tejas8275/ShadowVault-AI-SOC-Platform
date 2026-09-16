import test from 'node:test'
import assert from 'node:assert/strict'
import { createInvestigationService } from '../src/features/evidence/service.ts'

test('case intelligence opts into existing detail and keeps credentials in headers',async()=>{
 const calls=[]
 const api=createInvestigationService('http://localhost/api/v2/investigation',()=>{},async(url,options)=>{calls.push({url,options});return Response.json({id:'case',intelligence:{evidence_count:0}})})
 await api.connect('sv_operator_fixture')
 const result=await api.caseIntelligence('case')
 assert.equal(result.intelligence.evidence_count,0)
 assert.equal(calls[1].url,'http://localhost/api/v2/investigation/incidents/case?include_intelligence=true')
 assert.equal(calls[1].options.headers.Authorization,'Bearer sv_operator_fixture')
 api.disconnect();await assert.rejects(api.caseIntelligence('case'),{status:401})
})

test('case intelligence errors never become zero counts or expose backend details',async()=>{
 let calls=0
 const api=createInvestigationService('http://localhost/api',()=>{},async()=>++calls===1?Response.json({}):Response.json({detail:'secret'},{status:503}))
 await api.connect('sv_operator_fixture')
 await assert.rejects(api.caseIntelligence('case'),error=>error.status===503&&!error.message.includes('secret'))
 assert.equal(calls,2)
})
