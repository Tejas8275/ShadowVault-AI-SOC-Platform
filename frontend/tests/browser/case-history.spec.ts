import { test, expect, type Page } from '@playwright/test'
const caseId='00000000-0000-0000-0000-000000000014'
async function connect(page:Page){
  await page.goto('/#cases')
  await page.getByLabel('Operator token',{exact:true}).fill('sv_operator_'+'B'.repeat(43))
  await page.getByRole('button',{name:'Connect operator',exact:true}).click()
  await page.getByRole('link',{name:'Browser fixture',exact:true}).click()
}
const empty={items:[],tracking_started:false,tracking_started_revision:null,next_revision:null}
const event=(revision:number,type='case_updated')=>({id:String(revision),incident_id:caseId,revision,event_type:type,actor_label:'Investigator',source:'api',recorded_at:'2026-09-08T00:00:00Z',changes:{}})

test('real save appends history and refreshes grouped changes',async({page})=>{
  await connect(page)
  await page.getByLabel('Case title',{exact:true}).fill('History <script>text</script>')
  await page.getByRole('button',{name:'Save case',exact:true}).click()
  const panel=page.getByRole('region',{name:'Case history',exact:true})
  await expect(panel.getByRole('heading',{name:/Case updated/})).toBeVisible()
  await panel.getByText('title: changed',{exact:true}).click()
  await expect(panel.getByText('History <script>text</script>',{exact:true})).toBeVisible()
  await page.getByLabel('Case title',{exact:true}).fill('Browser fixture')
  await page.getByRole('button',{name:'Save case',exact:true}).click()
  await expect(panel.getByRole('heading',{name:/Case updated/})).toHaveCount(2)
})

test('history loading error retry and untracked states are explicit',async({page})=>{
  let release:()=>void=()=>{};const gate=new Promise<void>(resolve=>{release=resolve})
  await page.route('**/history?*',async route=>{await gate;await route.fulfill({status:503,json:{}})})
  await connect(page);await expect(page.getByText('Loading case history…')).toBeVisible()
  release();await expect(page.getByText('Unable to load case history.')).toBeVisible()
  await page.unroute('**/history?*')
  await page.route('**/history?*',route=>route.fulfill({json:empty}))
  await page.getByRole('button',{name:'Retry case history',exact:true}).click()
  await expect(page.getByText(/Case history tracking is unavailable/)).toBeVisible()
})

test('history baseline zero pagination and unchanged-field save display',async({page})=>{
  const seen:string[]=[]
  await page.route('**/history?*',async route=>{
    const q=new URL(route.request().url()).searchParams;seen.push(q.get('after_revision')??'initial')
    await route.fulfill({json:{items:[q.has('after_revision')?event(1):{...event(0,'baseline_registered'),source:'migration'}],tracking_started:true,tracking_started_revision:0,next_revision:q.has('after_revision')?null:0}})
  })
  await connect(page)
  await expect(page.getByText('Snapshot when tracking began; earlier history is unavailable.')).toBeVisible()
  await page.getByRole('button',{name:'Load more case history',exact:true}).click()
  await expect(page.getByRole('heading',{name:/Case saved — no field changes/})).toBeVisible()
  expect(seen.at(-1)).toBe('0')
  expect(seen.slice(0,-1).every(value=>value==='initial')).toBe(true)
  await page.getByRole('button',{name:'Refresh case history',exact:true}).click()
  await expect(page.getByRole('heading',{name:/Migration baseline/})).toHaveCount(1)
})

test('history unauthorized clears operator and mobile view fits',async({page})=>{
  await page.setViewportSize({width:390,height:844});await connect(page)
  await expect(page.getByText(/Tracking starts at revision/)).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await page.route('**/history?*',route=>route.fulfill({status:401,json:{}}))
  await page.getByRole('button',{name:'Refresh case history',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Connect operator',exact:true})).toBeVisible()
})
