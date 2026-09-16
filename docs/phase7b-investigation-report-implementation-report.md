# Phase 7B — Case-Scoped Investigation Report Draft

Implemented: 2026-09-12. Final verification: 2026-09-13. **Status: complete and fully verified.** Scope: deterministic, authorized metadata report preparation and viewing. No AI or investigation decisions.

## Implementation

The existing Case workspace now offers **Create report draft**. An explicit read prepares a transient report containing case details/revision/status/timestamps, counts of included records, evidence metadata and hashes, recorded integrity status/custody heads, notes, timeline observations, indicator originals/corrections, custody event metadata and case history. Every source entry displays its stored record citation; evidence-linked entries retain case-scoped source links. Timeline/indicator source locators are displayed as inert text and never fetched.

Reports are organized into expandable source sections with readable labels, UTC generation time, a draft marker, an explicit authorized scope and limitations. The investigator can close/reopen the in-memory draft and explicitly request a plain-text download after reviewing it. No fake observations, narrative synthesis, threat verdicts or conclusions are produced.

Creation, loading, error, limit refusal, ready and download-requested states are distinct. Failure is not represented as an empty report. Preparation can be cancelled; retries require another user action. Report creation/viewing leaves the indicator panel mounted, preserving an unresolved indicator retry identity. Disconnect/case changes clear the authenticated workspace; case refresh/reload can discard transient drafts as before.

## Architecture and persistence decision

The Phase 7A audit was reviewed against current case, evidence, notes, custody, history, timeline and indicator routes/services, frontend consumers, tests and migration 0008. No prior report implementation was found. Existing models contain the required metadata; persistence is not required for this approved first slice.

There is no Report table or saved report ID. Creating a draft means materializing a read-only snapshot in memory. Viewing it again within the mounted component uses that snapshot. Another API request prepares a new snapshot; there is no server-side retrieval of a historical draft. A downloaded text file is the investigator's local copy, not original evidence or a signed report.

SQLite snapshot handling is local to the new service: release the authentication lookup transaction, explicitly issue `BEGIN`, collect authorized metadata, materialize the DTO, remove the SQLite progress handler and roll back the read transaction. This avoids assuming sqlite3 legacy transaction behavior provides a multi-query snapshot automatically. The transaction ends before response delivery. Current operator and case/evidence scope are checked again before returning the draft.

Limits are **2,000 selected source rows including tags, 2 MiB serialized UTF-8 JSON and a five-second preparation deadline**. Queries use remaining-budget limits, and SQLite progress checks bound query execution. Exceeding row/byte limits returns 413; timeout/database unavailability returns a sanitized 503. Nothing silently truncates into a report labeled complete. SQLite lock waits retain the existing driver timeout; this is a bounded synchronous pilot, not a distributed resource scheduler.

Completeness means all authorized rows within the documented projection, independent of current workspace filters. It does not mean every database column, every historical integrity-check attempt or all physical records in a case. Integrity presentation reuses the latest recorded terminal result. Custody entries include attribution, sequence and hash linkage, but omit arbitrary detail payloads; the report explains this omission. No chain verification or integrity executor runs.

## API changes

One additive read-only operation:

`GET /api/v2/investigation/incidents/{id}/report-draft`

Response: schema version 1, `status: draft`, server UTC `generated_at`, existing Incident response as `case`, authorized-scope label, section counts, citation-bearing records and limitations. Uses `Cache-Control: no-store`. Existing route response shapes, pagination/filter semantics and write operations remain unchanged.

The shared frontend API client reuses its existing in-memory token, Authorization header, no-store request, cancellation, safe error handling and 401 disconnect. It additionally rejects a report with a mismatched case or unsupported version before rendering.

## Security and record preservation

- Incident remains the Case entity. Every draft requires its existing owner authorization.
- Evidence requires the existing owner plus collection-requester visibility. Notes, tags and custody are selected through that evidence scope; timeline and indicators reuse their authorized query predicates.
- Correction links resolve only among included observations on the same evidence. Hidden or malformed cross-evidence predecessor references are not exposed.
- Field projection excludes storage keys, acquisition filesystem paths, request hashes and credentials. Free-text descriptions, filenames, notes and citations can still contain sensitive information; review before exporting. No automatic redaction is claimed.
- React renders source strings as text. Downloads use `text/plain`; no external URLs are opened, no Markdown/HTML interpreter is added, and temporary object URLs are revoked.
- No original blob is read or executed. No retrieval, upload, evidence annotation, timeline mutation, indicator write, custody append, case save or history append is invoked by report creation/viewing/saving.
- Case revision/history and evidence custody remain separate. Initial verification is not threat safety; custody display is not chain verification; retrieval-prepared events do not prove delivery.
- Snapshot contents are not live. A saved local file is outside later credential revocation. No browser storage or server-side report persistence was introduced.

## Exact changed-file inventory

Backend:

1. `backend/app/schemas/case_report.py` — transient report DTOs.
2. `backend/app/services/case_report.py` — bounded, authorized SQLite snapshot and explicit projections.
3. `backend/app/api/routes/investigation_incidents.py` — additive report read endpoint and reauthorization.

Frontend:

4. `frontend/src/features/cases/CaseReport.tsx` — creation, review, source sections, cancellation and text saving.
5. `frontend/src/features/cases/report.ts` — report contracts and inert text formatter.
6. `frontend/src/features/cases/CaseWorkspace.tsx` — report panel integration without replacing existing panels.
7. `frontend/src/features/evidence/service.ts` — authenticated case report method and scope/version check.
8. `frontend/src/styles.css` — responsive report field/source styling.

Tests:

9. `tests/test_case_report.py` — eight backend report regressions.
10. `frontend/tests/case-report.test.mjs` — four service/formatter regressions.
11. `frontend/tests/browser/case-report.spec.ts` — four browser workflows.
12. `tests/browser_fixture.py` — dedicated report evidence fixture, preserving existing fixtures' initial custody states.

Documentation:

13. `docs/phase7b-investigation-report-implementation-report.md` — this report.

No existing model, migration, dependency, authentication, agent, custody mutation, timeline mutation or case-history mutation file was changed. Production build output is generated verification output, not another source implementation.

## Verification

Backend: **152 passed**, including eight new report tests and `test_real_cli_upload_and_repeat`. Full command: `backend/.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_*.py' -v` with `PYTHONPATH=backend`. Duration: 41.051 seconds. Zero final backend failures/errors.

Frontend service/formatter tests: **44 passed, 0 failed, 0 skipped/cancelled**, using `npm --prefix frontend test`; 826.5865 ms.

TypeScript: **passed**, `npm --prefix frontend run typecheck`.

Production build: **passed**, `npm --prefix frontend run build`; 61 modules, 2.10 seconds Vite build. No dependencies changed.

Browser final result: **57 passed, 0 failed**, 1.7 minutes, exit code 0. Command: `npm --prefix frontend run test:browser`. The final closure run on 2026-09-13 verified that test ports 5179/8769 were free and started fresh Playwright servers and an isolated fixture database (`backend/browser-test-e3kyzxsp`), with server reuse disabled. All 53 existing workflows and four report workflows passed, including indicator retry identity across report creation/viewing. The interrupted previous run was also found to have completed with 57 passing tests; the requested clean run independently confirmed it.

No product, test or configuration changes were needed during final closure. Backend/frontend/typecheck/build results above were confirmed from the completed implementation verification and were not unnecessarily rerun for documentation-only closure. The Windows collector/upload regression remains passing in the 152-test backend run. Final source fingerprints verify closure did not change that tested implementation.

Focused backend coverage verifies authorized/foreign/missing credentials, reauthorization after token rotation, empty creation/repeated retrieval without persistence, hidden collection-requester evidence and linked records, stored citations/inert source strings, correction links, all-table preservation, more-than-one-page completeness, row/byte/time refusals and sanitized errors. A WAL fixture permits a concurrent writer and verifies the explicit read snapshot keeps case/evidence sections consistent while a later report sees the new data.

Browser coverage includes opening the real case, creating/viewing the report, real API-backed evidence/indicator/timeline/note sections and citations, literal source text, a text download request, responsive width, keyboard focus, manual error recovery, 401 clearing, mismatched case response rejection and preservation of unchanged pending indicator retry payloads. Backend tests provide actual foreign-owner and hidden-requester authorization coverage; browser coverage adds unavailable-case denial and defensive wrong-case response handling.

## Database and migration status

The configured development database remains **0008**. Read-only SQLite inspection repeated on 2026-09-13 returned **integrity: ok**, **0 foreign-key violations**. Its SHA-256 remains `8f8e520eb9e23d2354652990d114fcb5895f7f1b5e293f0135299f279acde969`, matching the implementation's pre-edit verification and closure fingerprint. No migration was created, changed or run; no backup/migration operation was necessary because the application database was not modified. Regression suites use isolated temporary databases, including existing migration and collector tests.

## Warnings and intermediate verification failures

Existing Starlette/httpx TestClient deprecation and NO_COLOR/FORCE_COLOR warnings remain. An aborted browser request also produced a Windows connection-reset diagnostic during the initial run; it did not indicate report corruption.

The initial focused backend run had one test-fixture error: token rotation assigned a plain string instead of the configured SecretStr type. Correcting that fixture produced eight passing focused tests, followed by the passing full backend suite.

The first full browser run produced 55 passes and two failures. One new test asserted before its retry request arrived; it now waits for that request. The other failure came from the new report test starting custody on the shared annotation fixture before an older workflow checked its initial annotation baseline. A subsequent run produced 55 passes and two failures: moving setup to the retrieval fixture disturbed that fixture's baseline, and one timeline workflow timed out waiting for initial browser rendering. Report setup now uses a dedicated metadata evidence fixture, leaving all pre-existing fixture custody states unchanged. No existing test assertions or product behavior were weakened to make these tests pass.

Windows test-server teardown stalled under restricted process permissions. One attempted rerun stopped before executing tests because port 5179 was still occupied. Only descendants of the verified Playwright test runner were stopped. The final full suite was rerun with normal Windows process permissions; development servers and the real database were not stopped or reset.

Closure removed the named Phase 7B verification logs and generated `.last-run.json` after recording results. Private fixture directories `browser-test-4dzs42q0`, `browser-test-66coctq3`, `browser-test-nenxqb2z` and `browser-test-e3kyzxsp` remain under `backend`: cleanup encountered Windows access denial on the first directory and stopped. No ACLs were weakened or unrelated evidence/older fixtures removed. These are isolated generated test artifacts, not application records or additional source changes; their retention did not prevent the fresh suite from passing.

## Limitations and next phase

- Transient drafts only: no report catalog, durable server retrieval, approval/signature/retention, PDF generation or collaborative editing.
- The snapshot may become stale. Case revisions alone do not version all evidence, notes, custody or indicator activity.
- Hard limits refuse large complete reports; there is no background export, resumable work or silent partial output.
- Recorded assertions are not validated evidence contents, causal findings or maliciousness decisions. Original/correction links preserve observation history without claiming truth.
- Free-text privacy requires investigator review. Technical field exclusion does not guarantee source text lacks personal information or paths.
- The existing case-refresh/leaving-workspace loss of pending indicator memory is not redesigned. Opening/closing the new report itself preserves that panel and retry identity.
- Mobile width/focus workflows passed where tested; no comprehensive WCAG certification, multi-user deployment or large-volume benchmark is claimed.

Recommended next step, only after approval: a Phase 7C design review of investigator-authored findings and reviewed report retention if users need durable conclusions or historical report retrieval. Do not add persistence, AI or another history system speculatively.

No AI, enrichment, automatic verdicts, automation, background workers, teams/RBAC, framework replacement or architecture redesign was added. Phase 7C has not started.

**Phase 7B is complete. Stop here and await approval before Phase 7C.**
