# Phase 7C — Architecture and Investigator Workflow Audit

Date: 2026-09-13. Documentation only. No implementation is authorized by this report.

## Executive assessment

ShadowVault AI now supports a useful investigator-driven loop: connect an operator, manage an owned case, collect selected Windows files, review authorized evidence, record notes/timeline/indicators, inspect corrections and separate histories, and prepare a source-cited metadata report draft. It remains a local investigation pilot, not a multi-user enterprise platform or an automated analysis system.

**The highest-value next capability is safe investigation continuity during same-case refresh and report replacement.** Concrete state-loss paths remain in the current UI: a case refresh/save unmounts the indicator and report components, while starting another report clears the last successful draft before the request succeeds. These paths can discard an unresolved write's retry identity or the investigator's only in-app report snapshot. They are more immediately evidenced than a need for AI, external feeds, workers or a persistent report repository.

**Proposed Phase 7D: same-case refresh safety and report draft replacement safety, using existing APIs and in-memory state.** Keep this narrowly scoped. Do not introduce cross-session recovery, an application-wide data cache, automatic writes, persistent reports or a new authentication model.

## Audit basis and limits

Reviewed current models, schemas, API route inventory, services and authorization predicates; application/session composition and migration inventory; Windows agent/shared core documentation and implementation boundaries; React routes, CaseWorkspace, report, indicator, annotation/timeline forms and resource-loading behavior; existing service/browser/backend test structure; Phase 7A audit and Phase 7B completion report, with earlier phase documentation as context.

Key source anchors:

- `backend/app/core/security.py`, `services/incidents.py`, `services/evidence_query.py`: operator, case owner and collection-requester boundaries.
- `services/{collection,storage,evidence_reader,evidence_retrieval,custody,evidence_metadata,timeline,case_history,indicators,case_intelligence,case_report}.py`: acquisition, observation, mutation and read responsibilities.
- `frontend/src/features/evidence/{InvestigationWorkspace,AnnotationsPanel,useResource,service}.tsx/.ts`, `features/cases/{CaseWorkspace,CaseReport,CaseForm}.tsx`, `features/indicators/CaseThreatIntelligence.tsx`, `features/timeline/TimelineEventForm.tsx`, and `App.tsx`: state lifetime and navigation.
- `tests/test_case_report.py`, `test_incidents.py`, `test_indicators.py`, collection/retrieval/migration tests, and `frontend/tests/browser/{case-report,indicator-workflow,cases,investigation,timeline,download}.spec.ts`: regression boundaries.

This was source inspection and read-only SQLite verification. No evidence contents, production API mutations, downloads, collector runs, tests, migrations or external services were invoked. Private evidence and old test directories were not opened or cleaned. Conclusions about state loss follow the component control flow; this audit did not reproduce them in a fresh browser session. No penetration test, performance benchmark or accessibility certification was performed.

The verified Phase 7B baseline is **152 backend tests, 44 frontend tests, 57 browser workflows passing**, successful TypeScript/build and Windows CLI upload/repeat. These are prior verification results, not newly executed Phase 7C tests.

## Current architecture and data ownership

```text
Provisioned operator -> React + TypeScript workspace -> in-memory bearer client
                                  |
                                  v
                         FastAPI /api/v2/investigation
                                  |
                    owner / evidence-requester authorization
                                  |
                       services -> SQLAlchemy -> SQLite 0008
                                  |
                    Incident (the only Case entity)
                      |-> revisioned case metadata + CaseHistoryEvent
                      |-> Evidence -> notes/tags/review state
                      |              |-> CustodyEvent chain
                      |              |-> TimelineEvent observation
                      |              |-> IndicatorObservation + successor
                      |              `-> integrity-check structure
                      `-> authorized metadata snapshot -> transient report

Operator -> v1 agent/job APIs -> assigned Windows collector
          -> selected files -> private spool/hash -> bounded upload
          -> private original blob + Evidence receipt

Explicit retrieval -> authorize -> secure reader -> verify private copy
                   -> reauthorize -> retrieval-prepared custody -> attachment
```

Incident ownership is `created_by_id`. There is no independently assigned investigator or team. Evidence belongs to exactly one Incident. For collected evidence, visibility additionally requires that its CollectionJob requester match the operator. Timeline and indicator queries inherit authorized evidence scope; legacy unlinked timeline records inherit case scope. Notes/tags/custody are children of evidence. Same hashes do not merge records or ownership.

CaseHistoryEvent describes case revisions, not all investigator actions. Custody describes tracked evidence actions. Indicator corrections describe appended observations. Timeline is the sole occurrence-time system. These are distinct records, not redundant audit engines. The report projects them into separate sections without creating another history or changing ownership.

The browser owns only transient credentials, filters, unfinished forms, pending submission identities, receipts and report snapshots. The server owns durable investigation records and source blobs. Collector staging/receipts are separate local acquisition state. Explicit text/evidence downloads become local copies outside subsequent server revocation.

## Complete investigator workflow and capability assessment

### 1. Connection and case lifecycle

Local provisioning supplies an operator identity and bearer token. The client keeps the token in a closure, sends it in Authorization headers, and aborts/clears on disconnect or 401. No password login/session/RBAC exists; the legacy sign-in screen and v1 auth routes remain placeholders.

Cases support creation, owner-scoped list/search, status/severity filters, details and revision-safe updates. States are `open`, `investigating`, `closed`; transitions are open to investigating, investigating to closed, and explicit reopening to investigating. Same-state saves are allowed. There is no assignment, containment action, SLA, archival or deletion workflow. Closing is descriptive and does not cancel collection, prevent notes or revoke access. Do not infer an operational response from the status label.

### 2. Collection and evidence lifecycle

Operator APIs register/revoke agents and create/read/cancel jobs; the Windows CLI is invoked explicitly against approved selected files. Shared core handles configuration, hashing and transport. Private staging and matching receipts support retry; the backend independently checks byte count/SHA-256, enforces limits and prevents duplicate job/item records. No memory acquisition, remote execution, Linux collector or automatic task polling exists.

Evidence has immutable acquisition identity in the supported workflow and separately revisioned investigation metadata. Search, title/review/tags, appended notes and explicit verified-copy retrieval are available. A GUI acquisition/job wizard is absent; investigators still coordinate terminal/API steps. This is a meaningful onboarding gap, but collection itself is implemented and independently tested. Live selected-file collection is not disk imaging, endpoint attestation or a filesystem snapshot.

### 3. Custody and integrity

Custody appends coordinate sequence/head changes in the caller's transaction with SHA-256 chaining. Upload itself does not create a custody event; the first tracked annotation, note, timeline action or retrieval establishes a labeled baseline. Reports and indicator writes deliberately do not create custody. Do not manufacture earlier custody to make a display look complete.

Upload verification, subsequent integrity results, chain consistency and retrieval-copy verification remain separate claims. EvidenceIntegrityCheck has a schema but no executor; `not_checked` is not a pass/failure. The internal chain verifier is not automatically invoked by history/report reads. Retrieval recomputes hash/size and records preparation, not delivery. Local heads and records are not externally anchored signatures/WORM guarantees.

### 4. Timeline and case history

Investigators append evidence-linked TimelineEvent records with actor, occurrence time, reported offset, recording time and source locator. Cursor filters and details are available. New observation retries use submission identity; no edit/delete or correction/supersession workflow exists for timeline observations. Legacy unlinked rows remain distinct. A source locator is reported text, not a parsed coordinate verified by the system.

Case metadata updates and corresponding CaseHistoryEvent append commit atomically under revision compare-and-swap. Migration baselines explicitly mark tracking start. There is no reconstruction of earlier changes or universal activity audit. Case history and indicators have SQLite update/delete triggers as well as ORM controls; other immutable workflows rely on application/ORM restrictions and trusted database administration. Case history is not evidence custody and should not absorb unrelated operations.

### 5. Indicators and corrections

Manual SHA-256, IP, ASCII domain and filename observations must link to authorized evidence. The backend can promote an existing evidence hash/filename, normalizes supported values and records attribution. There is no extraction, DNS resolution, enrichment, maliciousness classification or global intelligence catalog.

Case lists expose existing exact kind/value/evidence filters and bounded observation lookup. Correction successors are resolved outside the loaded page/value filter but within authorized source scope. The original remains visible. Explicit receipts, conflicts, validation errors and unchanged manual retries are implemented. A null successor describes that response, not permanent correctness. No withdrawal disposition, cross-evidence finding or automatic timeline linkage exists.

### 6. Investigation intelligence and reports

The command center uses real bounded case list totals; independent requests are a live view, not one database snapshot. Case intelligence counts authorized evidence/timeline/history; its latest activity excludes indicator creation and report preparation. The UI documents included categories. It must not silently become an all-activity feed or threat score.

Phase 7B adds a complete authorized **projection** of case metadata, evidence, notes, timeline, indicators/corrections, custody metadata and history. It explicitly establishes a SQLite read snapshot, bounds rows/bytes/time, rechecks authorization and returns a transient DTO. It never reads original files or records custody. The UI supplies visible source IDs, expandable sections and explicit inert-text saving.

The report is not every database field or all historical integrity attempts. Private paths/storage keys and custody detail payloads are excluded. Free text may still contain sensitive information. There is no durable report ID, server-side version/retrieval, review approval or authored conclusion. Export supplies a usable handoff already; inability to reload a previous server report is an intentional persistence boundary, not proof a new table is immediately necessary.

### 7. Search, navigation and usability

Case and evidence filters/pagination are server-backed. Evidence text search covers metadata, not contents or note bodies. Indicator filtering is exact, not full-text threat search. Case scope remains fixed in embedded workspaces. Existing case/evidence links reduce UUID entry, but fallback UUID fields and technical timestamps remain demanding for less experienced investigators.

Report/indicator source links retain case context. Some timeline links switch to standalone routes, which can discard the CaseWorkspace. Long panels before the evidence section increase scrolling. Native controls, wrapping, focus targets and mobile tests exist; raw UUID citations/field-oriented reports still need usability feedback. Do not replace the routing framework or add another dashboard to solve these issues.

## Most important remaining gap: continuity under refresh and failure

Three source-supported paths explain the recommendation:

1. `CaseWorkspace` renders its panels only when `!state.loading && !state.error`. `useResource` replaces data with loading state on a new load. `Refresh case` and a successful case save change the load attempt, unmounting `CaseThreatIntelligence` and `CaseReport`. Their pending payload/submission ID, receipt and report state can be lost even though the operator remains in the same case.
2. `CaseReport.create()` calls `setDraft(undefined)` before awaiting the next report. A timeout, limit refusal or cancellation can therefore erase a successful previous snapshot without a replacement. The old text file, if saved, survives externally, but the in-app draft does not.
3. Timeline and annotation state is also component-local. Timeline explicitly warns that leaving details discards its retry ID; annotations preserve drafts while mounted and block after uncertainty. Navigation out of the case/detail remains a risk and a future follow-up. Phase 7D should not claim universal cross-route recovery merely by fixing same-case panels.

Existing tests prove indicator identity survives source navigation and report opening/closing. They do not establish survival across a whole-case refresh/save. Those successful tests and these remaining gaps are compatible. No production data loss or duplicate write was demonstrated in this audit; loss of a retry identity creates a plausible duplicate-submission risk when a user starts a replacement after an uncertain success.

## Security, technical and operational risks

- **Authorization:** retain `require_operator`, owner-scoped case reads, evidence requester scope and authorized timeline/indicator/report queries. Counts and references can leak data just as content can. A retained UI snapshot is not fresh authorization. Clear retained state on authentication/access denial and never display another case's memory.
- **Credential boundary:** no token in URLs, local/session storage, report text, logs or build variables. Device tokens are separately expiring/revocable; operator rotation is not global agent revocation. One configured operator is not multi-user authentication.
- **Untrusted text:** filenames, descriptions, notes, source locators and indicators remain inert. Field exclusion is not free-text redaction. Downloaded copies cannot be recalled. AI or external disclosure would require a separate destination/privacy decision.
- **Staleness/concurrency:** case revision, evidence metadata revision, custody head and indicator submission identity are not one global version. Preserving a form must never silently advance its expected revision or change a pending payload. The report snapshot cannot be labeled current after later mutations.
- **Scalability:** SQLite writer contention, substring searches, repeated aggregates and large histories need measurement. Report limits are 2,000 rows including tags, 2 MiB and a five-second preparation deadline; refusal is safer than silent incompleteness. It materializes data before the final byte check, so the byte limit is not a strict process-memory ceiling. Report calls have no dedicated concurrency semaphore; repeated authorized requests still consume workers and memory.
- **Small duplication:** report preparation bounds/loads tags and then reuses evidence summaries that query tags again. This is bounded redundant work, not a second domain system; optimize only after measurement, preserving projection/authorization semantics. Do not merge custody, timeline and case history to reduce code count.
- **Storage recovery:** filesystem promotion and database commit cannot be one atomic transaction. Process crashes can leave orphaned private files; staging can also retain incomplete acquisition artifacts. No automated cleanup is warranted without retention/reconciliation rules. Upload/retrieval capacity is process-local.
- **Deployment:** local tests and explicit CORS do not establish safe remote deployment. TLS/host controls, storage ACLs, disk encryption, tested database-plus-evidence restore, retention and service monitoring need an operational acceptance process. An existing backup is not evidence of a complete restore drill.
- **Test operations:** browser fixtures use dedicated ports/databases. Phase 7B exposed shared-fixture custody assumptions and Windows teardown/ACL cleanup issues; dedicated fixture isolation resolved verification. Protected leftover test directories are documented, not production evidence. Do not weaken ACLs to clean them.
- **Documentation:** README/roadmap/architecture status sections lag later completed work. They can mislead setup and feature expectations. Current code and completion reports are the baseline; stale phase labels are not approval for deferred implementation.

## Deferred-feature assessment

**AI — not justified for Phase 7D.** The observed gap concerns state lifetime and recovery, which AI cannot resolve. Future advisory analysis needs an explicit question, authorized context selection, evaluation/citations, destination policy and prompt-injection controls. The application name does not establish that need.

**Automation — not justified.** Collection, writes, retries, retrieval and reports are intentionally explicit. Automatic retry/closure/interpretation would weaken current human control rather than address continuity.

**Background workers — not justified by current evidence.** The integrity-check schema's lease fields are preparation, not a running job requirement. Introduce jobs only after measured long-running work and approved cancellation, ownership, recovery and resource policies. Report limit refusal alone does not authorize bypassing the bound through a queue.

**Teams/RBAC — not justified for this local single-operator workflow.** A demonstrated need for independently authenticated collaborators would justify a separate identity/access design. Adding role labels without that model would be misleading and dangerous.

**Case assignment — not independently justified.** Ownership is currently authorization, not workload assignment. Changing `created_by_id` to assign a case could break historical attribution and collection-requester visibility. A future assignee must be a separately designed concept with evidence access rules; do not introduce ownership transfer as a shortcut.

**Persistent reports — plausible later, not the next prerequisite.** Justified if users require reopening exactly the reviewed snapshot across sessions, retained approval/version identity or a formal report inventory. Current explicit text export already supports a basic handoff. Persistence requires immutable snapshot/version design, retention, current authorization over historical copied data, and retry identity. Case ownership alone must not expose evidence that was visible when a report was saved but is no longer visible. Do not persist client-submitted arbitrary report JSON as trusted source facts. A schema change would require separate approval and backup/upgrade tests.

**External threat intelligence — not justified.** No approved provider, disclosure policy or enrichment task exists. Candidate indicators are not permission to transmit case metadata or contact suspicious domains. Any later integration needs provenance, freshness/error semantics, quotas and human review.

**Other deferred work:** an acquisition wizard, timeline correction, investigator-authored multi-evidence findings, integrity-check execution and durable report review are legitimate candidate design tracks. None is proven necessary to fix the current continuity defect. Persistent findings would need explicit author/citations/correction semantics, not repurposed notes or a new timeline. Remote or multi-user deployment would change the priority toward operational/identity readiness; this recommendation assumes the present local pilot.

## Proposed Phase 7D: minimal implementation boundary

Deliver **same-case refresh safety and report replacement safety**, not general persistence.

1. Keep the indicator pending payload/submission ID and last receipt, plus the completed report snapshot, scoped to the same authenticated CaseWorkspace while refreshing case metadata or after a case save. Use stable component lifetime or narrowly lifted state; no external state library or cross-case cache.
2. Separate initial case loading from refresh state. Retained content must not flash for another case. While access is being revalidated, make retained private panels unavailable for interaction. On 401/disconnect clear the workspace immediately; on definitive case/access denial clear its retained state. Preserve current server-side write authorization in all cases. Do not globally change `useResource` consumers just to support one workspace.
3. Preserve the existing completed report while a replacement is pending. Replace it only after a successful, matching-case/version response. On cancellation or transient/limit failure, explicitly distinguish the previous timestamped snapshot from the failed new attempt; never show a false new success. Access denial must clear private report state, not preserve it as a successful offline cache.
4. Keep manual writes manual. Retained indicator retries must send the original payload/ID unchanged. Case/evidence forms must still require review of conflicts and must not silently acquire a new expected revision. Do not preserve or replay a cancelled write as background work.
5. Provide clear refresh/error/previous-snapshot labels and keyboard focus. Retaining data in memory is not permission to display it after reconnect. Leaving the case, disconnecting and tab reload remain explicit clearing boundaries; document them. Broader timeline-route/draft navigation recovery is outside this first slice.

### Impact and expected file surface

**Backend/API:** no new endpoint or contract change expected. Existing case detail, history, evidence, indicator and report reads suffice. If distinguishing a definitive HTTP error is necessary, preserve the existing ApiError status in a local frontend loader; do not create a backend access probe or weaken error sanitization.

**Frontend:** primarily `frontend/src/features/cases/CaseWorkspace.tsx` and `CaseReport.tsx`. `CaseThreatIntelligence.tsx` may need narrow state/callback changes if stable mounting alone is insufficient. Prefer case-local loading state over changing shared `useResource.ts`; shared client/security and App routing should remain unchanged unless an individually demonstrated requirement arises. Add focused service/browser regressions in the existing test structure. No site or layout replacement.

**Database:** remain at **0008**. No table, field or migration is required for same-session state lifetime. Existing Incident IDs, relationships, case history, indicator observations, custody and blobs remain untouched. No database backup operation is needed for a frontend-only change; any later persistence proposal is a separate migration gate.

**Agents/dependencies:** none. Preserve Windows CLI, staging/receipts, upload/retrieval, framework versions and authentication.

## Testing requirements and acceptance for proposed work

- Create an uncertain indicator submission, refresh the case, then explicitly retry: assert byte-equivalent payload and identical submission ID, with no automatic POST. Repeat after a successful case metadata save and a failed refresh.
- Preserve a successful indicator receipt through same-case refresh without presenting it as current correction status. Keep original/correction API behavior unchanged.
- Create report A, attempt B with 503/413/cancellation: retain A only as the previous snapshot under the approved access state, with its original generation time. On successful B, replace A once. A delayed cancelled response must not replace a newer snapshot.
- Case switch, nonexistent/foreign case, 401, definitive denial and disconnect must clear private state and abort requests. Reconnect must not restore another operator's drafts. Exercise mismatched report case/version and stale responses.
- Verify case/evidence CAS conflicts still require explicit reload/review; no hidden write, custody append, timeline event, history event or report regeneration on render/refresh.
- Preserve source links, filters, current-case scope and existing report/indicator opening behavior. Test focus, disabled/inert refresh controls, screen-reader status labels and representative narrow layouts.
- Full backend, frontend services, browser workflows, TypeScript/build and Windows collector/upload regressions before completion. Use dedicated fixture evidence so annotation/retrieval/timeline baseline assertions remain independent. Check database revision/integrity/foreign keys without altering the development database.

Acceptance is a demonstrated absence of same-case refresh/replacement state loss, correct denial/clearing behavior and unchanged API/mutation semantics. It is not durable recovery across browser crashes, authentication loss or navigation outside the case. Existing 152/44/57 counts are a baseline, not predetermined future test totals.

## Risks and rollback strategy

Retaining state can accidentally extend sensitive-data lifetime, leave an old form enabled, merge cases, accept stale responses or imply freshness. Bound it by case ID and authenticated workspace generation; clear on access loss; label snapshot age; suppress obsolete responses. Prefer a small local change whose lifecycle tests make those boundaries explicit.

If the approach requires persistent browser storage, new authentication, a report table or a broad routing/state rewrite, stop and re-scope rather than treating it as routine implementation. Revert only the approved frontend change set to the Phase 7B behavior if regression checks fail. No database downgrade, original evidence rollback, custody/history removal or migration is involved. Warn that rollback/reload itself clears transient state; resolve pending writes before an operator-initiated deployment reload where possible, without blocking urgent disconnect.

## Audit verification and conclusion

Read-only SQLite inspection returned **0008**, `integrity_check = ok`, and **0 foreign-key violations**. The database SHA-256 remains `8f8e520eb9e23d2354652990d114fcb5895f7f1b5e293f0135299f279acde969`. The live schema's update/delete triggers protect case history and indicators; no Report table or new migration exists.

Only `docs/phase7c-architecture-audit.md` was created. Before/after fingerprints verify application/agent/test sources, configuration/dependencies, migrations, existing documentation and the development database were unchanged. No tests were required or executed for this documentation-only audit. No Phase 7D implementation was performed, and no deferred feature was implemented.

Phase 7C Architecture Audit complete — awaiting approval before implementation.
