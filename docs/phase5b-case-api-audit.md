# Phase 5B — Case API Foundation architecture audit

Date: 2026-09-08. Post-Phase 5A, database **0006**. Documentation only.

## Decision

**No new endpoint or schema field is required for the current Case Workspace.**
Incident already is Case, its CRUD is implemented, and Phase 5A exposed updated_at.
Reuse `/api/v2/investigation/incidents`; do not add duplicate `/cases` routes or a
new Case table. A Phase 5B implementation should not invent work to fill a phase:
any further operation needs a concrete approved consumer requirement.

Optional presentation improvements (showing updated_at or exposing the existing
severity filter in the UI) require no backend expansion. Case history is a separate
future capability, not data obtainable by interpreting updated_at or custody.

## 1. Current API analysis

Primary sources: [routes](../backend/app/api/routes/investigation_incidents.py),
[schemas](../backend/app/schemas/incident.py),
[service](../backend/app/services/incidents.py),
[security](../backend/app/core/security.py),
[CaseWorkspace](../frontend/src/features/cases/CaseWorkspace.tsx),
[CaseForm](../frontend/src/features/cases/CaseForm.tsx),
[CaseList](../frontend/src/features/cases/CaseList.tsx) and
[client contracts](../frontend/src/features/cases/contracts.ts).

- `GET /api/v2/investigation/incidents`: owned records, text/status/severity filters,
  exact authorized total and cursor pagination. Order is created_at descending then
  UUID descending, not updated_at. Reads never write timestamps or custody.
- `GET /api/v2/investigation/incidents/{id}`: one owned case, including nullable
  updated_at. Inaccessible and absent IDs both return 404.
- `POST /api/v2/investigation/incidents`: creates an owned open case; returns 201
  with the complete record. New ORM creation initializes updated_at = created_at.
- `PATCH /api/v2/investigation/incidents/{id}`: revision-safe metadata/status change;
  returns 200 with the committed result. updated_at is written atomically with the
  conditional revision update.

The separate legacy `/api/v1/incidents` GET placeholders remain 501. Preserve them;
they are not missing v2 functionality to implement again. The route owns commit/
rollback, while the service handles authorization, transitions and conditional SQL.
Do not move storage reads or hidden commits into case queries.

Current lifecycle: open → investigating → closed; closed → investigating; same-state
edits allowed. Status does not cancel jobs or block evidence/timeline/retrieval.
The six-state lifecycle in Phase 4C remains deferred, not silently mapped to these enums.

## 2. Required case operations and frontend needs

Existing operations cover list, search, create, details, metadata edit, status change
and refresh after conflict. CaseList uses text/status filtering and cursor navigation;
the API already supports severity although the list UI does not expose it. CaseForm
submits the current revision and full editable fields. It blocks resubmission after
uncertain failure and provides explicit reload/discard actions.

CaseWorkspace loads case details, locks parent incident filters for EvidenceSearch
and TimelinePanel, and embeds existing evidence details including annotations,
custody and retrieval. It does not require embedded evidence arrays, aggregate case
counts or a combined case/evidence/timeline response. Such aggregation could expose
records that satisfy case ownership but fail evidence authorization.

Minimal expansion decision:

- Retain the four existing operations and current DTOs.
- If requested, display updated_at in the UI; null/absent means unknown/unavailable,
  never substitute created_at as a claimed last-edit time. Current optional frontend
  type supports older servers. No new backend contract is needed.
- Defer history, delete/archive, assignment, membership, multi-case links, bulk edits,
  export and transition-capability endpoints. None is required by the current UI.
- Do not add an unaudited Case History GET that returns a fabricated empty success
  or rebrands custody. Implement it only with its separately approved persistence.

## 3. Request/response schema proposal

The minimal proposal is to formalize and preserve the implemented schema.

**Create request:** title required, trimmed length 1–200; description optional,
default empty, maximum 10,000; severity optional, default medium, enum
low/medium/high/critical. Reject NUL in title/description and unknown fields.
Clients cannot set status on creation, owner, creator, ID, timestamps or revision.

```json
{"title":"Endpoint investigation","description":"Reported activity","severity":"high"}
```

**Update request:** title, status and expected_revision required. expected_revision
is a strict nonnegative integer (booleans rejected). Description and severity may
be omitted and then retain their stored values; explicit null is not a clearing
operation. Empty description is allowed. Preserve this existing PATCH contract
rather than changing required fields under a familiar route.

```json
{"title":"Endpoint investigation","status":"investigating","expected_revision":0}
```

**Record response:** id UUID, title, description, status, severity, created_by_id UUID,
created_at UTC timestamp, updated_at UTC timestamp or null, revision integer.
updated_at is present on the current server; older client/server compatibility can
treat its absence as unknown. Retain original IDs and creator attribution. No storage
key, token, evidence contents, role assertion or invented owner object is added.

**List request:** optional q length 1–200 after trimming, status, severity, limit
1–100 default 50, cursor bounded to 1024 characters. The client omits empty filters;
an explicitly empty q is invalid. Text wildcard characters are escaped literally.
**List response:** items of the record shape, total of authorized matching cases,
next_cursor string or null. UUID is the tie-breaker. Pagination is a live view,
not a snapshot; records can enter/leave the filter between requests.

**Errors:** retain 401 invalid/inactive operator; 404 inaccessible/absent case;
422 invalid input, cursor or lifecycle transition; 409 stale/concurrent update;
sanitized 503 for database write failure. Error bodies must not be repurposed to
echo submitted credentials or sensitive record contents. No new error envelope,
ETag or If-Match requirement is needed for current clients.

Future history contract, only after separate history implementation approval:
`GET /api/v2/investigation/incidents/{id}/history` with bounded after_sequence/limit;
items, tracking_started, head_sequence and next_sequence. Events require authentic
actor attribution, server recording time and bounded change data. No history update/
delete route. Its request and storage design is outside this minimal API foundation.

## 4. Revision and timestamp strategy

Authorize case first, compare expected_revision, validate lifecycle, then issue the
existing conditional UPDATE with id + creator/owner + revision. Advance revision once
and set server updated_at within that statement. A zero row count is a 409; a failed
commit rolls back timestamp and fields. Reload the result before returning it.
Keep created_at fixed. Same-value accepted PATCH operations continue advancing revision.

Do not replace revision with timestamps: timestamps may repeat or move backwards,
and historical updated_at is null. No blind merge or last-writer-wins overwrite.
The browser preserves drafts on conflict/uncertain failure, reloads explicitly and
does not auto-retry writes. POST has no idempotency key: after uncertain creation,
review the list before a manual retry. Durable create deduplication would require
separate semantics/persistence approval, not an in-memory cache disguised as a guarantee.

Evidence.metadata_revision, Incident.revision and custody_sequence are independent.
A case edit must not increment evidence metadata revision or custody sequence. Future
CaseHistory must append in the case transaction and use its own sequence; revision
is not a reconstruction of all management activity.

## 5. Security considerations

- **Identity:** existing configured operator digest resolves one active user. There
  is no implemented RBAC, individual browser session or team principal. A device
  credential cannot call case APIs. Shared operator tokens do not provide distinct
  human attribution. Do not invent Admin permissions from token possession.
- **Object scope:** enforce authorization on lists, counts, direct IDs and writes;
  UI hiding is not access control. Keep uniform absent/inaccessible 404 behavior.
- **Input authority:** request allowlists prevent ownership and timestamp spoofing.
  Preserve strict revision and enum validation. Do not accept creator or grants as
  writable convenience fields in a future Case DTO.
- **Credential lifetime:** reuse the shared in-memory client, Authorization header,
  disconnect/401 clearing and abort behavior. Never put tokens in URLs, browser
  storage, build variables or logs. In-memory storage does not defeat same-origin XSS.
- **Cursors:** current query binding hashes actor/filter context; it is not a secret
  signature. Treat cursors as validated positions, not permissions or authentication.
  SQL authorization must always apply even to a forged but syntactically valid cursor.
- **Caching:** browser requests use no-store; sensitive JSON API responses do not
  themselves establish a universal server-side no-store policy. Explicit response
  cache hardening is a separate potential approval item, not a new Case operation.
- **Scale:** exact totals and wildcard search can become expensive; keyset pagination
  does not eliminate count costs. No need to change ordering/indexes without measured
  requirements. Current verified deployment remains local SQLite/Windows.

These are source-level findings and boundaries, not claims of a demonstrated exploit.

## 6. Evidence, timeline, custody and retrieval boundaries

[Evidence authorization](../backend/app/services/evidence_query.py) requires Incident
ownership plus CollectionJob requester ownership for collected evidence. A case owner
must not receive a broader shortcut through new nested case routes. Use existing
evidence search with incident_id, followed by ordinary evidence authorization.
An evidence record belongs to one Incident; preserve composite job/incident and
timeline/evidence constraints. No reparenting or cross-case evidence grant is proposed.

[Timeline authorization](../backend/app/services/timeline.py) filters by Incident and
applies evidence access for linked observations. Legacy unlinked events remain
distinguishable. New observations keep human provenance, UTC/source timestamp
distinctions, duplicate-submission handling and atomic custody recording.

Custody is per-evidence application history, not case management history. Case GET/
PATCH must not append baseline or custody events or rewrite existing chains. Existing
custody GET returns stored history/head metadata, not an externally anchored integrity
certificate. Keep append-only semantics and the administrator trust boundary explicit.

[Retrieval](../backend/app/services/evidence_retrieval.py) rechecks authorization and
evidence identity after private verified-copy preparation, commits custody, then
serves bytes. Keep byte/time/capacity limits and cleanup. Do not turn a case details
link into a public download URL or imply preparation proves delivery. No parsing,
preview, analysis or original-byte modification is part of this design.

## 7. Future teams/RBAC compatibility and approval gates

Retain UUID identity and created_by_id attribution. Future assignment and membership
must use separate approved fields/grants; changing creator IDs would corrupt both
provenance and present authorization. A future policy interface should evaluate
principal + action + resource + organization context and current grant version.
Do not implement it as an unused abstraction in this phase.

Before enabling shared access, define matching policies for case, job requester,
agent assignment, evidence, notes, timeline, retrieval and reports together. A role
or team label is not sufficient to relax one owner check. Recheck grant revocation
before releasing prepared bytes; client-side capability hints are never authoritative.
Membership changes require attributable history, and authentication integration
requires separate approval. No migration is needed for the current API conclusion.

Recommended next decision: approve either documentation/consumer refinements using
the existing contract, or move to the separately scoped Case History design. Do not
create duplicate CRUD just because this phase is named Case API Foundation.

Any later implementation must retain negative owner/device tests, CAS/rollback and
timestamp tests, old-client null/absent field behavior, literal filter/cursor handling,
and evidence/timeline/custody/retrieval/Windows collection regressions. New role or
history operations need additional tests when authorized; none is implemented here.

## 8. Frontend integration requirements

Continuation review confirmed the existing implementation still matches this audit:
CaseForm submits title/status/expected_revision for updates; CaseWorkspace reloads
the case after a successful save and embeds the existing investigation components.
No backend operation required by these consumers is missing.

Preserve the integration chain:
`CaseList / CaseWorkspace / CaseForm → shared InvestigationService → existing v2 incidents routes`.
The shared client remains responsible for credential lifetime, request cancellation
and sanitized errors. Do not create a separate case-specific credential store.

For any separately approved presentation refinement:

- Render updated_at only as a last accepted case update time; show unknown for
  null/absent values. Keep created_at separately labeled and revision as the save token.
- A severity filter can use the existing query field. Reset cursor/page history
  when filters change; preserve server ordering and actor/filter-bound cursors.
- Keep title/status in PATCH requests, even for an edit focused on another field;
  do not assume every field is optional because the HTTP method is PATCH.
- Preserve explicit conflict reload/discard, drafts on failed writes, and list review
  after uncertain creation. Do not automatically resend writes with a new revision.
- Retain case-scoped parent filters and the evidence-details case mismatch check.
  Existing global timeline detail links may remain; no second timeline view model
  or case-level custody substitute is needed.
- Preserve disconnect/reload/401 clearing, stale-response suppression, keyboard
  navigation and mobile layout. UI visibility never grants backend access.

No frontend implementation or new screen is authorized by this audit.

## 9. Minimal Phase 5B implementation roadmap — proposal only

1. **Contract baseline:** retain the four implemented Incident-as-Case operations,
   current DTOs and 0006 schema. The audit outcome is zero required backend API
   expansion. Do not schedule duplicate CRUD or an unused policy abstraction.
2. **Optional consumer refinement, only if approved:** expose the existing severity
   filter and/or display updated_at in the existing case view. These are frontend
   changes using existing contracts, not reasons for a new endpoint or migration.
   Without a requested refinement, no implementation step is necessary.
3. **Focused verification when implementation is authorized:** test the approved
   UI change with null/absent/current timestamps or filter/cursor reset behavior as
   applicable. Retain backend authorization/revision tests and run existing frontend,
   typecheck/build and browser suites. Preserve upload, collector, timeline, custody
   and retrieval regressions. This documentation continuation runs none of them.
4. **Close the slice:** report actual changed files and results. Case history belongs
   to a separately approved phase; teams/RBAC, six-state adoption, exports and AI
   remain out of scope. Discovery of a genuinely missing operation requires a
   concrete consumer use case and contract review before expanding scope.

Acceptance for any later Phase 5B slice: Incident remains the source of truth, old
clients continue to work, no evidence access is widened, case writes retain CAS,
and no evidence/timeline/custody/retrieval behavior changes. This roadmap grants no
implementation approval.

## Continuation completion and verification

The existing document was read before editing. Sections 1–7 already completed the
current API, operations, schema, concurrency, authentication/authorization, evidence,
timeline/custody and future teams/RBAC analysis. Frontend requirements were present
in section 2 but dispersed; an explicit integration checklist and stepwise Phase 5B
roadmap were the remaining documentation gaps. Sections 8–9 fill those gaps without
replacing the prior analysis or changing its recommendation.

Only `docs/phase5b-case-api-audit.md` was updated in this continuation. Database queried read-only before and
after writing the document remains **0006**, with identical file hash. Source,
configuration, dependency and other documentation fingerprints remain unchanged. No migration, dependency,
application code, database record, test run or build was added/performed.

The prior Phase 5A results were 118 backend, 29 service and 31 browser tests passing,
plus typecheck/build; this audit does not claim a new execution of those suites.
Stop after this report; implementation requires separate approval.
