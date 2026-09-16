# Phase 2B-1 completion report

Verified on Windows, 2026-09-06. Phase 2B-1 is complete. Phase 2B-2 has not started
and requires approval. No implementation remains blocked by the interruption.

## Recovery inspection

The interrupted work already contained the five extended/new models, exports,
revision 0003, canonical custody hashing, investigation schemas, and the metadata,
custody, and query services. Existing migration-head and model-inventory assertions
had been updated. The three existing migration tests had passed before interruption.

The investigation router, application registration/body-limit extension, dedicated
Phase 2B-1 tests, populated Phase 2A migration verification, local database upgrade,
and completion documentation were missing. These were completed without restarting
or reverting the existing implementation. This directory has no Git metadata;
the inventory below is based on inspected files and recorded edits, not a Git diff.

## Implemented and verified

- Evidence display title, review state, revision, and custody head; acquisition fields preserved.
- CustodyEvent, EvidenceNote, EvidenceTag, EvidenceIntegrityCheck models and migration.
- Modular query, metadata, and custody services; atomic writes and optimistic concurrency.
- All six `/api/v2/investigation` operations: search, details, annotation PATCH,
  note POST, note GET, and custody GET. See [the API guide](phase2b1.md).
- Search authorization includes counts, incident/job ownership, exact hashes,
  literal text matching, all-tags matching, ranges, and cursor pagination.
- Notes have authenticated attribution and append-only ORM guards. Tags normalize
  and deduplicate. Metadata and custody roll back together on injected failures.
- Integrity-check constraints and pending/terminal result handling; execution is outside scope.
- Phase 2A valid uploads, hash rejection, duplicate races/retries, authorization,
  storage cleanup, Windows CLI, and real HTTP end-to-end collection still pass.
  A new integration test verifies upload → annotation → identical repeat receipt.

## Migration verification

The actual `backend/shadowvault.db` was at revision **0002**, with zero rows in
all six Phase 2A tables. It was backed up using SQLite's backup API to:

`backend/var/backups/shadowvault-before-phase2b1-20260906T160921989539Z.db`

It is now at **0003**. Original-column comparison passed for every original table;
`PRAGMA foreign_key_check` returned zero violations; `PRAGMA integrity_check`
returned `ok`. Zero local evidence rows meant zero local custody baselines.

To verify nonempty data, a separate migrated fixture contained an operator, incident,
agent, collection job, and verified evidence with acquisition provenance. Upgrade
preserved every original column in every original table, registered exactly one
truthful migration baseline, and passed canonical chain verification. Repeated
upgrade was harmless. Fresh migration matches current SQLAlchemy metadata.
Legacy Phase 1 adoption and refusal of unknown schemas also pass. Downgrade from
0003 is deliberately refused to avoid discarding history. Non-SQLite migration is unverified.

## Final verification results

- Complete Python suite: **62 passed, 0 failures, 0 errors, 0 skipped**, 18.097 seconds.
  This is 45 existing tests plus 15 investigation tests and 2 investigation migration tests.
- Frontend regression suite: **5 passed, 0 failures, 0 cancelled, 0 skipped, 0 todo**.
- Frontend build: **passed** (`tsc --noEmit && vite build`); Vite processed 36 modules.
- Backend warning: one displayed `StarletteDeprecationWarning` about the existing
  HTTPX TestClient adapter. No dependency was added to suppress it.
- Expected diagnostic: `Database readiness check failed` from the passing
  readiness-failure test. This is an intentionally simulated failure.
- Frontend tests/build: no warnings or errors reported.

Commands run from the repository root:

```powershell
$env:PYTHONPATH='backend'
backend/.venv/Scripts/python.exe -m unittest discover -s tests -v
npm --prefix frontend test
npm --prefix frontend run build
```

Initial inspection mistakenly looked under `backend/tests`; those read commands
failed because tests live in root `tests`. No files were altered by those reads.
The first new upload fixture used the default evidence directory; its identified
three-byte test blob was removed after verifying its SHA-256, and the fixture was
corrected to use temporary storage. Final tests use isolated temporary databases
and evidence directories. There were no failing test runs during this continuation.

## Every implementation/documentation file changed in Phase 2B-1

New files:

- `backend/app/api/routes/investigation.py` — all six investigation HTTP operations.
- `backend/app/core/custody_hash.py` — canonical versioned event hashing.
- `backend/app/models/custody.py` — attributed custody events and ORM guards.
- `backend/app/models/evidence_annotation.py` — notes and current tags.
- `backend/app/models/evidence_integrity.py` — durable check structure and constraints.
- `backend/app/schemas/investigation.py` — validated requests and safe response DTOs.
- `backend/app/services/custody.py` — atomic append, baseline, chain verification.
- `backend/app/services/evidence_metadata.py` — revision-controlled metadata/note transactions.
- `backend/app/services/evidence_query.py` — ownership-scoped details and paginated search.
- `backend/migrations/versions/0003_investigation.py` — additive schema and baseline migration.
- `tests/test_investigation.py` — 15 API/service/compatibility tests.
- `tests/test_investigation_migrations.py` — 2 populated upgrade/downgrade tests.
- `docs/phase2b1.md` — API, setup, transaction, and custody semantics.
- `docs/phase2b1-report.md` — this report.

Modified files:

- `backend/app/main.py` — registers the additive investigation router.
- `backend/app/core/limits.py` — bounds investigation bodies using the existing limiter.
- `backend/app/models/evidence.py` — title, review state, revisions/head, indexes/constraints.
- `backend/app/models/__init__.py` — exports/registers four new model classes.
- `tests/test_migrations.py` — expected head becomes 0003; behavioral assertions retained.
- `tests/test_models.py` — expected inventory becomes ten tables; behavioral assertions retained.
- `README.md` — current phase and links.
- `backend/README.md` — new schema/API and migration boundary.
- `tests/README.md` — new coverage and verified counts.
- `docs/architecture.md` — investigation services, records, and security boundaries.
- `docs/roadmap.md` — completed Phase 2B-1 and approval boundary.
- `docs/setup.md` — migration and investigation setup instructions.

Local runtime/build outputs, not source changes:

- `backend/shadowvault.db` — upgraded 0002 → 0003.
- `backend/var/backups/shadowvault-before-phase2b1-20260906T160921989539Z.db` — pre-upgrade backup.
- `frontend/dist/index.html`, `frontend/dist/assets/index-D8vI9LTd.css`,
  `frontend/dist/assets/index-D5A1J7Z4.js` — regenerated by the required regression build.
- Python `__pycache__/*.pyc` caches were generated/refreshed by imports and tests;
  these are ignored interpreter artifacts. Temporary test fixtures were cleaned up.

No frontend source, agent source, Phase 2A upload/service implementation, prior
migration, dependency manifest, or lock file was edited in this phase.

## Explicit boundaries

Migration baselines are migration-time registration, not retrospective acquisition
events. Unchanged v1 uploads do not append custody; their first annotation starts
tracking. Reads never fabricate history. Hash chains verify against the stored
head and do not protect against a privileged rewrite of that head and all events.
Notes and custody are append-only through these APIs and normal ORM operations;
direct database writes remain a trusted administrative boundary.

No frontend investigation UI, AI analysis, Linux collector, remote execution,
memory acquisition, integrity worker, browser session system, or Phase 2B-2 work
was introduced. Stop here and wait for approval.
