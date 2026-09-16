# Security operations — controlled pilot

Phase 8B prepares deployment; it does not certify a public or multi-user release. Database head remains 0008. Keep the single-operator ownership model and existing AI safety boundaries. Windows evidence storage/retrieval requires Python 3.13+; the verified environment uses Python 3.14. Use the existing dependency locks.

## Deployment boundary

Use a reviewed service identity and an HTTPS reverse proxy for network access. Bind the backend to loopback, restrict its port, and serve the built frontend rather than Vite development mode. Initially use one worker: upload/retrieval/AI limits are process-local and AI usage accounting resets on restart.

Example from repository root after privately configuring production settings:

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log --no-proxy-headers --log-config backend/logging.json
```

This does not configure TLS or a frontend server. Do not use `--reload` for deployment. `--no-proxy-headers` avoids trusting forwarded identity/scheme headers; separately review explicit trusted proxy addresses if forwarding is later required.

Privately configure `SHADOWVAULT_ENVIRONMENT=production` and exact HTTPS `SHADOWVAULT_CORS_ORIGINS`. Frontend API base URLs must point to the approved HTTPS endpoints; build variables must never contain tokens or provider keys. Production mode disables API documentation but does not enforce TLS itself.

The proxy/static server must provide and test:

- Exact hostname restrictions and valid TLS. Reject cleartext credential requests; redirecting cannot undo disclosure of an already-sent token.
- No API caching, Authorization/body logging or query-string access logs. Disable sensitive request buffering to disk where supported; otherwise protect temporary storage and define retention.
- Compatible body/time limits and ingress connection/rate limits, including unauthenticated and legacy routes. Do not log rejected request bodies.
- Frontend headers: nosniff, no-referrer, frame denial and a tested CSP restricting scripts/styles to actual built assets, `object-src 'none'`, `base-uri 'none'`, `frame-ancestors 'none'`, and `connect-src` to the exact API origin. Adapt and test against the build rather than development HMR.
- HSTS only after validating the HTTPS hostname and policy scope; do not apply it to loopback or unrelated subdomains.

Verify actual frontend/API headers on success, 401/404/422/500, preflight and downloads. The application adds no-store, nosniff, no-referrer and frame denial to `/api/` and `/health`; that does not configure the separately served frontend. Successful payloads and Bearer challenges remain unchanged. Invalid requests retain 422 with a generic `detail` rather than rejected input/parser context. Unexpected pre-response errors return generic 500. Interrupted attachments terminate rather than becoming successful downloads or a second JSON response.

## Logging and diagnostics

`backend/logging.json` is an opt-in deployment profile. It disables Uvicorn access logs and outputs numeric severity only, without interpolating messages, arguments, names, paths, exceptions or tracebacks. The command also explicitly disables access logs. Other launch commands and proxies do not automatically inherit this protection.

The profile deliberately loses detailed startup/error diagnostics. Use private readiness/liveness checks, exit codes and synthetic reproduction. Do not enable raw request, SQL or provider debug logging on real investigation data. Richer telemetry requires a separately reviewed event-code design and secret-canary tests. OS logs, crash dumps, process environments and arbitrary third-party output remain administrator responsibilities; logging configuration is not universal DLP.

## Operator credentials

Disconnect/reload clears browser credentials and transient work, not another client's credential or downloaded files. There is no password login, refresh token or session-revocation endpoint. Keep operator and agent/provider credentials separate.

Rotation procedure:

1. Schedule a pause; handle transient drafts appropriately. Stop new requests and shut down cleanly after in-flight work settles.
2. Preserve `SHADOWVAULT_OPERATOR_USER_ID`. Do not rerun `init-operator` to rotate: it creates another user, changing ownership visibility.
3. In a private trusted administrative tool, generate `sv_operator_` plus Python `secrets.token_urlsafe(32)` and SHA-256 of its exact UTF-8 bytes. Deliver the raw token privately. No command arguments, transcript, chat or screenshots; no new dependency is required.
4. Replace only `SHADOWVAULT_OPERATOR_TOKEN_SHA256` in protected backend configuration. Remove stale environment overrides, which take precedence over `.env`. Never save the raw token in frontend/build configuration.
5. Restart the controlled instance. Privately verify the old token returns 401 and the new one reads the same authorized case. Disconnect/reconnect browser tabs.
6. Record the rotation event without either credential or digest. Securely dispose of temporary secret material.

No rotation CLI is added. Initial provisioning prints a token once and must run only in a private, non-recorded administrative environment. Agents have separate expiry/revocation through the existing authorized DELETE operation. Operator rotation alone does not revoke all agent tokens; owner deactivation blocks subsequent checks. Do not change case ownership to revoke a credential or invent a public administration endpoint.

Provider keys remain backend-only. Keep AI disabled unless separately approved. Synthetic OpenAI/Gemini adapters and remote token-count exceptions must not be used as general production adapters. This guide grants no real-data disclosure permission and changes no provider behavior.

## Backup and restore verification

Backups contain sensitive metadata/evidence. Use restricted ACLs, encrypted storage, retention rules and a separate protected credential recovery process. Never place database/evidence backups or manifests under a public static root. `.gitignore` is not an access control.

Minimal offline pilot procedure:

1. Quiesce uploads, mutations, retrieval and AI work; stop the backend and confirm no other writers. Record application/lockfile versions and revision without secrets.
2. Use SQLite's backup API for a consistent database copy after writers stop. Do not assume copying only a main file captures active WAL data. Copy the matching finalized evidence directory while unchanged. Review `.part` and orphan objects conservatively; never automatically delete apparent orphan evidence.
3. Hash artifacts into a protected manifest; retain the paired, timestamped database/evidence set. Separate secret/configuration recovery from ordinary reports and document configured paths privately.
4. Restore into an isolated directory with no production port, collectors or AI. Use disposable copies for tests that write. Never run migrations/stamp revisions to disguise incompatibility.
5. Require database revision 0008, integrity `ok`, zero FK violations. Stop on discrepancies.
6. Use trusted offline verification to compare every supported evidence object's size/SHA-256 against restored records and manifest, using safe opaque storage keys. Reject links/reparse points; never turn arbitrary legacy paths into file reads. Use existing custody-chain verification against the stored head. Report unsupported/missing objects explicitly. These checks provide no external tamper anchor.
7. On a disposable restored copy, test authorized metadata workflows and access denial. Retrieval appends custody, so test it only on the disposable copy. Use synthetic evidence for collector upload/repeat tests; preserve the retained backup unchanged.
8. Record results and limitations, retain the verified backup securely, remove only identified disposable artifacts, then resume operations under the operator's procedure.

Read-only SQLite check against an isolated backup (illustrative path):

```python
from pathlib import Path
import sqlite3

backup = Path(r"D:\ProtectedRestore\shadowvault.db")
with sqlite3.connect(backup.resolve().as_uri() + "?mode=ro", uri=True) as db:
    revision = db.execute("SELECT version_num FROM alembic_version").fetchall()
    integrity = db.execute("PRAGMA integrity_check").fetchall()
    violations = len(db.execute("PRAGMA foreign_key_check").fetchall())
    print({"revision": revision, "integrity": integrity, "fk_violations": violations})
    assert revision == [("0008",)] and integrity == [("ok",)] and violations == 0
```

This guidance is not a completed restore drill. No backup automation, retention deletion, custody rewrite or background work was added. Schedule an approved drill before release.

## Release and rollback

Run backend/frontend/browser/typecheck/build and isolated collector regressions after approved changes. Test the actual deployment for TLS/headers/logging, disk-full recovery and capacity. Dependency vulnerability scans and external penetration testing are separate release activities.

Phase 8B rollback concerns only middleware/wiring, logging profile and documentation/tests; no database downgrade is involved. Do not resolve compatibility problems by enabling sensitive logging/caching in production. Keep deployment private until a safe adjustment is reviewed. Authentication, case scope, custody/history and AI safety remain unchanged.
