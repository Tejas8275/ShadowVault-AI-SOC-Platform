# Phase 5C completion report

Date: 2026-09-08. Scope: minimal append-only Case History linked to Incident.

## Implemented architecture

Incident remains the sole Case entity. Added one table, `case_history_events`, with
no Incident columns or relationship changes. It stores creation, accepted case updates
and migration baselines. Each event has the Incident revision, type/version, actor
ID and display-label snapshot, source, UTC recording time and bounded field changes.
Unique `(incident_id, revision)` supplies ordering and duplicate protection.

Supported field changes are title, description, status and severity. One accepted
PATCH produces one grouped event, including combined changes. Same-value saves keep
the existing revision/timestamp increment and produce an empty changes object, shown
as “Case saved — no field changes”. Close/reopen retains the existing lifecycle.

The case service writes history before the existing route commits. Case fields,
revision, updated_at and history therefore commit or roll back together. The timestamp
for an update event equals that accepted case update's timestamp; creation uses
created_at. Stale revision/CAS failures remain 409 and produce no event. History
validation/SQL failure cannot commit an unaudited case mutation. No automatic retry.

The trusted create-incident CLI now delegates to the same tracked service, retaining
its configured operator ownership checks and original JSON output. Its source is
explicitly trusted_cli. Arbitrary direct ORM/SQL writes are not automatically attributed.

## Migration, backup and integrity

Added migration **0007**, down_revision **0006**. Historical migrations are unchanged.
It creates only the history table, constraints/unique index and SQLite UPDATE/DELETE
rejection triggers. Existing cases receive one system baseline at their current
revision with migration recording time. Earlier changes are not reconstructed.
Legacy oversized/unsupported values stop preflight without truncating data or creating
partial schema. Migration uses frozen definitions, not application ORM hooks.

Before source editing/migration, SQLite backup API created and integrity-checked:

`backend/var/backups/shadowvault-before-phase5c-20260908T165309Z.db`

Development database upgrade **0006 → 0007 passed**. Compared every original column/
record in every original table against the backup, excluding only alembic_version:
all preserved. `PRAGMA integrity_check`: ok. `PRAGMA foreign_key_check`: zero violations.
The local development database had zero incidents; zero baseline rows is therefore
expected. Separate populated migration tests cover baseline revisions 0 and 7,
historical preservation, repeatable upgrades, failed preflight and downgrade refusal.
Existing populated timeline/custody migration tests also upgrade through 0007 and
retain their original-data and chain-verification assertions.

0007 is forward-only and deliberately requires the verified SQLite deployment for
its database guards. Back up and stop writers before deployment; do not mix old case
writers with the updated API/CLI. A restore after new writes can discard work and must
be reviewed; no automatic destructive rollback is supplied.

## API and authorization

Added exactly one endpoint:

`GET /api/v2/investigation/incidents/{id}/history`

Optional after_revision >= 0, omitted on the initial page so revision 0 is included;
limit 1–100, default 50. Returns items, tracking_started, tracking_started_revision
and next_revision (null when there are no additional rows). Ordered by revision,
not wall-clock time. A read never writes a baseline or changes the Incident.

Uses the existing Operator dependency and owned-Incident check before querying
history. Foreign cases return 404; missing/device/inactive credentials are rejected.
Responses set Cache-Control: no-store. No history POST/PATCH/DELETE exists. Actor,
source and timestamp are internal values, never trusted client assertions. Existing
case request/response contracts are unchanged.

ORM update/delete guards and SQLite triggers protect append-only behavior. Existing
evidence custody is separate: case edits do not append evidence events, and uploads,
annotations, observations or retrieval do not manufacture case events. Case-history
changes contain only case fields; credentials, internal storage paths and evidence
payloads are not copied from request context or evidence storage. User-authored case
text is retained as supplied/validated and escaped by React; it can itself contain
sensitive information and is not automatically redacted.

## Frontend

CaseWorkspace embeds a Case History panel using the existing in-memory authenticated
client. It shows revisions, actor/source, UTC time, grouped expandable before/after
text, migration baseline disclosure and explicit untracked state. It refreshes after
case save, supports load-more (including revision 0), manual refresh/retry, loading
and error states. Requests abort on unmount and cannot publish stale responses.
401 clears the shared operator connection. Existing evidence/custody/timeline views,
severity filter, last-update display and conflict/draft behavior remain compatible.

## Final verification

- Complete backend: `PYTHONPATH=backend backend/.venv/Scripts/python.exe -m unittest discover -s tests -v`
  — **129 passed, 0 failures, 0 errors, 0 skipped** (44.243 seconds).
- Frontend services: `npm --prefix frontend test`
  — **31 passed, 0 failed, 0 skipped, 0 cancelled** (786.6236 ms).
- `npm --prefix frontend run typecheck` — passed, zero TypeScript errors.
- `npm --prefix frontend run build` — passed, 55 modules; JS 247.06 kB / 75.09 kB gzip,
  CSS 5.34 kB / 1.69 kB gzip; Vite 1.72 seconds.
- `npm --prefix frontend run test:browser` — **38 passed, 0 failed** on final run (56.1 seconds).

New coverage comprises eight focused backend history tests and two migration tests,
two frontend service tests and four browser workflows. It covers creation, grouped
metadata/severity/status changes, close/reopen, same-value save, actor-label retention,
UTC timestamps, pagination, denied cross-case/device access, real concurrent writes,
stale replay, rollback after history insertion/commit failure, SQL/ORM append-only
guards, uniqueness, trusted CLI output and migration preflight/preservation. Browser
tests cover real save/render/refresh, escaped text, mocked loading/error/empty states,
baseline/revision-0 paging, mobile layout and authentication clearing.

Existing 119 backend tests and all previous service/browser tests remain passing.
The Windows collector real HTTP/SQLite upload and repeated receipt round trip ran
inside the backend suite and passed, alongside shared-core/manifest/Windows file
tests. Phase 2B annotations/custody, Phase 3A timeline/provenance, Phase 3B retrieval,
Phase 4A case access/concurrency, Phase 5A timestamps and Phase 5B filters/display
regressions all pass. The full upload→annotation→timeline→retrieval test additionally
asserts that case history remains unchanged.

Earlier runs: the old model table-inventory expectation failed until updated for the
new table; all behavior tests passed. Two browser runs each had 37 passes and one
test failure: an exact initial-read count under React development mode, then an expiry
simulation racing the initial authorized load. The tests now allow repeated initial
reads and wait for initial load before simulating expiry. These did not require
changes to authorization or product behavior.

Warnings remain the existing Starlette TestClient/httpx deprecation and browser
NO_COLOR/FORCE_COLOR environment warning. The intentional readiness-failure test
logs a sanitized readiness failure and passes. No dependency changes.

## Exact changed-file inventory

Added:

- `backend/app/models/case_history.py`
- `backend/app/schemas/case_history.py`
- `backend/app/services/case_history.py`
- `backend/migrations/versions/0007_case_history.py`
- `frontend/src/features/cases/CaseHistory.tsx`
- `tests/test_case_history.py`
- `tests/test_case_history_migration.py`
- `frontend/tests/case-history.test.mjs`
- `frontend/tests/browser/case-history.spec.ts`
- `docs/phase5c-implementation-report.md`

Modified:

- `backend/app/models/__init__.py`
- `backend/app/services/incidents.py`
- `backend/app/api/routes/investigation_incidents.py`
- `backend/app/cli.py`
- `frontend/src/features/cases/contracts.ts`
- `frontend/src/features/cases/CaseWorkspace.tsx`
- `frontend/src/features/evidence/service.ts`
- `tests/test_incidents.py`
- `tests/test_incident_migrations.py`
- `tests/test_migrations.py`
- `tests/test_models.py`
- `tests/test_retrieval.py`
- `tests/test_timeline_migrations.py`
- `docs/setup.md`

Historical migration tests explicitly retain 0005/0006 downgrade checks; current-head
expectations advance to 0007. Case-edit preservation checks exclude only Incident and
its new CaseHistory table; every evidence/timeline/custody table remains compared.

Local generated artifacts: database backup above, migrated backend/shadowvault.db,
frontend/dist output, Playwright results and Python caches. Isolated browser fixtures
created by this phase are removed after verification; pre-existing fixture and backups
are retained. No agent, evidence storage, custody or timeline implementation changed.

## Limitations and stop

Append-only application/SQLite controls do not defeat an administrator who drops
triggers or replaces the database. This is not a cryptographic case chain, an
external audit anchor or forensic proof of event truth. Shared-token attribution
identifies the configured principal; trusted CLI source is labeled honestly.
Older history cannot be reconstructed. Direct maintenance writes bypass service
attribution and must follow a reviewed procedure. Historical case text is retained;
there is no redaction/deletion or retention workflow. Case creation still has no
idempotency key; uncertain creation requires manual list review.

No teams/RBAC, ownership transfer, authentication sessions, case notes, new lifecycle,
AI, automation, background workers, reporting/export or duplicated custody events.
Incident remains Case. Phase 5D has not started. Stop after Phase 5C completion.
