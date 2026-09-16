import { test, expect, type Page } from '@playwright/test'
const caseId='00000000-0000-0000-0000-000000000014', evidenceId='00000000-0000-0000-0000-000000000001'
async function open(page:Page){
 await page.goto('/#cases');await page.getByLabel('Operator token',{exact:true}).fill('sv_operator_'+'B'.repeat(43))
 await page.getByRole('button',{name:'Connect operator',exact:true}).click()
 await page.getByRole('link',{name:'Browser fixture',exact:true}).click()
 const panel=page.getByRole('region',{name:'Case Threat Intelligence'})
 await panel.getByText('Add indicator observation',{exact:true}).click()
 await panel.getByLabel('Indicator evidence ID',{exact:true}).fill(evidenceId)
 return panel
}
test('real manual indicators render metadata evidence links and hash pivot',async({page})=>{
 const panel=await open(page)
 for(const [kind,value] of [['domain','Example.COM.'],['ip','2001:db8::1'],['filename','Sample.TXT'],['sha256','a'.repeat(64)]]){
  await panel.getByLabel('Indicator kind',{exact:true}).selectOption(kind)
  await panel.getByLabel('Indicator value',{exact:true}).fill(value)
  await panel.getByRole('button',{name:'Record indicator',exact:true}).click()
  await expect(panel.getByText('Indicator observation recorded.',{exact:true})).toBeVisible()
 }
 await expect(panel.getByRole('heading',{name:'domain: example.com',exact:true})).toBeVisible()
 await expect(panel.getByRole('heading',{name:'ip: 2001:db8::1',exact:true})).toBeVisible()
 await expect(panel.getByRole('link',{name:'Source evidence '+evidenceId}).first()).toHaveAttribute('href',`#cases/${caseId}/evidence/${evidenceId}`)
 await panel.getByRole('button',{name:'Find matching SHA-256 in this case'}).first().click()
 await expect(page.getByLabel('SHA-256',{exact:true})).toHaveValue('a'.repeat(64))
 expect(await panel.locator('a[href^="http"]').count()).toBe(0)
 await page.setViewportSize({width:390,height:844})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
})
test('indicator uncertain save retries identical payload and handles corrections',async({page})=>{
 const panel=await open(page);let fail=true;const bodies:string[]=[]
 await page.route('**/evidence/'+evidenceId+'/indicators',async route=>{
  bodies.push(route.request().postData()!);if(fail){fail=false;await route.fulfill({status:503,json:{}})}else await route.continue()
 })
 await panel.getByLabel('Indicator kind',{exact:true}).selectOption('domain')
 await panel.getByLabel('Indicator value',{exact:true}).fill('retry.example')
 await panel.getByRole('button',{name:'Record indicator',exact:true}).click()
 await expect(panel.getByRole('alert')).toContainText('Save not confirmed')
 await expect(panel.getByLabel('Indicator value',{exact:true})).toBeDisabled()
 const response=page.waitForResponse(r=>r.url().endsWith('/indicators')&&r.request().method()==='POST'&&r.status()===201)
 await panel.getByRole('button',{name:'Retry unchanged indicator'}).click()
 const created=await (await response).json();expect(bodies[0]).toBe(bodies[1])
 await panel.getByLabel('Corrects observation ID (optional)',{exact:true}).fill(created.id)
 await panel.getByLabel('Indicator value',{exact:true}).fill('corrected.example')
 await panel.getByRole('button',{name:'Record indicator',exact:true}).click()
 await expect(panel.getByText('Corrects observation: '+created.id+'. The original record remains preserved.',{exact:true})).toBeVisible()
})
test('indicator unavailable empty pagination and authorization expiry states',async({page})=>{
 let mode='error'
 await page.route('**/incidents/'+caseId+'/indicators?*',async route=>{
  if(mode==='error')await route.fulfill({status:503,json:{detail:'private'}})
  else if(mode==='expired')await route.fulfill({status:401,json:{}})
  else await route.fulfill({json:{items:[],next_cursor:mode==='next'?'testcursor':null}})
 })
 const panel=await open(page)
 await expect(panel.getByRole('alert')).toContainText('Indicators unavailable')
 mode='next';await panel.getByRole('button',{name:'Refresh indicators'}).click()
 await expect(panel.getByText('No indicator observations on this page.')).toBeVisible()
 await panel.getByRole('button',{name:'Next indicators'}).click()
 await expect(panel.getByRole('button',{name:'First indicator page'})).toBeEnabled()
 mode='expired';await panel.getByRole('button',{name:'Refresh indicators'}).click()
 await expect(page.getByRole('heading',{name:'Connect operator',exact:true})).toBeVisible()
})
