# Phase 5A implementation report

Completed 2026-09-08. Scope: Incident-as-Case timestamp foundation only.

## Outcome

Incident remains the sole Case entity. Inspection confirmed updated_at was absent
from the model, response schema and revision-0005 database. Added one nullable UTC
column, with no new table, relationship, route, dependency or lifecycle state.

New ORM-created incidents (including the existing trusted CLI path) initialize
updated_at to exactly created_at. Existing creation time is never changed by PATCH.
Each accepted case PATCH sets server UTC updated_at in the same owner-and-revision
conditional SQL update that increments revision. Same-value accepted PATCH requests
retain the existing revision-increment behavior. Failed, unauthorized, invalid or
stale requests do not commit timestamp changes. GET does not initialize missing times.

Case response schemas expose nullable updated_at additively on list/detail/create/
update. Inputs still reject server-owned fields, including both timestamps. Existing
field requirements, status transitions, ownership checks and error contracts remain.
The frontend type accepts optional/null timestamps for compatibility with older
servers; existing views and layout remain unchanged. No timestamp display was needed.

## Migration and development database verification

Added `0006_incident_updated_at`, down_revision `0005`. It adds only nullable
`incidents.updated_at`, without a backfill or server default. Historical last-update
times remain unknown/null. Existing IDs, created_at, revisions, ownership and
relationships are preserved. Historical migrations 0001–0005 are untouched.

Before editing, confirmed the local database at 0005 with no updated_at column.
SQLite backup API created:

`backend/var/backups/shadowvault-before-phase5a-20260908T102043Z.db`

Backup integrity passed. Applied the existing migration runner to the development
database, which is now **0006**. Compared every original column/row in every original
table against the backup, excluding only the migration version marker: all equal.
Historical updated_at values remain null. `PRAGMA integrity_check` returned `ok`;
`PRAGMA foreign_key_check` returned zero violations.

A populated 0005 fixture independently verifies preserved records/revisions, null
historical timestamps, repeatable upgrade, integrity and foreign keys. Existing
populated timeline/investigation migration tests also run through the new head and
retain their old-column and custody-chain assertions. The original 0004 → 0005
test explicitly targets 0005 so its historical downgrade guard remains tested.

0006 is forward-only. Deploy migration before the updated ORM. Recovery requires a
reviewed backup restore or forward fix; restoring a pre-upgrade backup after new
writes can discard legitimate work. Old writers/direct SQL do not maintain the new
timestamp convention and should not be mixed with the updated application.

## Exact verification results

- Backend: `PYTHONPATH=backend backend/.venv/Scripts/python.exe -m unittest discover -s tests -v`
  — **118 passed, 0 failures, 0 errors, 0 skipped**, final run 22.076 seconds.
- Frontend services: `npm --prefix frontend test`
  — **29 passed, 0 failed, 0 skipped, 0 cancelled**, 518.9987 ms.
- TypeScript: `npm --prefix frontend run typecheck` — passed, no errors.
- Production: `npm --prefix frontend run build` — passed, 54 modules, Vite 1.08 s.
  Output JS 244.02 kB / 74.30 kB gzip; CSS 5.34 kB / 1.69 kB gzip.
- Browser: `npm --prefix frontend run test:browser`
  — **31 passed, 0 failed**, 33.7 seconds, using the existing Windows browser setup.

Added three backend tests: populated 0005 migration; timestamp ownership/atomicity/
null retrieval; and full non-Incident table snapshot preservation during case edit,
including linked evidence, timeline and a verified custody baseline. Added one
frontend service compatibility test. Extended the real browser creation/update
workflow to check timestamps while preserving the original lifecycle/reload assertions.

All previous 115 backend tests remain passing, including authorization, CAS failure,
commit rollback, Windows collector HTTP/SQLite round trip, upload receipt retry,
timeline provenance, custody and verified-copy retrieval. All prior frontend service
and browser workflows pass. No implementation test failures occurred in this phase.

Warnings: existing Starlette TestClient/httpx deprecation and browser runner
NO_COLOR/FORCE_COLOR warning. The backend's expected readiness-failure test emits
`Database readiness check failed` and passes. No dependency changes were made.

## Changed file inventory

Added:

- `backend/migrations/versions/0006_incident_updated_at.py`
- `docs/phase5a-implementation-report.md`

Modified:

- `backend/app/models/incident.py` — nullable UTC field and ORM creation initialization.
- `backend/app/services/incidents.py` — timestamp within existing revision CAS.
- `backend/app/schemas/incident.py` — additive nullable response field.
- `frontend/src/features/cases/contracts.ts` — optional nullable client field.
- `tests/test_incidents.py` — timestamp and unchanged relationship/custody tests.
- `tests/test_incident_migrations.py` — new populated upgrade test; retain historical 0005 check.
- `tests/test_migrations.py` — expected current head 0006.
- `tests/test_timeline_migrations.py` — expected current head 0006; original preservation checks retained.
- `tests/test_retrieval.py` — expected current head 0006; retrieval behavior unchanged.
- `frontend/tests/cases.test.mjs` — timestamp response compatibility.
- `frontend/tests/browser/cases.spec.ts` — real create/update timestamp assertions.
- `docs/setup.md` — migration/deployment instructions.

Local generated artifacts: the backup above, migrated `backend/shadowvault.db`,
Python caches, rebuilt frontend/dist output and browser test results. These are
separate from the source inventory. The isolated browser fixture from this run is
removed after verification; pre-existing fixtures and backups are retained.

## Compatibility and remaining limitations

- No Case table, ownership transfer, RBAC, case history, audit event, AI, automatic
  decision or background workflow was implemented.
- Evidence, custody, timeline, storage and retrieval implementation files were not
  changed. Original evidence and custody records remain untouched by case edits.
- updated_at is not case history or a guaranteed monotonic clock. Revision remains
  the conflict token; historical last-edit times cannot be reconstructed.
- Normal ORM creation initializes timestamps; later trusted direct ORM/bulk SQL edits
  must use the case service or explicitly follow its timestamp/revision convention.
- Timestamp exposure is additive; the frontend does not add a new timestamp view.
- Database verification remains SQLite/Windows-specific; no new platform is claimed.

Phase 5A complete. Stop here; later phases require separate approval.
