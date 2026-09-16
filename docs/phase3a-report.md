# Phase 3A completion report

Completed on Windows, 2026-09-07. Phase 3A only: evidence-linked investigator timeline
observations. Phase 3B evidence retrieval has not started.

## Implemented

The existing TimelineEvent remains the only timeline system. Revision 0004 adds
evidence linkage, investigator/legacy origin, reported timestamp, source locator,
recorder label, submission UUID and request fingerprint. Existing legacy fields
remain intact; no evidence relationships or historical attribution were inferred.

Three additive operations create, query and inspect observations under
`/api/v2/investigation`. They reuse operator authentication and incident/evidence/job
ownership checks. Timeline and custody creation commit atomically. Identical
submission retries return the original record; conflicting content returns 409.
Counts and cursor pages are authorized, ordered by occurrence time and UUID, and
filter by evidence, dates, text and origin. Observations are append-only through
the new API and ordinary ORM operations, including attempts to change origin on an
expired ORM object. Legacy ORM behavior is retained.

The frontend adds a timeline list, observation details and an explicit observation
form on evidence details. It shares the existing memory-only operator client.
Reported offsets, UTC occurrence time and recording time remain distinguishable.
Unconfirmed writes retain an unchanged payload/UUID for explicit retry; current
observations can be reviewed within the form. Custody refresh and first-timeline
baseline labels are additive. No original evidence content is read or modified.

See [the API/workflow guide](phase3a.md).

## Upgrade path and backup

Before source implementation, the local database was confirmed at 0003 with passing
SQLite integrity and foreign-key checks. A SQLite backup was created and retained:

`backend/var/backups/shadowvault-before-phase3a-20260907T112521403770Z.db`

Migration 0004 was then created with `down_revision=0003`. It creates a unique
evidence ID/incident index without rebuilding evidence or its referencing tables,
and extends the existing timeline table. Table count remains ten.

The populated migration test builds revision 0003 with original evidence, a tag,
note, custody chain, queued integrity record and legacy timeline event. Every
original column in every original table remains identical after upgrade and repeat
upgrade. The existing custody chain verifies, and legacy provenance is null rather
than fabricated. Existing Phase 1 adoption and Phase 2A preservation tests pass.
The original 0003 downgrade guard remains explicitly tested at revision 0003;
0004 has its own forward-only downgrade test. Fresh migration matches ORM metadata.

Only after backend tests passed was `backend/shadowvault.db` upgraded to 0004.
All original-column comparisons passed, `PRAGMA foreign_key_check` returned no
violations and `PRAGMA integrity_check` returned `ok`. This local database had no
evidence/timeline records; populated migration coverage comes from the isolated fixture.
No rollback was needed. No previous migration was edited.

## Complete verification results

- Complete Python suite: **82 passed, 0 failures, 0 errors, 0 skipped**;
  final run 17.667 seconds. All 66 baseline tests plus 14 timeline and 2 migration tests.
- Frontend service suite: **16 passed, 0 failed, 0 cancelled, 0 skipped, 0 todo**;
  all 12 baseline tests plus 4 timeline tests.
- Browser suite: **21 passed, 0 failed, 0 skipped**, 30.1 seconds;
  all 15 baseline workflows plus 6 timeline workflows, headless Microsoft Edge.
- Standalone TypeScript check: **passed**, exit code 0.
- Production build: **passed**, exit code 0; Vite transformed 48 modules and bundled
  in 1.29 seconds. Production JS 232.65 kB / 71.31 kB gzip; CSS 5.34 kB / 1.69 kB gzip.
- Phase 2A Windows CLI/HTTP upload and repeat round trip: **passed** in the complete suite.
- Additional upload → timeline creation → identical upload test: **passed**;
  original stored bytes, receipt and metadata revision remain unchanged.

Commands from the repository root:

```powershell
$env:PYTHONPATH='backend'
backend/.venv/Scripts/python.exe -m unittest discover -s tests -v
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:browser
```

Incremental verification included the eight existing model tests, five existing
migration tests, 13 initial timeline tests, and an 81-test backend pass before
frontend work. Final review added the expired-origin immutability check and a direct
upload/timeline/retry regression; the full backend suite was then rerun at 82 tests.
There were no failing test or build runs during this implementation.

Backend coverage includes UTC/offset handling, authenticated attribution, safe
responses, original metadata/file preservation, custody rollback, commit failure,
idempotency and conflicting payloads, concurrent submissions, foreign incident/job
access, agent credential rejection, inactive operators, legacy visibility, literal
text/range filtering, timestamp-tie pagination, cursor binding, schema constraints,
body limits and new-record immutability.

Browser coverage adds real creation/custody/provenance/evidence navigation, legacy
event presentation, explicit-time validation, unchanged retry payload recovery,
timeline pagination/filter scope, shared authentication expiry, and mobile/focus
behavior. Existing notes/tags/search/integrity/credential workflows also pass.

## Warnings and operational notes

- Existing Starlette HTTPX TestClient deprecation warning remains.
- `Database readiness check failed` is the expected diagnostic from a passing
  simulated-failure test.
- Browser test server/worker emitted the existing Node NO_COLOR/FORCE_COLOR
  precedence warning. It did not affect results.
- No new dependencies, package installation or lockfile edits were needed.
- Browser tests used approved normal Windows process permissions for their isolated
  local servers. The remaining `backend/browser-test-cxdu3jif` fixture was inspected
  for exact path/content and fixture identity, then removed after shutdown.
- No unresolved test/build failures remain. Browser tests were not rerun after the
  final ORM-only guard adjustment; the final complete Python run covered that change.

## Exact changed source/documentation files

New files (14):

- `backend/app/schemas/timeline.py`
- `backend/app/services/timeline.py`
- `backend/app/api/routes/investigation_timeline.py`
- `backend/migrations/versions/0004_timeline_provenance.py`
- `frontend/src/features/timeline/contracts.ts`
- `frontend/src/features/timeline/TimelinePanel.tsx`
- `frontend/src/features/timeline/TimelineEventForm.tsx`
- `frontend/src/features/timeline/TimelineEventDetails.tsx`
- `tests/test_timeline.py`
- `tests/test_timeline_migrations.py`
- `frontend/tests/timeline.test.mjs`
- `frontend/tests/browser/timeline.spec.ts`
- `docs/phase3a.md`
- `docs/phase3a-report.md`

Modified files (22):

- `backend/app/models/timeline.py` — provenance, constraints/indexes and new-observation ORM guards.
- `backend/app/models/evidence.py` — composite-reference supporting unique index.
- `backend/app/services/custody.py` — optional baseline reason, existing default unchanged.
- `backend/app/main.py` — registers the additive timeline router.
- `frontend/src/features/evidence/service.ts` — three methods in the existing credential closure.
- `frontend/src/features/evidence/InvestigationWorkspace.tsx` — shared timeline views and filter state.
- `frontend/src/features/evidence/EvidenceDetailsPage.tsx` — observation form and custody refresh.
- `frontend/src/features/evidence/CustodyHistory.tsx` — timeline baseline/action labels and refresh trigger.
- `frontend/src/App.tsx` — additive hash routes and document titles.
- `frontend/src/components/Layout.tsx` — timeline navigation and phase label.
- `frontend/src/pages/DashboardPage.tsx` — timeline entry point.
- `frontend/src/styles.css` — wrapping navigation for the additional mobile item.
- `tests/test_migrations.py` — expected migration head becomes 0004.
- `tests/test_investigation_migrations.py` — explicitly tests original 0003 downgrade guard.
- `tests/browser_fixture.py` — separate timeline evidence and legacy timeline fixture.
- `README.md`
- `backend/README.md`
- `frontend/README.md`
- `tests/README.md`
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/setup.md`

The investigation-migration test adjustment is an additional file beyond the initial
proposal's inventory: it preserves the old guard's test coverage rather than letting
0004's downgrade refusal intercept that test. No existing behavioral assertion was removed.
Total source/documentation inventory: **36 files**. This workspace has no Git metadata;
the inventory is based on recorded edits and inspected files rather than a Git diff.

Local/generated outputs:

- `backend/shadowvault.db` — upgraded to 0004.
- `backend/var/backups/shadowvault-before-phase3a-20260907T112521403770Z.db` — retained 0003 backup.
- `frontend/dist/index.html`, `frontend/dist/assets/index-BCEswEAP.css`,
  `frontend/dist/assets/index-THGdEcJ0.js` — regenerated production output replacing prior bundles.
- Ignored Python bytecode and browser test-results metadata generated/refreshed by tests.
- Temporary backend/browser fixtures cleaned up; no live test server is required afterward.

## Preserved behavior and limitations

No Phase 2A upload code, agent source, existing investigation endpoint implementation,
v1 timeline route, existing schema contract, dependency manifest, lockfile or previous
migration was changed. Original evidence bytes and acquisition facts remain untouched.
Timeline actions only add observations and advance custody history, without editing
annotation revisions. The Windows collector and shared core are unchanged.

The only timeline remains TimelineEvent. Each new observation references one evidence
record; legacy rows may be unlinked. Observations are investigator assertions, not
automatically verified facts. No edit/delete, correction/supersession, timestamp-range
inference or multi-evidence link workflow is included. Direct database administrators
remain trusted, and custody verification uses the stored head rather than an external
trust anchor. Legacy ORM behavior remains available for compatibility.

The UI still uses provisioned operator tokens in memory rather than browser sessions.
Timeline queries require a known incident ID. Pagination is live; filters/drafts are
in memory, and leaving a detail/reloading loses an unresolved submission's draft/ID.
The retry review panel shows a page, not a definitive absence check; repeating the
unchanged submission is the deduplication mechanism. Other databases/browsers/platforms
remain unverified beyond the existing Windows/SQLite/Edge environment.

No Phase 3B retrieval, download, preview, AI analysis, malware analysis, file execution,
automatic extraction, integrity-check execution, remote execution, memory acquisition,
Linux collector or new authentication system was implemented.

Phase 3A is complete. Stop here and wait for approval before any further phase.
