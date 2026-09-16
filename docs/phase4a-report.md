# Phase 4A completion report

Date: 2026-09-08. Scope: Case Management only.

## Implemented behavior

Cases reuse Incident, its existing owner, identifiers, evidence and TimelineEvent
relationships. No new case/timeline system or dependencies were introduced.

Additive operator-only endpoints at `/api/v2/investigation/incidents`:

- GET: owner-scoped list, literal title/description search (`q`), status/severity
  filters, newest-first cursor pagination, limit 1–100 (default 50).
- GET `/{id}`: owned-case detail; foreign and absent cases return 404.
- POST: title required; optional description/severity default to empty/medium.
  Owner is the authenticated operator, status starts open and revision starts 0.
- PATCH `/{id}`: title, status and strict nonnegative expected_revision required;
  omitted description/severity remain unchanged. Server-owned fields are rejected.

Lifecycle: open → investigating → closed; closed → investigating explicitly
reopens a case. Same-status edits are allowed. Invalid transitions return 422;
stale revisions or a failed conditional update return 409. The service uses an
owner-and-revision SQL compare-and-swap and commits once in the route transaction.
Database failures roll back and return a sanitized 503. Writes never auto-retry.
Case status does not cancel jobs or change upload, evidence, custody or retrieval
authorization. Case edits do not fabricate evidence custody events.

Cases navigation offers search, pagination, creation, details, severity/status
editing and conflict recovery. The case workspace embeds existing evidence search,
details, notes/tags, custody, retrieval and timeline components with incident filters
locked to the selected case. Timeline event links retain the existing global detail
route. Evidence details reject a mismatched case association. Operator tokens remain
only in the existing in-memory client; reload/disconnect/401 clears the connection.

## Migration decision and database verification

Incident previously had no revision column. Reliable atomic stale-write detection
required one additive column; migration 0005 adds `incidents.revision`, non-null
integer with server default 0. Historical migrations 0001–0004 are unchanged.
This preserves the upgrade path from 0004, not runtime compatibility with an
unmigrated database: apply 0005 before using the updated application.

Before editing, the development database was confirmed at 0004 and backed up using
SQLite's backup API to `backend/var/backups/shadowvault-before-phase4a-20260908T093607Z.db`.
Backup integrity passed. The development database was then upgraded to 0005. Every
original table's original columns/records were compared before and after (excluding
the migration version marker), with no changes. Integrity and foreign-key checks
passed. A separate populated 0004 fixture verifies preserved legacy rows, revision
defaults, repeatable upgrade and refusal of destructive downgrade. Recovery uses a
reviewed backup restore; 0005 is forward-only.

## Final verification

- `PYTHONPATH=backend backend/.venv/Scripts/python.exe -m unittest discover -s tests -v`:
  **115 passed, 0 failures, 0 errors, 0 skipped** (20.985 seconds).
- `npm --prefix frontend test`: **28 passed, 0 failed, 0 skipped, 0 cancelled**.
- `npm --prefix frontend run typecheck`: passed, no TypeScript errors.
- `npm --prefix frontend run build`: passed; 54 modules; JS 244.02 kB / 74.30 kB gzip.
- `npm --prefix frontend run test:browser`: **31 passed, 0 failed** on final source (33.4 seconds).

New coverage: eight backend case API tests plus one populated migration test,
four frontend service tests and five browser workflows. Tests cover owner/token
boundaries, input validation, lifecycle, omitted-field preservation, bound cursors,
stale writes, conditional-update failure, rollback, creation, scoped components,
conflict recovery, authentication clearing, reload and mobile navigation.

The original 106 backend, 24 frontend service and 26 browser tests remain passing.
The backend suite includes the actual Windows collector HTTP/SQLite round trip,
upload retry/receipt behavior, manifest hardening and retrieval cleanup hardening.
Phase 3A timeline and Phase 3B verified-copy/custody regressions pass.

One earlier browser run had 30 passes and one failed exact-label lookup. The case
status selector now has an explicit label association. Another full run exposed an
existing download test race: it asserted URL revocation immediately after navigation,
before React cleanup completed. That assertion now waits for observable revocation
with Playwright polling, retaining the same requirement.
Final warnings are the existing Starlette TestClient/httpx deprecation and browser
runner NO_COLOR/FORCE_COLOR environment warning. No dependency changes were made.

## Exact source/document inventory

Added:

- `backend/migrations/versions/0005_incident_revision.py`
- `backend/app/schemas/incident.py`
- `backend/app/services/incidents.py`
- `backend/app/api/routes/investigation_incidents.py`
- `tests/test_incidents.py`
- `tests/test_incident_migrations.py`
- `frontend/src/features/cases/contracts.ts`
- `frontend/src/features/cases/CaseForm.tsx`
- `frontend/src/features/cases/CaseList.tsx`
- `frontend/src/features/cases/CaseWorkspace.tsx`
- `frontend/tests/cases.test.mjs`
- `frontend/tests/browser/cases.spec.ts`
- `docs/phase4a-report.md`

Modified:

- `backend/app/models/incident.py`
- `backend/app/main.py`
- `tests/test_migrations.py`
- `tests/test_retrieval.py`
- `tests/test_timeline_migrations.py`
- `frontend/src/features/evidence/service.ts`
- `frontend/src/features/evidence/InvestigationWorkspace.tsx`
- `frontend/src/features/evidence/EvidenceSearch.tsx`
- `frontend/src/features/evidence/EvidenceDetailsPage.tsx`
- `frontend/src/features/timeline/TimelinePanel.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/Layout.tsx`
- `frontend/tests/browser/download.spec.ts`
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/setup.md`

Historical migration tests now expect head 0005. The 0003 timeline fixture inserts
through the reflected historical Incident table, avoiding use of the newer ORM
against an old schema; its preservation assertions remain. The original 0004
forward-only check still explicitly tests 0004.

Generated local artifacts: migrated `backend/shadowvault.db`, the backup above,
rebuilt `frontend/dist/index.html` and hashed CSS/JS assets, Playwright test results
and Python bytecode caches. These are not dependency or application source changes.
The four isolated browser fixture directories created during this work were removed;
the pre-existing fixture and development database backups were retained.
No agent source, dependency lockfile, upload/retrieval service or original migration
was changed in Phase 4A.

## Limitations and stopping point

- Existing single-owner operator provisioning remains; no browser login/session,
  team access, ownership transfer, deletion, case audit history or closed timestamp.
- Case revision safety applies to these API writes; trusted direct database edits
  must respect the same revision protocol.
- An uncertain creation response requires reviewing the list before manually
  creating again; creation has no idempotency key and is never automatically retried.
- Lists are live, not snapshot-isolated, and large-data performance and non-SQLite
  database/browser platforms are not verified.
- No AI, malware analysis, automatic decisions, Linux collection or Phase 4B work.

Phase 4A is complete. Further implementation requires approval.
