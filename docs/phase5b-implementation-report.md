# Phase 5B implementation report

Date: 2026-09-08. Scope: the two consumer refinements identified in
[the completed Case API audit](phase5b-case-api-audit.md).

## Implemented

- Case list now exposes low/medium/high/critical severity and All. Search submits
  severity alongside the existing text/status fields through the existing API client.
  Submitting a search resets the cursor and previous-page history. Pagination retains
  the applied filters; choosing All omits severity from the query.
- Case details displays Last updated separately from Created and Revision. It renders
  the server timestamp in UTC; null or absent values display Unknown. It does not
  substitute creation time or imply an audit history.

Incident remains the Case source of truth. No backend application file, route,
schema, authentication code or client transport changed. Existing revision-safe
writes, timestamp maintenance, lifecycle, authorization and unknown-time semantics
are reused. Existing case navigation, conflict recovery, evidence/timeline filters,
custody and download components are unchanged.

## Exact changed-file inventory

Modified:

- `frontend/src/features/cases/CaseList.tsx` — severity selector and combined search.
- `frontend/src/features/cases/CaseWorkspace.tsx` — UTC/Unknown last-update display.
- `tests/test_incidents.py` — one added regression for severity, owner-scoped totals,
  cursor binding, invalid severity and read-only results.
- `frontend/tests/cases.test.mjs` — extend existing serialization test for severity.
- `frontend/tests/browser/cases.spec.ts` — three new browser tests for null/absent
  timestamps and combined filter/pagination reset; extend real API search and update
  workflows to assert severity results and timestamp presentation.

Added:

- `docs/phase5b-implementation-report.md` — this report.

Generated verification artifacts are frontend/dist, Playwright test results and
Python caches. They are separate from the source inventory. The isolated browser
fixture created for this run is removed after verification; pre-existing fixtures
and all existing database backups are retained.

## Migration and database result

**No migration required or added.** The audit establishes that all required API
fields already exist. Database remains at **0006**; no upgrade or migration backup
was necessary. Tests used isolated databases, not development data.

Read-only development database verification: revision 0006, integrity_check `ok`,
foreign_key_check zero violations. SHA-256 before/after:
`40e719fc1cd34949030ec01aea44e73e41e0eb094722f5d8412f1e8131f02966`.
The database file is unchanged. Historical migration preservation tests still run
as part of the complete backend suite; no new upgrade is claimed for this phase.

## Verification results

- `PYTHONPATH=backend backend/.venv/Scripts/python.exe -m unittest discover -s tests -v`:
  **119 passed, 0 failures, 0 errors, 0 skipped**, 32.784 seconds.
- `npm --prefix frontend test`: **29 passed, 0 failed, 0 skipped, 0 cancelled**,
  1053.7466 ms. Existing timestamp-null/absent compatibility tests also pass.
- `npm --prefix frontend run typecheck`: passed, zero TypeScript errors.
- `npm --prefix frontend run build`: passed; 54 modules, Vite 1.83 seconds.
  JS 244.44 kB / 74.42 kB gzip; CSS 5.34 kB / 1.69 kB gzip.
- `npm --prefix frontend run test:browser`: **34 passed, 0 failed**, 53.3 seconds.

Windows collector/upload regression ran within the full backend suite, including
`test_collection_e2e.CollectionEndToEndTests.test_real_cli_upload_and_repeat` and
the collection, shared agent-core and Windows-agent tests. The real CLI/HTTP/SQLite
upload and repeated receipt round trip passed. No collector source changed.

New browser coverage distinguishes real server integration (severity matching and
updated timestamp) from controlled response fixtures (null/absent timestamp and
cursor-reset assertions). No claim is made that mocked pagination creates real
backend records; backend cursor/ownership checks are tested separately.

No test failures occurred. Existing warnings remain: Starlette TestClient/httpx
deprecation and browser NO_COLOR/FORCE_COLOR environment warning. The readiness
failure test intentionally logs a database readiness failure and passes. No packages,
frameworks or lockfiles were changed to suppress these warnings.

## Compatibility and limitations

All prior backend and browser regressions passed: Phase 2A collection/upload/Windows
receipts; Phase 2B investigation metadata, notes/tags and custody; Phase 3A observations,
provenance and retries; Phase 3B verified-copy retrieval and cleanup; Phase 4A case
lifecycle/ownership/CAS; Phase 5A timestamp atomicity and migration preservation.
Original evidence, timeline, custody and retrieval behavior was not modified.

Severity takes effect on Search cases, matching existing text/status behavior.
Lists remain live and ordered by creation time, not last update. Unknown historical
last-update times remain unknown. updated_at is not monotonic history or a revision
token. Existing configured operator authentication remains; no browser sessions.

Team ownership, RBAC, case history/audit events, AI, automation and background
workflows remain explicitly out of scope. No new API, Case table, six-state workflow,
report/export or cross-incident sharing was introduced.

Phase 5B complete. Stop here; Phase 5C requires separate approval.
