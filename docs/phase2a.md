# Phase 2A — Secure collection foundation

## Delivered scope

Operator-authenticated agent registration, immutable selected-file jobs,
agent-authenticated binary uploads, independent SHA-256 verification, evidence
metadata persistence, and a Windows Python CLI. The Phase 1 frontend and legacy
placeholder routes remain compatible. No Phase 2B implementation is included.

## 1. Install and migrate

Use Python 3.13+ on Windows for private directory ACL support. Python 3.14.7 is
the verified runtime. From the repository root:

```powershell
backend/.venv/Scripts/python.exe -m pip install -c backend/requirements.lock -e "./backend[test]"
backend/.venv/Scripts/python.exe -m app.db.migrate
```

For an existing unversioned Phase 1 database, stop the backend, make a database
backup, then run:

```powershell
backend/.venv/Scripts/python.exe -m app.db.migrate --adopt-phase1
```

Adoption checks the four baseline tables, column/index/foreign-key structure,
check constraints, and orphan references before stamping revision `0001` and
upgrading to `0002`. Unknown schemas are refused. Never stamp an arbitrary
database manually to bypass this check. Existing evidence becomes `legacy`,
without fabricated verification timestamps. Fresh databases run both revisions.

The repository's development database was backed up under `backend/var/backups/`
and upgraded during implementation. No real operators, agents, or jobs were seeded.
Migration tests use temporary databases and preserve existing fixture records.

## 2. Provision the local operator

Phase 2A uses one configured API operator bound to a real User record. This is
separate from the unimplemented browser login/session flow. Provisioning is a
trusted server-local command, not a public registration API:

```powershell
backend/.venv/Scripts/python.exe -m app.cli init-operator --email investigator@example.com --name Investigator
```

This prints a random operator token once, its SHA-256 digest, and the user UUID.
Keep the raw token privately. Add the returned `SHADOWVAULT_OPERATOR_USER_ID`
and `SHADOWVAULT_OPERATOR_TOKEN_SHA256` to `backend/.env`. Only the digest goes
in backend configuration. Do not overwrite an existing `.env` with the example.
The created identity has no usable password or browser login.

Create an incident owned by the configured operator:

```powershell
backend/.venv/Scripts/python.exe -m app.cli create-incident --title "Selected file investigation"
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Record the incident UUID. Existing incidents owned by the same operator also work.
Rotate the operator credential by generating a new high-entropy token, replacing
the configured digest, and restarting the backend. Disabling the User invalidates
operator and associated agent access. Multi-user login/session management is deferred.

## 3. Register an agent and approve selected files

Example PowerShell 7 commands in a second terminal:

```powershell
$collectionApi = 'http://127.0.0.1:8000/api/v1'
$operatorToken = Read-Host 'Operator token' -MaskInput
$operatorHeaders = @{ Authorization = "Bearer $operatorToken" }
$registeredAgent = Invoke-RestMethod -Method Post -Uri "$collectionApi/agents" -Headers $operatorHeaders -ContentType 'application/json' -Body '{"name":"Windows workstation","platform":"windows","collector_version":"0.1.0"}'
$incidentId = Read-Host 'Incident UUID'
$selectedPath = Read-Host 'Absolute local Windows file path'
$jobBody = @{
  incident_id = $incidentId
  agent_id = $registeredAgent.id
  files = @(@{ source_path = $selectedPath; max_bytes = 104857600 })
} | ConvertTo-Json -Depth 4
$collectionJob = Invoke-RestMethod -Method Post -Uri "$collectionApi/collection-jobs" -Headers $operatorHeaders -ContentType 'application/json' -Body $jobBody
```

The returned `$registeredAgent.token` is visible only in this registration
response; the database stores its digest. Transfer it securely to the collector
operator. It expires after 24 hours by default. Registration requires the API
operator credential; possession of an agent token cannot register more agents.

Manifest paths are absolute local Windows file paths. The manifest cannot be
edited. Each selected file receives a server-generated item UUID and byte limit.
There are at most 100 files, 100 MiB per upload, and 500 MiB of approved file
limits per job by default. Changing a selection requires a new job.

## 4. Collect and upload

On the selected endpoint, run the collector with its agent token and job UUID.
For the same-machine development example:

```powershell
$env:SHADOWVAULT_AGENT_TOKEN = $registeredAgent.token
python agents/windows/collector.py --backend $collectionApi --allow-http-local --job-id $collectionJob.id --file $selectedPath
Remove-Item Env:SHADOWVAULT_AGENT_TOKEN
```

On another machine, use a properly configured HTTPS endpoint, omit
`--allow-http-local`, and enter the agent token at the hidden prompt. Never expose
the loopback HTTP development configuration over a network. Full options and
retry behavior are in the [Windows collector guide](../agents/windows/README.md).

Inspect verified metadata as the operator:

```powershell
Invoke-RestMethod -Uri "$collectionApi/collection-jobs/$($collectionJob.id)/evidence" -Headers $operatorHeaders
```

## API contract

- `POST /api/v1/agents`: operator-only registration; HTTP 201, one-time token,
  `Cache-Control: no-store`.
- `DELETE /api/v1/agents/{agent_id}`: operator-only revocation; HTTP 204.
- `POST /api/v1/collection-jobs`: operator-only creation for an owned incident and agent.
- `GET /api/v1/collection-jobs/{job_id}`: operator-only manifest and progress.
- `POST /api/v1/collection-jobs/{job_id}/cancel`: operator-only cancellation.
- `GET /api/v1/collection-jobs/{job_id}/evidence`: operator-only verified metadata.
- `GET /api/v1/agents/jobs/{job_id}`: assigned-agent-only manifest retrieval.
- `PUT /api/v1/agents/jobs/{job_id}/files/{item_id}`: assigned-agent-only upload.

The upload body is raw `application/octet-stream`, not multipart. Required headers
are `Authorization: Bearer ...`, `X-Evidence-SHA256` (lowercase hex),
`X-Evidence-Size` (bytes), and `X-Collected-At` (timezone-aware ISO 8601). The CLI
also sends `Content-Length`. No filenames or filesystem storage paths are accepted
in upload headers. The server derives provenance from the approved manifest.

A new verified upload returns HTTP 201. A verified identical retry returns HTTP
200 and the original evidence identity. A different digest/size for the same
job item returns HTTP 409. Actual bytes are verified even for duplicate requests.
SHA-256 or received-size mismatch returns HTTP 422 and stores no evidence record.
Oversized bytes return HTTP 413; invalid credentials return HTTP 401; foreign or
unselected resources return HTTP 404. Revoked, expired, and disabled-owner tokens
are rejected. Cancelled jobs return HTTP 409.

## Storage and consistency

Incoming bytes stream into random `.part` files inside `backend/var/evidence`.
After size and SHA-256 checks, the server rechecks authorization, renames the file
to an opaque `.blob` key, then commits metadata. Only committed, verified metadata
is returned. A database uniqueness constraint on `(collection_job_id,
collection_item_id)` handles simultaneous retries. Losing retries remove only
their own candidate object. No evidence is deduplicated across incidents.

Handled mismatch, disconnect, timeout, and database failures remove temporary
files. A process/power failure between rename and commit can leave an unreferenced
file. Files and SQL cannot share a transaction: orphan reconciliation and durable
custody auditing remain future work. Do not delete uncertain files automatically;
compare storage keys with the database while the service is stopped. Storage is
not publicly served and no download endpoint is introduced in Phase 2A.

Job completion is computed from the number of verified selected items. The
persisted job state remains `open` unless cancelled; retries remain valid after
completion. No worker or remote task polling is involved.

## Security and operational boundary

- Operator and agent credentials have separate authorization paths. Incident
  ownership and agent assignment are checked server-side, including after streaming.
- Job JSON bodies are limited to 128 KiB before parsing. Raw bodies are counted,
  bounded by per-file and server limits, and given a 120-second timeout. Upload
  concurrency is capped at four per process; excess requests return HTTP 429.
- Tokens are random, digested at rest, and absent from storage manifests/logs.
  Agent revocation preserves history; expired agents must be re-enrolled and
  assigned new jobs. Automatic rotation is deferred.
- New storage/spool directories use mode `0o700`; Windows requires Python 3.13+
  for its ACL handling. Existing ACLs are not modified. Use dedicated private
  directories, encrypted disks, and a minimally privileged service account.
- Selected files are treated as hostile bytes. The server never executes,
  unpacks, interprets, or invokes AI over their contents.
- Independent matching hashes prove byte consistency, not endpoint honesty.
  This is a local collection pilot, not a complete chain-of-custody system.
- TLS termination, enterprise identity, global rate/space quotas, backup retention,
  automated orphan reconciliation, custody logs, and production deployment remain
  outside Phase 2A. Use a controlled local environment until those are implemented.

Configuration defaults are listed in `backend/.env.example`. No frontend changes,
memory acquisition, remote execution, background agent service, or AI analysis
were implemented.

## Verification

```powershell
backend/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py" -v
backend/.venv/Scripts/python.exe -m pip check
npm --prefix frontend test
npm --prefix frontend run build
```

Tests cover migrations and legacy data preservation, valid/mismatched uploads,
duplicates and concurrent duplicates, authorization boundaries, revocation during
streaming, size limits, cleanup failures, timeouts/disconnects, collector staging
and retry behavior, and a real Windows CLI/HTTP/SQLite round trip. Windows-specific
tests skip on other operating systems; the verified run uses Windows.

References: [Python private directory behavior](https://docs.python.org/3/library/os.html#os.mkdir),
[Alembic batch migrations](https://alembic.sqlalchemy.org/en/latest/batch.html),
[Starlette request streaming](https://www.starlette.io/requests/), and
[OWASP upload controls](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
