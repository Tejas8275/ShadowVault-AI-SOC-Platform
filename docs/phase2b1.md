# Phase 2B-1 investigation backend

This slice adds metadata and history without changing acquisition. Browser login,
frontend investigation pages, AI, Linux collection, and integrity-check execution
are not implemented. Existing Phase 1 placeholders and Phase 2A collection remain compatible.

## Setup and migration

Use the existing backend environment and operator provisioning in [Phase 2A](phase2a.md).
No new dependencies or credentials are needed. Stop writers and back up the
configured database before running, from the repository root:

```powershell
backend/.venv/Scripts/python.exe -m app.db.migrate
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend
```

Migration `0003` extends evidence and creates custody_events, evidence_notes,
evidence_tags, and evidence_integrity_checks. It preserves all original metadata,
uses bounded batches to register migration-time baselines, and is repeatable.
It deliberately refuses downgrade: do not drop custody data to reverse deployment.
Use a reviewed backup restoration when rollback is required. Only SQLite has been verified.

## API contract

All paths below start with `/api/v2/investigation`. Send the existing operator
credential as `Authorization: Bearer <operator-token>` over HTTPS outside local
development. Agents cannot call these endpoints. All reads, counts, and writes
require an active operator who owns the incident and, when present, the collection job.
Inaccessible evidence returns 404. Missing or invalid credentials return 401.

- `GET /evidence`: search; returns `items`, authorized `total`, and `next_cursor`.
- `GET /evidence/{id}`: details, annotation revision, tags, custody head, note count,
  provenance IDs, initial verification, and latest terminal integrity result.
- `PATCH /evidence/{id}/annotations`: update title, review state, and/or current tags.
- `POST /evidence/{id}/notes`: append an attributed note; returns 201 and the new revision.
- `GET /evidence/{id}/notes`: notes in creation-time/UUID order with `limit` and `cursor`.
- `GET /evidence/{id}/custody`: sequence order with `after_sequence` (exclusive),
  `limit`, current head, and `next_sequence` to pass as the next `after_sequence`.

There are six HTTP operations on five paths. All pages default to 50 and allow
1–100 items. Reads do not mutate custody. Safe response schemas omit storage keys
and credentials. Notes and paths may contain sensitive case information and are
available only within the ownership boundary.

### Search

Optional filters: `incident_id`, `collection_job_id`, `agent_id`, `q`, `sha256`,
repeated `tags`, `review_state`, `verification_status`, `integrity_result`,
`created_from`, `created_to`, `collected_from`, `collected_to`, `min_size`, `max_size`.
`sort` is `newest` (default) or `oldest`; ordering uses creation time and UUID.
Date bounds require timezone-aware values and ranges are inclusive. Text searches
filename, display title, and source path; `%` and `_` are literal characters.
All supplied tags must match. SHA-256 accepts either case. Unknown parameters fail validation.

Use `next_cursor` with the same filters and sort. Cursors are bound to the operator
and query, not signed access tokens; authorization is always reapplied. Pagination
is a live view, not a frozen snapshot across requests. Totals may change with writes.

### Annotation examples

```json
{"expected_revision":0,"display_title":"Suspicious document","review_state":"in_review","tags":["document","priority"]}
```

```json
{"expected_revision":1,"body":"Reviewed the acquisition metadata."}
```

Every mutation requires the revision returned by evidence details. A stale revision
returns 409; reload before retrying. Metadata, tags/notes, revision, and custody events
commit together. Database write failures return a sanitized 503; reload before retrying
because an ambiguous commit outcome must not be assumed to mean failure.

Review states: `unreviewed`, `in_review`, `reviewed`. Null title clears the title;
empty tag list clears tags. Tags normalize to lowercase, are deduplicated, and allow
1–64 ASCII letters/digits/dots/underscores/hyphens, starting with a letter or digit.
Maximum 20 submitted tags, 200 title characters, 10,000 note characters. Request bodies
are limited to 128 KiB. Acquisition fields, incident reassignment, actor IDs, and
client-selected custody timestamps are never accepted as annotation inputs.

## Custody and integrity semantics

Migration registers existing evidence with `baseline_registered`, system actor
`migration:0003`, and the actual migration timestamp. This does not imply the
file was acquired or reverified at that time. Evidence arriving through unchanged
Phase 2A uploads has `custody_started=false` until the first annotation or note;
that transaction records a baseline and the user action. No historical actor or
timestamp is fabricated, and read/download auditing is not provided in this slice.

User events retain an authenticated user ID and display-name snapshot. Note events
include the note ID and SHA-256 of its text. Custody events include schema version,
sequence, operation ID, details, UTC time, previous hash, and event hash. Services
never commit independently. ORM updates/deletes of notes and custody events fail;
there are no HTTP edit/delete operations for them.

`app.services.custody.verify_chain` checks canonical hashes and sequence linkage
against the captured stored head. It is an internal read-only function, not a
byte-integrity check or external trust anchor. A privileged database operator can
bypass ORM guards and rewrite the entire chain/head; independent signed checkpoints,
database access controls, backups, and retention controls are future operational work.

`initial_verification_status` / `initial_verified_at` represent acquisition history.
`integrity_result` is `not_checked` without a terminal check; otherwise it reports
the latest terminal record (`matches`, `mismatch`, `missing`, or `unavailable`).
Queued/running checks never claim successful verification. Check records include
expected/observed hashes and sizes, requester, lifecycle timestamps, lease fields,
attempt count, and error code. This is a database structure only: no enqueue API,
worker, storage reread, or automatic integrity event is supplied yet.
