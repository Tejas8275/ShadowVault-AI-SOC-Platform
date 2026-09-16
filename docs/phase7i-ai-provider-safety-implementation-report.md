# Phase 7I — AI provider safety implementation report

Date: 2026-09-14.

**Phase 7I safety implementation and all available automated verification are complete.** The implementation is limited to adapter safety, usage controls and synthetic evaluation preparation. No live model is selected, configured or evaluated. Real-model evaluation remains a separately approved manual step, not a completed result of this phase.

## Exact changed files

Seventeen implementation/test/configuration-example files plus this report (18 total), compared with the pre-Phase-7I fingerprint inventory:

- `backend/app/core/config.py` — explicit disabled-by-default AI settings and bounded usage settings.
- `backend/app/main.py` — optional reviewed adapter wiring and per-process usage control.
- `backend/app/services/ai_adapter.py` — new bounded request-scoped Python adapter process protocol.
- `backend/app/services/ai_execution.py` — new deadline encompassing counting and selection, plus existing-provider compatibility.
- `backend/app/services/ai_usage.py` — new atomic cooldown/window/run budget; no queue or persistence.
- `backend/app/services/ai_model.py` — token-count protocol permits asynchronous counting without removing existing synchronous providers.
- `backend/app/services/ai_context.py` — source/field ceilings and duplicate-manifest rejection.
- `backend/app/services/ai_briefing.py` — integrates deadline/admission handling and checks configured provider-key canaries before dispatch.
- `backend/.env.example` — placeholder-only settings; AI explicitly disabled.
- `frontend/src/features/cases/CaseBriefing.tsx` — clearer capacity/usage-limit guidance only.
- `frontend/tests/ai-briefing.test.mjs` — one additional explicit-retry/usage-denial test.
- `frontend/tests/browser/ai-briefing.spec.ts` — two additional usage/timeout and inert synthetic-injection workflows.
- `tests/test_ai_briefing.py` — explicit test-only usage allowance so existing failure/retry tests retain their purpose.
- `tests/browser_fixture.py` — explicit test-only cooldown/window settings, still using the deterministic fixture provider.
- `tests/test_ai_safety.py` — 16 new adapter, context, usage, configuration, privacy and isolation tests.
- `tests/synthetic_ai_cases.py` — fixed synthetic A/B report projections, with normal/injection/empty/oversize variants.
- `tests/evaluate_ai.py` — manual synthetic preview and explicitly opted-in one-attempt evaluator; no live database input.
- `docs/phase7i-ai-provider-safety-implementation-report.md` — this report and evaluation procedure.

No existing file was removed. Authentication, evidence/custody/history/timeline/indicator models and services, migrations, collector code, dependency manifests/locks and the actual `.env` were not changed. Build output and temporary verification logs are generated artifacts, not additional source changes.

## Provider boundary and configuration behavior

The original versioned briefing endpoint, source-selection response contract, report projection, case authorization and transient UI remain intact. A provider is never chosen automatically. Default settings leave `app.state.ai_provider` as `None`; the authorized request receives safe 501/unavailable behavior.

The new `CommandProvider` is a **generic adapter boundary, not an implementation of any model/vendor API**. An administrator must supply a reviewed absolute `.py` script. With explicit enablement and that path, the factory starts a fresh adapter process for each count/select operation, using the backend Python interpreter with isolated mode and forced UTF-8. No shell or caller-controlled command is used. Invalid configured script paths fail with a generic startup error; missing configuration stays unavailable. The existing explicit `create_app(ai_provider=...)` injection remains supported for tests/trusted integrations independently of environment enablement.

The script receives exactly one JSON request on stdin and returns one JSON result on stdout. It must not log context, spawn children, create tools/actions, retain conversations, retry or select a fallback destination. Stderr is discarded. The environment is restricted to operating-system/temp variables and, only if explicitly supplied, a separate backend provider key. Operator/database/Python injection environment variables are not inherited. The process runs with the application's OS identity: this is a resource boundary, **not a filesystem/network sandbox for hostile administrator code**. Review and OS restrictions remain required before live evaluation.

Count request: `operation="count"`, fixed `instructions`, and `data` containing the canonical metadata JSON string. Response must be exactly an object with integer `input_tokens`; duplicates/extra fields/wrong types fail. Counting must be local, use the actual model/template/tokenizer framing and perform no inference/network request. Selection request uses `operation="select"` with the same messages plus `max_output_bytes` and `max_output_tokens`. It returns only the existing `{"sources":["S1",...]}` object. A reviewed adapter must honor token limits and perform at most one bounded inference request. Token-count honesty and provider-side billing behavior cannot be proven by a protocol alone.

There is no vendor SDK, model download, endpoint default, new dependency, key in browser code, API-key request in chat or actual credential added to configuration.

## Context and output limits

Context creation retains existing allowlists and rejects rather than truncates:

- More than **128 AI source records**, including the case record.
- Any string metadata field over **2,048 characters**.
- More than **64 KiB** canonical provider context.
- More than **8,000 input tokens**, including model framing as counted by the reviewed adapter.

The existing report's 2,000-row/2 MiB/5-second snapshot limits remain in force upstream. A case can still be browsed/reported normally if the narrower AI limits reject it. No investigation record is shortened or edited.

Selection remains 1–20 distinct aliases. Required correction context can expand the server-resolved result to at most 40 records. Provider output/final response is limited to 32 KiB and the requested output token allowance remains 1,024. Count-process stdout is limited to 128 bytes. Adapter stdout is read in bounded chunks and rejected as soon as the limit is exceeded, rather than collecting an unbounded response string. Adapter-internal remote HTTP/decompression limits still require review; killing the wrapper process is not proof that a remote processor stopped billing/computing.

## Deadline and cleanup behavior

The 30-second provider deadline now covers **both counting and selection**. For the configured command boundary, timeout/cancellation terminates the current direct process, closes stdin and drains/discards remaining output in bounded chunks. Cleanup has a one-second deadline and closes the process transport, including Windows pipe cleanup. No detached service, work queue or background workflow is introduced. The reviewed script must not launch descendants; this implementation is not an OS process-tree sandbox. Cleanup uses the asyncio process transport because Process exposes no public close method; this compatibility point is covered by Windows subprocess tests.

Existing in-process injected providers run through the existing Starlette thread pool with a private event loop, so blocking token counting does not block the ASGI event loop. Requests time out with a short 0.1-second cleanup grace. If arbitrary injected Python ignores cancellation, the single AI capacity slot stays quarantined until that call finishes; repeated requests cannot accumulate abandoned calls. Python threads cannot be forcibly terminated and shutdown could require operator intervention for a permanently stuck custom provider. Use the reviewed command boundary for live evaluation, not an unbounded injected implementation.

No retry or hidden provider fallback occurs on timeout. The previous authorized same-case briefing remains visible after a failed replacement, while access denial still clears it. Existing cancel/disconnect/case-switch semantics remain unchanged.

## Usage and retry controls

Admission is atomic and occurs after authorization/context checks but before counting or inference. Default application-process limits are:

- One active AI computation (existing capacity slot).
- At least **5 seconds** between admitted attempts.
- At most **6 admitted attempts per rolling minute**.
- At most **96 admitted attempts during the application process lifetime**.

Failed counting, invalid output, provider failure and timeout consume an admitted attempt; admission is not refunded to encourage retries. Rejected capacity/context/authorization calls do not invoke the provider. No automatic retries occur; there is no retry loop or automatic JSON repair. Explicit retries are subject to the same budget. The existing busy button prevents duplicate clicks; server limits also cover other tabs/direct callers in that process.

The browser 429 message now explains capacity/usage limits and that a run budget may require administrator review. Tests explicitly relax cooldown/window settings only in their isolated fixtures; production defaults are not disabled by environment name.

These are process-local controls for the current single-operator architecture. Restart resets counters; multiple processes have independent budgets. They are not a durable organizational billing cap. A future paid provider also needs its own hard account quota and controlled evaluation attempt ledger. No queue, shared cache, RBAC or database table is introduced to implement that here.

## Source, privacy and prompt-injection protections

The model selects aliases; it cannot supply final citations, timestamps, new evidence or authored factual prose. The server validates selections and resolves exact authorized fields, preserving correction context. Unknown/cross-case IDs, wrong source types, duplicates, excessive selections, extra fields and malformed output are rejected. Duplicate server-manifest citations are also rejected. Authorization and fresh-context checks remain before dispatch/publication; raw evidence is never read for briefing preparation.

Fixed instructions remain separate from `untrusted_records`. Synthetic attacks cover instructions to reveal prompts/tokens, use another case, mark an indicator malicious and delete evidence. Values remain inert source text; React does not execute injected markup. This verifies application controls with a test provider, not that a real model resists manipulation. Selection bias/omission can remain even with valid aliases. System prompts are not secrets; output prose containing a prompt is rejected by the existing schema, but model compliance is not guaranteed.

Provider context still excludes raw files, note bodies, storage paths/keys, actor identities and credential arguments. Known operator/agent patterns and the current operator credential/digest are checked. The configured provider-key value is now checked too, against both serialized context and original string fields, including escaped characters. Rejection is generic 422 before dispatch. This is not general secret redaction: arbitrary sensitive free text, old case-history values or unknown credentials may remain. No real-data remote disclosure is authorized.

The normal application remains unconfigured. The manual evaluator constructs fixtures directly; it imports no application Settings, database connection or evidence reader and accepts no case ID/file-content input. Provider keys, when required later, are used only in the child environment for the reviewed adapter's transport authentication, never included in the displayed synthetic payload. No raw provider response is printed by the evaluator; only validated citations and review status are printed.

## Synthetic evaluation procedure and manual configuration

**Real-provider evaluation status: NOT PERFORMED.** No named model/adapter or credentials were provided or silently selected. The available automated checks use deterministic providers and temporary local subprocess scripts. They verify safety plumbing, not model relevance, injection resistance, latency, retention or cost. Live evaluation remains a separately approved manual step.

Preview without any provider, from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe tests/evaluate_ai.py --case A --variant normal
.\backend\.venv\Scripts\python.exe tests/evaluate_ai.py --case B --variant injection
```

The default is always preview-only, even if `--adapter-script` is supplied. The preview prints the exact synthetic context. Available variants are normal, injection, empty and large; large intentionally fails the field limit without a provider call. Fixtures contain distinct A/B titles, synthetic filenames/digests, zero sizes, fixed 2020 timestamps, `.example` domain indicators, timeline/history records and transient report metadata. Injection strings are distributed across description/display-title/locator/history fields. No case information is loaded from the live database. Report wrapper metadata is not automatically added to the AI allowlist.

Only after developer approval, review a concrete script/runtime/license/network destination and accurate tokenizer. Preview/review each fixture, then explicitly invoke one attempt:

```powershell
.\backend\.venv\Scripts\python.exe tests/evaluate_ai.py --case A --variant normal --adapter-script "C:\Approved\provider_adapter.py" --run-reviewed-synthetic
```

That path is an illustrative placeholder, not an installed adapter. The evaluator does not read `.env`; if a chosen adapter requires a key, the developer supplies `SHADOWVAULT_AI_PROVIDER_API_KEY` privately through a secure process environment, never chat/source/CLI argument/browser storage. There is no reason to request or insert a key until a concrete provider is approved. The evaluator makes one explicit generation attempt (count then select), applies context/deadline/output validation and writes no case result. Its per-command bound does not track a budget across repeated shell invocations; record a maximum 96-attempt synthetic evaluation ledger manually, stop on any safety failure and use vendor account limits if applicable. Do not enable the main application on real cases to run this procedure.

Future main-application configuration names, **not enabled here**:

- `SHADOWVAULT_AI_ENABLED=false` by default.
- `SHADOWVAULT_AI_ADAPTER_SCRIPT`: absolute reviewed Python script; no command string or provider chosen by a browser request.
- `SHADOWVAULT_AI_PROVIDER_API_KEY`: optional backend-only secret, no value committed.
- `SHADOWVAULT_AI_MIN_INTERVAL_SECONDS=5` (allowed 0–3600; lowering removes only cooldown, not other caps).
- `SHADOWVAULT_AI_MAX_PER_MINUTE=6` (allowed 1–60).
- `SHADOWVAULT_AI_MAX_ATTEMPTS=96` (allowed 1–96).

The next evaluation must cover A/B grounding/isolation; exact citations and invalid/cross-case references; empty and oversize contexts; malicious instructions and unsupported claims; corrections/conflicting records; tokenizer limits; delayed/unavailable/rate-limited provider; malformed/oversize responses; no secret or unrelated-record transmission. Extend the fixed synthetic corpus for correction/conflict variants before claiming the full Phase 7H real-model matrix is complete. Existing automated correction/authorization tests remain part of regression coverage but are not a substitute for real-model evaluation. Record pinned model/tokenizer/template/adapter versions, measured usage/latency and investigator relevance/omission review outside case records. No real provider quality claim is made by this implementation.

## Verification

- Final full backend: `PYTHONPATH=backend` with `.\backend\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v` — **182 passed, 0 failures**, 84.545 seconds, including all 16 new safety tests and 14 existing briefing tests.
- Frontend services: `npm --prefix frontend test` — **51 passed, 0 failed, 0 skipped**, 1124.0158 ms.
- TypeScript: `npm --prefix frontend run typecheck` — **passed**.
- Production build: `npm --prefix frontend run build` — **passed**; 61 modules; Vite 1.82 seconds.
- Complete browser suite: `npm --prefix frontend run test:browser` — **77 passed, 0 failed**, 2.0 minutes, isolated test database/servers.
- Adapter-focused Windows cleanup run with ResourceWarning treated as error: **6 passed** after fixing a pipe-cleanup warning; all adapter tests are also included in the full suite.
- Synthetic preview: Case A injection payload printed successfully with **no provider invoked**.
- Windows collector/upload repeat: **passed** within the final full backend suite (`test_collection_e2e.CollectionEndToEndTests.test_real_cli_upload_and_repeat`); not counted as an additional test outside the 182 total.

New tests cover context source/field limits; exact alias/case isolation; invalid/wrong/duplicate/excess citations; injected metadata; empty case; atomic cooldown/window/lifetime budgets; subprocess environment/UTF-8; count/select timeout and cancellation; incremental oversize output rejection; invalid/duplicate counts; blocking injected counting and slot quarantine; configuration defaults; provider-key canary rejection; and failed attempts consuming budget. Browser/service tests cover explicit retry, timeout/rate-limit retention and inert source rendering. Existing evidence/custody/timeline/history/IOC/report/operator/collector regressions are preserved.

## Database, warnings and limitations

Read-only checks: **revision 0008**, SQLite integrity **ok**, **0 FK violations**. Database SHA-256 remains `8f8e520eb9e23d2354652990d114fcb5895f7f1b5e293f0135299f279acde969`. No migration, AI persistence or database modification. No dependency addition or upgrade. The actual environment file and existing evidence records are unchanged.

Non-blocking warnings observed: existing Starlette/httpx test-client deprecation and Node NO_COLOR/FORCE_COLOR notice. The foundation test intentionally emits a sanitized database-readiness failure while testing error handling; it passes. The new subprocess ResourceWarning found during focused verification was fixed rather than ignored.

Remaining limitations: no live model or named adapter; no OS sandbox for trusted scripts; subprocess descendants prohibited by adapter contract rather than a process-tree sandbox; Python-injected uncooperative calls may quarantine capacity until completion/restart; local process counters are not durable billing quotas; a remote request may continue after local termination; actual tokenizer/transport/privacy compliance requires adapter review; metadata sensitivity and model selection quality still require evaluation. These are not permissions to expand context or weaken controls.

## Rollback and scope

Leave `SHADOWVAULT_AI_ENABLED=false` or remove optional adapter wiring to keep AI unavailable. If enabled later, stop new generation, cancel direct adapter work best-effort and revoke only the separate provider credential as needed. Restore the listed safety/UI changes if necessary without downgrading the database or changing authentication/custody/history. Remote disclosure, if separately authorized later, cannot be undone by code rollback.

No raw evidence analysis, autonomous agents/actions, threat-verdict automation, enrichment, background workers, AI memory/persistence, RBAC or authentication/custody changes were added. Phase 7J was not started. Live AI evaluation still requires approval.

Phase 7I complete — awaiting approval before live AI evaluation.
