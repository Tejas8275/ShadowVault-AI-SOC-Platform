import { test, expect, type Page } from '@playwright/test'

const id='00000000-0000-0000-0000-000000000014'
const evidence='00000000-0000-0000-0000-000000000005'
const base='http://127.0.0.1:8769/api/v2/investigation'
const token='sv_operator_'+'B'.repeat(43), headers={Authorization:`Bearer ${token}`}
const caseUrl=`**/incidents/${id}`
const reportUrl=`**/incidents/${id}/report-draft`
async function connect(page:Page){
  await page.getByLabel('Operator token',{exact:true}).fill(token)
  await page.getByRole('button',{name:'Connect operator',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Browser fixture',exact:true})).toBeVisible()
}
async function open(page:Page){await page.goto(`/#cases/${id}`);await connect(page)}
const indicators=(page:Page)=>page.getByRole('region',{name:'Case Threat Intelligence',exact:true})
const report=(page:Page)=>page.getByRole('region',{name:'Case report',exact:true})
async function fill(page:Page,value='continuity.example'){
  const panel=indicators(page)
  await panel.getByText('Add indicator observation',{exact:true}).click()
  await panel.getByLabel('Indicator evidence ID',{exact:true}).fill(evidence)
  await panel.getByLabel('Indicator kind',{exact:true}).selectOption('domain')
  await panel.getByLabel('Indicator value',{exact:true}).fill(value)
  await panel.getByLabel('Source citation (optional)',{exact:true}).fill('Continuity source')
}
async function createReport(page:Page){
  await report(page).getByRole('button',{name:'Create report draft',exact:true}).click()
  await expect(report(page).getByText('Report draft ready. Review before sharing.',{exact:true})).toBeVisible()
  return await report(page).locator('time').first().getAttribute('datetime')
}
async function refresh(page:Page){
  await page.getByRole('button',{name:'Refresh case',exact:true}).click()
  await expect(page.getByRole('button',{name:'Refresh case',exact:true})).toBeEnabled()
  await expect(page.getByRole('heading',{name:'Browser fixture',exact:true})).toBeVisible()
}

test('uncertain indicator and report survive same-case refresh, failed refresh, save and navigation',async({page})=>{
  await open(page);await fill(page)
  const bodies:string[]=[]
  await page.route(`**/evidence/${evidence}/indicators`,route=>{bodies.push(route.request().postData()!);return route.fulfill({status:503,json:{}})})
  await indicators(page).getByRole('button',{name:'Record indicator',exact:true}).click()
  await expect(indicators(page).getByRole('button',{name:'Retry unchanged indicator'})).toBeVisible()
  const timestamp=await createReport(page)
  let release!:()=>void
  const gate=new Promise<void>(resolve=>{release=resolve})
  await page.route(caseUrl,async route=>{await gate;await route.fulfill({status:503,json:{detail:'PRIVATE'}})})
  await page.getByRole('button',{name:'Refresh case',exact:true}).click()
  await expect(page.getByText('Loading case…',{exact:true})).toBeVisible()
  await expect(indicators(page)).toHaveCount(0)
  // Hidden retained nodes are inert, so neither mouse nor keyboard can submit.
  await expect(page.locator('[inert]')).toHaveCount(1)
  release()
  await expect(page.getByRole('alert')).toContainText('Retained work is hidden')
  await expect(page.getByText('PRIVATE',{exact:true})).toHaveCount(0)
  await page.unroute(caseUrl);await refresh(page)
  await expect(indicators(page).getByLabel('Indicator value',{exact:true})).toHaveValue('continuity.example')
  expect(await report(page).locator('time').first().getAttribute('datetime')).toBe(timestamp)
  await page.getByRole('button',{name:'Save case',exact:true}).click()
  await expect(page.getByRole('button',{name:'Save case',exact:true})).toBeEnabled()
  await expect(indicators(page).getByRole('button',{name:'Retry unchanged indicator'})).toBeVisible()
  await page.getByRole('button',{name:'Case timeline',exact:true}).click()
  await page.getByRole('button',{name:'Case evidence',exact:true}).click()
  await page.evaluate(hash=>{location.hash=hash},`#cases/${id}/evidence/${evidence}`)
  await expect(page.getByRole('heading',{name:'report-fixture.txt',exact:true})).toBeVisible()
  await page.evaluate(hash=>{location.hash=hash},`#cases/${id}`)
  await expect(indicators(page).getByRole('button',{name:'Retry unchanged indicator'})).toBeVisible()
  expect(bodies).toHaveLength(1)
  await indicators(page).getByRole('button',{name:'Retry unchanged indicator'}).click()
  await expect.poll(()=>bodies.length).toBe(2);expect(bodies[1]).toBe(bodies[0])
  expect(await report(page).locator('time').first().getAttribute('datetime')).toBe(timestamp)
})

test('validation input survives refresh; explicit successful submission clears it and retains receipt',async({page})=>{
  await open(page);await fill(page,'invalid domain!')
  await indicators(page).getByRole('button',{name:'Record indicator',exact:true}).click()
  await expect(indicators(page).getByRole('alert')).toContainText('Validation failed')
  await refresh(page)
  await expect(indicators(page).getByLabel('Indicator value',{exact:true})).toHaveValue('invalid domain!')
  await expect(indicators(page).getByLabel('Source citation (optional)',{exact:true})).toHaveValue('Continuity source')
  await indicators(page).getByLabel('Indicator value',{exact:true}).fill('saved.continuity.example')
  await indicators(page).getByRole('button',{name:'Record indicator',exact:true}).click()
  await expect(indicators(page).getByText('Indicator observation recorded.',{exact:true})).toBeVisible()
  await expect(indicators(page).getByLabel('Indicator value',{exact:true})).toHaveValue('')
  await expect(indicators(page).getByLabel('Source citation (optional)',{exact:true})).toHaveValue('')
  await refresh(page)
  await expect(indicators(page).getByRole('region',{name:'Last saved indicator'})).toContainText('saved.continuity.example')
  await expect(indicators(page).getByRole('button',{name:'Retry unchanged indicator'})).toHaveCount(0)
})

for(const status of [503,413])test(`report retains previous snapshot after ${status}; manual retry replaces it`,async({page})=>{
  await open(page);const timestamp=await createReport(page)
  let calls=0
  await page.route(reportUrl,route=>{calls++;return route.fulfill({status,json:{detail:'PRIVATE'}})})
  await report(page).getByRole('button',{name:'Create report draft'}).click()
  await expect(report(page).getByRole('alert')).toContainText(status===413?'complete report limit':'replacement failed')
  await expect(report(page).getByText(/Previous successful report retained/)).toBeVisible()
  expect(await report(page).locator('time').first().getAttribute('datetime')).toBe(timestamp)
  expect(calls).toBe(1)
  await page.unroute(reportUrl)
  const next=await createReport(page);expect(next).not.toBe(timestamp)
  await expect(report(page).getByRole('alert')).toHaveCount(0)
  await expect(report(page).getByText(/Previous successful report retained/)).toHaveCount(0)
})

test('cancelled report replacement retains old draft and ignores delayed response',async({page})=>{
  await open(page);const timestamp=await createReport(page)
  let release!:()=>void, finished!:()=>void, retry=false
  const gate=new Promise<void>(resolve=>{release=resolve})
  const handled=new Promise<void>(resolve=>{finished=resolve})
  await page.route(reportUrl,async route=>{
    if(retry){await route.continue();return}
    await gate
    try {await route.fulfill({status:503,json:{}})}
    catch(error){expect(String(error)).toContain('Route is already handled')}
    finally {finished()}
  })
  await report(page).getByRole('button',{name:'Create report draft'}).click()
  await expect(report(page).getByText('Preparing authorized case report…')).toBeVisible()
  await expect(report(page).getByText(/Previous successful report retained/)).toBeVisible()
  await report(page).getByRole('button',{name:'Cancel report preparation'}).click()
  await expect(report(page).getByRole('button',{name:'Create report draft'})).toBeFocused()
  await report(page).getByRole('button',{name:'View report draft'}).click()
  await expect(report(page).getByRole('alert')).toContainText('cancelled')
  expect(await report(page).locator('time').first().getAttribute('datetime')).toBe(timestamp)
  retry=true
  const next=await createReport(page)
  release();await handled
  await expect(report(page).getByText('Report draft ready. Review before sharing.')).toBeVisible()
  expect(await report(page).locator('time').first().getAttribute('datetime')).toBe(next)
})

for(const status of [403,404])test(`definitive ${status} clears case work and report access denial clears snapshot`,async({page})=>{
  await open(page);await fill(page);await createReport(page)
  await page.route(reportUrl,route=>route.fulfill({status,json:{}}))
  await report(page).getByRole('button',{name:'Create report draft'}).click()
  await expect(report(page).getByRole('alert')).toContainText('retained draft has been cleared')
  await expect(report(page).locator('article')).toHaveCount(0)
  await page.unroute(reportUrl);await createReport(page)
  await page.route(caseUrl,route=>route.fulfill({status,json:{}}))
  await page.getByRole('button',{name:'Refresh case',exact:true}).click()
  await expect(page.getByRole('alert')).toContainText('Retained work has been cleared')
  await expect(page.locator('[inert]')).toHaveCount(0)
  await page.unroute(caseUrl);await refresh(page)
  await expect(report(page).locator('article')).toHaveCount(0)
  await indicators(page).getByText('Add indicator observation',{exact:true}).click()
  await expect(indicators(page).getByLabel('Indicator value',{exact:true})).toHaveValue('')
})

test('switching cases, disconnect and tab reload clear private transient state',async({page})=>{
  await open(page);await fill(page);await createReport(page)
  await page.route(`**/evidence/${evidence}/indicators`,route=>route.fulfill({status:503,json:{}}))
  await indicators(page).getByRole('button',{name:'Record indicator',exact:true}).click()
  await expect(indicators(page).getByRole('button',{name:'Retry unchanged indicator'})).toBeVisible()
  await page.route(reportUrl,route=>route.fulfill({status:503,json:{}}))
  await report(page).getByRole('button',{name:'Create report draft'}).click()
  await expect(report(page).getByRole('alert')).toContainText('replacement failed')
  const response=await page.request.post(`${base}/incidents`,{headers,data:{title:'Continuity isolated case',description:'',severity:'low'}})
  expect(response.status()).toBe(201);const other=await response.json()
  await page.evaluate(hash=>{location.hash=hash},`#cases/${other.id}`)
  await expect(page.getByRole('heading',{name:'Continuity isolated case',exact:true})).toBeVisible()
  await expect(report(page).locator('article')).toHaveCount(0)
  await indicators(page).getByText('Add indicator observation',{exact:true}).click()
  await expect(indicators(page).getByLabel('Indicator value',{exact:true})).toHaveValue('')
  await expect(indicators(page).getByRole('alert')).toHaveCount(0)
  await expect(report(page).getByRole('alert')).toHaveCount(0)
  await expect(indicators(page).getByRole('button',{name:'Retry unchanged indicator'})).toHaveCount(0)
  await page.unroute(reportUrl)
  await page.evaluate(hash=>{location.hash=hash},`#cases/${id}`)
  await expect(page.getByRole('heading',{name:'Browser fixture',exact:true})).toBeVisible()
  await expect(report(page).locator('article')).toHaveCount(0)
  await fill(page);await createReport(page)
  await page.getByRole('button',{name:'Disconnect operator'}).click();await connect(page)
  await expect(report(page).locator('article')).toHaveCount(0)
  await fill(page);await createReport(page)
  await page.reload();await connect(page)
  await expect(report(page).locator('article')).toHaveCount(0)
  await indicators(page).getByText('Add indicator observation',{exact:true}).click()
  await expect(indicators(page).getByLabel('Indicator value',{exact:true})).toHaveValue('')
  expect(await page.evaluate(()=>({local:localStorage.length,session:sessionStorage.length}))).toEqual({local:0,session:0})
})
