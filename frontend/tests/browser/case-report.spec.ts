import { test, expect, type Page } from '@playwright/test'
const id='00000000-0000-0000-0000-000000000014', eid='00000000-0000-0000-0000-000000000001'
const base='http://127.0.0.1:8769/api/v2/investigation'
const headers={Authorization:'Bearer sv_operator_'+'B'.repeat(43)}
async function open(page:Page){
 await page.goto('/#cases');await page.getByLabel('Operator token',{exact:true}).fill('sv_operator_'+'B'.repeat(43))
 await page.getByRole('button',{name:'Connect operator',exact:true}).click()
 await page.getByRole('link',{name:'Browser fixture',exact:true}).click()
 return page.getByRole('region',{name:'Case report',exact:true})
}

test('create and view real report with evidence timeline indicators notes and citations',async({page})=>{
 // Dedicated source keeps every pre-existing fixture's initial custody state unchanged.
 const source='00000000-0000-0000-0000-000000000005'
 const indicator=await page.request.post(`${base}/evidence/${source}/indicators`,{headers,data:{kind:'domain',raw_value:'report.example',source_locator:'Investigator citation <b>plain text</b>',submission_id:crypto.randomUUID()}})
 expect(indicator.status()).toBe(201);const recorded=await indicator.json()
 const event=await page.request.post(`${base}/evidence/${source}/timeline-events`,{headers,data:{title:'Report observation fixture',source:'Investigator source',source_locator:'Recorded line 7',occurred_at:'2026-01-01T12:00:00+05:30',submission_id:crypto.randomUUID()}})
 expect(event.status()).toBe(201)
 const evidence=await (await page.request.get(`${base}/evidence/${source}`,{headers})).json()
 const note=await page.request.post(`${base}/evidence/${source}/notes`,{headers,data:{body:'Report investigator note',expected_revision:evidence.metadata_revision}})
 expect(note.status()).toBe(201)
 const panel=await open(page)
 const response=page.waitForResponse(r=>r.url().endsWith('/report-draft'))
 await panel.getByRole('button',{name:'Create report draft',exact:true}).click()
 const draft=await (await response).json()
 await expect(panel.getByRole('heading',{name:'Report draft — Browser fixture',exact:true})).toBeFocused()
 await expect(panel.getByText(`incident:${id}`,{exact:true})).toBeVisible()
 await expect(panel.getByRole('region',{name:'Report Evidence records'})).toContainText('evidence:'+eid)
 const indicators=panel.getByRole('region',{name:'Report Recorded indicators'})
 await indicators.getByText('Source citation: indicator:'+recorded.id,{exact:true}).click()
 await expect(indicators).toContainText('report.example')
 await expect(indicators).toContainText('Investigator citation <b>plain text</b>')
 expect(await indicators.locator('b').count()).toBe(0)
 await expect(panel.getByRole('region',{name:'Report Timeline observations'})).toContainText('timeline:'+(await event.json()).id)
 await expect(panel.getByRole('region',{name:'Report Investigator notes'})).toContainText('note:'+(await note.json()).note.id)
 expect(draft.case.id).toBe(id)
 const download=page.waitForEvent('download');await panel.getByRole('button',{name:'Save draft as text'}).click()
 expect((await download).suggestedFilename()).toBe(`case-${id}-draft.txt`)
 await page.setViewportSize({width:390,height:844})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 await panel.getByRole('button',{name:'Close report view'}).click()
 await expect(panel.getByRole('button',{name:'Create report draft'})).toBeFocused()
 await panel.getByRole('button',{name:'View report draft'}).click()
 await expect(panel.getByText('Report draft ready. Review before sharing.',{exact:true})).toBeVisible()
})

test('report loading error explicit retry and authorization expiry',async({page})=>{
 let mode='error', calls=0
 await page.route('**/incidents/'+id+'/report-draft',async route=>{
  calls++;await new Promise(r=>setTimeout(r,300))
  if(mode==='ok')await route.continue()
  else await route.fulfill({status:mode==='expired'?401:503,json:{detail:'private internal data'}})
 })
 const panel=await open(page)
 await panel.getByRole('button',{name:'Create report draft'}).click()
 await expect(panel.getByRole('status')).toContainText('Preparing')
 await expect(panel.getByRole('alert')).toContainText('Report unavailable')
 await expect(panel).not.toContainText('private internal');expect(calls).toBe(1)
 mode='ok';await panel.getByRole('button',{name:'Create report draft'}).click()
 await expect(panel.getByText('Report draft ready. Review before sharing.')).toBeVisible()
 mode='expired';await panel.getByRole('button',{name:'Create report draft'}).click()
 await expect(page.getByLabel('Operator token',{exact:true})).toBeVisible()
 await expect(page.getByRole('region',{name:'Case report',exact:true})).toHaveCount(0)
})

test('wrong-case report response is rejected and unavailable case API denies access',async({page})=>{
 const missing='00000000-0000-0000-0000-000000000099'
 expect((await page.request.get(`${base}/incidents/${missing}/report-draft`,{headers})).status()).toBe(404)
 await page.route('**/incidents/'+id+'/report-draft',route=>route.fulfill({json:{case:{id:missing,title:'PRIVATE OTHER CASE'},status:'draft',schema_version:1}}))
 const panel=await open(page);await panel.getByRole('button',{name:'Create report draft'}).click()
 await expect(panel.getByRole('alert')).toContainText('Report unavailable')
 await expect(panel).not.toContainText('PRIVATE OTHER CASE')
})

test('report view preserves unresolved indicator retry identity',async({page})=>{
 const report=await open(page), panel=page.getByRole('region',{name:'Case Threat Intelligence'})
 await panel.getByText('Add indicator observation',{exact:true}).click()
 await panel.getByLabel('Indicator evidence ID',{exact:true}).fill(eid)
 await panel.getByLabel('Indicator kind',{exact:true}).selectOption('domain')
 await panel.getByLabel('Indicator value',{exact:true}).fill('pending.report.example')
 const bodies:string[]=[]
 await page.route('**/evidence/'+eid+'/indicators',route=>{bodies.push(route.request().postData()!);return route.fulfill({status:503,json:{}})})
 await panel.getByRole('button',{name:'Record indicator',exact:true}).click()
 await expect(panel.getByRole('button',{name:'Retry unchanged indicator'})).toBeVisible()
 await report.getByRole('button',{name:'Create report draft'}).click()
 await expect(report.getByText('Report draft ready. Review before sharing.')).toBeVisible()
 await report.getByRole('button',{name:'Close report view'}).click()
 await panel.getByRole('button',{name:'Retry unchanged indicator'}).click()
 await expect.poll(()=>bodies.length).toBe(2);expect(bodies[0]).toBe(bodies[1])
})
