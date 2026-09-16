# Local setup

Use a fresh isolated source workspace for demonstrations, excluding existing environment files, databases, evidence and backups. Do not overwrite a working installation. Commands below run in PowerShell from the root containing both backend and frontend.

## Requirements

Windows Python3.13+ for storage/collection, Node22.18+, npm, and installed Microsoft Edge for browser tests. Prior verification used Python3.14 and Node24. Initial installation requires package registry access. No model API key is needed.

## Install backend

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -c backend/requirements.lock -e "./backend[test]"
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

Leave AI disabled and provider keys blank. Environment variables override backend/.env. The default database is backend/shadowvault.db and storage is backend/var/evidence and backend/var/retrieval. A dedicated source copy isolates those defaults; do not copy the original private data. With custom locations, use absolute paths and ensure every CLI/server uses the same settings.

## Initialize the fresh database

```powershell
.\backend\.venv\Scripts\python.exe -m app.db.migrate
```

Existing migrations reach **0008** without seeding records. Startup does not migrate. Existing databases require stopped writers and backup first. Legacy adoption/manual stamping is not a fresh-install step.

Read-only check of the default database:

```powershell
@'
from pathlib import Path
import sqlite3
p = Path('backend/shadowvault.db')
with sqlite3.connect(p.resolve().as_uri() + '?mode=ro', uri=True) as db:
    revision = db.execute('SELECT version_num FROM alembic_version').fetchall()
    integrity = db.execute('PRAGMA integrity_check').fetchall()
    fk = len(db.execute('PRAGMA foreign_key_check').fetchall())
    print({'revision': revision, 'integrity': integrity, 'fk_violations': fk})
    assert revision == [('0008',)] and integrity == [('ok',)] and fk == 0
'@ | .\backend\.venv\Scripts\python.exe -B -
```

Adapt the path privately if configured differently. Health/readiness alone does not verify migration head.

## Provision privately

Outside recordings/transcripts:

```powershell
.\backend\.venv\Scripts\python.exe -m app.cli init-operator --email demo@example.test --name "Demo Investigator"
```

This prints a new token once, digest and user UUID. Secure the token privately; set only returned SHADOWVAULT_OPERATOR_USER_ID and SHADOWVAULT_OPERATOR_TOKEN_SHA256 in backend configuration. Never publish provisioning output. Existing identities are not overwritten; creating a new user is not credential rotation. See [rotation guidance](security-operations.md).

## Start servers

Backend terminal:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers --log-config backend/logging.json
```

Leave it running. The optional logging profile emits severity only. Check http://127.0.0.1:8000/health and /api/v1/health; development documentation is at /docs. Restart after settings changes.

Frontend terminal, from root:

```powershell
npm --prefix frontend ci
if (-not (Test-Path frontend/.env)) { Copy-Item frontend/.env.example frontend/.env }
npm --prefix frontend run dev
```

Open http://127.0.0.1:5173. VITE_API_BASE_URL targets /api/v1; VITE_INVESTIGATION_API_BASE_URL targets /api/v2/investigation. Both examples point to port8000. These values are public, never secret storage. Exact CORS origins must match frontend host/port. Changing URLs requires restart/rebuild.

Open Cases and enter only the provisioned token in the masked field. Email/password endpoints remain501 but operator connection is functional. Disconnect/reload clears credentials and transient work, not other clients' access.

## Use, test and troubleshoot

Follow [Demo workflow](demo-guide.md) and [README verification commands](../README.md#verification). Browser tests use isolated ports5179/8769 and require Edge/process teardown permissions. Tests use temporary databases.

- Port occupied: identify the existing server; do not kill unrelated processes.
- 401: check private configuration, identity and environment overrides without exposing credentials.
- Empty evidence: case creation does not upload files; run the job/collector workflow.
- 503 upload/retrieval: check supported Python, permissions, free space and readiness. Preserve staged retries.
- 501 AI: expected without an approved provider; reports remain available.
- 422: input rejected; privacy handling deliberately does not echo rejected values.

This is local setup, not network deployment. TLS, proxy/static headers, storage ACLs/encryption, backup drills and production limits are in [Security operations](security-operations.md). Linux collection, sessions and RBAC are unavailable. Do not enable remote case disclosure for a demo.
