# Phase 2A completion report

## Result

Implemented the first selected-file collection workflow: provision a local
operator, register a Windows agent, authorize selected files for an owned incident,
stage/hash/upload those files, independently verify received bytes, and persist
verified evidence metadata. Phase 2B has not started.

## Changed files

Database and dependencies:

- `backend/alembic.ini`
- `backend/migrations/env.py`
- `backend/migrations/script.py.mako`
- `backend/migrations/versions/0001_phase1.py`
- `backend/migrations/versions/0002_collection.py`
- `backend/app/db/migrate.py`
- `backend/app/db/init_db.py`
- `backend/app/models/agent.py`
- `backend/app/models/collection_job.py`
- `backend/app/models/evidence.py`
- `backend/app/models/__init__.py`
- `backend/pyproject.toml`
- `backend/requirements.lock`

Backend API, security, and storage:

- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/core/limits.py`
- `backend/app/schemas/collection.py`
- `backend/app/services/__init__.py`
- `backend/app/services/collection.py`
- `backend/app/services/storage.py`
- `backend/app/api/routes/collection.py`
- `backend/app/api/router.py`
- `backend/app/main.py`
- `backend/app/cli.py`
- `backend/.env.example`

Collector and tests:

- `agents/windows/collector.py`
- `tests/test_models.py` — extended the expected table inventory to six; preserved all existing behavioral assertions.
- `tests/test_migrations.py`
- `tests/test_collection.py`
- `tests/test_storage.py`
- `tests/test_windows_agent.py`
- `tests/test_collection_e2e.py`

Documentation and ignore rules:

- `.gitignore`
- `README.md`
- `backend/README.md`
- `agents/README.md`
- `agents/windows/README.md`
- `tests/README.md`
- `docs/README.md`
- `docs/setup.md`
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/phase2a.md`
- `docs/phase2a-report.md`

Local runtime state: `backend/shadowvault.db` upgraded to revision `0002` after a
backup under `backend/var/backups/`. No production identities or credentials were
created. Installed Alembic and its required transitive packages only in the
repository virtual environment. The Windows CLI has no third-party dependencies.
Frontend source and dependencies are unchanged.

## Verification

Verified on Windows with Python 3.14.7 and Node 24.19.0:

- Backend/collector suite: **45 tests passed**, including every Phase 1 test.
- Frontend service suite: **5 tests passed**.
- TypeScript checking and production frontend build: **passed**.
- Python dependency consistency: **passed**.
- Local SQLite revision: **0002**, with **zero foreign-key violations**.
- Real CLI/HTTP upload, server-stored byte comparison, and duplicate run: **passed**.

The tests demonstrate rejection of mismatched hashes, unauthorized agents,
foreign incidents, unselected paths, expired/revoked credentials, and oversize
uploads. They also verify identical and concurrent retries, stream cleanup,
database-failure cleanup, and data-preserving migration adoption.

The existing Starlette HTTPX TestClient deprecation warning remains. The readiness
failure regression test intentionally logs its simulated database failure.
No test/build errors remain. Verification servers are stopped automatically.

## Current boundaries

This is a controlled local collection pilot. Browser login, enterprise identity,
full custody auditing, downloads, automated orphan reconciliation, deployment,
and global storage/rate policies remain future work. A process crash between file
finalization and metadata commit may leave an orphan object, which is never
exposed through the API. Existing storage/spool ACLs must be private; Windows
collection requires Python 3.13+ for newly created directory ACLs.

No memory acquisition, remote execution, background collection, or AI analysis
was implemented. Follow [Phase 2A setup](phase2a.md) to provision an operator and
run a selected-file collection. Phase 2B requires separate approval.
