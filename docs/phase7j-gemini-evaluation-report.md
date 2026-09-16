# Phase 7J-G — Controlled Gemini evaluation completion report

Date: 2026-09-15. **Phase 7J-G complete for the approved synthetic-only evaluation scope.** All four final live synthetic scenarios and the full regression suites passed. This does not authorize production Gemini use, transmission of real case data, or Phase 7K.

## Exact changed files

Full Phase 7J-G inventory:

1. `tests/gemini_synthetic_adapter.py` — isolated Gemini REST adapter; fixed-fixture boundary, bounded transport, source-selection and usage validation; model pin corrected to gemini-3.6-flash; optional opaque response signature is now validated and discarded.
2. `tests/evaluate_gemini.py` — explicit synthetic-only evaluation runner through the existing CommandProvider pattern, separate preflight/generation reporting and model pin.
3. `tests/test_gemini_synthetic.py` — 19 deterministic Gemini tests, including model-pin regression and two response-signature compatibility regressions.
4. `backend/.env.example` — empty GEMINI_API_KEY placeholder and synthetic-only GEMINI_MODEL example.
5. `docs/phase7j-gemini-evaluation-report.md` — this consolidated report, preserving the relevant earlier failure history below.

This final generation investigation changed only the adapter, its test file and this report. No request payload fields, evaluator, model pin, environment setting, production source, dependency or migration changed in this continuation. No private credentials were edited or exposed. Ordinary ignored frontend build/browser outputs were regenerated. Temporary phase7jg-generation test logs were removed after their results were recorded.

There is no Git metadata in this workspace; this inventory records controlled task edits rather than claiming a Git diff across earlier phases. Fingerprint comparison of 86 protected production/OpenAI/migration/dependency/database files found zero changes. The user-managed private environment is excluded from that comparison.

## Diagnosis and compatibility correction

### SDK, model and request

No Gemini SDK is installed or used: neither google-genai nor google-generativeai is required. The adapter uses existing **httpx 0.28.1**, direct HTTPS REST and the pinned **gemini-3.6-flash** model. OpenAI adapter/evaluator/support remain unchanged.

Counting uses the documented `models/{model}:countTokens` endpoint with the full `generateContentRequest`. Generation uses `models/{model}:generateContent` with that same request: fixed instructions, independently reconstructed synthetic metadata, JSON response schema, one candidate, maxOutputTokens=1024, thinkingBudget=0 and includeThoughts=false. No tools, external grounding, files, caches, custom safety overrides or extra data sources are enabled. The existing provider safety defaults were not weakened.

The previous HTTP 400 did **not** reproduce in this investigation. The first diagnostic returned temporary high-demand HTTP 503. Subsequent diagnostics accepted the unchanged request and returned completed model responses, but local validation rejected the extra `thoughtSignature` field. The earlier 400's precise cause was not established, so this report does not claim that removing or changing a request parameter fixed it.

Google documents that Gemini 3 may attach opaque thought signatures to text parts. The successful diagnostic had one text part plus a signature, matching modelVersion, STOP finish reason, and zero reported thought tokens. See [Gemini thinking and signatures](https://ai.google.dev/gemini-api/docs/generate-content/thinking), [countTokens contract](https://ai.google.dev/api/tokens), and [Gemini 3.6 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash).

### Minimal fix

The response parser now permits an optional, nonempty string `thoughtSignature` alongside the required text in the single model part. It discards the signature immediately: it is never returned, logged, persisted, treated as evidence, cited, or reused in another request. It is covered by the existing 64-KiB response bound.

Unknown part fields, thought text, function calls, invalid signature types, multiple parts/candidates, non-STOP results, grounding data, wrong model version, invalid source aliases and inconsistent/excessive usage still fail closed. The zero-thought-token check remains. Only the text selection reaches existing strict server citation resolution. No normal API output shape changed.

New regression tests verify signature removal and that signatures cannot allow thought output, tools, unknown fields, invalid metadata or nonzero thought usage to bypass validation. The generation request itself was left unchanged because live evidence showed it was accepted.

## Architecture and synthetic boundary

SyntheticGeminiProvider extends the generic CommandProvider, not the OpenAI provider. Fixed fixtures are reused from the historically named `openai_synthetic_data.py`; OpenAI adapter and evaluator code are not imported or modified. No provider registry, fallback, Interactions API or architecture redesign was introduced. Future Ollama work can still implement the existing generic provider contract; it is not implemented here.

The explicit runner creates an isolated in-memory SQLite application and fixed A/B/empty/injection records. Each adapter operation independently reconstructs its fixture, requires exact context/instruction equality, and constructs outbound content from its own fixture. Arbitrary case IDs, database URLs, user metadata and evidence files cannot enter this path. The existing authorized briefing endpoint supplies admission, context construction, server citation resolution and final freshness/access checks.

Normal CommandProvider remains local-only for token counting. Its restricted child environment does not forward Gemini credentials or the synthetic opt-in. The remote count exception exists only in the explicitly approved test evaluator. Environment example settings alone cannot enable production Gemini.

Phase 7I boundaries remain: 64-KiB context, 128 sources, 2,048-character fields, 8,000 input tokens, 1,024 output tokens, 32-KiB child output, 30-second combined preflight/generation deadline, one active operation, existing 5-second cooldown, 6-per-minute and 96-per-process defaults. Failed attempts consume admission. There are no automatic retries or provider fallbacks.

## Final real Gemini evaluation

Command: `python tests/evaluate_gemini.py --run-approved-synthetic`.

All four scenarios returned HTTP 200 from the existing briefing endpoint and passed server grounding/case-isolation assertions. Each used one preflight and one generation request:

- **A:** preflight 1,647 tokens; generation input 1,647, output 80, total 1,727; **15.916 seconds**; passed.
- **B:** preflight 1,648 tokens; generation input 1,648, output 38, total 1,686; **24.479 seconds**; passed.
- **Empty:** preflight 230 tokens; generation input 230, output 6, total 236; **8.762 seconds**; passed.
- **Injection:** preflight 1,682 tokens; generation input 1,682, output 54, total 1,736; **21.078 seconds**; passed.

Final evaluation totals: **4/4 preflights passed; 4/4 generations passed; 4/4 server grounding/case-isolation checks passed**. Reported generation usage totals 5,207 input and 178 output tokens (5,385 total). These are provider-reported usage values, not an independent billing audit. No raw generated text or signature is published in this report.

The final pass is separate from three preceding explicit diagnostic count/generation pairs: first temporary HTTP 503, then two completed responses rejected by the old local signature check. Each diagnostic preflight returned 1,647 tokens. This continuation therefore made **7 count requests and 7 generation requests**, including diagnostics and the final evaluation; no automatic retry policy was added. Earlier phase attempts are summarized separately below.

All network content was fixed synthetic metadata. No real ShadowVault cases, evidence, indicators, timelines, history, custody or reports were transmitted. No evidence bytes were read. Results were transient in-memory test results and were not stored as case data.

## Fresh deterministic and regression verification

- Focused Gemini tests before full verification: **19 passed, 0 failures**, 10.418 seconds.
- Complete backend: `python -m unittest discover -s tests -p 'test_*.py' -v` — **218 passed, 0 failures**, 129.516 seconds. Includes the 19 Gemini tests; they are not additional to 218.
- Frontend services: `npm --prefix frontend test` — **51 passed, 0 failures, 0 skipped**.
- TypeScript: `npm --prefix frontend run typecheck` — **passed**.
- Production build: `npm --prefix frontend run build` — **passed**, 61 modules, Vite build 2.67 seconds.
- Complete browser suite: `npm --prefix frontend run test:browser` — **77 passed, 0 failures**, 2.2 minutes, using isolated local servers and Windows test-storage permissions.
- Windows collector/upload: `test_collection_e2e.CollectionEndToEndTests.test_real_cli_upload_and_repeat` — **passed** within the full backend suite, alongside staging, hash, source-selection, retry/receipt and transport regressions.

Deterministic tests remain distinct from live Gemini evaluation. They cover exact synthetic inputs, count/generation framing, local production refusal, limits, malformed/duplicate JSON, authorization/cross-case denial, citation rejection, usage admission, timeouts, sanitized errors, redirects/body bounds, no retries and record preservation. Existing evidence/custody, timeline, case history, indicators, reports, operator authentication and frontend workflows remain passing.

## Security and database checks

GEMINI_API_KEY presence was confirmed without exposing its value. It remains backend-only and is sent only in the fixed HTTPS API-key header. It is never placed in URLs, browser storage/build variables or logs. Diagnostic messages were credential-redacted; final evaluation prints only status, numeric usage and validation outcomes. Signatures and raw provider bodies are not persisted.

TLS verification, fixed destination/model, disabled proxy inheritance/redirects/retries, 64-KiB bounded HTTP bodies, duplicate-key rejection and 32-KiB subprocess output limits remain. Provider error handling returns safe fixed categories/numeric status. Known-secret/context checks and server-side reauthorization remain unchanged.

Final read-only database verification: **revision 0008**, integrity **ok**, **0 foreign-key violations**. SHA-256 remains `8f8e520eb9e23d2354652990d114fcb5895f7f1b5e293f0135299f279acde969`, identical to the original baseline. No migration or database write occurred. No dependency manifest/lockfile changed. No OpenAI code changed.

No raw-evidence AI analysis, threat verdicts, autonomous decisions, case modifications, custody changes, external enrichment, AI persistence/memory, background workers, teams/RBAC or new authentication behavior was added.

## Prior evaluation history

- Initial implementation paused for approval of remote counting; the user subsequently approved a synthetic-only exception. Production local counting never changed.
- Initial credential checks found no usable local Gemini key and made zero calls. Earlier deterministic baselines passed at 215 backend / 51 services / 77 browser tests.
- After the key became available, the old gemini-2.5-flash preflight returned HTTP 404. Three bounded diagnostic count calls established Google's message that the model was no longer available to new users. Switching only the model pins/example to gemini-3.6-flash resolved preflight at 1,647 tokens; generation then returned HTTP 400. That fix's regressions passed at 216 backend / 51 services / 77 browser tests.
- Today's investigation did not reproduce that HTTP 400. It established and corrected a separate response-metadata compatibility defect without changing the payload or safety limits, then passed the full live evaluation and regression suites above.

## Warnings and limitations

The final browser run emitted two Node NO_COLOR/FORCE_COLOR warnings, with no test failures. A temporary provider high-demand HTTP 503 occurred during diagnosis; provider availability and repeat-run latency are not guaranteed. The earlier Windows connection-reset test-server warning did not recur in this final run.

This is a fixed synthetic structural evaluation, not proof of universal prompt-injection resistance, source-selection quality or completeness. Investigator review remains necessary. Valid citations do not establish a threat verdict. Google documents that Gemini 3 cannot guarantee fully disabled thinking; the unchanged evaluator rejects nonzero reported thought usage, so a future response may fail closed even though these fixtures passed. Model-version/schema changes and provider limits can also cause future failures. No limits were raised to avoid such failures.

**Phase 7J-G is complete for controlled synthetic evaluation. Production Gemini remains disabled/unapproved, and Phase 7K has not started.**
