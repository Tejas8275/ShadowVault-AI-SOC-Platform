import { expect, test, type Page } from '@playwright/test'
import { readFile } from 'node:fs/promises'
const id = '00000000-0000-0000-0000-000000000004'
async function connect(page: Page) {
  await page.goto('/#evidence')
  await page.getByLabel('Operator token', { exact: true }).fill('sv_operator_' + 'B'.repeat(43))
  await page.getByRole('button', { name: 'Connect operator', exact: true }).click()
  await page.getByRole('link', { name: 'retrieval-fixture.bin', exact: true }).click()
}

test('real retrieval saves exact bytes and records preparation without changing integrity status', async ({ page }) => {
  await connect(page)
  await page.getByRole('button', { name: 'Prepare download', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Save evidence copy' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '1. Tracking started at first retrieval' })).toBeVisible()
  await expect(page.getByText('Verified copy prepared by the server. Delivery and local saving are not confirmed.')).toBeVisible()
  const pending = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Save evidence copy' }).click()
  const download = await pending
  expect(download.suggestedFilename()).toBe(`evidence-${id}.bin`)
  expect(await readFile((await download.path())!)).toEqual(Buffer.concat([Buffer.from('Original browser evidence'), Buffer.from([0, 255])]))
  await expect(page.getByText('Legacy — upload verification not recorded')).toBeVisible()
  await expect(page.locator('.integrity-not_checked')).toBeVisible()
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0)
})

test('retrieval failure stays explicit and only a manual retry sends another request', async ({ page }) => {
  await connect(page)
  let requests = 0
  await page.route('**/evidence/*/download', async route => { requests++; await route.fulfill({ status: 503, body: 'private path' }) })
  await page.getByRole('button', { name: 'Prepare download', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Review custody')
  expect(requests).toBe(1)
  await expect(page.getByRole('link', { name: 'Save evidence copy' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Prepare download', exact: true }).click()
  await expect.poll(() => requests).toBe(2)
  await expect(page.getByText('private path', { exact: true })).toHaveCount(0)
})

test('cancelled preparation cannot publish a delayed response', async ({ page }) => {
  await connect(page)
  let release!: () => void
  const delayed = new Promise<void>(resolve => { release = resolve })
  await page.route('**/evidence/*/download', async route => {
    await delayed
    await route.fulfill({ contentType: 'application/octet-stream', body: Buffer.alloc(27), headers: { 'Content-Length': '27' } }).catch(() => {})
  })
  const pending = page.waitForRequest('**/evidence/*/download')
  await page.getByRole('button', { name: 'Prepare download', exact: true }).click(); await pending
  await page.getByRole('button', { name: 'Cancel download', exact: true }).click()
  await expect(page.getByText(/Download cancelled/)).toBeVisible()
  release()
  await expect(page.getByRole('link', { name: 'Save evidence copy' })).toHaveCount(0)
})

test('download authentication expiry clears the whole operator workspace', async ({ page }) => {
  await connect(page)
  await page.route('**/evidence/*/download', route => route.fulfill({ status: 401, body: '' }))
  await page.getByRole('button', { name: 'Prepare download', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Connect operator', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Save evidence copy' })).toHaveCount(0)
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0)
})

test('discard and navigation revoke download URLs with mobile keyboard access', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.addInitScript(() => {
    const original = URL.revokeObjectURL.bind(URL)
    ;(window as unknown as { revoked: string[] }).revoked = []
    URL.revokeObjectURL = url => { (window as unknown as { revoked: string[] }).revoked.push(url); original(url) }
  })
  await connect(page)
  const button = page.getByRole('button', { name: 'Prepare download', exact: true })
  await button.focus(); await page.keyboard.press('Enter')
  const save = page.getByRole('link', { name: 'Save evidence copy' })
  await expect(save).toBeVisible()
  const first = await save.getAttribute('href')
  await page.getByRole('button', { name: 'Discard copy', exact: true }).click()
  await expect(save).toHaveCount(0)
  expect(await page.evaluate(() => (window as unknown as { revoked: string[] }).revoked)).toContain(first)
  await button.click(); await expect(save).toBeVisible()
  const second = await save.getAttribute('href')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('link', { name: 'Back to evidence results', exact: true }).click()
  await expect.poll(() => page.evaluate(() => (window as unknown as { revoked: string[] }).revoked)).toContain(second)
})
