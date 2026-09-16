# Backend

FastAPI application with validated environment settings and SQLAlchemy 2 sessions.

From the repository root (PowerShell, Python 3.13+ for Windows evidence storage/retrieval):

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -c backend/requirements.lock -e "./backend[test]"
Copy-Item backend/.env.example backend/.env
backend/.venv/Scripts/python.exe -m app.db.migrate
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1
```

For deployment preparation, private logging, operator rotation and backup restore
verification, follow [Security operations](../docs/security-operations.md).
The commands above are local development commands, not a production deployment.

Run tests from the repository root:

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py" -v
```

`/health` checks the process. `/api/v1/health` checks database connectivity.
Development API documentation is at `http://127.0.0.1:8000/docs`.

For an existing unversioned Phase 1 database, back up and use
`python -m app.db.migrate --adopt-phase1`. See the [Phase 2A guide](../docs/phase2a.md)
for operator provisioning, registration, jobs, and uploads. Windows collection
storage requires Python 3.13+.

Settings load from `backend/.env`, overridden by `SHADOWVAULT_*` environment
variables. The default SQLite database is `backend/shadowvault.db`; the first
connection creates the file. Startup does not create or migrate tables.
`DATABASE_URL` supports synchronous SQLAlchemy URLs; other database engines
require their corresponding driver. SQLite is the only database verified here.

The application factory owns the engine through FastAPI lifespan. Every database
request receives a separate session. Write operations must commit explicitly;
failed requests roll back and sessions always close. SQLite foreign keys are enabled.

`python -m app.db.migrate` applies reviewed Alembic migrations and is repeatable.
`app.db.init_db` remains a development-only compatibility wrapper over migrations;
it still refuses production mode. Unversioned databases require explicit adoption.

The ten models live in `app/models`. Collection routes are protected with
operator and device credentials. Original authentication, incident, evidence,
and timeline placeholder routes still return HTTP 501. Verified evidence metadata
is accessed through the operator-only collection-job route. See the
[Phase 2A API contract](../docs/phase2a.md) for details.

Revision `0003` adds investigation metadata and custody structures. Operator-only
`/api/v2/investigation` routes provide search, details, annotations, notes, and custody
history. See the [Phase 2B-1 contract](../docs/phase2b1.md). Back up before migration;
revision `0003` refuses downgrade to prevent losing custody records.

Revision `0004` extends the existing timeline table with evidence provenance and
submission deduplication. Three additive investigation timeline operations create,
list and inspect observations. Event/custody writes commit atomically; original
evidence is never read or modified by this workflow. Legacy v1 timeline routes
retain HTTP 501. Revision 0004 is also forward-only. See [Phase 3A](../docs/phase3a.md).

Phase 3B keeps revision 0004. The operator-only
`POST /api/v2/investigation/evidence/{evidence_id}/download` prepares a private verified
copy, commits a custody preparation event and serves a binary attachment. Uploads
and models are unchanged. See [Phase 3B](../docs/phase3b.md) for storage requirements,
configuration, authorization, failure semantics and limits.

`requirements.lock` records the tested runtime and test dependency versions.
`pyproject.toml` declares compatible ranges; install with the constraints file
for the verified set. HTTPX is used only for tests; no separate test framework
dependency is required. The current Starlette TestClient emits an HTTPX adapter
deprecation warning; all tests pass. Track the adapter migration with future
dependency updates.
