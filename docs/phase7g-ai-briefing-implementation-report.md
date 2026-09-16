# Phase 7G — case metadata briefing implementation report

Verification completed: 2026-09-14.

## Completion and release boundary

Phase 7G's authorized provider-neutral metadata briefing workflow is implemented and fully regression-tested. This continuation finished verification and documentation without adding capabilities or changing product code.

**No production AI provider/model is installed or selected.** The normal application returns a safe 501 when briefing generation is requested without a provider. Successful integration tests use an explicitly injected, test-only deterministic provider; they do not establish real-model relevance, hallucination resistance, latency, privacy or production readiness. The user's Phase 7G instruction explicitly required a clean provider boundary and safe unavailable behavior when no existing provider configuration exists. Concrete model deployment and the Phase 7F real-model evaluation gate remain pending; this report does not claim a released live AI model.

## Exact changed-file inventory

Compared with the captured pre-Phase-7G SHA-256 inventory, the implementation changes these 15 files and adds this report (16 files total). No inspected pre-existing file was removed.

Backend:

- `backend/app/main.py` — explicit optional provider injection and per-process inference capacity initialization.
- `backend/app/api/routes/investigation_incidents.py` — additive authorized briefing endpoint.
- `backend/app/schemas/ai_briefing.py` — new versioned request, provider selection and response contracts.
- `backend/app/services/ai_model.py` — new trusted provider protocol and fixed instructions; no default implementation or network client.
- `backend/app/services/ai_context.py` — new metadata allowlists, canonical context manifest and server citation resolution.
- `backend/app/services/ai_briefing.py` — new authorization, limits, provider orchestration, stale-context checks and safe errors.

Frontend:

- `frontend/src/features/cases/briefing.ts` — new briefing response types.
- `frontend/src/features/cases/CaseBriefing.tsx` — new transient case briefing panel.
- `frontend/src/features/cases/CaseWorkspace.tsx` — integrates the panel with the existing case/authentication lifetime.
- `frontend/src/features/evidence/service.ts` — reuses the operator client for briefing generation, scoped timeout and response validation.

Tests:

- `tests/briefing_fixture.py` — new deterministic provider used only by tests.
- `tests/test_ai_briefing.py` — 14 focused backend tests.
- `tests/browser_fixture.py` — explicitly injects the test provider into the isolated browser backend.
- `frontend/tests/ai-briefing.test.mjs` — four focused service tests.
- `frontend/tests/browser/ai-briefing.spec.ts` — four focused browser workflows, including concurrent refresh and cancellation.

Documentation:

- `docs/phase7g-ai-briefing-implementation-report.md` — this report.

Build output and temporary verification logs are generated artifacts, not additional source changes. No dependency manifests/locks, environment configuration, migration files, database models, collector code or existing custody/history/timeline services changed.

## Architecture and API

The only new endpoint is `POST /api/v2/investigation/incidents/{id}/ai-briefing`. Its fixed task accepts the versioned request `{ "schema_version": 1 }` (version defaults to 1); unknown request fields are rejected. Clients cannot supply case context, provider destinations, prompts or citations. Successful responses use `Cache-Control: no-store` and include case identity/revision, snapshot time, a context digest, versioned task metadata, resolved sources and limitations.

Flow: existing operator authorization → existing authorized case-report snapshot → allowlisted metadata/context manifest → explicitly injected provider selects request-local aliases → server resolves exact source fields and correction context → fresh authorization/context checks → transient case panel.

`create_app(ai_provider=reviewed_provider)` is the explicit integration boundary. A provider supplies local input-token counting and asynchronous bounded source selection. No SDK, API key, model, endpoint selection, automatic fallback or new configuration file is introduced. Arbitrary provider implementation code is trusted deployment code, not sandboxed by this protocol.

## Context, citations and interpretation boundaries

The context includes allowlisted case metadata, evidence metadata and verification metadata, timeline records, indicator observations/corrections, case-history changes and limited custody metadata. It reuses authorized report projection and scope checks rather than reading evidence or calling internal HTTP endpoints.

Original evidence/file content, note bodies, storage identities/paths, custody detail payloads and actor identities are excluded. Source UUIDs remain in the server manifest; the provider receives request-local aliases and authorized metadata. Free-text fields can nevertheless contain sensitive information entered by an investigator.

The provider returns only a strict JSON list of distinct known aliases, not authored facts or prose. The server rejects unresolved aliases, duplicates, extra keys, wrong types, invalid JSON and excessive output. Selected values come from stored source metadata. Indicator correction chains are included by the server and checked for authorized evidence relationships; an unresolved correction fails the response rather than appearing as a valid citation.

The UI explicitly labels this as **AI-generated selection, not AI interpretation**. Recorded assertions are not certified facts. Citations establish traceability, not truth; selection is non-exhaustive. Initial upload verification is distinguished from current integrity, and this workflow neither verifies custody chains nor certifies retrieval delivery. The context digest is labeled as distinct from an evidence hash.

## Authorization, security and persistence

- Existing operator bearer-token and incident ownership boundaries remain authoritative. Agent credentials do not grant operator access.
- Context construction excludes foreign cases and hidden requester-owned evidence. Authorization is checked before dispatch and again before publication, including all snapshot sources rather than only selected citations.
- A fresh context digest comparison rejects metadata changes during preparation with 409. Access revocation prevents publication.
- Fixed instructions and untrusted metadata are separate provider arguments. The model receives no database handle, credential argument, file reader or action/tool interface. Displayed text is rendered through existing React text rendering, not executable markup.
- Known operator/agent credential patterns and the current request credential/digest in context are rejected before dispatch. Provider exception text is not returned to the client. No production prompt/output logging or credential storage was added.
- Secret filtering is **not general data-loss prevention**. Unknown secrets or private information in free text require deployment review; a future remote provider requires explicit disclosure/privacy approval.
- Briefings live only in current case-workspace memory. Same-case refresh preserves pending/successful work; failed replacement retains the prior successful briefing with a separate failure/retry message. Case switching, leaving the case, disconnect and reload clear transient state; definitive access denial clears retained output. Old responses cannot populate another case.
- There is no AI persistence, report mutation, automatic retry, evidence read/retrieval, custody append, case-history event or investigation write caused by generation/viewing.

## Limits and recovery

The service retains existing report snapshot limits and adds a 64 KiB serialized context limit, 8,000 input-token ceiling, 1,024 requested output-token limit, 32 KiB output/response limit, and one inference slot per application process. The model selects at most 20 sources; required correction context may expand the resolved result to at most 40. Inference has a 30-second deadline; the briefing client alone uses a 50-second request timeout.

Unavailable configuration returns 501; capacity exhaustion 429; size/token limits 413; sensitive-context rejection 422; stale context 409; timeout 504; malformed/provider failure 503. Messages are sanitized. Capacity and database transaction cleanup run in finally blocks. Database transactions are not held across model inference. Retry is always explicit.

Cancellation is cooperative. Browser cancellation prevents publication in that browser, but cannot promise immediate termination/erasure of work already dispatched to a future provider. Provider token counting must include actual framing and reserve output capacity. The interface cannot forcibly contain a blocking or non-cooperative implementation. Multiple processes would require a separate capacity assessment.

## Final verification results

All final commands exited successfully; no tests failed or were skipped.

- Full backend: `$env:PYTHONPATH='backend'; .\backend\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v` — **166 passed, 0 failures**, 58.254 seconds. Includes the 14 new briefing tests and all existing regressions.
- Frontend services: `npm --prefix frontend test` — **50 passed, 0 failures, 0 skipped**, 993.1533 ms. Includes four new briefing tests.
- TypeScript: `npm --prefix frontend run typecheck` — **passed**.
- Production build: `npm --prefix frontend run build` — **passed**, 61 modules transformed; Vite build 2.74 seconds.
- Complete browser suite: `npm --prefix frontend run test:browser` — **75 passed, 0 failures**, 1.8 minutes. Clean isolated test servers on ports 5179/8769; dedicated fixture database. Includes four briefing workflows plus all 71 existing workflows.
- Windows collector/upload regression: `test_collection_e2e.CollectionEndToEndTests.test_real_cli_upload_and_repeat` — **passed within the full backend suite**. This exercises the actual CLI/upload/repeat path. The remaining Windows collector tests also passed; no separate count is added to 166.
- Live SQLite revision, read-only — **0008**.
- SQLite `PRAGMA integrity_check` — **ok**.
- SQLite `PRAGMA foreign_key_check` — **0 violations**.
- Database file SHA-256 — `8f8e520eb9e23d2354652990d114fcb5895f7f1b5e293f0135299f279acde969`, matching the pre-implementation fingerprint.

Focused backend verification covers unauthorized/inactive operators, foreign-case denial, hidden/foreign evidence exclusion, exact server fields, correction resolution, invented/invalid citations, hostile metadata separation, provider failures, limits, capacity release, timeout, concurrent context mutation, access revocation, known-credential rejection, no original-file reads and unchanged database rows.

Frontend/browser verification covers existing bearer request semantics, sanitized failures, invalid/foreign responses, loading, same-case refresh while generation is pending, completed snapshot retention, Case A/Case B isolation, failed replacement/manual retry, stale-context errors, access denial clearing, actual cancellation/focus return, mobile layout, disconnect and reload. Existing notes/tags, custody/integrity, retrieval, timeline, history, IOC corrections/retry and report workflows remain passing.

## Database, dependencies, warnings and limitations

Database remains **0008**. No migration or database write was required, so no migration backup/upgrade was performed in this phase. Existing records are preserved by the unchanged database fingerprint and focused before/after table checks. No dependencies were added or upgraded.

Observed non-blocking warnings: Starlette test-client deprecation concerning its existing httpx integration; Node reports NO_COLOR ignored because FORCE_COLOR is set; npm prints an available major-version update notice. These did not fail verification and no dependency changes were made to silence them.

No live model calls or external disclosures were performed. Test-provider success does not prove model selection quality or semantic completeness. Free-text sensitivity, prompt-induced omission/selection bias, cooperative cancellation, bounded case size and per-process capacity remain limitations. Authorization is checked at defined request boundaries; this does not implement continuous revocation push into an idle browser. No automatic threat verdicts, raw evidence AI analysis, autonomous actions, external enrichment, teams/RBAC, background workers or AI persistence were added.

The next separately approved work would be selection/privacy review of a concrete provider and sanitized real-model evaluation, not automatic expansion of AI capabilities. Rollback of this additive feature requires disabling/removing its panel/route/provider integration, with no database downgrade or custody/history changes. No next phase was started.

Phase 7G complete — awaiting approval before the next AI phase.
