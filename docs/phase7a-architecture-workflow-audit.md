# Phase 7A — Architecture and Investigation Workflow Audit

Date: 2026-09-12. Status: audit complete; implementation requires approval.

## Decision

ShadowVault AI is an investigator-driven collection and investigation workspace. It can preserve selected Windows files, organize an owned case, record evidence annotations, timeline observations and candidate indicators, retain separate histories, and prepare authorized verified evidence copies. It does not detect threats, interpret file contents, or produce final investigation conclusions.

**Recommend Phase 7B: an explicit, case-scoped investigation report draft, assembled from authorized existing metadata with source citations and correction history.** This is a deterministic presentation/export capability, not AI summarization. It closes the gap between recording an investigation and handing its documented observations to a reviewer. No new Case entity, report persistence table, migration, external service or worker is needed for the proposed first slice.

The immediate prerequisite is an explicit report scope and completeness contract. A collection of first-page API results must never be labeled a complete case report. The proposed capability and endpoint below do not exist today and are not implemented by this audit.

## Audit method and verification limits

Reviewed the application composition, configuration and database boundaries; models, schemas, routes and services; migration history through 0008; Windows collector and shared core; React navigation, API clients and investigation components; test inventory and workflow coverage; roadmap, architecture and phase completion documentation, particularly Phases 6A–6F.

Implementation references include `backend/app/main.py`, `core/security.py`, `services/{incidents,case_history,case_intelligence,evidence_query,evidence_metadata,custody,timeline,indicators,collection,storage,evidence_reader,evidence_retrieval}.py`, corresponding models/schemas/routes, and `frontend/src/features/{cases,evidence,timeline,indicators}`. Agent entry point is `agents/windows/collector.py`; common transport, hashing and connection validation are in `agents/core`.

This was static source inspection and read-only SQLite inspection, not a penetration test, load test, fresh browser/accessibility assessment or rerun of regression suites. No original evidence content was opened, parsed, retrieved or executed. Private original-storage and older browser-fixture directories were not inspected; directory enumeration encountered access-denied entries and those permissions were left intact. Generated dependency trees, binary evidence and old fixture databases are not treated as application source.

The Phase 6F completion report records **144 backend tests, 40 frontend service tests and 53 browser workflows passing**, successful TypeScript/build and the real Windows CLI upload/repeat regression. Those are historical verified results, not tests executed during Phase 7A. Existing documented warnings are Starlette/httpx TestClient deprecation and NO_COLOR/FORCE_COLOR interaction.

## Current architecture

```text
Locally provisioned operator
  -> React/TypeScript hash navigation
  -> in-memory bearer client -> FastAPI authorization -> SQLAlchemy -> SQLite 0008
                                      |
                                      +-> owned Incident = Case
                                            |-> revision-safe edits + CaseHistoryEvent
                                            |-> read-only case intelligence aggregates
                                            |-> CollectionJob -> assigned Agent
                                            |                    -> Windows selected files
                                            |                    -> private spool + SHA-256
                                            |                    -> bounded authenticated upload
                                            |                         -> private original + Evidence
                                            |-> Evidence
                                                 |-> notes/tags/review metadata
                                                 |-> TimelineEvent observations
                                                 |-> IndicatorObservation -> correction successor
                                                 |-> CustodyEvent chain
                                                 |-> integrity-check structure (no executor)
                                                 `-> explicit verified-copy retrieval
```

FastAPI owns request-scoped sessions and process-local capacity limits. Pydantic DTOs separate API fields from persistence internals. SQLite foreign keys and revision/uniqueness constraints support service-level validation. Blob storage remains outside the database; no queue, search engine, graph store or AI service exists. React and TypeScript use native fetch and shared abortable resource loading. The Linux agent directory contains documentation only.

Backend read flow is route → authenticated operator → case/evidence-scoped query service → models → response DTO. Ordinary metadata reads do not access blob storage or append custody. Case writes use route → lifecycle/revision validation → Incident update and CaseHistoryEvent in one transaction. Evidence annotations and timeline writes instead append evidence custody in their mutation transaction. Indicator writes use their own append-only observation/idempotency constraints and deliberately change neither case history nor custody.

Frontend flow is `App` hash selection → `InvestigationWorkspace` connection boundary → `CaseWorkspace`/evidence/timeline/indicator component → shared `features/evidence/service.ts` → existing investigation endpoint. The shared client is named for evidence historically but also serves cases, history and indicators; extending it does not require another credential store or parallel client architecture.

## What an investigator can accomplish now

1. Provision an operator locally, enter its token in the connection field, and view only authorized data. Disconnect or reload clears the in-memory connection. Email/password sign-in remains a placeholder, not an alternative authentication method.
2. Create and find cases by text, severity and status; view ownership, creation/update timestamps, revision and recorded history. Incident remains the sole Case entity. Supported lifecycle is `open → investigating → closed`, with explicit `closed → investigating` reopening; unchanged status is allowed. Closed status does not cancel jobs or revoke evidence access.
3. Register/revoke an agent and create/read/cancel a collection job through the v1 API. Invoke the Windows CLI with approved selected files. There is no equivalent acquisition wizard in the browser.
4. Acquire regular selected files into private staging, calculate SHA-256, upload with byte/time limits, and receive independently verified hash/size receipts. Job/item identity makes identical retries return the original receipt; conflicting bytes are rejected. Staging and durable receipts support explicit retry without reacquiring successfully collected files.
5. Search evidence by case, collection job, agent, text metadata, exact hash, tags, review/verification/integrity state, dates and sizes. Open acquisition metadata, annotate title/review/tags, and add attributed notes without changing original bytes.
6. Record an evidence-linked timeline observation with occurrence time, supplied offset, source/citation and authenticated recorder. Search and page the single TimelineEvent system. Recorded time and forensic occurrence time remain distinct.
7. Record SHA-256, IP, domain and filename indicators against authorized evidence. Promote the evidence hash/filename through server-selected metadata or enter a manual observation. Inspect raw/normalized values, source, actor, recording time, source evidence and correction links.
8. Correct an indicator by appending a successor. Filter by kind, exact normalized value, evidence or observation identity; navigate to source evidence and original/corrected records. These are candidate observations, not confirmed threats or automatically extracted IOCs.
9. Review case intelligence counts, case revision history and evidence custody as different views. Explicitly request an attachment copy whose bytes are checked again before retrieval custody is committed.

The end-to-end result today is a navigable investigation record and individually retrievable evidence. An investigator still has to assemble a coherent handoff outside the application. There is no report preparation/export, persisted finding/hypothesis model, threat verdict, automatic response or source-content analysis.

## Data semantics and reusable contracts

All paths below are relative to `/api/v2/investigation` unless marked v1.

- **Cases:** `GET/POST /incidents`, `GET/PATCH /incidents/{id}`. `CaseList`, `CaseForm` and `CaseWorkspace` already provide search, creation, conflict/reload and details. Edits use expected revision and server UTC updated_at; existing IDs and relationships remain stable.
- **Case history:** `GET /incidents/{id}/history`, consumed by `CaseHistory`. Events record actor, UTC time, revision and before/after supported metadata. Migration baselines identify the start of tracking rather than reconstructing unknown changes. SQLite update/delete triggers and ORM guards protect appends; history is not a custody hash chain or all-activity feed.
- **Case intelligence:** optional `include_intelligence=true` on case detail, consumed by `CaseIntelligencePanel`. Counts use authorized evidence/timeline and recorded case-history rows. Latest activity covers case creation/update, evidence registration, timeline recording, history and visible evidence custody. **Indicator writes are excluded.** History-row count is not necessarily the Incident revision number; latest activity is not the latest occurrence or proof of delivery.
- **Evidence:** `GET /evidence`, `GET /evidence/{id}`, `PATCH /evidence/{id}/annotations`, `GET/POST /evidence/{id}/notes`. Reuse `EvidenceSearch`, `EvidenceDetailsPage`, annotation contracts and revision handling. Evidence belongs to one Incident; job/item references preserve acquisition identity. Equal hashes do not merge records or custody. Text search is metadata search, not file-content or note-body search.
- **Custody:** `GET /evidence/{id}/custody`, consumed by `CustodyHistory`. Sequence/head compare-and-swap coordinates transaction-bound appends and canonical SHA-256 chaining. Internal `verify_chain` compares against the locally stored head; displaying history does not execute that verification.
- **Timeline:** `GET /timeline-events`, `GET /timeline-events/{id}`, `POST /evidence/{id}/timeline-events`. Reuse `TimelinePanel`, details and observation submission. New observations have one source evidence; legacy events can be unlinked. Submission identity prevents duplicate identical retries. No correction API exists for timeline observations.
- **Indicators:** `GET /incidents/{id}/indicators`, `POST /evidence/{id}/indicators`. Reuse `CaseThreatIntelligence`, normalization, authorized query and list-only `superseded_by_id`. Successors resolve outside page/value filters but inside authorized case/evidence scope. POST receipt shape remains unchanged. No totals or full-text search should be inferred from a loaded page.
- **Retrieval:** `POST /evidence/{id}/download`, consumed by `EvidenceDownload`. It prepares a bounded private copy, validates size/hash, reauthorizes before commit and records `evidence_retrieval_prepared`. No public URL, inline preview, Range/resume or delivery confirmation exists. Closing failures cannot retain the response capacity slot after preflight hardening.
- **Collection and readiness:** v1 `/agents`, `/collection-jobs`, assigned-agent `/agents/jobs/{job_id}` and PUT file upload, plus health. Shared core connection/transport/hash logic and the Windows CLI remain reusable unchanged. Legacy v1 incident/evidence/timeline and auth placeholders are not the implemented v2 contracts.

Indicator normalization is deliberately conservative: SHA-256 lowercases validated hexadecimal; IP uses literal address validation without zones/CIDR; domains are normalized ASCII names, not URLs, Unicode/defanged strings or DNS lookups; filenames are names, not filesystem paths. A citation is investigator-supplied text, not verified extraction coordinates. Manual IP/domain recording does not prove the source file contains the value.

## Findings and priorities

### 1. Investigation handoff is missing — highest product value

Cases, notes, timelines and corrected indicators contain useful work but are distributed over live paginated views. There is no explicit metadata report, completeness marker, source inventory or stable reviewed output. Copying browser rows can omit later pages, corrections or qualification text. A human-reviewed report draft is the smallest next capability that turns existing work into a shareable result without needing AI or parsing.

### 2. Acquisition onboarding remains difficult

The browser can show zero evidence correctly but cannot enroll a collector or create its job. Operators must coordinate API calls, two credential types, job IDs and local paths in a terminal. A future explicit collection wizard/runbook would reduce errors. It is a separate usability slice, not a missing backend acquisition mechanism and not part of the proposed report work.

### 3. Pending write recovery is only partly preserved

Phase 6F correctly retains indicator payload/submission ID for manual retries and separates saved receipts from list-refresh failure. Same-case evidence navigation keeps the panel mounted. However, `CaseWorkspace` conditionally removes its content during case reload/save; the indicator panel can unmount and lose pending identity. Leaving the case, disconnecting or reloading the tab also loses it. The panel's broad in-case preservation wording should not be interpreted as refresh-safe recovery.

This is a reproducible-by-code workflow risk, not a new claim of observed duplicate production data. A narrowly approved follow-up should retain pending state within the authenticated workspace or explicitly guard disruptive navigation. Never solve it by persisting credentials or automatically retrying writes. Report navigation must not introduce another silent pending-state-loss path.

### 4. Navigation and accessibility need targeted follow-up

Indicator source links retain case context, but `TimelinePanel` links to standalone evidence/event routes. That can lose the working case and drafts. UUID fallback fields, oldest-first indicator pages and a long indicator panel above the evidence workspace still impose cognitive/scrolling costs. Native controls, focus actions, status/error roles, wrapping and representative mobile tests exist; comprehensive keyboard/screen-reader conformance and large-list performance are not established. Prefer small context-preserving navigation improvements over another workspace shell.

### 5. Integrity and custody guarantees have important limits

Upload verifies transfer size/hash, not endpoint authenticity, malware safety or acquisition completeness. Collection is live selected-file acquisition, not imaging or an atomic disk snapshot. Agent names/version and collection times are reported context, not hardware attestation.

Upload creates Evidence without an initial CustodyEvent. The first tracked annotation, note, timeline observation or retrieval establishes a baseline. Indicator recording intentionally does not start custody. Empty custody must not mean failed acquisition, and a report must not fabricate earlier events.

EvidenceIntegrityCheck has a storage structure and presentation/query support, but no execution workflow. `not_checked`, initial `verified`, custody-chain consistency and retrieval byte verification are four different claims. Retrieval does not create a subsequent integrity result, and prepared-copy custody does not attest to delivery. Custody/notes/investigator timeline rely on application/ORM boundaries; database triggers currently cover case history and indicators. Local administrators can bypass/remove guards or replace a chain and its head. No externally anchored/WORM/signature guarantee exists.

### 6. Threat-intelligence workflow is observation management

The four Phase 6F priorities are implemented: correction visibility across pages, existing filters, authorized evidence context and explicit save/retry receipts. A null successor describes the authorized response at read time; it is not permanent correctness. Original and successor remain queryable. There is no withdrawal disposition, cross-evidence finding, automatic IOC-to-timeline relationship, extraction, enrichment or maliciousness score. Do not repurpose case history or custody to provide those concepts.

### 7. Authorization is consistent in inspected paths, but future aggregation is a risk

No new cross-case disclosure was demonstrated by this static review. Case queries require owner identity. Collected evidence additionally requires matching collection requester; timeline, indicator and aggregate queries inherit that stricter visibility. Both case and evidence scope must precede counting, correction lookup or report assembly. An owner-scoped case alone does not authorize every joined row.

The configured operator credential is a local pilot authentication boundary, not individual multi-user sessions/RBAC. CORS is not authorization; remote deployment still needs reviewed TLS and host/storage controls. Operator rotation does not revoke all existing agent tokens automatically. Agent expiry/revocation and active-owner checks remain separate. No broad deployment/security certification is implied.

### 8. Scale and crash recovery need measurement

SQLite write contention, metadata substring queries, correlated integrity lookups, overview fan-out and long observation histories can become expensive. Upload/retrieval limits are process-local, not distributed quotas. Filesystem promotion and database commit are not a single durable transaction; a process crash can leave an orphaned blob. No reconciliation worker should be added incidentally. A report must have row/byte/time limits rather than enumerate unlimited pages or download originals.

### 9. Documentation and legacy surface are duplicated or stale

README and architecture status passages still describe general incident workflows as unimplemented; roadmap coverage lags later completed phases and older proposed phase numbers. The v1 placeholder login/domain routes coexist intentionally with implemented v2 APIs. The legacy sign-in preview is confusing but is not a second working authentication system. Case management/history, timeline and custody are **not** redundant audit systems: each records a different semantic event and must remain separate.

Do not remove backward-compatible placeholders, combine the histories, rewrite routing or split the shared client during Phase 7B. Updating inaccurate product/setup documentation is appropriate in a separately approved implementation's documentation scope; this audit changes only its own report.

## Phase 7B recommendation and impact

### One capability: source-cited case report draft

Add an explicit Prepare investigation report action inside the authorized Case workspace. The investigator reviews a deterministic, metadata-only snapshot and can explicitly save a plain-text draft. Label it a draft of recorded observations, not a threat assessment, legal certification or validated conclusion. No generated narrative, severity decision or case closure follows preparation.

The first version should include case metadata/revision; permitted evidence identities, filenames, hashes and acquisition/verification times; review annotations/notes; timeline records with occurrence and recording provenance; indicator originals/corrections; case-history tracking start and changes; and custody heads plus recorded entries for included evidence. Include source record IDs and schema/version/generation time. Clearly separate each history and show missing legacy provenance. Explain the aggregate exclusions instead of silently redefining Phase 6B's latest-activity semantics.

Default to a complete **authorized metadata scope**, not all physical case rows and not current UI filters. Exclude private storage keys, source filesystem paths, credentials, raw request fingerprints and original bytes. Free-text case descriptions, notes, filenames and citations may themselves contain sensitive information: a technical field allowlist is not automatic redaction. Require explicit review before saving; no automatic sharing/upload. A saved local draft is outside subsequent access revocation and must be described as such.

### Backend/API impact

Existing API models/query helpers can supply all underlying facts, but independently paginating many existing endpoints cannot promise a consistent snapshot. For the proposed complete-snapshot semantics, one additive read-only endpoint is justified: **proposed `GET /api/v2/investigation/incidents/{id}/report-draft`**. Reuse `require_operator`, `require_incident` and authorized evidence/timeline/indicator queries; use an explicit allowlisted response DTO. Do not change any existing response or route semantics.

Build the bounded DTO within one explicitly established SQLite read snapshot, materialize it and end the transaction before response delivery. Pin this behavior in tests: do not assume merely creating a SQLAlchemy Session creates the needed SQLite multi-query snapshot. Apply hard row, byte and execution limits with a sanitized refusal if complete output cannot be prepared. No silent truncation, background completion, mixed-snapshot cursor aggregation or partial output labeled complete. The exact limits must be reviewed before coding and exercised at boundaries.

The read does not call retrieval/storage, run integrity checks, append history/custody, create an indicator or mutate the case. Response uses no-store; report assembly is manually requested, not automatic on opening a case. Revalidate the active operator boundary before returning the materialized output. Reuse internal query predicates rather than calling HTTP endpoints recursively.

### Database and migration impact

**No schema change required; retain 0008.** Existing source records contain the information needed for a transient report draft. No Report, Case or second Timeline table is proposed. There is no persistent report ID, report history, server-side saved draft or signing workflow in this slice. Source IDs, per-record revisions/heads and generated time describe the output; a case revision alone cannot version evidence or indicator activity.

If durable findings, report retention/approval/signatures or exports larger than the bounded synchronous limit become requirements, stop and seek a separate architecture decision. Those requirements do not justify a speculative migration now. Existing migration 0008 is forward-only; do not downgrade it to introduce reporting. Existing original-record relationships remain untouched.

### Frontend impact

Add a small report component and typed service method inside the existing authenticated Case workspace. Provide preparation/loading/unavailable/empty/ready states, explicit retry for failed reads, visible scope/limits and generated time, source navigation and a separate Save draft action. A zero-evidence case should still display its case/history facts honestly. Preserve pending indicator submissions when entering/closing the report; do not force a whole-case refresh.

Use React's escaped text and an inert plain-text download, not active HTML from source strings or an added Markdown parser. Revoke any temporary object URL and clear report memory on disconnect/case change. No token in a URL, filename, browser storage or exported document. Printing, PDF libraries, redaction editors and rich document engines are not required for this first version.

### Agent impact

None. Keep shared hashing/uploader/config, Windows CLI arguments, staging/receipt behavior, manifest limits and upload contracts unchanged. No Linux collection or new telemetry is needed.

## Minimal implementation sequence, after approval

1. Approve the allowlisted draft DTO, completeness wording, row/byte/time limits and plain-text output. Define snapshot behavior and pending-write navigation before editing.
2. Add a bounded read-only case report service/schema and one additive route. Prove owner and collection-requester scope across every section and successor lookup. No storage access or mutations.
3. Add the Case workspace preparation/review/save component through the current in-memory client. Preserve pending indicator state, loading/error distinctions and accessible focus.
4. Add focused API/service/browser regressions; run complete existing suites and the Windows CLI upload/repeat regression in isolated fixtures. Verify unchanged database revision/integrity and original flows.
5. Document actual report coverage, privacy/disclosure and consistency limits. Stop for review; no AI phase starts automatically.

Expected implementation file surface, subject to approved DTO review: new `backend/app/schemas/case_report.py` and `backend/app/services/case_report.py`; additive route in `backend/app/api/routes/investigation_incidents.py`; new `frontend/src/features/cases/CaseReport.tsx` and report contracts; existing shared `features/evidence/service.ts` and `cases/CaseWorkspace.tsx`; existing stylesheet only if needed; new focused backend, frontend service and browser tests; implementation documentation. No model, migration, collector, custody mutation service, case-history mutation service or dependency file is expected to change.

## Testing requirements and acceptance

- Authorization: missing/invalid/inactive operator; foreign case; owned case with evidence belonging to another requester; hidden linked timeline/indicators/corrections; no leaked counts, IDs, labels or existence signals. Recheck all scope server-side, never trust supplied frontend IDs.
- Completeness: more than one page in each source; correction successor outside original value filter/page; empty and legacy cases; accurate history start; no duplicated custody/history; clear indicator observation semantics; no current-UI-filter leakage into full authorized scope.
- Consistency: concurrent case save, annotation, indicator correction and custody append during preparation; all sections from one established snapshot or explicit refusal. Bounded execution, exact limit behavior and sanitized database errors.
- Immutability: before/after Incident revision, Evidence metadata/head, source bytes, TimelineEvent, IndicatorObservation, CaseHistoryEvent and custody rows unchanged by report reads. Assert storage/retrieval and mutation services are never invoked. Export is not evidence delivery and creates no retrieval event.
- Privacy: no token/digest/storage key/source path in structured fields or diagnostics; malicious HTML, domains and citation strings remain inert text; document the free-text disclosure limitation; no external requests or browser persistence.
- Frontend/browser: prepare/review/save, cancel/read retry, disconnect during load, case switch/stale response suppression, pending indicator identity preservation, complete/empty/unavailable distinctions, long text, keyboard focus and mobile overflow. Saving a draft must never submit an investigation mutation.
- Full regression: backend unittest suite, frontend services, all browser workflows, TypeScript, production build and real Windows collector upload/repeat. Preserve case CAS/updated_at/history atomicity, evidence annotations/custody, timeline idempotency and verified-copy retrieval. Check development DB remains 0008, integrity ok and foreign keys clean; use isolated test databases.

Acceptance requires a useful reviewable output with traceable existing facts, explicit completeness/privacy limits, no invented conclusions and no changes to existing contracts or stored records. Test failures or an inability to establish bounded snapshot consistency block completion; do not substitute a misleading first-page report.

## Phase 7 readiness and explicit exclusions

The project is ready for a narrowly scoped metadata report capability subject to the tests above. It is not established as an enterprise multi-user platform or ready to send evidence to an AI provider. An AI phase would first need separate approved data destinations, authorized context selection, source citation/evaluation, prompt-injection handling and human decision boundaries. Neither the project name nor an older roadmap mention authorizes AI.

Out of scope: AI, automatic narrative/conclusions, threat verdicts, extraction/parsing/preview, malware analysis or execution, external feeds/DNS/enrichment, automatic case decisions, workers, scheduling, teams/RBAC/browser sessions, Linux acquisition, cross-case sharing/correlation, persistent findings/reports, signatures/legal certification, integrity-check execution, retroactive custody, timeline correction redesign and architecture/dependency replacement.

## Audit closure

Read-only SQLite inspection of the configured `backend/shadowvault.db` returned revision **0008**, `PRAGMA integrity_check = ok`, and **0 foreign-key violations**. The schema contains existing case/evidence/history/timeline/indicator structures; update/delete triggers protect case history and indicators. No migration, database mutation or test run was performed.

Only `docs/phase7a-architecture-workflow-audit.md` was created. Before/after SHA-256 inventories verify that inspected application, agent, test, configuration, dependency, migration and existing documentation files and the development database remain unchanged. No implementation was performed.

Phase 7A complete — awaiting approval before implementation.
