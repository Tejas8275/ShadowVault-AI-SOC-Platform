import { expect, test, type Page } from '@playwright/test'
const evidenceId = '00000000-0000-0000-0000-000000000002'
const incidentId = '00000000-0000-0000-0000-000000000014'
const event = { id: '00000000-0000-0000-0000-000000000099', incident_id: incidentId, evidence_id: evidenceId,
  recorded_by_id: incidentId, recorded_by_label: 'Fixture investigator', origin: 'investigator',
  occurred_at: '2026-09-06T07:00:00Z', reported_time: '2026-09-06T12:30:00+05:30', created_at: '2026-09-07T00:00:00Z',
  title: 'Fixture observation', description: 'Reported', source: 'Manual', source_locator: 'Record 12', submission_id: incidentId }
async function connect(page: Page) {
  await page.goto('/#evidence')
  await page.getByLabel('Operator token', { exact: true }).fill('sv_operator_' + 'B'.repeat(43))
  await page.getByRole('button', { name: 'Connect operator', exact: true }).click()
  await page.getByRole('link', { name: 'timeline-fixture.bin', exact: true }).click()
}
async function fill(page: Page) {
  await page.getByLabel('Occurrence time (ISO timestamp with offset)', { exact: true }).fill('2026-09-06T12:30:00+05:30')
  await page.getByLabel('Observation title', { exact: true }).fill('Explicit investigator observation')
  await page.getByLabel('Observation description', { exact: true }).fill('<script>alert(1)</script> reported as text')
  await page.getByLabel('Observation source', { exact: true }).fill('Manual examination account')
  await page.getByLabel('Source locator (optional)', { exact: true }).fill('Record 12')
}

test('real timeline creation preserves provenance, updates custody and links evidence', async ({ page }) => {
  await connect(page); await fill(page)
  await page.getByRole('button', { name: 'Record observation', exact: true }).click()
  await expect(page.getByText('Observation recorded.', { exact: false })).toBeVisible()
  await expect(page.getByRole('heading', { name: '1. Tracking started at first timeline observation' })).toBeVisible()
  await page.getByRole('link', { name: 'View recorded observation', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Explicit investigator observation', exact: true })).toBeVisible()
  await expect(page.getByText('2026-09-06T12:30:00+05:30', { exact: true })).toBeVisible()
  await expect(page.getByText('2026-09-06T07:00:00.000Z (UTC)', { exact: true })).toBeVisible()
  await expect(page.getByText('<script>alert(1)</script> reported as text', { exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'View this incident timeline', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Explicit investigator observation', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Legacy timeline fixture', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Legacy timeline fixture', exact: true }).click()
  await expect(page.getByText('No evidence link recorded.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: /Delete|Edit observation/ })).toHaveCount(0)
})

test('occurrence time is required and naive timestamp never submits', async ({ page }) => {
  await connect(page)
  await expect(page.getByLabel('Occurrence time (ISO timestamp with offset)', { exact: true })).toHaveValue('')
  await fill(page)
  await page.getByLabel('Occurrence time (ISO timestamp with offset)', { exact: true }).fill('2026-09-06T12:30:00')
  let writes = 0
  page.on('request', request => { if (request.method() === 'POST') writes++ })
  await page.getByRole('button', { name: 'Record observation', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('explicit offset')
  expect(writes).toBe(0)
})

test('unconfirmed observation retains an unchanged retry payload and draft', async ({ page }) => {
  await connect(page); await fill(page)
  const payloads: string[] = []
  await page.route('**/evidence/*/timeline-events', async route => {
    payloads.push(route.request().postData()!)
    await route.fulfill({ status: payloads.length === 1 ? 503 : 200, json: event })
  })
  await page.getByRole('button', { name: 'Record observation', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Submission not confirmed')
  expect(payloads.length).toBe(1)
  await expect(page.getByLabel('Observation title', { exact: true })).toHaveValue('Explicit investigator observation')
  await expect(page.getByLabel('Observation title', { exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Review current observations' }).click()
  await expect(page.getByText(/Latest occurrence-time page/)).toBeVisible()
  await page.getByRole('button', { name: 'Retry unchanged submission' }).click()
  await expect(page.getByText('Observation recorded.', { exact: false })).toBeVisible()
  expect(payloads.length).toBe(2); expect(payloads[0]).toBe(payloads[1])
})

test('timeline filters and cursor pagination preserve incident scope', async ({ page }) => {
  await connect(page)
  const queries: URLSearchParams[] = []
  await page.route('**/timeline-events?**', async route => {
    const params = new URL(route.request().url()).searchParams; queries.push(params)
    const next = params.has('cursor')
    await route.fulfill({ json: { items: [{ ...event, title: next ? 'Second observation' : 'First observation' }], total: 2, next_cursor: next ? null : 'next-page' } })
  })
  await page.getByRole('link', { name: 'View incident timeline', exact: true }).click()
  await expect(page.getByRole('link', { name: 'First observation' })).toBeVisible()
  await page.getByLabel('Timeline text', { exact: true }).fill('%_')
  await page.getByRole('button', { name: 'Search timeline' }).click()
  await page.getByRole('button', { name: 'Next observations' }).click()
  await expect(page.getByRole('link', { name: 'Second observation' })).toBeVisible()
  expect(queries.at(-1)!.get('incident_id')).toBe(incidentId)
  expect(queries.at(-1)!.get('q')).toBe('%_')
  await page.getByRole('button', { name: 'Previous observations' }).click()
  await expect(page.getByRole('link', { name: 'First observation' })).toBeVisible()
  expect(page.url().includes('%_')).toBe(false)
})

test('timeline authentication failure clears the shared evidence connection', async ({ page }) => {
  await connect(page)
  await page.route('**/timeline-events?**', route => route.fulfill({ status: 401, json: {} }))
  await page.getByRole('link', { name: 'View incident timeline', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Connect operator', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Evidence', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Connect operator', exact: true })).toBeVisible()
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0)
})

test('timeline mobile layout and direct links keep keyboard navigation', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await connect(page)
  await page.getByRole('link', { name: 'View incident timeline', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Incident timeline', exact: true })).toBeVisible()
  await expect(page.locator('#main-content')).toBeFocused()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Connect operator', exact: true })).toBeVisible()
})
