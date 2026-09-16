import { test, expect, type Page } from '@playwright/test'
const caseId='00000000-0000-0000-0000-000000000014'
async function connect(page:Page){
  await page.goto('/#cases')
  await page.getByLabel('Operator token',{exact:true}).fill('sv_operator_'+'B'.repeat(43))
  await page.getByRole('button',{name:'Connect operator',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Cases',exact:true})).toBeVisible()
}

test('real case creation revision-safe lifecycle and reload',async({page})=>{
  await connect(page);await page.getByRole('button',{name:'New case',exact:true}).click()
  await page.getByLabel('Case title',{exact:true}).fill('Case workflow fixture')
  await page.getByLabel('Case description',{exact:true}).fill('<script>reported text</script>')
  const createdResponse=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/incidents'))
  await page.getByRole('button',{name:'Create case',exact:true}).click()
  const created=await (await createdResponse).json()
  expect(created.updated_at).toBe(created.created_at)
  await expect(page.getByRole('heading',{name:'Case workflow fixture',exact:true})).toBeVisible()
  await expect(page.getByLabel('Case status',{exact:true})).toHaveValue('open')
  await page.getByLabel('Case status',{exact:true}).selectOption('investigating')
  const updatedResponse=page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().endsWith('/incidents/'+created.id))
  await page.getByRole('button',{name:'Save case',exact:true}).click()
  const updated=await (await updatedResponse).json()
  expect(updated.created_at).toBe(created.created_at)
  expect(Date.parse(updated.updated_at)).toBeGreaterThanOrEqual(Date.parse(created.updated_at))
  await expect(page.getByText(/Case ID:.*Revision: 1/)).toBeVisible()
  await expect(page.getByText(`Last updated: ${new Date(updated.updated_at).toISOString()} (UTC)`,{exact:true})).toBeVisible()
  await page.getByLabel('Case status',{exact:true}).selectOption('closed')
  await page.getByRole('button',{name:'Save case',exact:true}).click()
  await expect(page.getByText(/Case ID:.*Revision: 2/)).toBeVisible()
  await page.getByLabel('Case status',{exact:true}).selectOption('investigating')
  await page.getByRole('button',{name:'Save case',exact:true}).click()
  await expect(page.getByText(/Case ID:.*Revision: 3/)).toBeVisible()
  await page.reload();await expect(page.getByRole('heading',{name:'Connect operator',exact:true})).toBeVisible()
})

test('case workspace reuses scoped evidence custody and timeline without widening filters',async({page})=>{
  await connect(page);await page.getByRole('link',{name:'Browser fixture',exact:true}).click()
  await expect(page.getByLabel('Incident ID',{exact:true})).toBeDisabled()
  await page.getByRole('button',{name:'Clear filters',exact:true}).click()
  await expect(page.getByLabel('Incident ID',{exact:true})).toHaveValue(caseId)
  await page.getByRole('link',{name:'retrieval-fixture.bin',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Custody history',exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'Prepare download',exact:true})).toBeVisible()
  await page.getByRole('link',{name:'Back to evidence results',exact:true}).click()
  await page.getByRole('button',{name:'Case timeline',exact:true}).click()
  await expect(page.getByLabel('Timeline incident ID',{exact:true})).toBeDisabled()
  await expect(page.getByRole('link',{name:'Legacy timeline fixture',exact:true})).toBeVisible()
})

test('case conflict requires explicit reload and never retries the write',async({page})=>{
  await connect(page);await page.getByRole('link',{name:'Browser fixture',exact:true}).click()
  let writes=0
  await page.route('**/incidents/'+caseId,async route=>{
    if(route.request().method()==='PATCH'){writes++;await route.fulfill({status:409,json:{}})}else await route.continue()
  })
  await page.getByLabel('Case title',{exact:true}).fill('Preserved case draft')
  await page.getByRole('button',{name:'Save case',exact:true}).click()
  await expect(page.getByRole('alert')).toContainText('Reload')
  await expect(page.getByLabel('Case title',{exact:true})).toHaveValue('Preserved case draft')
  await expect(page.getByRole('button',{name:'Save case',exact:true})).toBeDisabled();expect(writes).toBe(1)
  await page.getByRole('button',{name:'Reload case and discard draft',exact:true}).click()
  await expect(page.getByLabel('Case title',{exact:true})).toHaveValue('Browser fixture')
})

test('case auth failure clears shared workspace and mobile navigation remains accessible',async({page})=>{
  await page.setViewportSize({width:390,height:844});await connect(page)
  await page.getByRole('link',{name:'Browser fixture',exact:true}).click()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await expect(page.locator('#main-content')).toBeFocused()
  await page.route('**/incidents/'+caseId,route=>route.fulfill({status:401,json:{}}))
  await page.getByRole('button',{name:'Refresh case',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Connect operator',exact:true})).toBeVisible()
  expect(await page.evaluate(()=>localStorage.length+sessionStorage.length)).toBe(0)
})

test('case list search preserves query scope',async({page})=>{
  await connect(page)
  await page.getByLabel('Case search',{exact:true}).fill('no matching case')
  await page.getByRole('button',{name:'Search cases',exact:true}).click()
  await expect(page.getByText('No cases match these filters.')).toBeVisible()
  await page.getByLabel('Case search',{exact:true}).fill('Browser')
  await page.getByRole('button',{name:'Search cases',exact:true}).click()
  await expect(page.getByRole('link',{name:'Browser fixture',exact:true})).toBeVisible()
  await page.getByLabel('Filter case severity',{exact:true}).selectOption('critical')
  await page.getByRole('button',{name:'Search cases',exact:true}).click()
  await expect(page.getByText('No cases match these filters.')).toBeVisible()
  await page.getByLabel('Filter case severity',{exact:true}).selectOption('')
  await page.getByRole('button',{name:'Search cases',exact:true}).click()
  await expect(page.getByRole('link',{name:'Browser fixture',exact:true})).toBeVisible()
  expect(page.url()).not.toContain('Browser')
})

for(const mode of ['null','absent']){
  test(`case update time is unknown when ${mode}`,async({page})=>{
    await connect(page)
    await page.route('**/incidents/'+caseId,async route=>{
      const response=await route.fetch();const record=await response.json()
      if(mode==='null')record.updated_at=null;else delete record.updated_at
      await route.fulfill({response,json:record})
    })
    await page.getByRole('link',{name:'Browser fixture',exact:true}).click()
    await expect(page.getByText('Last updated: Unknown',{exact:true})).toBeVisible()
    await expect(page.getByText(/Owner:.*Created:/)).toBeVisible()
  })
}

test('severity search resets cursor history and retains combined filters',async({page})=>{
  await connect(page)
  const queries:URLSearchParams[]=[]
  await page.route('**/incidents?*',async route=>{
    const query=new URL(route.request().url()).searchParams;queries.push(query)
    await route.fulfill({json:{items:[],total:2,next_cursor:query.has('cursor')?null:'next-page'}})
  })
  await page.getByRole('button',{name:'Refresh cases',exact:true}).click()
  await page.getByRole('button',{name:'Next cases',exact:true}).click()
  await expect.poll(()=>queries.at(-1)?.get('cursor')).toBe('next-page')
  await expect(page.getByRole('button',{name:'Previous cases',exact:true})).toBeEnabled()
  await page.getByLabel('Case search',{exact:true}).fill('scope')
  await page.getByRole('combobox',{name:'Filter case status',exact:true}).selectOption('open')
  await page.getByLabel('Filter case severity',{exact:true}).selectOption('high')
  await page.getByRole('button',{name:'Search cases',exact:true}).click()
  await expect.poll(()=>queries.at(-1)?.get('severity')).toBe('high')
  expect(queries.at(-1)?.has('cursor')).toBe(false)
  expect(queries.at(-1)?.get('q')).toBe('scope');expect(queries.at(-1)?.get('status')).toBe('open')
  await expect(page.getByRole('button',{name:'Previous cases',exact:true})).toBeDisabled()
  await page.getByRole('button',{name:'Next cases',exact:true}).click()
  await expect.poll(()=>queries.at(-1)?.get('cursor')).toBe('next-page')
  expect(queries.at(-1)?.get('severity')).toBe('high')
})
