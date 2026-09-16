# Phase 6A — Investigation Intelligence Architecture Audit

Date: 2026-09-12. Scope: documentation only, following Phase 5D.

## Executive assessment

ShadowVault AI has a useful investigator-driven intelligence foundation: authorized metadata search, review states, notes/tags, attributed evidence-linked observations, revisioned case history, and verified-copy retrieval. It organizes and preserves investigation context. It does **not** interpret evidence contents, identify threats, establish causation, or generate analytical findings.

The minimal next step is a metadata-only workflow enhancement using existing APIs and relationships. Keep Incident as the Case entity and TimelineEvent as the sole forensic timeline model. Do not introduce AI, a graph database, a second case/timeline system, or background processing to deliver those improvements.

The local database is at **0007**. No schema change is needed for the recommended first implementation slice. This audit authorizes no implementation.

## Audit basis and limits

Reviewed the evidence, annotation, integrity, incident, case-history, timeline, collection-job, agent, and custody models; collection, query, annotation, case-history, timeline, custody, storage-reader and retrieval services; investigation routes and operator/device security; Windows collector staging/receipts; frontend service, overview, case/evidence/timeline consumers; and architecture/roadmap/completion documentation.

Primary implementation references:

- [Evidence and relationships](../backend/app/models/evidence.py), [annotations](../backend/app/models/evidence_annotation.py), [integrity structure](../backend/app/models/evidence_integrity.py).
- [Incident](../backend/app/models/incident.py), [case history model](../backend/app/models/case_history.py), [case mutations](../backend/app/services/incidents.py), [history service](../backend/app/services/case_history.py).
- [Timeline model](../backend/app/models/timeline.py), [timeline service](../backend/app/services/timeline.py), [custody model](../backend/app/models/custody.py), [custody service](../backend/app/services/custody.py).
- [Collection routes](../backend/app/api/routes/collection.py), [collection service](../backend/app/services/collection.py), [storage](../backend/app/services/storage.py), [Windows collector](../agents/windows/collector.py).
- [Evidence queries](../backend/app/services/evidence_query.py), [secure reader](../backend/app/services/evidence_reader.py), [retrieval preparation](../backend/app/services/evidence_retrieval.py), [retrieval response](../backend/app/api/routes/investigation_retrieval.py).
- [Operator/device authorization](../backend/app/core/security.py), [frontend service](../frontend/src/features/evidence/service.ts), [shared workspace](../frontend/src/features/evidence/InvestigationWorkspace.tsx), [overview loader](../frontend/src/features/cases/overview.ts).
- [Phase 5D completion report](phase5d-ui-implementation-report.md), [roadmap](roadmap.md), [architecture](architecture.md).

The roadmap is not a complete description of the present implementation. It still describes earlier identity limitations and planned later phases that subsequent case/history/UI work has partly superseded. Its broad mentions of detection, analysis, exports, and an AI assistant are future intentions, not authorization or evidence that those features exist. The code and Phase 5D completion report are the baseline for this audit. Neither older document was changed here.

This was static inspection plus read-only database revision/fingerprint verification. No evidence was opened, downloaded, parsed, executed, or sent to another service. No test suite was rerun. The last documented Phase 5D results are 129 backend tests, 35 frontend tests, 44 browser workflows, and successful typecheck/build; these are historical verification results, not a new test claim.

## 1. Existing data and investigation flow

```text
Configured operator -> owned Incident (Case)
                         |-- revision-safe metadata/lifecycle changes
                         |     `-- CaseHistoryEvent (same DB transaction)
                         |
                         `-- CollectionJob -> assigned Agent
                               `-- explicitly selected Windows file
                                    `-- private staging + SHA-256 + receipt
                                         `-- bounded binary upload
                                              `-- private original + Evidence
                                                   |-- metadata search/review/tags
                                                   |-- EvidenceNote
                                                   |-- TimelineEvent observation
                                                   |-- CustodyEvent chain
                                                   |-- EvidenceIntegrityCheck structure
                                                   `-- explicit verified-copy retrieval

Investigator reads authorized metadata -> selects source evidence -> records
an observation/note -> reviews timeline, case history, and evidence custody
as distinct views. No analysis engine sits between evidence and observations.
```

### Evidence model and search

Evidence preserves identity, incident ownership linkage, filename, media type, size, SHA-256, opaque storage key, collecting-user reference, selected source path, job/item IDs, collected time, verified time, and initial verification status. Acquisition facts are not editable through investigation annotation APIs. Separate display title, review state, metadata revision, and custody head/sequence support investigator work without changing original bytes.

Each evidence record belongs to **one** Incident. The job/incident composite foreign key prevents assigning a collection receipt to a different incident. Job/item uniqueness provides upload retry identity; it is not global content deduplication. Legacy records may lack collection provenance and must remain labeled as such. The collection job links evidence to the assigned Agent and requester; the evidence detail response resolves these references without exposing the private storage key.

Search already supports case, job, agent, exact SHA-256, tags, review state, initial verification, subsequent integrity result, collection/creation dates, size bounds, and creation-order pagination. Text search is over filename, display title, and source path. It does **not** search original file contents or note bodies. Multiple tags are applied as combined requirements. SQL wildcard characters are escaped. Result totals come from authorized queries, not the currently loaded page.

### Case history and case lifecycle

Incident is the source of truth for cases: title, description, severity, status, creator/owner, creation/update timestamps, and revision. Current states are `open`, `investigating`, and `closed`; the implementation does not use the expanded lifecycle from older design proposals. Status is descriptive and does not automatically stop collection, revoke evidence access, or execute response actions.

CaseHistoryEvent records a case revision, event kind, actor attribution/label, UTC recording time, source, and bounded before/after values for title, description, status, and severity. A case save and its history insert share the same transaction. Compare-and-swap revision checks prevent stale writes. Even an unchanged-field save can produce a new revision with an empty change set; consumers must not invent a substantive change.

Revision 0007 backfills explicit migration baselines rather than reconstructing unknown earlier changes. Case history has ORM update/delete guards and SQLite triggers. It has no evidence-custody hash chain, no edit/delete API, and no universal database-change capture. Direct trusted SQL or application writes bypassing the case service are not automatically attributed case history. Database administrators remain trusted.

### Timeline

TimelineEvent is sufficient for the currently supported investigator observation workflow. It links to Incident and, for new investigator observations, one Evidence record. A composite foreign key preserves the evidence/case relationship. Legacy events can be unlinked.

Occurrence time is normalized to UTC; reported time preserves the supplied offset representation. Creation time records when the observation was stored. Source, optional source locator, actor ID/label, origin, submission ID, and request fingerprint preserve provenance. Source locators are investigator text, not validated parser coordinates. Client submission IDs plus payload fingerprints distinguish identical retries from conflicting reuse.

An observation and its custody append commit together. Existing endpoints do not edit or delete observations. ORM protection covers investigator events, but should not be confused with a database-wide immutable ledger. A future correction/supersession design must extend this model and its protections deliberately, not mutate existing events or create another timeline system.

### Collection metadata

Agent enrollment records name, platform, collector version, enrolling operator, credential digest, expiry, and active state. These labels are useful context, not hardware attestation, a host inventory, or proof that endpoint clocks are accurate.

CollectionJob preserves an approved JSON manifest of selected absolute paths, item IDs, and byte limits, plus incident, agent, requester, and status. The API derives completion from verified items; consumers must not rely solely on the persisted `open` value to decide whether acquisition finished.

The Windows collector validates selected regular files, rejects unsupported paths/reparse points, checks identity/size/modification changes during acquisition, stages bytes privately, hashes, uploads, and persists matching receipts for retries. This is live selected-file acquisition, not memory capture, disk imaging, or an atomic filesystem snapshot. Collection timestamps are not automatically filesystem creation/modification event times. Source-file checks are not equivalent to trustworthy endpoint attribution.

### Integrity and custody

Three independent concepts must remain visible:

1. **Initial upload verification:** the backend independently compares received byte count and SHA-256 with the submitted expectations. Matching hashes establish transfer consistency, not benignness, authenticity of the endpoint's claims, or completeness of an investigation.
2. **Subsequent integrity:** EvidenceIntegrityCheck contains expected/observed size and hash, status/result, timestamps, requester, and future execution/lease fields. No executor, worker, scheduling API, or user-triggered check workflow is implemented. Query code selects the latest terminal row by creation time/ID; it does not expose pending state. `not_checked` must not be displayed as a failed or passing check.
3. **Custody-chain consistency:** CustodyEvent includes sequence, operation ID, actor, time, event details, previous hash and event hash. Compare-and-swap updates to the evidence head coordinate appends in the caller's transaction. `verify_chain` exists as an internal read-only helper; the history endpoint displays records/head but does not promise that a chain verification was executed on each read. A locally stored head is not an independent trust anchor.

Upload currently commits Evidence without an initial CustodyEvent. The first annotation, note, timeline observation, or retrieval can establish a baseline. Preserve that historical boundary: an empty chain does not mean no acquisition happened, and no synthetic prior custody should be invented. Notes are append-only through application controls; tags are replaceable annotations with custody recording. Case changes do not create evidence custody entries.

### Retrieval

Explicit POST retrieval authorizes evidence, snapshots storage identity, releases the read transaction, opens a validated regular-file handle, and constructs a bounded private copy while recomputing SHA-256 and size. It then rechecks operator/evidence access and identity before committing the custody event and serving an attachment.

The reader accepts server-generated opaque blob names, rejects unsupported paths/links, and uses platform-specific safe opening. Originals are never executed or served as inline previews. Unsupported legacy storage keys fail safely. HTTP responses use attachment disposition, no-store, nosniff, no range/resume support, capacity limits, timeouts, and cleanup paths.

`evidence_retrieval_prepared` means a verified copy was prepared. It does not prove successful delivery or a saved local file. Retrieval does not change initial verification or create an EvidenceIntegrityCheck result. The frontend separately prepares, saves, cancels, or discards a copy, with bounded memory and object-URL cleanup. A future intelligence feature must not silently call this POST while rendering metadata.

## 2. APIs and frontend consumers

Existing `/api/v2/investigation` contracts:

- `GET /incidents`: owner-scoped search, status/severity filters, total, creation-ordered cursor page. `CaseList` and `CaseOverview` reuse it.
- `POST /incidents`, `GET/PATCH /incidents/{id}`: create/read/revision-safe change through `CaseForm` and `CaseWorkspace`.
- `GET /incidents/{id}/history`: revision-ordered history through `CaseHistory`, including explicit start-of-tracking metadata.
- `GET /evidence`, `GET /evidence/{id}`: search and metadata detail through `EvidenceSearch`/`EvidenceDetailsPage`.
- `PATCH /evidence/{id}/annotations`, `GET/POST /evidence/{id}/notes`: revision-aware annotation and attributed notes through `AnnotationsPanel`.
- `GET /evidence/{id}/custody`: sequence-based history through `CustodyHistory`.
- `POST /evidence/{id}/timeline-events`, `GET /timeline-events`, `GET /timeline-events/{id}`: observation submission/search/detail. Timeline search requires incident scope.
- `POST /evidence/{id}/download`: explicit verified-copy preparation through `EvidenceDownload`.

Version 1 separately provides operator agent enrollment/revocation, job creation/read/cancellation/evidence receipts, assigned-agent manifest/upload, and health. Legacy authentication/domain placeholder routes must not be mistaken for the implemented v2 workflows.

App uses hash routes for Overview, Cases, Evidence, Timeline, and the legacy sign-in screen. One investigation service closure owns the credential. Disconnect aborts pending requests and clears credential/data state; 401 resets the shared workspace. Tokens are not persisted in URLs, logs, storage, or build configuration.

Phase 5D overview makes eight bounded list requests for real counts and five newest cases. It is a live view, not a consistent multi-query snapshot or global activity feed. Existing case filters and scoped evidence/timeline views are reusable; no routing framework or service replacement is warranted.

## 3. Missing investigator workflows and reusable relationships

The highest-value gaps are navigation and explicit attribution, not an AI engine:

- A one-click pivot from evidence to other same-hash records, its collection batch, or its timeline. Existing filters support this; scope and labels must be preserved.
- A clearly scoped review queue using existing `review_state`, dates, and tags. Do not interpret `reviewed` as a conclusion or incident resolution.
- Better explanation of the agent/job context without requiring investigators to copy UUIDs into forms. Use existing metadata/manifest contracts with authorization; do not imply enrollment details are trusted host telemetry.
- Structured, durable findings or hypotheses with supporting/contradicting evidence citations are absent. Notes can record human narrative now, but they are not typed finding objects or a cross-evidence relationship model.
- Typed evidence-to-evidence relationships, confidence/rationale, correction/supersession links, consistent report snapshots and report export are absent.
- No full-text content/note search, extraction, IOC/entity normalization, threat-intelligence enrichment, or automatic correlation exists.
- No GUI agent enrollment/job wizard or acquisition-status management exists in the present investigation client.

Existing relationships can support a first metadata-only slice without new tables:

- `Incident.id -> Evidence.incident_id -> TimelineEvent.evidence_id`: scoped evidence observations.
- `Evidence.collection_job_id -> CollectionJob.agent_id/requested_by_id`: acquisition batch and enrolled collector context.
- `Evidence.sha256`: exact digest comparison across separately acquired records. Equal hashes are not proof of common origin or maliciousness; never merge records/custody based on equality.
- `EvidenceTag(evidence_id, tag)` and review state: investigator-defined organization, not a rules engine.
- Case revision/history, evidence metadata revision, custody sequence/hash, and timeline submission ID: distinct concurrency/provenance markers. They are not interchangeable global revision numbers.

Evidence continues to belong to one case. Any future many-to-many case sharing requires an explicit access/ownership/migration design. Do not introduce it incidentally through a correlation view.

## 4. Security and operational boundaries

1. Reuse `require_operator`, `require_incident`, and `require_evidence`. Evidence access requires both owned incident scope and matching job requester for collected evidence. Timeline must inherit evidence scope for linked records. Frontend hiding/filter locking is supplementary, never authorization.
2. Scope correlation queries **before** grouping/counting. A same-hash result, count, filename, or existence signal from an unauthorized case is an information leak. Default new pivots to the current case; broader owner-authorized search requires an explicit user choice.
3. Keep operator/device credentials separate. Agent access remains assigned-job-only, with expiry/revocation and active-owner checks. Operator rotation does not rotate existing agent credentials.
4. Original storage keys are private implementation details. Authorized acquisition source paths are useful but may contain personal or sensitive information. Do not expose them in public links, diagnostics, external prompts, or future reports without an explicit disclosure decision.
5. Preserve immutable originals, bounded uploads/retrieval, transactional custody and case history, optimistic revisions, and explicit retries. Do not create custody events simply because a metadata panel was opened.
6. HTML-like titles/notes/source text remain untrusted plain text. Future linkification must not turn source locators into executable links. Any later AI system must treat evidence text as untrusted data and never as instructions or permission.
7. Append-only protections differ: case history has SQLite triggers; custody/notes/investigator timeline also rely on application/ORM boundaries. Privileged database/file administrators can undermine local records. Do not advertise signatures, WORM guarantees, or externally anchored tamper resistance that do not exist.
8. Pagination binding validates query context, but its hash is not a secret authorization credential. Always reauthorize queries; pages/totals can change during live investigation.
9. Storage and SQL commits are not one atomic transaction. An interrupted upload may leave an unreferenced file between promotion and commit. No automatic orphan deletion/reconciliation is implemented. A retained staged receipt/copy must not be discarded during recovery.
10. Retrieval limits and upload slots are process-local. SQLite write contention, repeated aggregate requests, substring searches, latest-check subqueries, and long histories need measurement before enterprise-scale use. No global quota/coordinator is present. Private Windows directory ownership must match the server account; diagnose permissions without making evidence directories public.

These are design boundaries and operational limitations, not claims of a demonstrated exploit. No network penetration test or administrative tamper test was performed during this audit.

## 5. Minimal proposed Phase 6 roadmap

### Phase 6A — this audit

Deliver architecture inventory, gaps, boundaries, and the proposed sequence. Database stays at 0007. Stop for approval.

### Recommended Phase 6B — investigator-driven metadata pivots

Add explicit actions in evidence details for same-SHA-256 records within the case, records from the same job, and the evidence-linked case timeline. Add a case-scoped review queue entry using the existing review-state filter if useful. Reuse `service.search`, `timelineSearch`, and current components; retain filters in memory and immutable source records.

No backend endpoint or migration is expected. Do not fetch entire datasets to count them, infer relationships from partial pages, call retrieval implicitly, or persist a new relationship just because two records match. Show the criterion and scoped result count, with loading/error/empty/pagination states. Route/filter wiring should be small, backward-compatible frontend changes rather than a new workspace architecture.

Acceptance: pivots stay in the selected case; inaccessible records/counts never appear; clearing filters cannot widen a locked case; equal hashes leave distinct records and custody untouched; errors show unavailable rather than zero; requests are cancellable on disconnect; existing tests pass.

### Proposed Phase 6C — human findings and evidence relationships design gate

First decide whether existing notes/timeline citations suffice. If durable multi-evidence conclusions are actually required, design an additive finding record and scoped evidence references with actor, rationale, source IDs, revision, and explicit correction history. A finding is a human conclusion, not an event; do not make a second timeline table or repurpose custody as a findings feed.

This would require a separately approved schema/API design and migration only if persisted new concepts are necessary. Enforce same-case references initially. Do not overload CaseHistoryEvent's current one-event-per-case-revision contract or existing custody event meanings. The event/history policy must be reviewed before implementation.

### Proposed Phase 6D — explicit report preparation/export design gate

Define a user-requested, authorized report with stable source citations, generation time, case revision, evidence IDs/hashes, timeline provenance, and clear limitations. Distinguish a live view from an immutable snapshot. Decide privacy/redaction, consistency, size limits, and whether report records are needed before choosing dependencies or migrations. Never execute or embed original evidence as active content.

### Deferred technical tracks — not part of the minimal next implementation

Integrity-check execution needs a dedicated scope even though its table exists: request policy, authorization, bounded execution, failure recovery, and result/custody semantics. Timeline correction needs explicit supersession semantics while preserving old observations. Parsing, external enrichment, and AI require separate threat/privacy/citation and deployment reviews. They are not prerequisites for Phase 6B and are not approved by this audit.

The roadmap contains a future AI assistant intention, but Phase 6 numbering does not itself authorize AI. If later approved, summaries must cite permitted sources, distinguish observation from inference, and remain advisory. No autonomous evidence changes, custody edits, case closure, remote execution, or final security decisions.

## 6. Testing and recovery plan for future approved work

- API/service: current-case scoping, foreign evidence/job IDs, combined filters, exact hash semantics, server totals versus partial pages, pagination binding, null legacy provenance, and sanitized errors.
- Security: missing/invalid/revoked credentials, foreign incident/job requester, disconnect during loading, zero tokens in URLs/storage/logs, and no unauthorized aggregate disclosure.
- Browser: same-hash/job/timeline navigation, preserved selection and filters, explicit scope labels, empty/loading/error states, manual retry, mobile overflow, keyboard focus, long untrusted titles, and escaped text.
- Regression: full backend suite, frontend service tests, typecheck/build, all browser workflows, and Windows selected-file CLI upload/retry. Verify custody heads and original bytes remain unchanged after metadata-only reads.
- Concurrency: continue rejecting stale case/evidence revisions; retries must never silently duplicate mutations. New read-only pivots need cancellation and stale-response suppression, not transactional writes.
- Future migrations, if approved: backup first, populated upgrade preservation, foreign-key/integrity checks, rollback/forward-only recovery decision, and no fabricated legacy facts. No migration was needed or run in this audit.

## 7. Audit closure

Only `docs/phase6a-investigation-intelligence-audit.md` was created. No application, agent, test, configuration, dependency, migration, or database edits were made. No tests were required or run for this documentation-only task.

The database revision was read as **0007**. Before/after fingerprints were used to verify the inspected source/configuration/dependency set and development database remained unchanged. No evidence content was read.

Phase 6A audit complete. Awaiting approval before implementation.
