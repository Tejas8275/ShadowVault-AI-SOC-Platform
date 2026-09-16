import test from 'node:test'
import assert from 'node:assert/strict'
import { prepareSubmission } from '../src/features/timeline/contracts.ts'
import { createInvestigationService } from '../src/features/evidence/service.ts'
const draft = { occurred_at: '2026-09-06T12:30:00+05:30', title: ' Observation ', description: ' Reported ', source: ' Manual ', source_locator: '' }

test('timeline submission preserves offset and rejects inferred or naive timestamps', () => {
  const payload = prepareSubmission(draft, 'fixture-id')
  assert.equal(payload.occurred_at, draft.occurred_at)
  assert.equal(payload.title, 'Observation')
  assert.equal(payload.source_locator, null)
  assert.equal(payload.submission_id, 'fixture-id')
  for (const occurred_at of ['', '2026-09-06T12:30:00', 'not a date']) assert.throws(() => prepareSubmission({ ...draft, occurred_at }, 'id'))
  assert.throws(() => prepareSubmission({ ...draft, title: ' ' }, 'id'))
})

test('timeline endpoints share the operator client without changing evidence methods', async () => {
  const calls = []
  const api = createInvestigationService('http://localhost/api/v2/investigation', () => {}, async (url, options) => {
    calls.push({ url, options }); return Response.json({})
  })
  await api.connect('sv_operator_fixture')
  await api.createTimeline('evidence-id', prepareSubmission(draft, 'submission-id'))
  await api.timelineDetails('event-id')
  await api.timelineSearch({ incident_id: ' incident-id ', q: '%_', occurred_from: draft.occurred_at }, 'opaque+/=')
  assert.equal(calls.length, 4)
  assert.ok(calls[1].url.endsWith('/evidence/evidence-id/timeline-events'))
  assert.equal(JSON.parse(calls[1].options.body).occurred_at, draft.occurred_at)
  assert.ok(calls[2].url.endsWith('/timeline-events/event-id'))
  const query = new URL(calls[3].url).searchParams
  assert.equal(query.get('incident_id'), 'incident-id'); assert.equal(query.get('cursor'), 'opaque+/=')
  assert.equal(query.get('occurred_from'), draft.occurred_at)
  api.disconnect()
  await assert.rejects(api.timelineDetails('event-id'), { status: 401 })
})

test('timeline conflicts and uncertain outcomes are surfaced without automatic retries', async () => {
  for (const status of [409, 422, 503]) {
    let count = 0
    const api = createInvestigationService('http://localhost/api', () => {}, async () => ++count === 1 ? Response.json({}) : Response.json({}, { status }))
    await api.connect('sv_operator_fixture')
    await assert.rejects(api.createTimeline('id', prepareSubmission(draft, 'same-id')), { status })
    assert.equal(count, 2)
  }
})

test('explicit timeline retry sends the identical submission payload', async () => {
  const bodies = []
  const api = createInvestigationService('http://localhost/api', () => {}, async (_, options) => {
    if (options.body) bodies.push(options.body)
    return bodies.length === 1 ? Response.json({}, { status: 503 }) : Response.json({})
  })
  await api.connect('sv_operator_fixture')
  const payload = prepareSubmission(draft, 'same-id')
  await assert.rejects(api.createTimeline('id', payload), { status: 503 })
  await api.createTimeline('id', payload)
  assert.equal(bodies[0], bodies[1])
})
