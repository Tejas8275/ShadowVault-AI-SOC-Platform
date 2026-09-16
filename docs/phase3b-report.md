# Phase 3B completion report

Completed on Windows, 2026-09-07. Scope: authorized evidence retrieval only.
No architecture replacement, schema change, new migration or dependency was needed.

## Delivered

One additive operator-only endpoint:
`POST /api/v2/investigation/evidence/{evidence_id}/download`.

The dedicated storage reader validates opaque storage names, directory/file types,
Windows final handle paths and sharing protections. It creates a bounded private
copy, checks its size and SHA-256, and never opens originals for writing. The retrieval
service rechecks authorization and storage identity, then uses existing transactional
custody services to record preparation before any content response starts. A custom
stream response closes the copy and releases its capacity slot even on send failure
or timeout. The API serves a no-store, nosniff, download-only .bin attachment.

Custody events record server preparation with authenticated attribution and matching
expected/observed facts. They never claim confirmed delivery or local saving. An
explicit first-retrieval baseline is created only when needed. Retrieval does not
change metadata revisions, initial verification, integrity-check rows or TimelineEvent.

The frontend adds prepare/cancel/save/discard controls in evidence details, sharing
the existing in-memory credential client. It rejects oversized/malformed/truncated
responses, bounds buffering, cancels pending reads, prevents delayed responses from
publishing, and revokes temporary URLs on discard/navigation/disconnect. Custody
refresh and labels are additive. Details/search/notes/tags/timeline behavior remains.

See [the API and operational guide](phase3b.md) for exact contracts and limitations.

## Database backup and preservation

Before the first source edit, opened the development database read-only, confirmed
revision 0004, passed integrity/FK checks and created a SQLite backup:

`backend/var/backups/shadowvault-before-phase3b-20260907T174252408312Z.db`

The backup passed integrity verification. After implementation/testing, compared full
logical SQLite dumps of development database and backup: identical. Both still report
0004, `PRAGMA integrity_check = ok`, and zero FK violations. No migration command was
run against development data. Only migrations 0001, 0002, 0003 and 0004 exist.
Existing populated migration/fresh-schema tests still pass without modification.

## Final verification

- Complete Python suite: **102 passed, 0 failures, 0 errors, 0 skipped**, 25.941 seconds.
  Includes all 82 baseline tests and 20 new tests (12 retrieval + 8 reader/lifecycle).
- Frontend Node service suite: **24 passed, 0 failed, 0 cancelled, 0 skipped, 0 todo**,
  551.7515 ms. Includes all 16 baseline tests and 8 new download tests.
- Browser suite: **26 passed, 0 failed, 0 skipped**, 38.6 seconds, headless Microsoft Edge.
  Includes all 21 baseline workflows and 5 new retrieval workflows.
- Standalone TypeScript check: **passed**, exit 0, including a final post-test run.
- Production build: **passed**, exit 0. Vite 7.3.6 transformed 50 modules in 1.94 seconds.
  JS: 237.37 kB / 72.73 kB gzip; CSS: 5.34 kB / 1.69 kB gzip.
- Phase 2A real Windows CLI → HTTP → SQLite upload/repeat round trip: **passed** in
  the complete Python suite. Collector source and transport were not changed.
- New upload → annotation → timeline → retrieval → identical upload regression:
  **passed**, preserving receipt, original bytes, and annotation revision semantics.
- Real browser save: **passed**, comparing the saved file against exact fixture bytes,
  including NUL and non-UTF-8 content, with safe .bin name and truthful custody labels.

Commands from repository root:

```powershell
$env:PYTHONPATH='backend'
backend/.venv/Scripts/python.exe -m unittest discover -s tests -v
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:browser
```

Backend completed before frontend implementation: the initial full suite passed 101
tests; final review added the Windows Python-version guard/test, then all 102 passed.
The final browser rerun covered that guard and all final frontend source changes.
Subsequent changes were documentation only.

## Coverage and encountered errors

New tests cover operator/device/incident/job boundaries, inactive users and mid-copy
reauthorization, metadata changes during preparation, safe attachment headers, current
revision, read-only metadata GETs, size/hash mismatch, missing/unsupported storage,
empty files, repeated preparations, custody/commit rollback, concurrent annotation
activity, prepared-copy stability, capacity/range limits, invalid path/stream keys,
junctions, parent replacement between validation/open, Windows write/delete sharing,
I/O failure, preparation/response timeout, send failure cleanup and Python ACL support.

Frontend tests cover token confinement, fixed binary request policy, sanitized errors,
no automatic retries, 401/disconnect clearing, safe filenames, byte/header validation,
zero-byte copies, over-limit rejection, truncation/overflow, aborting pending reads,
real saving/custody, cancelled delayed responses, URL revocation and mobile keyboard use.

One incremental reader run had **4 passed and 1 error**: its send-failure assertion
expected OSError, whereas installed Starlette translates it to ClientDisconnect.
Corrected the assertion to the actual framework contract; cleanup assertions and all
final tests pass. No product fix was necessary for that test expectation.

The first browser run passed all 26 workflows but waited for restricted Windows test
server teardown. Read-only process inspection initially returned Access denied;
Stop-Process then failed with an object-reference error. Verified only the isolated
test-server identities and terminated them through the Windows process API. One
already-terminated child returned Not found. That run exited 0 with 26 passed (3.2m).
Reran with normal user process permissions: all 26 passed in 38.6s with normal teardown.

Temporary browser fixtures required cleanup under their respective owning accounts.
An initial cross-account cleanup attempt returned Access denied before deleting
anything. Verified absolute containment, fixture-only file inventory and the isolated
browser user identity, then removed both fixtures with their owning permissions.
No project data or development evidence was deleted. No unresolved test failures remain.

## Warnings

- Existing Starlette HTTPX TestClient adapter deprecation warning.
- Expected `Database readiness check failed` diagnostic from a passing failure test.
- Existing Node NO_COLOR/FORCE_COLOR precedence warning during browser tests.
- Windows process/ACL cleanup behavior described above; final fixtures were removed.
- No dependency installs, lockfile edits, new frameworks or new warnings from the build.

## Exact changed source/documentation inventory

New files (11):

- `backend/app/services/evidence_reader.py` — validated read handles and verified private copies.
- `backend/app/services/evidence_retrieval.py` — authorization recheck and custody transaction.
- `backend/app/api/routes/investigation_retrieval.py` — attachment API and response cleanup.
- `frontend/src/features/evidence/download.ts` — bounded binary reader and safe copy names.
- `frontend/src/features/evidence/EvidenceDownload.tsx` — explicit download/save/discard UI.
- `tests/test_retrieval.py` — retrieval API, custody and upload compatibility tests.
- `tests/test_evidence_reader.py` — storage protection and response-lifecycle tests.
- `frontend/tests/download.test.mjs` — binary service tests.
- `frontend/tests/browser/download.spec.ts` — browser retrieval workflows.
- `docs/phase3b.md` — API, operator workflow, configuration and security limits.
- `docs/phase3b-report.md` — this report.

Modified files (14):

- `backend/app/core/config.py` — private-copy directory and retrieval limits.
- `backend/app/main.py` — retrieval router and separate capacity semaphore.
- `backend/.env.example` — retrieval setting examples.
- `frontend/src/features/evidence/service.ts` — binary method in existing private-token closure.
- `frontend/src/features/evidence/EvidenceDetailsPage.tsx` — download panel and custody refresh.
- `frontend/src/features/evidence/CustodyHistory.tsx` — first-retrieval and preparation labels.
- `tests/browser_fixture.py` — isolated retrievable object and temporary-copy directory.
- `tests/README.md` — test coverage/counts.
- `README.md` — Phase 3B status and references.
- `backend/README.md` — additive endpoint and configuration references.
- `frontend/README.md` — download workflow and limits.
- `docs/architecture.md` — retrieval boundaries and custody semantics.
- `docs/roadmap.md` — implemented Phase 3B slice.
- `docs/setup.md` — retrieval setup and current regression instructions.

Total: **25 source/documentation files**. The workspace has no Git metadata; inventory
is based on recorded edits and inspected files. Existing phase reports were not edited.

Generated/local artifacts:

- The retained pre-edit backup above; development `backend/shadowvault.db` is unchanged logically.
- `frontend/dist/index.html`, `frontend/dist/assets/index-BCEswEAP.css`, and
  `frontend/dist/assets/index-D92nEaAI.js` from the successful build, replacing prior output.
- Ignored Python bytecode and browser test-results metadata refreshed by test execution.
- Isolated browser fixtures `backend/browser-test-m7xqivk2` and
  `backend/browser-test-4d50pdfu` were verified and removed after shutdown.

## Preserved scope and remaining limitations

Models/migrations, upload routes/services, existing investigation/timeline APIs, shared
custody implementation, Windows collector and agent core are unchanged. There is one
TimelineEvent system and no newly inferred event data. No existing test was removed
or weakened. Existing browser fixtures are retained; the retrieval fixture is additive.

Retrieval supports current opaque .blob keys only. Unsupported legacy storage is not
remapped. The server/browser cap is 100 MiB content, with additional browser memory
overhead. Limits are per process. Private ACLs on existing directories and trusted
parents, local disk availability, TLS and deployment administration remain operational
requirements. Windows/Python 3.14/SQLite/Edge are verified; the POSIX reader branch is
not a verified Linux collector or deployment.

Preparation timeouts are checked between synchronous filesystem operations and cannot
forcibly interrupt a hung filesystem call. Client cancellation may only be observed
after synchronous preparation; a committed preparation can remain after disconnect.
There is no delivery acknowledgement, failed-attempt ledger, background recovery,
resumption or physical-erasure guarantee. Custody is application-level hash linkage,
not an external trust anchor. The frontend's subsequent integrity result is intentionally
unchanged by retrieval-time verification. Saved copies remain under user control.

No AI, malware analysis, execution, parsing, preview, automatic extraction, background
jobs, integrity workers, Linux collection, browser sessions or further phase was started.
Phase 3B is complete; stop and wait for approval.
