# Phase 8B — Security hardening implementation report

Date: 2026-09-15. **Complete for the approved hardening scope.** No Phase 8C work started.

## Findings addressed and exact changed files

Phase 8A F2 is addressed with consistent API response privacy, safe validation/unexpected-error handling and an opt-in private logging profile. F1 deployment preparation, F3 credential operations and F5 backup verification are addressed through an operational runbook. This does not claim a deployed TLS configuration or completed restore drill.

Exactly seven files:

1. `backend/app/core/privacy.py` — new ASGI response privacy boundary, generic validation handler and content-free logging formatter.
2. `backend/app/main.py` — register privacy middleware and validation handler.
3. `backend/logging.json` — new opt-in server logging profile suppressing access logs and arbitrary diagnostic content.
4. `tests/test_security_hardening.py` — six focused regressions.
5. `docs/security-operations.md` — deployment, private logging, operator rotation and offline backup/restore verification guide.
6. `backend/README.md` — Windows runtime clarification and operational guide link.
7. `docs/phase8b-security-hardening-report.md` — this report.

Existing changes were preserved. No frontend source, provider adapter, authentication service, dependency/lockfile, migration, agent or actual environment file changed. Temporary verification logs and regenerated ignored frontend build/test artifacts are not product source changes.

## Implemented behavior

HTTP responses under `/api/` and `/health` now consistently receive `Cache-Control: no-store`, `Pragma: no-cache`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and `X-Frame-Options: DENY`. Coverage includes successful responses, authentication/validation/not-found failures, body-limit rejections and CORS preflights. Existing attachment headers and Bearer challenges remain intact. No response bodies are buffered by this middleware.

Validation retains HTTP 422, with `{"detail":"Request validation failed"}` instead of input values, dynamic field locations or parser context. This intentional error-detail change prevents rejected sensitive content from being echoed. Successful API schemas, authorization and mutation semantics remain unchanged.

Unexpected failures before headers are sent return a generic HTTP 500 and log only a fixed failure message. Dependency cleanup/rollback unwinds before the middleware handles the error. A failure after response start raises a sanitized interruption rather than sending a second response or representing a partial attachment as successful. Existing retrieval cleanup/capacity release remains in place. Cancellation is not swallowed by the ordinary-exception handler.

The logging profile emits only numeric severity and suppresses Uvicorn access messages; it ignores arbitrary message arguments, names, paths and traceback data. It must be explicitly selected by the documented command. The application does not globally change logging at import time. Logs from a separately configured proxy, OS or arbitrary third-party output remain deployment responsibilities.

No TLS server, reverse proxy, host infrastructure or frontend header configuration was installed. The guide defines those deployment requirements and verification steps. It also explains consistent SQLite/evidence backups, protected manifests, isolated restore testing, safe opaque-key verification and the difference between retrieval preparation and confirmed delivery.

## Security boundaries preserved

Operator bearer credentials remain in browser memory; no sessions, passwords, refresh flow or RBAC were added. Credential rotation guidance preserves the existing user identity and case ownership. Disconnect is explicitly distinguished from revocation. Existing agent expiry/revocation remains separate.

Case isolation, evidence custody, case history, IOC corrections, timeline and report/briefing transient-state behavior remain unchanged. No original evidence was read by this implementation task. Tests use isolated synthetic fixtures; no real investigation data was transmitted to OpenAI or Gemini and no live-provider evaluation was invoked. Phase 7I local-only production counting and provider limits remain untouched.

## Exact verification results

- Focused privacy regressions: **6 passed, 0 failures**, 0.260 seconds. Included in the full backend total below, not additional tests.
- Complete backend: `python -m unittest discover -s tests -p 'test_*.py' -v` — **224 passed, 0 failures**, 92.478 seconds, exit 0 (218 existing plus 6 new).
- Complete frontend service/helper tests: `npm --prefix frontend test` — **54 passed, 0 failures, 0 skipped**, 903.7038 ms, exit 0.
- TypeScript: `npm --prefix frontend run typecheck` — **passed**, exit 0.
- Production build: `npm --prefix frontend run build` — **passed**, exit 0; 62 modules, Vite build 1.52 seconds.
- Complete browser rerun: `npm --prefix frontend run test:browser` — **81 passed, 0 failures**, 1.8 minutes, exit 0. No browser tests or product behavior were changed to obtain this result.
- Windows collector/upload/repeat: `test_collection_e2e.CollectionEndToEndTests.test_real_cli_upload_and_repeat` — **passed** within the 224-test backend suite, alongside existing storage, retrieval, custody and authorization regressions.
- Isolated logging-profile smoke check: **passed**. Loaded the actual JSON profile in a subprocess; synthetic access output was suppressed and two server events contained only severity, with no synthetic secret message content. This is a separate smoke check, not counted in the 224 tests.

New focused tests cover private success/denial/not-found/preflight responses; Bearer/CORS compatibility; invalid JSON/body secret suppression; generic unexpected error and content-free logging; partial-stream failure semantics; formatter secret/traceback suppression; body-limit and legacy 501 compatibility.

The first browser attempt reported all 81 individual test passes but stalled during Windows process teardown and was interrupted (exit 1). It was not counted as a completed suite. The identical suite was rerun with expanded process permissions and completed cleanly. This was a test-environment recovery, not a product fix or relaxation of tests.

## Database and preservation

Read-only SQLite checks: **revision 0008**, integrity **ok**, **0 foreign-key violations**. Database SHA-256 remains `8f8e520eb9e23d2354652990d114fcb5895f7f1b5e293f0135299f279acde969`, identical to the pre-change baseline. No migration or database backup was necessary because this phase does not modify the database. Backup guidance was created, not executed on real evidence.

A pre-change fingerprint inventory of 253 existing files covers sources, migrations, tests/provider tools, agents, documentation and root/backend/frontend configuration/dependency/database files. Only `backend/app/main.py` and `backend/README.md` changed among existing files; the other five inventory entries above are new. Provider and authentication source fingerprints, the actual `.env`, dependencies and database remain unchanged.

## Warnings and limitations

Both browser runs emitted the existing Node NO_COLOR/FORCE_COLOR warning. The first attempt also emitted a Windows asyncio ConnectionResetError during a passing browser workflow; the final suite exited successfully. The backend intentionally printed its sanitized readiness failure while testing that path; the test passed.

The logging profile intentionally removes detailed diagnostics and startup messages. It is opt-in, cannot govern another server's logs, and is not comprehensive DLP. Network/TLS/host/CSP/proxy tests, dependency vulnerability scanning, disk-full/load testing and an actual backup restore drill remain release gates. This work does not certify public production readiness.

Middleware headers do not apply to frontend assets served by another process. Production mode alone does not enforce HTTPS. Usage limits remain process-local; static operator lifecycle, trusted database administrators, crash orphan review and non-revocable downloaded copies remain documented limitations. OpenAI's previously recorded live-generation evaluation is still incomplete; Gemini's prior success remains synthetic-only.

No architecture redesign, new dependencies, AI permissions, autonomous actions, external enrichment, teams/RBAC, background workers or authentication/custody changes were added. Rollback requires only reverting the listed code/logging/documentation changes and tests; no database downgrade. Keep deployment private while resolving any compatibility issue rather than re-enabling sensitive logging or caching.

**Phase 8B complete. Awaiting approval before Phase 8C.**
