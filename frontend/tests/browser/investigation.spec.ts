import { expect, test, type Page } from '@playwright/test'
const id = '00000000-0000-0000-0000-000000000001'
const evidence = {
  id, filename: 'sample.bin', display_title: null, incident_id: id, collection_job_id: null, collection_item_id: null,
  agent_id: null, requested_by_user_id: null, collected_by_user_id: id, source_path: null,
  media_type: 'application/octet-stream', size_bytes: 3, sha256: 'a'.repeat(64), created_at: '2026-09-06T00:00:00Z',
  collected_at: null, initial_verification_status: 'legacy', initial_verified_at: null,
  review_state: 'unreviewed', metadata_revision: 0, tags: [], note_count: 0,
  custody_started: false, custody_sequence: 0, custody_head_hash: null,
  integrity_result: 'not_checked', integrity_checked_at: null,
}
async function connect(page: Page) {
  await page.goto('/#evidence')
  await page.getByLabel('Operator token', { exact: true }).fill('sv_operator_' + 'B'.repeat(43))
  await page.getByRole('button', { name: 'Connect operator', exact: true }).click()
  await expect(page.getByText('Operator connected', { exact: true })).toBeVisible()
}
async function mock(page: Page, options: { conflict?: boolean; ambiguous?: boolean; integrity?: string; unauthorized?: boolean } = {}) {
  await page.route('**/api/v2/investigation/**', async route => {
    const url = new URL(route.request().url())
    let value: unknown = { items: [evidence], total: 1, next_cursor: null }
    let status = 200
    if (options.unauthorized) status = 401
    else if (route.request().method() !== 'GET') { status = options.conflict ? 409 : options.ambiguous ? 503 : 200; value = { ...evidence, metadata_revision: 1 } }
    else if (url.pathname.endsWith('/custody')) value = { items: [], tracking_started: false, head_sequence: 0, head_hash: null, next_sequence: null }
    else if (url.pathname.endsWith('/notes')) value = { items: [], next_cursor: null }
    else if (url.pathname.endsWith(id)) value = { ...evidence, integrity_result: options.integrity || 'not_checked' }
    else if (url.searchParams.get('q') === 'empty') value = { items: [], total: 0, next_cursor: null }
    await route.fulfill({ status, json: value })
  })
}

test('real FastAPI workflow saves notes and tags, updates custody, and retains initial status', async ({ page }) => {
  await connect(page)
  await page.getByRole('link', { name: 'browser-fixture.bin', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Acquisition metadata' })).toBeVisible()
  await page.getByLabel('Display title', { exact: true }).fill('Reviewed browser fixture')
  await page.getByLabel('Evidence tags (comma-separated)', { exact: true }).fill(' Disk,urgent,disk')
  await page.getByRole('button', { name: 'Save annotations' }).click()
  await expect(page.getByRole('heading', { name: 'Reviewed browser fixture', exact: true })).toBeVisible()
  await page.getByLabel('New note', { exact: true }).fill('<img src=x onerror=alert(1)> observed as text')
  await page.getByRole('button', { name: 'Add note', exact: true }).click()
  await expect(page.getByText('<img src=x onerror=alert(1)> observed as text', { exact: true })).toBeVisible()
  await expect(page.locator('img')).toHaveCount(0)
  await expect(page.getByText('Browser investigator', { exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: '1. Tracking started at first annotation' })).toBeVisible()
  await expect(page.getByText('Legacy — upload verification not recorded')).toBeVisible()
  await page.getByRole('link', { name: 'Back to evidence results' }).click()
  await expect(page.getByRole('link', { name: 'Reviewed browser fixture', exact: true })).toBeVisible()
})

test('disconnect and reload discard credentials and investigation data', async ({ page }) => {
  await mock(page); await connect(page)
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0)
  await page.getByRole('button', { name: 'Disconnect operator' }).click()
  await expect(page.getByRole('heading', { name: 'Connect operator' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'sample.bin', exact: true })).toHaveCount(0)
  await connect(page); await page.reload()
  await expect(page.getByRole('heading', { name: 'Connect operator' })).toBeVisible()
})

test('search empty state, filter preservation, details direct links and keyboard focus', async ({ page }) => {
  await mock(page); await connect(page)
  await page.getByLabel('Text', { exact: true }).fill('sample')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await page.getByRole('link', { name: 'sample.bin', exact: true }).click()
  await expect(page.locator('#main-content')).toBeFocused()
  await page.getByRole('link', { name: 'Back to evidence results' }).click()
  await expect(page.getByLabel('Text', { exact: true })).toHaveValue('sample')
  await page.getByLabel('Text', { exact: true }).fill('empty')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByText('No evidence matches these filters.')).toBeVisible()
  expect(page.url().includes('empty')).toBe(false)
  await page.goto('/#evidence/' + id)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Connect operator' })).toBeVisible()
})

test('revision conflicts preserve draft and require reload before resubmission', async ({ page }) => {
  await mock(page, { conflict: true }); await connect(page)
  await page.getByRole('link', { name: 'sample.bin', exact: true }).click()
  await page.getByLabel('New note', { exact: true }).fill('Preserved draft')
  await page.getByRole('button', { name: 'Add note', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Add note', exact: true })).toBeDisabled()
  await expect(page.getByLabel('New note', { exact: true })).toHaveValue('Preserved draft')
  await page.getByRole('button', { name: 'Reload before resubmitting' }).click()
  await expect(page.getByRole('button', { name: 'Add note', exact: true })).toBeEnabled()
  await expect(page.getByLabel('New note', { exact: true })).toHaveValue('Preserved draft')
})

test('ambiguous failures do not automatically retry writes', async ({ page }) => {
  await mock(page, { ambiguous: true }); let writes = 0
  page.on('request', request => { if (request.method() === 'POST') writes++ })
  await connect(page); await page.getByRole('link', { name: 'sample.bin', exact: true }).click()
  await page.getByLabel('New note', { exact: true }).fill('Observation')
  await page.getByRole('button', { name: 'Add note', exact: true }).click()
  await expect(page.getByText(/Save was not confirmed/)).toBeVisible()
  expect(writes).toBe(1)
})

test('rejected operator connection reveals no evidence', async ({ page }) => {
  await mock(page, { unauthorized: true }); await page.goto('/#evidence')
  await page.getByLabel('Operator token', { exact: true }).fill('sv_operator_fixture')
  await page.getByRole('button', { name: 'Connect operator', exact: true }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByLabel('Operator token', { exact: true })).toHaveValue('')
  await expect(page.getByRole('link', { name: 'sample.bin', exact: true })).toHaveCount(0)
})

for (const result of ['not_checked', 'matches', 'mismatch', 'missing', 'unavailable']) {
  test(`integrity ${result} is distinct from acquisition and custody claims`, async ({ page }) => {
    await mock(page, { integrity: result }); await connect(page)
    await page.getByRole('link', { name: 'sample.bin', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Initial upload verification' })).toBeVisible()
    await expect(page.getByText('Legacy — upload verification not recorded')).toBeVisible()
    await expect(page.locator(`.integrity-${result}`)).toBeVisible()
    await expect(page.getByText('Custody tracking has not started for this evidence.')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Verify now' })).toHaveCount(0)
  })
}

test('mobile layout fits viewport and operator connection remains available', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await mock(page); await connect(page)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('link', { name: 'sample.bin', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Acquisition metadata' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('link', { name: 'Operator connection', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Operator connection', exact: true })).toBeVisible()
})

test('search, notes and custody pagination use server cursors and show migration baselines', async ({ page }) => {
  await mock(page)
  await page.route('**/api/v2/investigation/evidence?**', async route => {
    const second = new URL(route.request().url()).searchParams.has('cursor')
    await route.fulfill({ json: { items: [{ ...evidence, filename: second ? 'second.bin' : 'first.bin' }], total: 2, next_cursor: second ? null : 'page-two' } })
  })
  await page.route('**/notes?**', async route => {
    const second = new URL(route.request().url()).searchParams.has('cursor')
    await route.fulfill({ json: { items: [{ id: second ? 'note2' : 'note1', body: second ? 'Second note' : 'First note', author_label: 'Investigator', created_at: evidence.created_at }], next_cursor: second ? null : 'notes-two' } })
  })
  await page.route('**/custody?**', async route => {
    const second = new URL(route.request().url()).searchParams.get('after_sequence') === '1'
    await route.fulfill({ json: { items: [{ id: second ? 'event2' : 'event1', sequence: second ? 2 : 1, event_type: second ? 'annotations_updated' : 'baseline_registered', system_actor: 'migration:0003', actor_type: 'system', actor_label: 'Migration', recorded_at: evidence.created_at, details: {}, event_hash: 'a'.repeat(64) }], tracking_started: true, head_sequence: 2, head_hash: 'a'.repeat(64), next_sequence: second ? null : 1 } })
  })
  await connect(page)
  await page.getByRole('button', { name: 'Next page', exact: true }).click()
  await expect(page.getByRole('link', { name: 'second.bin', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Previous page', exact: true }).click()
  await page.getByRole('link', { name: 'first.bin', exact: true }).click()
  await expect(page.getByRole('heading', { name: '1. Migration registration baseline' })).toBeVisible()
  await page.getByRole('button', { name: 'Next notes', exact: true }).click()
  await expect(page.getByText('Second note', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Previous notes', exact: true }).click()
  await expect(page.getByText('First note', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Next custody events' }).click()
  await expect(page.getByRole('heading', { name: '2. annotations updated' })).toBeVisible()
})

test('range validation is accessible and stale search responses cannot replace new results', async ({ page }) => {
  await mock(page); await connect(page)
  await page.getByText('Advanced filters', { exact: true }).click()
  await page.getByLabel('Minimum bytes', { exact: true }).fill('20')
  await page.getByLabel('Maximum bytes', { exact: true }).fill('10')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveText('Range start must not exceed range end.')
  await page.getByRole('button', { name: 'Clear filters' }).click()
  let release!: () => void
  const delayed = new Promise<void>(resolve => { release = resolve })
  await page.route('**/evidence?q=old', async route => {
    await delayed
    await route.fulfill({ json: { items: [{ ...evidence, filename: 'obsolete.bin' }], total: 1, next_cursor: null } }).catch(() => {})
  })
  await page.getByLabel('Text', { exact: true }).fill('old')
  const requested = page.waitForRequest(request => request.url().endsWith('evidence?q=old'))
  await page.getByRole('button', { name: 'Search', exact: true }).click(); await requested
  await page.getByLabel('Text', { exact: true }).fill('empty')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByText('No evidence matches these filters.')).toBeVisible()
  release()
  await expect(page.getByRole('link', { name: 'obsolete.bin', exact: true })).toHaveCount(0)
})

test('authentication expiry clears an active workspace', async ({ page }) => {
  await mock(page); await connect(page)
  await expect(page.getByRole('link', { name: 'sample.bin', exact: true })).toBeVisible()
  await page.route('**/api/v2/investigation/**', route => route.fulfill({ status: 401, json: {} }))
  await page.getByRole('button', { name: 'Refresh results' }).click()
  await expect(page.getByRole('heading', { name: 'Connect operator' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'sample.bin', exact: true })).toHaveCount(0)
})
