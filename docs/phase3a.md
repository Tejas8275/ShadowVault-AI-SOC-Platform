# Phase 3A — evidence-linked timeline observations

This phase extends the existing `timeline_events` table and existing investigation
workspace. Observations are investigator-reported accounts, not automatically
established forensic findings. No evidence bytes are read, parsed or executed.

## Migration and startup

Stop writers and keep a database backup. From the repository root with the existing
backend environment installed:

```powershell
backend/.venv/Scripts/python.exe -m app.db.migrate
```

Revision 0004 follows 0003. It adds an evidence/incident unique index and extends
TimelineEvent with evidence ID, origin, reported timestamp, source locator, recorder
label, submission UUID and request fingerprint. Existing rows retain every original
column value and receive `origin=legacy`; unknown provenance stays null. No historic
evidence links, actor snapshots or custody actions are invented. No second timeline
system or additional table is created. Downgrade is refused; recovery requires a
reviewed backup restore. Only SQLite is verified.

Use the existing backend/frontend startup and operator provisioning instructions.
No dependency, credential or frontend environment variable is added.

## API

All operations use the existing `Authorization: Bearer <operator-token>` credential.
Agent credentials cannot call these operations. No credential belongs in a URL.

- `POST /api/v2/investigation/evidence/{evidence_id}/timeline-events`
- `GET /api/v2/investigation/timeline-events`
- `GET /api/v2/investigation/timeline-events/{event_id}`

Example create body:

```json
{
  "occurred_at": "2026-09-06T12:30:00+05:30",
  "title": "Observed login entry",
  "description": "Investigator-reported account of the referenced record.",
  "source": "Manual examination account",
  "source_locator": "Record 12",
  "submission_id": "78d137de-3f2c-477d-9f50-8fd271913322"
}
```

Occurrence input must be an ISO timestamp with an explicit offset or Z. Numeric
timestamps and timezone-naive values are rejected. `occurred_at` is returned in
UTC. `reported_time` retains the parsed input's offset representation (canonical
ISO formatting, not exact original lexical formatting). `created_at` is server
recording time. The server supplies incident, recorder, recorder label and origin.

Title/source are required, at most 200 characters each. Description is at most
10,000 characters; optional locator at most 512. Text is trimmed and rejects NUL.
Unknown fields are rejected. The existing investigation body limit is 128 KiB.
The API never accepts a chosen actor, custody hash, origin, or creation timestamp.

Search requires `incident_id`. Optional filters: `evidence_id`, `occurred_from`,
`occurred_to`, `q`, `origin` (`legacy`/`investigator`), `sort` (`oldest` default or
`newest`), `limit` (1–100, default 50), and `cursor`. Date ranges are inclusive and
timezone-aware. Text searches title, description, source and locator, with literal
percent/underscore characters. Ordering uses occurrence time and UUID. Cursors
are bound to operator/query/sort; counts and every page reapply authorization.
Pages are live views rather than frozen snapshots.

Responses omit storage keys and internal request fingerprints. They include event,
incident, evidence, recorder, origin, timestamps, source/locator, title/description,
and submission ID. Legacy records show missing attribution/linkage honestly.

Status codes: 201 created; 200 identical retry; 401 invalid/inactive operator;
404 inaccessible incident/evidence/event; 409 changed-content submission or
concurrent write; 422 invalid input; 503 unconfirmed database operation.

## Transactions and retries

Choose a UUID for each intended observation and retain it with the exact payload
until the outcome is known. The server fingerprints the normalized payload, including
evidence ID and reported offset. An identical retry returns the original event;
the same recorder/submission ID with different content returns 409. Concurrent
losers can receive 409 and retry with the same ID/content. No background retry worker
is introduced. Authorization is checked before returning a duplicate receipt.

The timeline row, any necessary baseline, and `timeline_observation_added` custody
event commit together. Failure rolls them back together. The custody entry references
the event, canonical request fingerprint and evidence digest; it does not claim that
the observation's content was independently verified. Original evidence fields,
metadata revision and bytes are unchanged. Custody head/sequence alone advance.

When tracking has not started, creation records a system baseline with reason
`tracking_started_at_first_timeline_event`. Existing annotation defaults and migration
baselines retain their previous behavior and labels. Read endpoints create no events.
Legacy v1 timeline endpoints remain 501; existing investigation contracts are unchanged.

New observations cannot be edited/deleted through these APIs or normal ORM operations.
Legacy ORM behavior is preserved. Direct database administration remains trusted;
ORM guards and stored-head hash chains do not provide an external tamperproof anchor.

## Frontend workflow

Connect the existing operator, open evidence details, and use Add timeline observation.
Enter the occurrence timestamp explicitly; no acquisition or verification date is
substituted. Successful submission refreshes custody and provides an observation link.
Timeline navigation accepts an incident ID; no incident directory endpoint was added.
Observation details link back to the incident timeline and original evidence metadata.

After an unconfirmed save, the form freezes its payload and UUID. Review current
observations within the form if needed, then use Retry unchanged submission. The
review shows only a page ordered by occurrence time: absence is not proof of failure.
Identical retry is the authoritative deduplication path. Invalid-input rejection
allows editing. Writes never retry automatically. Navigating away or reloading
discards in-memory drafts and retry IDs; resolve ambiguous submissions before leaving.

Timeline/evidence share the same in-memory credential. Disconnect or 401 removes
private workspace state and cancels pending requests. Filter values and drafts are
not written to page URLs, logs or browser storage. Notes/observations render as text.
API query parameters necessarily carry filters to the authorized server; deployments
should handle access logs as sensitive investigation data.

## Scope and verification

No retrieval, file preview, AI, malware analysis, automatic extraction, integrity
worker, browser session system, Linux collector, correction/supersession or
multi-evidence observation model is included. Windows collector code and Phase 2A
upload flow are untouched. See [the completion report](phase3a-report.md) for exact
tests, backup, changed files, and remaining limitations.
