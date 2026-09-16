import test from 'node:test'
import assert from 'node:assert/strict'
import { createInvestigationService } from '../src/features/evidence/service.ts'
import { downloadFilename, MAX_DOWNLOAD_BYTES, readDownload } from '../src/features/evidence/download.ts'
const id = '00000000-0000-0000-0000-000000000004'
const response = (data = 'abc', length = data.length) => new Response(data, {
  headers: { 'Content-Type': 'application/octet-stream', 'Content-Length': String(length) },
})
async function service(fetcher, unauthorized = () => {}) {
  let connected = false
  const api = createInvestigationService('http://localhost/api/v2/investigation', unauthorized, async (...args) => {
    if (!connected) { connected = true; return Response.json({}) }
    return fetcher(...args)
  })
  await api.connect('sv_operator_fixture')
  return api
}

test('download sends token only in header, accepts binary and never follows redirects', async () => {
  let calls = 0
  const api = await service(async (url, options) => {
    calls++; assert.equal(url, `http://localhost/api/v2/investigation/evidence/${id}/download`)
    assert.equal(options.method, 'POST'); assert.equal(options.redirect, 'error')
    assert.equal(options.credentials, 'omit'); assert.equal(options.cache, 'no-store')
    assert.equal(options.headers.Authorization, 'Bearer sv_operator_fixture')
    return response()
  })
  const progress = []
  const blob = await api.download(id, 3, new AbortController().signal, n => progress.push(n))
  assert.equal(await blob.text(), 'abc'); assert.deepEqual(progress, [0, 3]); assert.equal(calls, 1)
})

test('download filenames cannot carry executable names or path/header input', () => {
  assert.equal(downloadFilename(id), `evidence-${id}.bin`)
  for (const value of ['../evil.exe', 'file\r\nheader', '<script>', 'C:\\file']) assert.equal(downloadFilename(value), 'evidence-copy.bin')
})

test('download errors are sanitized and never automatically retried', async () => {
  for (const status of [404, 409, 413, 429, 503]) {
    let calls = 0
    const api = await service(async () => { calls++; return new Response('secret-path-token', { status }) })
    await assert.rejects(api.download(id, 3, new AbortController().signal), error => error.status === status && !error.message.includes('secret'))
    assert.equal(calls, 1)
  }
})

test('download 401 clears the shared connection and disables subsequent reads', async () => {
  let expired = 0
  const api = await service(async () => new Response(null, { status: 401 }), () => expired++)
  await assert.rejects(api.download(id, 3, new AbortController().signal), { status: 401 })
  assert.equal(expired, 1); await assert.rejects(api.details(id), { status: 401 })
})

test('oversized evidence is rejected before network access', async () => {
  const api = await service(async () => assert.fail('must not fetch'))
  for (const size of [MAX_DOWNLOAD_BYTES+1, -1, NaN]) await assert.rejects(api.download(id, size, new AbortController().signal))
})

test('binary reader rejects absent/wrong headers, truncation and oversized bodies', async () => {
  const signal = new AbortController().signal
  for (const item of [new Response('abc'), response('abc', 4), response('ab', 3), response('abcd', 3), Response.json({})]) {
    await assert.rejects(readDownload(item, 3, signal))
  }
  assert.equal((await readDownload(response('', 0), 0, signal)).size, 0)
})

test('disconnect discards even a fetch result delivered after abort', async () => {
  let release
  const delayed = new Promise(resolve => { release = resolve })
  const api = await service(async () => { await delayed; return response() })
  const pending = api.download(id, 3, new AbortController().signal)
  api.disconnect(); release()
  await assert.rejects(pending, { name: 'AbortError' })
})

test('cancelling a pending stream read releases the reader without producing a blob', async () => {
  let cancelled = false, reading
  const started = new Promise(resolve => { reading = resolve })
  const body = new ReadableStream({ pull() { reading() }, cancel() { cancelled = true } })
  const controller = new AbortController()
  const result = readDownload(new Response(body, { headers: { 'Content-Type': 'application/octet-stream', 'Content-Length': '3' } }), 3, controller.signal)
  await started; controller.abort()
  await assert.rejects(result, { name: 'AbortError' }); assert.equal(cancelled, true)
})
