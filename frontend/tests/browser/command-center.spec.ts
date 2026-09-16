import { test, expect, type Page } from '@playwright/test'

async function connect(page: Page) {
  await page.goto('/#dashboard')
  await page.getByLabel('Operator token', { exact: true }).fill('sv_operator_' + 'B'.repeat(43))
  await page.getByRole('button', { name: 'Connect operator', exact: true }).click()
}

test('real command center totals match authorized API and connection survives navigation', async ({ page }) => {
  await connect(page)
  const region = page.getByRole('region', { name: 'Authorized case overview' })
  await expect(region.getByRole('heading', { name: 'Newest cases' })).toBeVisible()
  const response = await page.request.get('http://127.0.0.1:8769/api/v2/investigation/incidents?limit=5', {
    headers: { Authorization: 'Bearer sv_operator_' + 'B'.repeat(43) },
  })
  const result = await response.json()
  await expect(region.locator('.metric').first().locator('strong')).toHaveText(String(result.total))
  await expect(region.locator('.case-card')).toHaveCount(result.items.length)
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Cases', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Cases', exact: true })).toBeVisible()
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Overview' }).click()
  await expect(region.getByRole('heading', { name: 'Newest cases' })).toBeVisible()
  await page.getByRole('button', { name: 'Disconnect operator' }).click()
  await expect(region).toHaveCount(0)
  await expect(page.getByLabel('Operator token', { exact: true })).toHaveValue('')
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0)
})

test('overview loading failure and manual retry never show false zero counts', async ({ page }) => {
  let release = () => {}
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route('**/incidents?*', async route => { await gate; await route.fulfill({ status: 503, json: {} }) })
  await connect(page)
  await expect(page.getByText('Loading authorized case overview…')).toBeVisible()
  release()
  await expect(page.getByRole('alert')).toContainText('Counts are not available')
  await expect(page.locator('.metric')).toHaveCount(0)
  await page.unroute('**/incidents?*')
  await page.route('**/incidents?*', route => route.fulfill({ json: { items: [], total: 0, next_cursor: null } }))
  await page.getByRole('button', { name: 'Refresh overview' }).click()
  await expect(page.getByRole('heading', { name: 'No cases yet' })).toBeVisible()
  await expect(page.locator('.metric').first().locator('strong')).toHaveText('0')
})

test('overview unauthorized response clears private data and token input', async ({ page }) => {
  await page.route('**/incidents?*', route => route.fulfill({ status: 401, json: { detail: 'not for display' } }))
  await connect(page)
  await expect(page.getByRole('heading', { name: 'Connect operator', exact: true })).toBeVisible()
  await expect(page.getByLabel('Operator token', { exact: true })).toHaveValue('')
  await expect(page.locator('.metric')).toHaveCount(0)
  await expect(page.getByText('not for display')).toHaveCount(0)
})

test('mobile command center is keyboard accessible with no horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await connect(page)
  await expect(page.getByRole('heading', { name: 'Newest cases' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('button', { name: 'Disconnect operator' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Connect operator', exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('case cards show last update and workspace exposes severity and section selection', async ({ page }) => {
  await connect(page)
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Cases', exact: true }).click()
  await expect(page.locator('.case-card').first()).toContainText('Last updated:')
  await page.getByRole('link', { name: 'Browser fixture', exact: true }).click()
  await expect(page.locator('.case-header')).toContainText('Severity:')
  await expect(page.getByRole('region', { name: 'Case history' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Case evidence', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('button', { name: 'Case timeline', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Case timeline', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByLabel('Timeline incident ID', { exact: true })).toBeDisabled()
})

test('readiness failure is explicit and can be retried without authenticating', async ({ page }) => {
  await page.route('**/api/v1/health', route => route.fulfill({ status: 503, json: {} }))
  await page.goto('/#dashboard')
  await expect(page.getByText('Unable to reach the backend or database. Start the backend, then retry.')).toBeVisible()
  await page.route('**/api/v1/health', route => route.fulfill({ json: { status: 'ok', database: 'connected' } }))
  await page.getByRole('button', { name: 'Check connection' }).click()
  await expect(page.getByText('Backend and database connected')).toBeVisible()
  await expect(page.locator('.metric')).toHaveCount(0)
})
