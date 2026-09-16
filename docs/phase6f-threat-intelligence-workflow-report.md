# Phase 6F — Threat Intelligence Workflow Report

Date: 2026-09-12. **Status: complete and fully verified.** Scope is limited to the four approved Phase 6E priorities. Phase 7 has not started.

## Delivered improvements

### Correction visibility

Indicator list responses now include `superseded_by_id`, resolved from authorized observations independently of the current page and exact-value filter. An original remains visibly marked as corrected even when its successor is outside the loaded page or has a different value. The panel provides View correction / View original actions and a Correct observation action that prefills the evidence, predecessor and value. Original rows and correction chains remain append-only.

The existing case-scoped list accepts an optional `observation_id` filter for bounded lookup. No new endpoint or storage structure was needed. Lookup stays inside the existing case/evidence authorization boundary and is included in cursor binding when supplied. Default pagination ordering and old filter cursor bindings remain unchanged. The POST response and write behavior remain unchanged; successor information is a read-only list addition.

A null successor means no later correction was recorded in that response, not that the observation is a verified truth. Missing successor data from an older backend is shown as unavailable rather than silently treated as current.

### Existing API filters

The panel exposes the existing server-supported kind, exact-value and evidence-ID filters through the shared client. Exact value requires kind; the backend remains responsible for normalization and validation. Changing filters resets pagination while keeping the case ID fixed. Previous-page navigation now complements First/Next.

Correction/receipt lookup uses the new optional observation-ID filter. Clear filters returns to the case list; applying visible filters exits the single-observation lookup. No duplicate filtering engine, client-only scope enforcement or full content search was added.

### Evidence-context actions

Authorized case evidence details now offer View indicators for this evidence and Record indicator for this evidence. These reuse the loaded evidence ID and filename, prefill the form or filter and return to the same case's indicator panel. The selected evidence is named alongside its ID. The manual-ID fallback remains available.

Indicator cards keep case-scoped source-evidence links and offer a filter action for that source. No private storage key, filesystem path or credential field was added to indicator responses or context actions. Existing evidence detail behavior remains unchanged. No storage reads or downloads are triggered by these actions.

The panel remains mounted, hidden, while opening evidence within the same case. Its pending submission, receipt, filters and draft therefore survive that evidence-navigation round trip. Context actions do not overwrite an unresolved pending submission. Prefilled form actions move keyboard focus to the evidence field; lookup actions focus the panel heading. There was no timeline navigation or semantics redesign.

### Save/retry handling

Successful saves retain a separate in-memory receipt with the returned observation ID/value and source link. View saved observation opens that record even when it would be beyond the first oldest-first page. A list refresh failure does not erase the save receipt or pretend the write failed.

The UI distinguishes validation failure (422), unavailable evidence/correction (404), submission conflict (409), uncertain write outcome, and failure to verify evidence before a write was sent. It does not echo private backend error bodies. Uncertain/conflicting submissions retain their original payload and submission ID for an explicit unchanged retry; writes never retry automatically. Starting a different submission requires an additional explicit confirmation after a warning. The form prevents duplicate in-flight submissions.

## Authorization and preservation

All backend changes are read-only. Successor lookup reuses the existing evidence-authorized indicator query and additionally checks matching evidence identity. Hidden or incorrectly cross-linked successors cannot leak through a visible original. Observation lookup cannot expand incident scope. Existing operator authentication, collection-requester restrictions and cursor authorization remain in force.

The shared API service keeps credentials in memory and Authorization headers, uses no-store, and clears/aborts requests on disconnect or authorization expiry. No browser storage or new authentication system was introduced. All posted evidence/correction relationships remain enforced by the existing backend write service; prefilled UI IDs are not trusted as authorization.

No Incident, Evidence, IndicatorObservation, TimelineEvent, CaseHistoryEvent or custody model changed. Indicator writes, original evidence bytes, evidence custody, case-history revisions, timeline provenance, upload, retrieval and Windows collector behavior were preserved. Phase 6B aggregate meanings were not changed. No AI, external feeds, enrichment, automation, workers, teams/RBAC or dependencies were added.

## Database and migration verification

The configured development database was inspected read-only with SQLite `mode=ro`:

- Revision: **0008**.
- `PRAGMA integrity_check`: **ok**.
- `PRAGMA foreign_key_check`: **0 violations**.
- SHA-256 of `backend/shadowvault.db`: unchanged from the Phase 6F pre-edit baseline.

No migration was required, created or run. No application database records were changed by Phase 6F. Tests used isolated temporary databases; existing migration regression tests remain part of the complete backend suite.

## Exact changed-file inventory

Modified backend files:

1. `backend/app/api/routes/investigation_indicators.py` — optional observation-ID list filter.
2. `backend/app/schemas/indicator.py` — list-only successor response field.
3. `backend/app/services/indicators.py` — scoped lookup, successor resolution and cursor binding.

Modified frontend files:

4. `frontend/src/features/cases/CaseWorkspace.tsx` — same-case evidence context and retained panel mounting.
5. `frontend/src/features/evidence/EvidenceDetailsPage.tsx` — optional case indicator context actions.
6. `frontend/src/features/evidence/service.ts` — existing indicator method accepts supported filters; existing call positions remain compatible.
7. `frontend/src/features/indicators/CaseThreatIntelligence.tsx` — filters, navigation, correction visibility, context, receipt and explicit retry states.
8. `frontend/src/features/indicators/contracts.ts` — successor/filter/context types.

Tests:

9. `tests/test_indicators.py` — two added backend regressions.
10. `frontend/tests/indicators.test.mjs` — one added API-client regression.
11. `frontend/tests/browser/indicator-workflow.spec.ts` — new file with three browser workflows.

Documentation:

12. `docs/phase6f-threat-intelligence-workflow-report.md` — this report.

The inventory is compared with the Phase 6F source fingerprint baseline. No model, migration, dependency, configuration, agent, custody, case-history or timeline source files changed. Frontend build outputs are generated artifacts, not additional source changes.

## Final verification results

- **Backend: 144 passed, 0 failures, 0 errors**, 41.834 seconds. Command: with `PYTHONPATH=backend`, `backend/.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_*.py' -v`.
- **Frontend services: 40 passed, 0 failed, 0 skipped/cancelled**, 1075.4993 ms. Command: `npm --prefix frontend test`.
- **Browser workflows: 53 passed, 0 failed**, 1.6 minutes. Command: `npm --prefix frontend run test:browser`; completed with exit code 0.
- **TypeScript: passed**, `npm --prefix frontend run typecheck`.
- **Production build: passed**, `npm --prefix frontend run build`; 59 modules transformed, Vite build 1.21 seconds.
- **Windows collector/upload regression: passed** within the complete backend suite, including `test_real_cli_upload_and_repeat`. Existing agent-core, Windows selected-file/staging/retry, collection, timeline and retrieval regression tests also passed.

The final browser suite includes all previous workflows plus the three new Phase 6F workflows. No test failure required a feature change during closure; finalization confirmed the completed results rather than rerunning unchanged suites unnecessarily.

New backend coverage verifies a successor beyond 50 intervening rows, exact-value filtering that excludes the correction's value, direct observation lookup, unchanged POST response shape, cursor rebinding and hidden/cross-evidence successor denial. Existing tests continue checking concurrent writes, idempotency, rollback, append-only guards and original table preservation.

New browser coverage exercises evidence-context entry and focus, correction/original navigation, exact filtering, pending retry identity across source navigation, a successful receipt retained through list-refresh failure, distinct validation/conflict states, explicit discard confirmation and mobile width. The service test verifies filter serialization through the existing authorized case route.

## Warnings and artifact cleanup

Existing warnings remain: Starlette/httpx TestClient deprecation and Playwright/Node NO_COLOR ignored when FORCE_COLOR is set. They did not fail verification; no dependency change was made to suppress them.

Removed only isolated Phase 6F test artifacts: `backend/browser-test-b7tr_kvt` (created by this browser run, containing fixture test.db/evidence/retrieval), the run's `frontend/test-results/.last-run.json`, and root `phase6f-*` verification logs/baseline after recording results. The fixture required normal-user access because the sandbox user could not read its private directory. Its absolute target and absence of reparse points were checked before deletion.

Older browser-test directories, prior-phase database backups, the real application database, collected evidence and production build output were retained. No general cleanup or deletion of unrelated artifacts was performed.

## Remaining limitations

- This is a live view. Successor status is authoritative for the authorized response, not a permanent verdict; refresh after concurrent changes. No global correction graph or automatic classification exists.
- Receipt/draft/retry data are in-memory only. Same-case evidence navigation preserves them, but refreshing/reloading the case, leaving the case workspace, disconnecting or reloading the tab can discard them. A receipt confirms the saved response, not current successor status. Investigators should resolve an uncertain submission before those actions.
- The manual-ID fallback remains; evidence-context actions avoid copying for normal case evidence use. No evidence picker or filename lookup per indicator row was added.
- Filters are exact-value/type/evidence filters, not full-text, source-content or threat-feed search. Page results are not a frozen report or estimated threat totals.
- Native controls, focus behavior and representative mobile layouts were tested; this is not a comprehensive screen-reader/WCAG certification or large-volume performance benchmark.
- No changes were made to the independent timeline, case-history or custody workflows. Those remain separate from indicator correction history.

**Phase 6F is complete and fully verified. Stop here; Phase 7 has not started.**
