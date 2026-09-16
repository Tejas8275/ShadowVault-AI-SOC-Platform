# Phase 7D — Same-case investigation continuity

Completed: 2026-09-13. Scope: the approved `phase7c-architecture-audit.md` recommendation to preserve pending indicator work and completed transient reports through same-case metadata refresh and failed report replacement.

## Implementation and exact changed-file inventory

Five source/documentation files were added or modified:

1. `frontend/src/features/cases/CaseWorkspace.tsx` — replaces the shared resource hook only in this workspace with a local, abortable case loader. Previously, refreshing/saving case metadata unmounted every panel. The loader now retains the last authorized case and mounted panels while revalidating. Retained content is hidden and inert during loading or refresh failure. A successful refresh restores it; definitive 401/403/404 or mismatched case identity clears it. Existing case form revision/reset behavior is retained.
2. `frontend/src/features/cases/CaseReport.tsx` — retains the last successful report while preparing a replacement and after transient/limit failure or cancellation. Only a successful validated response replaces it. Separate previous-snapshot, error and manual-retry messages avoid presenting the failed attempt as a new report. Access denial clears the retained report. Cancellation returns keyboard focus after the action button has been re-enabled. Persistence-boundary copy is explicit.
3. `frontend/src/features/indicators/CaseThreatIntelligence.tsx` — updates the pending-submission notice to distinguish case metadata refresh from tab reload. No indicator submission, correction, receipt or authorization logic changed.
4. `frontend/tests/browser/case-continuity.spec.ts` — adds eight focused browser workflows, using the isolated fixture API and dedicated report evidence. Covers retained input/identity/receipt, revalidation, failed replacement, cancellation, success, access denial and case/authentication boundaries.
5. `docs/phase7d-implementation-report.md` — this completion report.

Before/after SHA-256 inventory comparison confirms that backend application code, migrations, agents, existing tests, configuration, dependency manifests/locks and prior documentation are unchanged. No API endpoints, shared resource loader, shared authentication client or routing framework were changed.

## State and persistence boundaries

- The existing authenticated parent keys CaseWorkspace by connection generation and case ID. There is no cross-case cache. Case A's components unmount on switching to Case B; returning to A starts fresh.
- Same-case evidence navigation, evidence/timeline section selection, explicit case metadata refresh and post-save refresh retain indicator input, unresolved payload/submission identity, last receipt and completed report while their case workspace remains mounted.
- Retained panels are hidden from display/accessibility navigation and marked inert while case access is being revalidated or a transient refresh failure remains unresolved. The external Refresh case button supplies explicit recovery. They are not an interactive offline cache.
- Definitive case denial clears retained panels and evidence-context state. Operator disconnect/401 clears the existing authenticated workspace. Leaving the case workspace or reloading the tab also clears transient state. Nothing is written to localStorage, sessionStorage or a server report table.
- Existing 422 handling keeps editable indicator input while discarding the rejected pending submission identity. Uncertain writes retain their original identity and payload; a manual retry sends the identical payload. Success clears pending values/citation/correction input and preserves the existing receipt. Refresh/navigation does not submit an indicator automatically.
- A retained report remains a timestamped metadata snapshot, not a live view. During replacement, failure or cancellation it is explicitly identified as the previous successful report. It remains viewable/saveable within the authorized case boundary. HTTP 413 refuses an incomplete replacement without destroying that snapshot. Report 401/403/404 clears the retained report.
- Successful replacement uses the existing client case/schema validation. Abort checks prevent a cancelled response from updating the draft. Closing a view does not create a report; another generation requires the explicit Create report draft action. Case/evidence writes still use their existing concurrency checks.

## Verification results

All final verification commands completed successfully:

- Backend: **152 passed, 0 failures/errors**, 51.767 seconds. Command: `backend/.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_*.py' -v` with `PYTHONPATH=backend`.
- Frontend services: **44 passed, 0 failed, 0 skipped/cancelled**, 779.3145 ms. Command: `npm --prefix frontend test`.
- TypeScript: **passed**, exit 0. Command: `npm --prefix frontend run typecheck`, repeated after the focus correction.
- Production build: **passed**, exit 0; TypeScript plus Vite, 61 modules, Vite build 2.87 seconds. Command: `npm --prefix frontend run build`.
- Complete browser suite: **65 passed, 0 failed**, 1.7 minutes, one worker, headless Microsoft Edge. Command: `npm --prefix frontend run test:browser`. Includes all 57 existing workflows and eight new continuity workflows. Final run used fresh isolated fixture servers with test ports checked before startup.
- Windows collector/upload: **passed** within the backend suite, specifically `test_real_cli_upload_and_repeat`. It executes the real Windows CLI against isolated HTTP/SQLite storage, repeats the upload, checks the digest and one resulting evidence record, verifies stored bytes, and checks the accepted large-manifest transport regression. No real evidence was collected for verification.
- SQLite: **revision 0008; integrity_check = ok; 0 foreign-key violations**. Checks use a read-only connection to the configured development database.

The new browser coverage verifies:

1. Uncertain indicator payload/ID and successful report survive a blocked/failed case refresh, explicit recovery, successful case save, and same-case evidence/timeline navigation; no automatic POST occurs.
2. Validation input survives refresh; an explicit valid save clears pending input and retains the receipt through refresh.
3. HTTP 503 replacement keeps the old timestamped report; manual retry replaces it.
4. HTTP 413 replacement keeps the old timestamped report; manual retry replaces it.
5. Cancellation keeps the old draft, restores keyboard focus and cannot let a delayed cancelled request overwrite a later successful report.
6. HTTP 403 report denial clears the snapshot; case denial clears all retained case work.
7. The corresponding HTTP 404 behavior also clears state.
8. Case switching clears values, pending retries, report and errors; returning, disconnect/reconnect and tab reload do not restore them. Browser storage remains empty.

Existing full-suite coverage still passes for case revision conflicts/history, evidence annotations/custody, timeline provenance/retries, indicator corrections, report citations/scoping, authorized retrieval/cancellation, mobile layout, keyboard navigation and authentication expiry. No new backend behavior required new backend tests.

## Database and compatibility

No database migration was created, edited or run. No application database records were changed. No backup operation was needed for this frontend-only scope. The configured database fingerprint remains:

`8f8e520eb9e23d2354652990d114fcb5895f7f1b5e293f0135299f279acde969`

This matches the pre-edit fingerprint. Incident remains the case entity. Evidence originals, custody semantics, case history, timeline and indicator authorization are unchanged. Reports remain transient projections with the existing API limits. Regression suites modify only their isolated fixture databases.

## Security considerations

The change extends only component lifetime within an already authenticated case. It adds no credential storage, credentials in URLs/logs, new authorization shortcut, external fetch or automatic write/retry. Backend authorization remains authoritative. Definitive denial clears retained private state; temporarily unavailable case access hides retained panels until an explicit successful revalidation. Existing inert rendering and report field exclusions remain unchanged. Downloaded local report/evidence copies still cannot be revoked by disconnecting.

## Warnings, resolved failures and generated artifacts

The initial focused run was **7 passed / 1 failed**: cancellation attempted to focus a still-disabled button. This was a product accessibility defect, fixed by restoring focus after React commits the enabled state.

The first complete run was **64 passed / 1 failed**: the cancellation fixture attempted to fulfill an already handled cancelled route. This was test isolation/timing, corrected by independently gating the old response and the new retry and recognizing only that expected cancellation diagnostic. No additional product change was made for it. The fresh final complete run passed all 65 workflows.

Existing Starlette/httpx TestClient deprecation and NO_COLOR/FORCE_COLOR warnings remain. A Windows ConnectionResetError diagnostic occurred during the first full run; the final full browser run had no such diagnostic and no failures. No dependency change was made to suppress warnings.

Build output under `frontend/dist` was regenerated. Named Phase 7D verification logs and generated Playwright `.last-run.json` are disposable verification output, removed after recording results. Three isolated browser fixture directories remain under `backend`: `browser-test-cr38omky`, `browser-test-jmrvf1ph`, and `browser-test-msviriz1`. Private Windows ACLs deny tool access to these directories; they were left intact, as were older fixtures. No ACL was weakened and no original evidence or development server was removed.

## Remaining limitations and scope closure

This is same-case continuity, not durable recovery. Leaving the case, tab/browser reload/crash and authentication loss still discard transient work. Resolve uncertain submissions using their existing retry identity before deliberately leaving when possible. Broader timeline/annotation draft retention across other routes is not implemented. Reports have no persistent ID/version repository; previous snapshots can become stale and still require investigator review. Only the last successful in-memory report is retained, not a report history.

No AI, automatic conclusions, enrichment, automation, background workers, teams/RBAC, persistent reports, dependencies or backend redesign were added. Phase 7E has not started.

Phase 7D complete — awaiting approval before Phase 7E.
