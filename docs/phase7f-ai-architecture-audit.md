# Phase 7F — AI Architecture and Evidence-Grounding Audit

Date: 2026-09-13. Read-only architecture/design work; only this document is created. All AI services, endpoints and controls described as proposed below are unimplemented.

## Executive recommendation: one first capability

**Phase 7G should offer an investigator-requested, case-scoped briefing of recorded observations, with server-resolved field-level citations.** Start with a bounded, extractive briefing: the model selects and orders useful source records; the server supplies exact recorded text, values, timestamps, correction context and citations. Do not initially publish model-written factual prose or investigative conclusions.

The existing report is a complete deterministic metadata projection. The proposed briefing helps an investigator orient within that projection without reading every expanded source. It must identify itself as a non-exhaustive reading aid, not a complete report, risk ranking, threat assessment or evidence-content analysis. Selection itself can be biased or incomplete; keep the complete report and underlying records available.

This narrower use of AI is preferable to unrestricted chat, automatic IOC extraction, malware verdicts or autonomous response. It introduces one model task and one output contract. If evaluation shows it offers no useful improvement over the existing report, do not ship AI merely because the product name includes it.

## Audit basis and current architecture

Reviewed current models, report/context projections, case/evidence authorization predicates, investigation routes, security/configuration, integrity/custody/retrieval boundaries, Windows collector documentation, case/report frontend composition, Phase 7D continuity and Phase 7E connection implementation, and associated test structure. Key anchors include:

- `backend/app/services/{case_report,case_intelligence,evidence_query,evidence_reader,evidence_retrieval,timeline,indicators,case_history}.py`.
- `backend/app/models/{incident,evidence,evidence_annotation,evidence_integrity,custody,timeline,case_history,indicator,collection_job,agent}.py` and migrations 0001–0008.
- `backend/app/core/security.py`, investigation API routes, and `schemas/case_report.py`.
- `frontend/src/features/cases/{CaseWorkspace,CaseReport}.tsx`, `report.ts`, investigation service/workspace, LoginPage and App routing.
- `tests/test_case_report.py`, authorization/collection/retrieval/timeline/indicator tests, frontend services and browser authentication/continuity/report workflows.

This is a source-based architecture audit, not a model evaluation, prompt-injection penetration test, provider assessment or evidence-content review. No uploaded files, private fixture directories, live credentials or external model were opened or submitted. No tests or live application mutations were run. The verified baseline from Phase 7E is 152 backend tests, 46 frontend service tests, 71 browser workflows, successful TypeScript/build and Windows collector/upload regression.

```text
Operator token in browser memory
  -> authorized FastAPI investigation routes
  -> Incident owner + collection-requester/evidence scope
  -> SQLAlchemy / SQLite 0008
       Incident (Case)
         + Evidence metadata -> notes/tags/review metadata
         + TimelineEvent -> evidence-linked observations / distinct legacy rows
         + CaseHistoryEvent -> append-only case revision history
         + IndicatorObservation -> evidence link + appended correction
         + CustodyEvent -> separate evidence-action chain
         + deterministic metadata report -> transient browser draft

Explicit Windows selected-file collection -> staged hash -> bounded upload
  -> private original blob + verified Evidence receipt

Explicit authorized retrieval -> secure verified copy -> custody preparation event
  -> investigator download; no parsing or AI
```

There is no existing model runtime, semantic index, model key, tool agent, AI chat history, extraction service or AI result table. Case intelligence is deterministic counting, not AI. Integrity-check execution is not implemented. The original TimelineEvent remains the sole timeline system.

## Opportunity assessment

**First: source-cited case orientation briefing.** Reduce reading effort across recorded notes, timeline and indicator corrections while retaining exact sources and uncertainty. Fits the existing report snapshot and requires no blob access or persistence.

**Later candidates, only after evaluation/approval:** constrained paraphrase of selected observations; explaining differences between occurrence and recording time; identifying explicitly missing metadata for investigator review; answering narrow questions against selected records. Paraphrase and cross-record reasoning have a larger semantic validation burden than extractive selection.

**Not first:** file-content summarization, OCR/parsing, IOC extraction, cross-case correlation, prediction, threat verdicts, external intelligence, report authoring/approval, automatic evidence creation or response actions. These require new disclosure, parser, provenance, authorization or decision boundaries. A domain/IP/hash observation alone is not evidence of maliciousness.

## Data sources: available versus suitable for the first context

1. **Case metadata:** Incident title, description, severity, status, created/updated time and revision are available. Include recorded status/severity as investigator-maintained labels, never as model conclusions. Keep case/actor IDs in the server manifest; omit unnecessary personal identifiers from model input.
2. **Evidence metadata:** filename/display title, size, SHA-256, acquisition/verification timestamps, review state, metadata revision, tags and collection job/item references are available in the report projection. Include only fields needed for the briefing. Never pass storage_key, source_path, arbitrary ORM attributes or deployment paths. Filename/title/tag/description remain untrusted data.
3. **Evidence content:** original bytes are stored, and the existing authorized download workflow prepares a verified copy. There is no safe general text extraction/preview API. Reading bytes is not equivalent to reviewing metadata. **Exclude all file contents in Phase 7G, even for an authorized operator.** Do not use the download endpoint as a hidden AI input route: it records custody preparation, and doing so would silently alter the investigation. A later content phase must separately specify verified derivative copies, supported inert formats, byte/encoding limits, parser isolation, location citations, retention and access/custody meaning without changing originals or inventing delivery events. Never execute evidence, macros, scripts or URLs within it.
4. **Custody:** report rows contain sequence, event type, actor metadata, recording time and chain hashes. The report excludes details payloads and does not run chain verification. Provide deterministic caveats; send only necessary event/type/time information to the model. Tracking may start after acquisition. Do not infer an unbroken acquisition-to-present chain or successful download from `retrieval_prepared`.
5. **Integrity:** distinguish initial upload hash/size verification, the latest stored integrity-check result and chain consistency. `not_checked`, legacy, mismatch, missing and unavailable must retain their literal meanings. The report does not execute integrity checks or certify authenticity. A matching digest does not establish benignness or truth of content.
6. **Timeline:** recorded title/description, occurred_at, reported_time, created_at, origin, source and source_locator are available. Keep occurrence, reported offset and recording time distinct. Preserve legacy versus investigator origin. A recorded source locator is an assertion, not proof a file location was parsed or verified.
7. **Case history:** revision, action, actor, timestamp, source and allowlisted before/after values are available. Describe tracked case changes only. Migration baseline is not a reconstruction of older activity; case history is not custody.
8. **Indicators/corrections:** kind, raw/normalized value, source kind/locator, recorded time and correction links are available. Support SHA-256, IP, domain and filename only as recorded observations. Attach original and successor context together; a filtered/selected original must not be presented as uncorrected. Preserve evidence links. No DNS resolution, reputation lookup or model-derived verdict.
9. **Investigator observations:** evidence notes, timeline narrative, case description and indicator locators can supply quoted material. They are untrusted assertions, even when entered by an authenticated person. Include minimal relevant text and source attribution; do not treat embedded instructions as policy.
10. **Reports:** `CaseReportDraft` is transient, version 1, with `incident:`, `evidence:`, `note:`, `timeline:`, `indicator:`, `custody:` and `history:` source identities. It has no durable report ID. Build a fresh server-side snapshot; do not trust browser-submitted report JSON. Report sections are presentation groupings, not independent evidence. Never use an AI briefing as corroborating input for another briefing.

`case_intelligence` counts and latest_activity_at have specific coverage; latest activity is not all indicator/report activity. Use source-derived deterministic counts/times with an explicit scope instead of asking the model to calculate or reinterpret them.

## Proposed AI data flow and authorization

```text
Explicit Generate cited briefing in the current Case Workspace
  -> existing in-memory operator client -> proposed POST case/{id}/ai-briefing
  -> require_operator + require_incident
  -> existing case_report.build: consistent authorized metadata snapshot
  -> release SQLite transaction
  -> AI-specific allowlist/minimization + bounded context + source manifest
  -> reauthenticate/recheck all context sources before model dispatch
  -> approved isolated model adapter (no tools, files, SQL or bearer token)
  -> strict response validation: only known source IDs/field selections
  -> reauthenticate/recheck all context sources again
  -> server-resolved exact excerpts + citations + deterministic limitations
  -> transient, case-keyed briefing beside current sources
```

Use the current operator identity, never a model-selected actor/case ID. Reuse `incidents.require_incident`, `evidence_query.authorized_query`, timeline/indicator scope and report `recheck_scope`. Case ownership alone is insufficient for collected evidence: CollectionJob.requested_by_id is also required. Notes, custody and indicator corrections must inherit their evidence scope. Include legacy timeline rows only through existing case authorization.

Do not give the model database credentials, a Session, a filesystem root, a bearer token or a general endpoint tool. Construct all context on the backend. Recheck the **entire input source scope**, not only citations the model chose; uncited content could still influence output. Return generic 404 for inaccessible cases, existing 401 behavior for invalid authentication, and no partial private output after denial. Keep no cross-case prompt/result cache or shared conversation history.

Snapshot timestamps describe the records at capture time. Incident revision is not a version of every child record. Preserve manifest/source versions and snapshot age; do not claim atomicity across model processing and later reads. Access can change after dispatch: a second check prevents publication but cannot retract material already delivered to a remote model. This residual risk is central to deployment choice.

## Minimal context and citation architecture

Reuse `case_report.build` as the first read-snapshot source without changing its existing API semantics. Apply a separate AI field allowlist; do not send the complete serialized report unreviewed. Its 2,000-row, 2 MiB and five-second limits are upstream safeguards, not suitable model-token budgets by themselves.

The backend creates a request-scoped manifest with case ID, snapshot time, case revision, context schema version, canonical context digest, per-record source type/ID, evidence association, field names and relevant revisions/correction relationships. The digest identifies context bytes; it is not an evidence hash, signature or authenticity proof. Bind it to the authenticated request on the server, not a client-supplied cache key.

Give the model short request-scoped aliases such as `S1`, not authority to create links/UUIDs. For the first task, its output is a bounded list of source aliases and allowlisted field names arranged into fixed server-defined sections. Reject extra properties, free-form factual prose, URLs, invented aliases, duplicate selections beyond policy and unsupported field names. Server rendering retrieves exact values from the captured manifest, not model-provided copies of hashes/timestamps/quotes.

Each displayed item includes a server-built citation to source type/ID and field, plus snapshot time. Resolve navigation with existing authorized case/evidence routes. Timeline, history and indicator references may need an in-panel source excerpt when existing routes cannot directly focus the row; do not invent unsupported deep links or fetch all pages without bounds. A report-section citation uses this request's context digest + stable section key + constituent record citations, explicitly labeled transient rather than a persistent report ID.

Mutable metadata must show captured revision and snapshot time; opening the live record may show newer values. Notes, history and investigator timeline/indicator records retain their existing append-only meanings. Correction context is attached by the server whether or not the model selected it. Missing data renders as “not recorded in this context,” not a fabricated zero, event or negative finding.

## Hallucination controls and prompt boundaries

Prompts are a constraint, not an authorization mechanism or guarantee of truth. Use versioned trusted instructions that define the single extractive task; treat all source text as quoted data; prohibit following instructions in records; prohibit external knowledge, verdicts, actions, free-form facts and new citations; require only the validated selection schema. User scope cannot change system policy. No open-ended user prompt or multi-turn chat is necessary for the first release.

Deterministic output validation and rendering prevent the model from supplying new evidence IDs, indicator values, timestamps, events and citation targets in this first format. Deterministic case status/counts, correction warnings and integrity/custody caveats remain outside model discretion. Do not render raw streamed model tokens, HTML, Markdown images or external links.

**Grounding is not truth verification.** A citation can point to a mistaken or malicious note; selecting a true quote can still omit crucial context. Label quotations as recorded assertions and selection as non-exhaustive. No confidence percentage or second-model approval can certify accuracy. Future paraphrase requires sentence-level support and contradiction evaluation; exact-ID validation alone would be insufficient. First release excludes paraphrase instead of promising to eliminate hallucinations with a prompt.

## AI decision and human approval boundaries

AI MAY select and organize authorized recorded observations for human review. The server MAY render their exact content and deterministic context/limitations. Later suggested questions would be clearly labeled suggestions with supporting sources, requiring separate evaluation before inclusion.

AI MUST NOT modify originals, custody, case history, case status, evidence metadata, timeline or indicators; create a new observation; declare a domain/IP/hash malicious; block/quarantine/delete anything; invoke shell/network/file tools; fetch citations; resolve domains; contact external services; or make final/irreversible decisions. These capabilities are absent from the model adapter, not merely discouraged in prose.

The investigator explicitly requests generation and reviews the selected sources. They must separately authorize any approved external disclosure before dispatch. There is no “approve all” that turns model output into trusted records. Phase 7G offers no Save as indicator/timeline/note/case-status action and no automatic insertion into the deterministic report. Subsequent investigation actions continue through existing explicit forms and authorization/revision rules. A later export/save workflow would require a separate review and retention boundary.

## Model architecture options and selection gate

**Local model:** strongest candidate for a privacy-first pilot because approved context can remain on the controlled host/network. However, local does not automatically mean safe: runtime logging/telemetry, caches, model supply chain, shared users, filesystem privileges, resource load and model quality still require review. Run outside the evidence store with no evidence/database mount or arbitrary tool access. Establish capacity on the actual hardware; none was benchmarked in this audit.

**Remote API:** may reduce local serving burden but discloses case text to another processor. Require a named approved destination, region/retention/training/logging/subprocessor review, transport and key management, cost/time bounds and explicit disclosure policy. Field minimization is not guaranteed secret redaction: free text may contain private paths, identities or credentials. Keys stay server-side, separate from operator tokens, never in VITE settings or browser requests. No user-controlled endpoint or automatic redirect/fallback.

**Hybrid:** adds routing, consistency and disclosure complexity without proving value for this first task. Do not silently send to a remote provider when local inference fails. A later hybrid mode needs explicit per-destination approval and an independently tested failure/disclosure contract.

No external provider or model is selected by this audit. Recommend evaluating one approved local deployment first on sanitized fixtures. Before implementation can claim released AI, choose and approve a concrete runtime/model and pass its evaluations. If no candidate meets quality, latency or privacy requirements, keep the existing report workflow; do not substitute a fake AI response or enable an unreviewed remote API. Adapter design can remain provider-neutral without implementing multiple backends.

## Security threat model

- **Prompt injection in notes, filenames, locators, tags or future file text:** structured untrusted-source separation, no tools, no secrets in context and source-selection-only output. Adversarial instructions may still bias selection; attach mandatory source caveats/corrections and measure omissions. Do not treat source text as a system message.
- **Malicious collected files:** excluded entirely in the first phase. MIME/filename are not trust signals. Later parsing needs isolation and content-location provenance, not direct execution or hidden retrieval.
- **Cross-case leakage:** server-owned context; owner/requester predicates; scope rechecks before dispatch/publication; no shared history/cache; reject mixed-case response manifests; clear UI on case/auth changes. A model must never request another case to improve an answer.
- **Sensitive text disclosure:** minimize allowlisted fields, exclude storage/config/auth data and unnecessary actor identities, use deployment approval. Secret-pattern filtering cannot establish that all free text is safe. Logs should contain only sanitized outcome codes, duration, counts and version metadata, not prompts/output/credentials; sensitive hashes/IDs must not become public telemetry.
- **Exfiltration/SSRF:** fixed administrator-approved adapter destination, redirect rejection, no model-controlled URL or frontend key. Local runtime must not have unrestricted network/tool access. Render model/source text inertly.
- **Denial of service/resource exhaustion:** bound context/output, concurrent inference, time and request body; reject excess before model dispatch; release capacity on timeout, malformed response and cancellation. Do not hold SQLite transactions during inference.
- **Stale authorization/response:** recheck and abort as above; a cancelled request must not overwrite a newer case result. A remote request may already have been processed despite browser cancellation; disclose that limitation rather than promising erasure.
- **Misleading authoritative output:** visibly distinguish model selection, source assertions, unverified integrity and a deterministic report. No threat colors/verdict score, fake confidence or custody certification.

## Proposed backend and frontend integration

One additive endpoint is justified because existing APIs neither invoke a model nor validate its output: proposed `POST /api/v2/investigation/incidents/{id}/ai-briefing`, fixed versioned task, no client context/credential/provider URL in its body. POST represents explicit computation/disclosure, not a persistent record. Response is no-store and contains case ID, snapshot/context version, selected source-backed items, limitations and non-sensitive model/prompt version metadata. No streaming, chat/session CRUD or AI write endpoints.

Use a small `ai_briefing` orchestration service, `ai_context` allowlist/manifest builder and one bounded model adapter with a strict response validator/schema. Reuse report building and scope services, not internal HTTP calls to existing routes. Release DB resources before inference and use a fresh authorization read before output. No new background worker, vector database or general agent framework is necessary.

Place a collapsed “Cited case briefing” panel in existing CaseWorkspace near the deterministic report. Show exactly which case, metadata-only scope, approved processing destination and transient lifetime. Generation is explicit. Display source excerpts and limitations, clear loading/cancel/failure/manual-retry states, and keep the last successful same-case result during a failed replacement only while access remains authorized, following Phase 7D patterns. Never auto-generate on mount, refresh, reconnect or case switch.

Reuse the current bearer client, with a narrowly scoped request timeout only if required by the approved inference deadline; do not increase all existing API timeouts. Preserve generation/case keys, hide/inert while access revalidates, clear on definitive denial/disconnect/reload/leaving the case, and ignore stale responses. Use accessible status/focus and responsive source rows. Do not embed unvalidated model output in the existing report or disturb pending indicator retries.

Likely future files (design only): `backend/app/services/ai_context.py`, `ai_briefing.py`, `ai_model.py`; `backend/app/schemas/ai_briefing.py`; an additive case route in `api/routes/investigation_incidents.py`; narrow reviewed settings/resource initialization in `core/config.py`/`main.py` if the selected runtime needs them; `frontend/src/features/cases/CaseBriefing.tsx` and a small contract module; CaseWorkspace, investigation service and scoped styles; new backend/service/browser tests and completion documentation. No changes to existing report semantics, source models, migrations, original-reader/retrieval or collector are expected. Model/runtime installation and any dependency proposal require approval, not inference from this filename list.

## Performance, failure and database decision

Provisional pilot limits to validate against the selected runtime: existing report snapshot ceilings plus at most 64 KiB minimized serialized context, an 8,000-input-token ceiling with reserved output capacity, up to 20 displayed source selections, 32 KiB response cap, one inference at a time per process and a 30-second inference deadline. These are proposed ceilings, not measured capability or current configuration. Use the selected adapter's reliable tokenizer/counting or a proven conservative bound; bytes and characters are not tokens. Account for trusted instructions and output allowance too.

If a complete small-case context exceeds limits, refuse with a clear message and retain the ordinary report. Do not silently truncate, summarize recursively, drop correction partners or present partial context as complete. User-selected subsets can be designed later with explicit included/excluded scope. No vector search/index is necessary now. Process-local capacity is only appropriate for the current pilot; multi-process deployment needs a separate capacity assessment.

Timeout, invalid schema/citation, context excess, model unavailability or capacity exhaustion returns a sanitized typed failure, no partial/unvalidated output and no automatic retry. Preserve prior authorized UI results using existing transient patterns. Release slots and handles in all failure paths; no SQLite lock during slow inference. Retry may produce another selection, so do not promise model determinism or model-side cancellation.

**Keep output transient. Database remains 0008; no migration is required.** No AI history table, embeddings, report persistence or browser storage. Backend request memory is released after completion; runtime retention must be separately checked. If later users require reopening a reviewed AI artifact, design immutable derivative identity, model/prompt/context versions, source snapshots, retention and current authorization over copied records. Do not repurpose custody or CaseHistory as an AI transcript. Such persistence would require a separately approved migration and restore strategy.

## Testing and release gates

1. **Unit/context:** exact field allowlists, canonical manifests, deterministic citation resolution, UTC/offset distinctions, missing-data labels, integrity caveats, correction partners, unsupported kinds/fields and row/byte/token/output limits. Test invented aliases, extra prose, wrong types, duplicates and Unicode/control-text cases. No invalid response may be displayed as a successful briefing.
2. **Authorization:** absent/wrong operator, device token, inactive user, foreign case, same-case hidden evidence requester, hidden corrections, notes/timeline/history scope; access changes before dispatch and during inference. Assert the model receives no unauthorized sentinel and publication fails closed. Recheck all input records, not only returned citations.
3. **Preservation:** compare all database rows before/after success and failure. Patch original-file reader, retrieval/custody append and mutation services to fail if invoked. Confirm no source/custody/history/timeline/indicator writes or original reads occur.
4. **Adversarial fixtures:** embedded “ignore instructions”, forged system messages/citations, fabricated maliciousness claims, requests for another case, encoded instructions, URLs/exfiltration requests, conflicting notes, corrected indicators and fabricated timestamps. Confirm exact-source rendering, no external requests/actions and no secret in logs/output. Evaluate misleading selection and omitted correction context, not just JSON validity.
5. **Real-model evaluation:** sanitized investigator-reviewed cases, fixed versioned evaluation set and held-out cases, human relevance/coverage review against the complete report, repeated runs for selection variance, measured latency/resource use. Require zero unauthorized sources, fabricated rendered values/citations, prohibited actions and secret leakage in the release suite; any such failure blocks release. Predefine acceptable relevance/coverage with investigators rather than invent an unmeasured score. Passing a finite suite does not guarantee universal safety.
6. **Browser/service:** explicit generation only, pending input unaffected, correct case/snapshot, source navigation, safe text, no external image/link loads, keyboard/mobile, cancellation/late output, replacement failure, scope switching and 401/disconnect. Verify keys/tokens never appear in browser storage, URL or errors. Stubbed model responses validate application controls but do not establish real-model quality.
7. **Regression/operations:** full backend, frontend services, TypeScript/build, all browser workflows, Windows upload/repeat, SQLite revision/integrity/FK. Test concurrency release, timeout cleanup and disabled/unconfigured runtime. Existing reports and all investigation actions must work while AI is unavailable.

## Minimal phased roadmap and rollback

**Phase 7G, pending approval:** one model-assisted extractive case briefing, metadata only, fixed task and strict selection schema, server-resolved citations, explicit generation, one approved adapter, no tool access, transient output and full release gates. First settle runtime/deployment/privacy and evaluation criteria on sanitized data; then implement the narrow context/API/panel. Do not claim AI completion using only a mock adapter or a disabled endpoint.

**Later, separately approved:** bounded paraphrase or source-specific questions after semantic-support evaluation; investigator-reviewed report assistance without automatic report changes; content-derived excerpts only after parser/custody/disclosure design; optional retained derivative artifacts only after persistence authorization. None is automatically authorized by completing Phase 7G. External enrichment, autonomous decisions and teams/RBAC are not prerequisites.

Rollback is to disable/remove the additive briefing surface/adapter and restore only its reviewed code/configuration changes. Existing report and investigation workflows remain available. No database downgrade, evidence deletion or custody/history rollback is involved. Cancel active inference best-effort, clear transient UI and remove approved runtime secrets via operational controls; a remote disclosure cannot be rolled back. Never weaken auth, lift limits or silently switch providers to keep AI appearing available.

## Audit verification and completion

Read-only SQLite checks returned **0008**, `integrity_check = ok`, and **0 foreign-key violations**. Database SHA-256 remains `8f8e520eb9e23d2354652990d114fcb5895f7f1b5e293f0135299f279acde969`.

Only `docs/phase7f-ai-architecture-audit.md` was created. Before/after source/configuration/dependency/migration/documentation fingerprints confirm no other inspected files changed. No AI, provider API, dependencies, migration, database write, authentication change, custody change or application implementation was performed. Tests were not run for this documentation-only task. Phase 7G has not started.

Phase 7F AI Architecture Audit complete — awaiting approval before AI implementation.
