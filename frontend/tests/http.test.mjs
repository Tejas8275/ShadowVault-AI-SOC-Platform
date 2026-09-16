import assert from 'node:assert/strict'
import test from 'node:test'
import { ApiError, createApiClient } from '../src/services/http.ts'

test('client joins paths, sends JSON and returns response data', async () => {
  const api = createApiClient('http://localhost:8000/api/v1/', async (url, options) => {
    assert.equal(url, 'http://localhost:8000/api/v1/auth/login')
    assert.equal(options.headers.get('Content-Type'), 'application/json')
    assert.equal(options.headers.get('Accept'), 'application/json')
    assert.equal(options.body, '{"email":"test@example.com"}')
    assert.ok(options.signal instanceof AbortSignal)
    return Response.json({ status: 'ok' })
  })
  assert.deepEqual(await api('/auth/login', { method: 'POST', body: '{"email":"test@example.com"}' }), { status: 'ok' })
})

test('not implemented responses preserve API status and message', async () => {
  const api = createApiClient('/api/v1', async () => Response.json({ detail: 'Sign-in is not available yet.' }, { status: 501 }))
  await assert.rejects(api('/auth/login'), error => error instanceof ApiError && error.status === 501 && error.message === 'Sign-in is not available yet.')
})

test('validation details do not echo submitted credentials', async () => {
  const api = createApiClient('/api/v1', async () => Response.json({ detail: [{ input: 'private-test-value' }] }, { status: 422 }))
  await assert.rejects(api('/auth/login'), { message: 'Please check the information you entered.' })
})

test('non-JSON server failures have a readable fallback', async () => {
  const api = createApiClient('/api/v1', async () => new Response('<h1>Bad gateway</h1>', { status: 502 }))
  await assert.rejects(api('/health'), { message: 'Request failed (502).' })
})

test('empty success responses and network errors are handled', async () => {
  const empty = createApiClient('/api/v1', async () => new Response(null, { status: 204 }))
  assert.equal(await empty('/resource'), undefined)
  const failed = createApiClient('/api/v1', async () => { throw new TypeError('Failed to fetch') })
  await assert.rejects(failed('/health'), { message: 'Failed to fetch' })
})
