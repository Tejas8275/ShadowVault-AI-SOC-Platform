import test from 'node:test'
import assert from 'node:assert/strict'
import { createInvestigationService } from '../src/features/evidence/service.ts'
import { reportText } from '../src/features/cases/report.ts'

test('report read uses existing credential boundary and exact case endpoint',async()=>{
 const calls=[]
 const api=createInvestigationService('http://localhost/api',()=>{},async(url,options)=>{
  calls.push({url,options});return Response.json({case:{id:'case'},status:'draft',schema_version:1})
 })
 await api.connect('sv_operator_fixture');await api.caseReport('case')
 assert.equal(calls[1].url,'http://localhost/api/incidents/case/report-draft')
 assert.equal(calls[1].options.method,undefined)
 assert.equal(calls[1].options.headers.Authorization,'Bearer sv_operator_fixture')
 assert.equal(calls[1].options.cache,'no-store')
 api.disconnect();await assert.rejects(api.caseReport('case'),{status:401})
})
test('report errors are sanitized and reads are not automatically retried',async()=>{
 let calls=0
 const api=createInvestigationService('http://localhost/api',()=>{},async()=>++calls===1?Response.json({}):Response.json({detail:'private storage path'},{status:503}))
 await api.connect('sv_operator_fixture')
 await assert.rejects(api.caseReport('case'),e=>e.status===503&&!e.message.includes('private'))
 assert.equal(calls,2)
})
test('report client rejects a mismatched case or unsupported version',async()=>{
 let body={case:{id:'foreign'},status:'draft',schema_version:1}
 const api=createInvestigationService('http://localhost/api',()=>{},async()=>Response.json(body))
 await api.connect('sv_operator_fixture');await assert.rejects(api.caseReport('own'),/scope or version/)
 body={case:{id:'own'},status:'draft',schema_version:2};await assert.rejects(api.caseReport('own'),/scope or version/)
})
test('plain text draft contains stored citations and limitations without interpreting text',()=>{
 const result=reportText({case:{id:'own',title:'<script>source text</script>'},generated_at:'2026-01-01T00:00:00Z',scope:'Authorized snapshot',summary:{Evidence:1},sections:[{title:'Notes',records:[{citation:'note:1',evidence_id:'2',fields:{body:'https://example.test/citation',unknown:null}}]}],limitations:['No verdicts']})
 assert.match(result,/Case citation: incident:own/);assert.match(result,/Source citation: note:1/)
 assert.match(result,/Source evidence: evidence:2/);assert.match(result,/Not recorded/)
 assert.match(result,/<script>source text<\/script>/);assert.match(result,/No verdicts/)
})
