import test from 'node:test'
import assert from 'node:assert/strict'
import { loadCaseOverview } from '../src/features/cases/overview.ts'
import { createInvestigationService } from '../src/features/evidence/service.ts'

test('overview uses authorized server totals and a bounded creation-ordered page', async () => {
  const calls = [], signal = new AbortController().signal
  const api = { cases: async (filters, cursor, receivedSignal) => {
    calls.push(filters); assert.equal(cursor, undefined); assert.equal(receivedSignal, signal)
    return { total: filters.status ? 17 : filters.severity ? 9 : 101, items: filters.limit === '5' ? [{ id: 'recent' }] : [], next_cursor: 'more' }
  } }
  const result = await loadCaseOverview(api, signal)
  assert.equal(result.total, 101); assert.equal(result.recent.length, 1)
  assert.deepEqual(result.statuses.map(v => v.total), [17,17,17])
  assert.deepEqual(result.severities.map(v => v.total), [9,9,9,9])
  assert.equal(calls.length, 8); assert.ok(calls.every(v => ['1','5'].includes(v.limit)))
})

test('failed overview count does not become a fabricated zero', async () => {
  await assert.rejects(loadCaseOverview({ cases: async filters => {
    if (filters.status === 'closed') throw new Error('unavailable')
    return { total: 10, items: [], next_cursor: null }
  } }, new AbortController().signal), /unavailable/)
})

test('overview reuses authorization without exposing a token in URLs and clears on rejection', async () => {
  let expired = 0, reject = false
  const api = createInvestigationService('http://localhost/api', () => expired++, async (url, options) => {
    assert.ok(!url.includes('sv_operator_'))
    assert.equal(options.headers.Authorization, 'Bearer sv_operator_fixture')
    assert.equal(options.cache, 'no-store'); assert.equal(options.credentials, 'omit')
    return Response.json({ items: [], total: 0, next_cursor: null }, { status: reject ? 401 : 200 })
  })
  await api.connect('sv_operator_fixture')
  assert.equal((await loadCaseOverview(api, new AbortController().signal)).total, 0)
  reject = true
  await assert.rejects(loadCaseOverview(api, new AbortController().signal))
  assert.ok(expired > 0)
  await assert.rejects(api.caseDetail('id'), { status: 401 })
})

test('disconnect aborts in-flight overview requests', async () => {
  let count = 0, started
  const ready = new Promise(resolve => { started = resolve })
  const api = createInvestigationService('http://localhost/api', () => {}, async (_url, options) => {
    if (++count === 1) return Response.json({})
    started()
    return new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('cancelled', 'AbortError')), { once: true }))
  })
  await api.connect('sv_operator_fixture')
  const result = loadCaseOverview(api, new AbortController().signal)
  await ready; api.disconnect()
  await assert.rejects(result, { name: 'AbortError' })
})
