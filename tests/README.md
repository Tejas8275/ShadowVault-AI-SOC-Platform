# Tests

Backend tests use Python's built-in `unittest` runner and FastAPI TestClient.
Install the backend test extra, then run from the repository root:

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py" -v
```

- `test_backend_foundation.py`: configuration, health, CORS, session cleanup.
- `test_models.py`: relationships, constraints, UTC timestamps, bootstrap restrictions.
- `test_api_routes.py`: route registration, validation, and explicit HTTP 501 behavior.
- `test_migrations.py`: fresh upgrade, legacy data preservation, and unknown-schema refusal.
- `test_collection.py`: authentication, authorization, verified uploads, duplicate races, and cleanup.
- `test_storage.py`: disconnect and timeout cleanup.
- `test_windows_agent.py`: selected-file staging, selection boundaries, transport, and retry behavior.
- `test_collection_e2e.py`: a real Windows CLI subprocess uploading over HTTP to FastAPI and migrated SQLite.
- `test_investigation.py`: 15 investigation API, authorization, search, concurrency,
  transaction rollback, annotation, custody, integrity-structure, and upload compatibility tests.
- `test_investigation_migrations.py`: 2 populated Phase 2A preservation and downgrade-refusal tests.

Phase 2B-1 verification: 62 Python tests passed, 5 frontend tests passed, and the
TypeScript/Vite production build passed. See [the report](../docs/phase2b1-report.md).

Tests use in-memory or temporary SQLite databases inside the repository and do
not change the development database. The end-to-end test binds an ephemeral
loopback port and shuts down its server afterward. Windows-only tests skip on
other operating systems; the Phase 2A verification run was on Windows.
The readiness-failure test deliberately emits `Database readiness check failed`.
Starlette currently emits a deprecation warning for its HTTPX TestClient adapter.

Frontend API-client tests are in `frontend/tests`. Run them with
`npm --prefix frontend test`, then run `npm --prefix frontend run build` to
validate TypeScript and bundling. Browser workflows were added in Phase 2B-2 below.

Phase 2B-2 adds `test_agent_core.py` (four shared-core tests) and the separate
`browser_fixture.py` isolated API server. Current Python total: 66 tests. Frontend
Node service total: 12 tests. `npm --prefix frontend run test:browser` runs 15
Playwright/Edge browser workflows, including one real FastAPI workflow. Playwright
is development-only. The browser fixture never opens the development database.
Full commands, warnings, and limitations are in [the Phase 2B-2 report](../docs/phase2b2-report.md).

Phase 3A adds 14 tests in `test_timeline.py`, 2 in `test_timeline_migrations.py`,
4 frontend service tests in `frontend/tests/timeline.test.mjs`, and 6 browser
workflows in `frontend/tests/browser/timeline.spec.ts`. Final totals: 82 Python,
16 frontend service, and 21 browser tests, all passed. The original revision 0003
downgrade test now explicitly targets 0003 so it still exercises its original guard.
The browser fixture includes a separate timeline evidence record and an unlinked
legacy event. See [the Phase 3A report](../docs/phase3a-report.md).

Phase 3B adds 12 retrieval API/workflow tests in `test_retrieval.py`, 8 safe-reader
and response-lifecycle tests in `test_evidence_reader.py`, 8 Node tests in
`frontend/tests/download.test.mjs`, and 5 browser workflows in
`frontend/tests/browser/download.spec.ts`. Final totals: 102 Python, 24 Node service,
and 26 browser tests passed. TypeScript and production build passed. No migration
test or existing behavioral assertion was changed. The browser fixture adds a third,
separate evidence record with real private bytes; original fixtures remain intact.
See [the Phase 3B report](../docs/phase3b-report.md) for warnings and cleanup details.
