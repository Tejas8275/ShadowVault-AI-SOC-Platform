import test from 'node:test'
import assert from 'node:assert/strict'
import { createInvestigationService, searchParameters, validateFilters } from '../src/features/evidence/service.ts'

test('connection rejects malformed input locally and accepts an empty authorized result', async () => {
  const calls=[]
  const api=createInvestigationService('http://localhost/api',()=>{},async(url,options)=>{
    calls.push({url,options});return Response.json({items:[],total:0,next_cursor:null})
  })
  for(const value of ['', 'wrong', ' sv_operator_test', 'sv_operator_test '])await assert.rejects(api.connect(value))
  assert.equal(calls.length,0)
  await api.connect('sv_operator_test')
  assert.equal(calls.length,1);assert.equal(calls[0].url,'http://localhost/api/evidence?limit=1')
  assert.equal(calls[0].options.headers.Authorization,'Bearer sv_operator_test')
})

test('failed connection clears its credential and permits only an explicit new attempt', async () => {
  let calls=0, fail=true
  const api=createInvestigationService('http://localhost/api',()=>{},async()=>{
    calls++;if(fail)throw new DOMException('Timed out','TimeoutError')
    return Response.json({items:[]})
  })
  await assert.rejects(api.connect('sv_operator_test'),{name:'TimeoutError'})
  await assert.rejects(api.search({}),{status:401});assert.equal(calls,1)
  fail=false;await api.connect('sv_operator_test');assert.equal(calls,2)
})

test('investigation filters serialize repeated tags, aware dates and opaque cursors', () => {
  const query = new URLSearchParams(searchParameters({ tags: ' Disk,urgent,disk', created_from: '2026-09-06T12:00:00+05:30', q: '%_' }, 'opaque+/='))
  assert.deepEqual(query.getAll('tags'), ['disk', 'urgent'])
  assert.equal(query.get('created_from'), '2026-09-06T06:30:00.000Z')
  assert.equal(query.get('q'), '%_')
  assert.equal(query.get('cursor'), 'opaque+/=')
  assert.ok(validateFilters({ min_size: '20', max_size: '10' }))
  assert.equal(validateFilters({ min_size: '10', max_size: '20' }), null)
})

test('operator token travels only in header to fixed API and disconnect cancels requests', async () => {
  const calls = []
  const api = createInvestigationService('http://localhost:8000/api/v2/investigation', () => {}, async (url, options) => {
    calls.push({ url, options }); return Response.json({ items: [], total: 0, next_cursor: null })
  })
  await api.connect('sv_operator_test')
  await api.search({ q: 'file' })
  assert.ok(calls.every(({ url, options }) => !url.includes('sv_operator') && options.headers.Authorization === 'Bearer sv_operator_test' && options.redirect === 'error' && options.cache === 'no-store' && options.credentials === 'omit'))
  api.disconnect()
  await assert.rejects(api.search({}), { status: 401 })
})

test('unauthorized clears credential and never echoes server body', async () => {
  let expired = 0
  const api = createInvestigationService('http://localhost/api/v2/investigation', () => expired++, async () => Response.json({ detail: 'sensitive' }, { status: 401 }))
  await assert.rejects(api.connect('sv_operator_test'), error => error.status === 401 && !error.message.includes('sensitive'))
  assert.equal(expired, 1)
  await assert.rejects(api.details('id'), { status: 401 })
})

test('unsafe API destinations rejected before any credential is sent', () => {
  for (const url of ['http://remote.example/api', 'https://user:pass@example.com/api', 'https://example.com/api?token=x', 'https://example.com/api#x']) {
    assert.throws(() => createInvestigationService(url, () => {}))
  }
})

test('all detail and mutation contracts retain revisions and never retry writes', async () => {
  const calls = []
  const api = createInvestigationService('http://localhost/api/v2/investigation', () => {}, async (url, options) => {
    calls.push({ url, options }); return Response.json({})
  })
  await api.connect('sv_operator_test')
  await api.details('id'); await api.notes('id', 'cursor'); await api.custody('id', 2)
  await api.annotate('id', { expected_revision: 3, tags: [] })
  await api.addNote('id', 'Observation', 4)
  assert.equal(calls.length, 6)
  assert.deepEqual(JSON.parse(calls[4].options.body), { expected_revision: 3, tags: [] })
  assert.deepEqual(JSON.parse(calls[5].options.body), { expected_revision: 4, body: 'Observation' })
  assert.ok(calls[3].url.includes('after_sequence=2'))
})

test('disconnect prevents delayed response from publishing data', async () => {
  let release
  let count = 0
  const api = createInvestigationService('http://localhost/api/v2/investigation', () => {}, async () => {
    if (++count === 1) return Response.json({})
    await new Promise(resolve => { release = resolve })
    return Response.json({ items: ['private'] })
  })
  await api.connect('sv_operator_test')
  const pending = api.search({})
  api.disconnect(); release()
  await assert.rejects(pending, { name: 'AbortError' })
})

test('write errors preserve status and are never retried', async () => {
  for (const status of [409, 422, 503]) {
    let count = 0
    const api = createInvestigationService('http://localhost/api/v2/investigation', () => {}, async () => {
      return ++count === 1 ? Response.json({}) : Response.json({ detail: 'private draft' }, { status })
    })
    await api.connect('sv_operator_test')
    await assert.rejects(api.addNote('id', 'private draft', 1), error => error.status === status && !error.message.includes('private'))
    assert.equal(count, 2)
  }
})
