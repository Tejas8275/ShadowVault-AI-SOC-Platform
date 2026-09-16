import test from 'node:test'
import assert from 'node:assert/strict'
import { createInvestigationService } from '../src/features/evidence/service.ts'

test('indicator list and registration reuse secure service and preserve retry submission',async()=>{
 const calls=[]
 const api=createInvestigationService('http://localhost/api/v2/investigation',()=>{},async(url,options)=>{calls.push({url,options});return Response.json({items:[],next_cursor:null})})
 await api.connect('sv_operator_fixture')
 await api.indicators('case','cursor+/=')
 const payload={kind:'domain',source_kind:'manual',raw_value:'Example.COM',submission_id:'unchanged'}
 await api.addIndicator('evidence',payload);await api.addIndicator('evidence',payload)
 assert.equal(new URL(calls[1].url).searchParams.get('cursor'),'cursor+/=')
 assert.equal(calls[2].options.body,calls[3].options.body)
 assert.equal(calls[2].options.headers.Authorization,'Bearer sv_operator_fixture')
 assert.equal(calls[2].options.cache,'no-store')
 assert.equal(calls[2].options.method,'POST')
 api.disconnect();await assert.rejects(api.indicators('case'),{status:401})
})
test('indicator conflicts never automatically retry or reveal private server messages',async()=>{
 let calls=0
 const api=createInvestigationService('http://localhost/api',()=>{},async()=>++calls===1?Response.json({}):Response.json({detail:'private'},{status:409}))
 await api.connect('sv_operator_fixture')
 await assert.rejects(api.addIndicator('evidence',{kind:'ip',source_kind:'manual',raw_value:'1.2.3.4',submission_id:'x'}),e=>e.status===409&&!e.message.includes('private'))
 assert.equal(calls,2)
})

test('indicator filters reuse server contracts including case-bound observation lookup',async()=>{
 const urls=[]
 const api=createInvestigationService('http://localhost/api',()=>{},async(url)=>{urls.push(url);return Response.json({items:[]})})
 await api.connect('sv_operator_fixture')
 await api.indicators('case',undefined,undefined,{kind:'domain',value:' EXAMPLE.COM ',evidence_id:'source',observation_id:'record'})
 const url=new URL(urls[1]);assert.equal(url.pathname,'/api/incidents/case/indicators')
 assert.equal(url.searchParams.get('kind'),'domain');assert.equal(url.searchParams.get('value'),'EXAMPLE.COM')
 assert.equal(url.searchParams.get('evidence_id'),'source');assert.equal(url.searchParams.get('observation_id'),'record')
})
