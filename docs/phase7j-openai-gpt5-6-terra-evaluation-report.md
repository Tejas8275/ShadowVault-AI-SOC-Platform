# Phase 7J — controlled GPT-5.6 Terra evaluation

Date: 2026-09-14. **Implementation and automated verification pass; Phase 7J is NOT complete because live generation has not passed.** No Phase 7K work has started.

## Preserved work and approved exception

The initial inspection found the Phase 7G/7I provider boundary intact and no existing Terra adapter. The approved SDK installation and dependency pins from the earlier continuation were preserved. The earlier blocker concerned Phase 7I's local-only counting contract: the SDK counts through POST `/responses/input_tokens`. The user subsequently approved a bounded remote count **only for Phase 7J synthetic evaluation**. That exception is now implemented entirely in test/evaluation tooling. The normal provider interface, CommandProvider, application factory, authorization, context builder, resolver, execution deadline and usage controls are unchanged.

There is no Git working tree here. Before/after SHA-256 inventories identify the files changed by Phase 7J and verify unchanged production backend, migrations, collector and database. The user has since configured the backend environment file; the assistant has not edited that file.

## Exact changed-file inventory

- `backend/pyproject.toml`: official SDK dependency `openai==3.13.0` (preserved from the previous continuation).
- `backend/requirements.lock`: SDK and required transitive pins (preserved): `httpx2==2.12.0`, `httpcore2==2.12.0`, `jiter==0.17.0`, `sniffio==1.3.1`, `truststore==0.10.4`. Existing pins were not upgraded.
- `backend/.env.example`: empty backend-only API-key placeholder and exact model name, explicitly labeled synthetic-evaluator-only.
- `tests/openai_synthetic_data.py`: fixed authored fixtures and in-memory SQLite seeding; independently reconstructs expected metadata through the existing report/context services.
- `tests/openai_synthetic_adapter.py`: official SDK adapter with exact-fixture matching, bounded remote count and generation transports, strict response/selection checks and safe process output.
- `tests/evaluate_openai.py`: explicit opt-in evaluator, test-only CommandProvider subclass, existing briefing endpoint against isolated in-memory data, separate preflight/generation metrics, stop-on-failure and no automatic retries.
- `tests/test_openai_synthetic.py`: 17 focused deterministic tests, including real SDK serialization through mock HTTP transport and the existing endpoint.
- `frontend/src/features/cases/CaseBriefing.tsx`: explicit advisory/not-a-threat-verdict label; no behavior change.
- `frontend/tests/browser/ai-briefing.spec.ts`: assertion for that label in an existing workflow.
- `docs/phase7j-openai-gpt5-6-terra-evaluation-report.md`: this updated report.

The backend virtual environment contains the six approved/newly required distributions. Generated frontend build output is not source. Temporary verification logs were removed after results were recorded. No existing source file was deleted. No new dependency beyond the official SDK and its requirements was added.

## Synthetic-only boundary and data flow

The outbound adapter does not accept a database URL, case ID, file, URL, arbitrary fixture, model, prompt template or network destination from the browser. It accepts one of four fixed scenario names from the test runner's restricted child environment. It independently creates a fresh **in-memory** SQLite fixture, obtains the report with the existing case-report service, and builds the context with the unchanged allowlist service. The caller's context and instructions must exactly match that reconstructed fixture. Any difference, including another synthetic case's context, fails **before HTTP client construction**. The network payload uses the reconstructed context, not caller fields.

The evaluator creates a separate in-memory database using existing ORM metadata, seeds only fixed authored records, and calls the existing `/api/v2/investigation/incidents/{id}/ai-briefing` endpoint through TestClient. Report generation, authorization, context construction, secret rejection, server-side citation resolution and freshness checks run normally. Report services are not mocked in the evaluator. No real database path is accepted. No live database records or evidence files are copied into fixtures. There is no temporary on-disk synthetic database or persistent AI result to clean up.

Flow: fixed synthetic rows -> existing authorized briefing endpoint -> existing report/context builder -> Phase 7I admission and deadline -> test-only count process -> exact fixture/instruction check -> OpenAI count -> reject above 8,000 -> test-only generation process -> exact fixture/instruction check -> OpenAI structured selection -> adapter validation -> independent server citation resolution and reauthorization -> transient endpoint response -> numeric/status-only console evaluation results.

Normal operation remains local-only. Neither backend Settings nor `create_app` imports/selects the synthetic provider. Normal CommandProvider strips the synthetic opt-in and OpenAI key environment variables; pointing it at the test script fails closed. A focused subprocess test verifies this. Installing the SDK, setting OPENAI_MODEL, or setting OPENAI_API_KEY does not enable OpenAI for the production app. No production API contract or normal token-count requirement changed.

## Model, SDK and transport controls

Only `gpt-5.6-terra` is accepted. [Official model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-terra) lists Responses and structured-output support. The [official input-token method](https://developers.openai.com/api/reference/python/resources/responses/subresources/input_tokens) is remote; its results are reported separately from model generation.

Count and generation use identical model, instructions, user context, reasoning setting (`none`), source-alias JSON schema, empty tools, disabled parallel tool calls and disabled truncation. Generation adds `store=false`, `background=false`, `stream=false`, and `max_output_tokens=1024`. No conversation, previous response, files, tools, enrichment or external action is supplied. The strict selection schema permits only source aliases from that fixture. Duplicate/unknown IDs, extra prose/verdict fields, malformed JSON, refusals, tool output, incomplete responses and unexpected usage/output are rejected. Citations and displayed fields remain server-resolved, not model-authored.

The official SDK has `max_retries=0`. Its transport verifies TLS, disables environment proxies and redirects, fixes the exact HTTPS host/path, and permits one request per child operation. Success and error bodies are capped at 64 KiB before SDK parsing/error handling; compressed bodies and oversized declared/streamed responses are rejected. Count stdout remains capped at 128 bytes. Selection plus numeric usage metadata stays within the existing 32-KiB child-output bound; source resolution separately enforces the existing selection/output constraints. These wrapper checks are in addition to the 1,024 output-token limit.

The unchanged parent applies the **30-second total deadline across count and generation**, kills the direct child on timeout/cancellation, and retains existing cleanup behavior. HTTP connect timeout is 5 seconds, other HTTP operation timeouts 20 seconds. The total parent deadline is authoritative. SDK errors/timeouts produce a generic unavailable response; an exhausted outer deadline produces the existing 504 response. No private exception text is published. The evaluation wrapper now reports only predefined failure categories and a bounded integer HTTP status; exception messages, HTTP bodies, URLs and headers are never serialized. A secret-canary test covers this diagnostic path. No automatic retry, fallback or JSON repair occurs. Each synthetic provider instance permits one preflight and one selection; failed attempts require an explicit new evaluation run.

The endpoint retains single capacity, 64-KiB context, 128-source, 2,048-character field, 8,000-input-token and 32-KiB output limits. Default admission remains 5 seconds between attempts, 6 attempts per rolling minute and 96 per application-process lifetime. The live evaluator makes at most four intentional attempts, waits 5 seconds between them, and stops on its first failed endpoint/validation result. Its attempts are subject to the same admission object. Restarting a runner resets process-local counters; this is not a durable account spending cap.

## Fixtures

Four disjoint fixed cases are constructed, all with fixed 2020 timestamps and synthetic identities:

- A: **Synthetic Phishing Investigation A**; `synthetic-evidence-a1`, `synthetic-email-artifact-a`, `synthetic-file-a`; indicators `192.0.2.10`, `example-a.test`, `synthetic-a.txt`.
- B: **Synthetic Malware Investigation B**; distinct IDs, filenames, IP `192.0.2.20`, domain `example-b.test`, filename `synthetic-b.txt`.
- Empty: case metadata only; no evidence, timeline, indicators or history rows. A valid response can select the case record; the server invents no absent records.
- Injection: separate synthetic identifiers, with fixed instructions to reveal prompts/tokens, use another case, assert maliciousness and delete evidence embedded as untrusted case/history text.

A/B/injection each have 3 evidence metadata records, 3 manual indicators, 3 investigator timeline observations and one case-history event, yielding 11 allowed sources including the case. Empty has 1 source. Context byte sizes: A 4,053; B 4,052; empty 332; injection 4,347. Evidence is explicitly **legacy synthetic metadata**, with no original files and no claim of an actual verified upload. No custody entries are fabricated. Existing custody/verified-upload behavior is tested by the regression suite.

## Authentication, privacy and security checks

The existing operator bearer-token and incident-owner checks remain authoritative. The evaluator uses a fixed test-only operator token against its in-memory app, never the user's operator token. The child environment contains only minimal OS variables, fixed evaluation selectors, exact model and the separate API key. Operator/database/Python injection variables are not inherited. The key is consumed from backend process configuration or backend `.env`; it is never shown in console output, errors, frontend code, browser storage, prompts or responses. The assistant did not edit the actual `.env`; the user configured the key locally, and local environment files remain ignored.

Fixed-context equality blocks real or modified data before either outbound operation. The independent context reconstruction means admission is not based merely on a 'synthetic' label supplied alongside arbitrary data. The key is also checked against the fixed context; the evaluator supplies it to the existing secret-check setting for endpoint validation. Child logging is disabled and stderr discarded; failed SDK responses are not echoed.

Deterministic checks prove non-synthetic and cross-scenario rejection before network, unchanged normal-provider isolation, unauthorized/cross-owner denial, identical SDK count/generation payloads, no tools/retries, constrained destinations, bounded error/success bodies, strict output/citation handling, safe failures and no record changes. All tables are compared before/after an SDK-mocked endpoint generation. Existing tests cover original-file non-reading, stale context, revocation, case isolation, custody/history preservation and secret rejection.

**No real case data was transmitted in this run.** The locally configured key was checked for presence only. Both live attempts used the independently reconstructed fixed Case A fixture; no real database or file inputs were accepted. Each preflight returned 1,344 input tokens. Generation failed and the evaluator stopped before other scenarios. MockTransport tests never contact OpenAI.

## Exact automated verification results

- Focused SDK/synthetic tests: **17 passed, 0 failures** within the final full backend run, including the new safe-diagnostics secret-canary test. Do not add them again to the backend total. A separate intermediate focused run before the final test addition passed 16 tests in 22.155 seconds.
- Full backend: `PYTHONPATH=backend` with `backend/.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_*.py' -v`: **199 passed, 0 failures**, 120.992 seconds.
- Frontend services: `npm --prefix frontend test`: **51 passed, 0 failures, 0 skipped**, 1198.8266 ms.
- TypeScript: `npm --prefix frontend run typecheck`: **passed**.
- Production build: `npm --prefix frontend run build`: **passed**, 61 modules, Vite build 3.04 seconds.
- Complete browser suite: `npm --prefix frontend run test:browser`: **77 passed, 0 failures**, 2.4 minutes, isolated local test servers/database and headless Edge. Includes the advisory label and existing unavailable/loading/success/timeout/failure/usage/retry/isolation workflows.
- Windows collector/upload/repeat: **passed** as `test_collection_e2e.CollectionEndToEndTests.test_real_cli_upload_and_repeat`, included in the 199 backend tests.
- `python -m pip check`: **passed**, no broken requirements.
- Preview command: **passed**, all four fixtures prepared without network.

These are deterministic SDK/application tests and existing regressions, not real-model results. Provider timeouts, invalid citations, malformed responses, rate limits and failures are induced with mocks or existing deterministic providers. No product/test failures remained in automated verification; live generation failed as documented separately. Non-blocking browser warning: Node ignores NO_COLOR when FORCE_COLOR is set. Existing private test/evidence directories were not opened or removed.

## Live preflight and real-model results — separate from automated tests

The backend key is now present. Its value was neither displayed nor logged. The earlier absent-key run remains historical and made no network calls. This continuation made two explicit attempts using:

```powershell
.\backend\.venv\Scripts\python.exe tests/evaluate_openai.py --run-approved-synthetic
```

1. **Case A, first attempt:** remote preflight passed, **1,344 input tokens**. Generation failed or was cancelled; the endpoint returned **503** after **20.946 seconds**. The original safe error handling discarded provider details, so the exact cause of this first failure is unknown. No valid briefing was published.
2. **Case A, explicit diagnostic retry:** remote preflight passed, **1,344 input tokens**. Generation returned **OpenAI HTTP 429**; the endpoint safely returned **503** after **17.446 seconds**. The evaluator stopped immediately. The diagnostic reports only a fixed category and numeric HTTP status, not the provider body. It cannot distinguish an account quota issue from a rate limit.

No automatic retry, fallback, model substitution or increased limit occurred. The second attempt was an explicit diagnostic rerun after adding safe failure categorization, not an SDK retry. No further live requests were made after the identified 429.

- Live preflight: **2/2 passed**; reported count **1,344 on each attempt**. Counts are preflight results, not generation usage/billing metrics.
- Live generation: **0/2 passed**; no accepted structured response or briefing. One unspecified failure and one confirmed provider HTTP 429.
- Cases B, empty and injection: **NOT RUN**, because each run stopped on Case A's failed generation.
- Real-model structured validity, citation accuracy, relevance, injection resistance, unsupported-claim rate and hallucinated-source rate: **NOT MEASURED**, because no generation succeeded. Do not interpret absent output as zero hallucinations or safe model behavior.
- Actual generation token usage and evaluation charges: **UNAVAILABLE**; do not infer zero cost from a failure. Preflight counts are not billed generation measurements.
- Deterministic transport counts, usage numbers and adversarial outputs in tests remain synthetic mock responses, not real-model measurements.

Evaluation acceptance gate: **FAIL / incomplete because required live generation and all scenarios have not passed**, not a measured judgment of model quality. The local-count compatibility exception remains confined to the approved synthetic tool. The current external blocker is the provider's HTTP 429 response. No safety boundary was weakened to bypass it.

## Database and preservation

Read-only production SQLite checks: revision **0008**, integrity **ok**, **0 foreign-key violations**. SHA-256 remains identical to the initial inspection and Phase 7I baseline: `8f8e520eb9e23d2354652990d114fcb5895f7f1b5e293f0135299f279acde969`. No migration or database write occurred. The in-memory evaluator schema is constructed from existing ORM metadata; it does not upgrade or seed the real database. No AI result/prompt/provider response is persisted as case data.

## Exact next step and limitations

The key is already configured; do not paste it into chat. Review the associated OpenAI API project/account rate and quota availability before another explicit evaluation attempt. The sanitized 429 does not prove which limit was responsible. `OPENAI_MODEL=gpt-5.6-terra` is the only allowed model and is used only by the explicit evaluator. Leave SHADOWVAULT_AI_ENABLED false and do not point the normal application at the test adapter. Run the command above from the repository root to execute the four fixed scenarios. Each printed result separates preflight status/count from generation status/usage and server grounding/isolation. On any failure, the evaluator stops without retrying. Do not switch models or use real cases to obtain a result.

A successful structural run does not establish model relevance or robust injection resistance. Selection can omit useful sources or select hostile text while still yielding valid citations. The response format contains no model prose or automatic verdict, so absence of invented prose is primarily a structural application guarantee, not proof that a model understood the evidence. One count and generation can still diverge in provider accounting; generation usage is checked and rejected if over limits, but that cannot undo a remote charge. Strict response shape/model/identity-encoding checks may reject otherwise valid future API behavior; review failures rather than weakening the boundary silently.

The scripts are trusted repository code, not an OS sandbox against a compromised developer account. Local cancellation does not guarantee remote computation/billing stops. SDK store=false is not a claim of zero provider retention; account/privacy settings must be reviewed before any later real-data phase. No real-data disclosure is authorized here. There is no durable cross-run usage ledger. After a live structural pass, investigator relevance/omission review and final report update remain necessary before considering a later phase.

Rollback: keep the evaluator unused; the normal app is unchanged and remains without an OpenAI provider. Remove the test-only files and SDK dependency changes if required without changing the database, authentication or custody. Synthetic metadata has been sent during the documented preflight/generation attempts; a local rollback cannot undo that disclosure. No real case data was sent.

No raw evidence AI, threat-verdict automation, autonomous actions, AI memory/persistence, external enrichment, RBAC/teams, background workers or authentication/custody changes were added. Phase 7J remains pending live evaluation; Phase 7K has not started.

## Continuation change inventory

This continuation changed only `tests/openai_synthetic_adapter.py`, `tests/evaluate_openai.py`, `tests/test_openai_synthetic.py`, and this report. It added safe diagnostic categories plus a regression test; it did not alter any context, output, timeout, retry, usage, authorization or production boundary. The full Phase 7J inventory remains the ten files listed above. The user configured the actual backend environment file; the assistant did not edit it.
