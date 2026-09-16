# ShadowVault AI Roadmap

## Phase 0 — Repository scaffold (complete)

- Top-level backend, frontend, agents, tests, and documentation directories.
- Project overview and initial ignore rules.

## Phase 1 — Foundation (implemented)

- FastAPI application factory and lifespan-managed database engine.
- Validated environment configuration and explicit CORS origins.
- SQLAlchemy declarative base and request-scoped sessions.
- User, Incident, Evidence, and TimelineEvent models with relationship constraints.
- Explicit, development-only table initializer.
- Authentication, incident, evidence, and timeline router placeholders.
- React + TypeScript dashboard shell, login view, and shared API client.
- Backend integration tests, frontend API-client tests, and TypeScript build checks.
- Dependency snapshots and local setup documentation.

Acceptance: install locally; bootstrap tables without creating accounts; run
liveness/readiness checks; open dashboard/login views; return explicit HTTP 501
for unimplemented domain operations; pass tests and frontend build.

Known limitations: no working sign-in or CRUD, no evidence storage/collection,
no schema migrations, no automated browser tests, and SQLite-only verification.
The Starlette test adapter emits an HTTPX deprecation warning; it currently passes.

## Phase 2 — Identity and incident workflows (planned)

The approved Phase 2A slice below is implemented first. Broader identity,
incident, and UI work remains unimplemented and requires further approval.

### Phase 2A — Secure selected-file collection (complete)

- Alembic baseline/adoption and Agent, CollectionJob, Evidence migrations.
- Trusted local API-operator provisioning and owned-incident setup.
- Operator-only agent registration and job creation; separate expiring device tokens.
- Assigned-agent-only, bounded streaming uploads with independent SHA-256 verification.
- Verified metadata, incident/job constraints, and duplicate/concurrent retry handling.
- Windows standard-library CLI with explicit file selection, private staging,
  pending retries, and durable verified receipts.
- Regression, migration, authorization, failure-cleanup, and real CLI integration tests.

See the [implementation guide](phase2a.md) and [completion report](phase2a-report.md).
No memory acquisition, remote execution, or AI analysis is included.

### Phase 2B-1 — implemented and verified

- Migration `0003`: Evidence extensions, CustodyEvent, EvidenceNote, EvidenceTag,
  and EvidenceIntegrityCheck structure.
- Operator-authorized investigation search, details, annotations, notes, and custody APIs.
- Transactional custody appends, optimistic metadata revisions, and populated migration verification.
- 62 Python tests and 5 frontend regression tests pass; frontend build passes.

See [the completion report](phase2b1-report.md). Integrity-check execution remains deferred.

### Phase 2B-2 — implemented and verified

- Investigation dashboard/search/details connected to the existing v2 API.
- In-memory operator connection, revision-aware notes/tags, custody history and
  distinct initial/subsequent integrity presentation.
- Shared agent core extracted while retaining Windows CLI compatibility.
- Browser workflows, service tests, backend regressions and Windows round-trip verified.

See [the completion report](phase2b2-report.md). The approved Phase 3A slice is below.

### Remaining identity and dashboard work — not started

- Decide deployment/database targets beyond the verified local SQLite pilot.
- Add secure account provisioning, password hashing, sign-in/session lifecycle,
  logout, and server-side authorization.
- Incident create/read/update, pagination and owner authorization are implemented
  in Phase 4A below; broader account and team access policy remains deferred.
- Extend the remaining incident and timeline UI beyond the implemented evidence workspace.

Acceptance: unauthenticated/unauthorized requests are rejected; users can access
only permitted incidents; authentication and authorization tests cover failures;
migrations work against the selected target database.

## Phase 3 — Extended evidence and timeline workflows

- Define isolated evidence storage, upload constraints, integrity verification,
  provenance, and append-only custody/audit records.
- Extend Phase 2A ingestion with authorized retrieval and timeline creation/querying.
- Define collector enrollment and authenticated communication for Windows/Linux.

Acceptance: evidence digest verification and custody records are tested; storage
paths cannot escape their intended location; event timestamps are normalized;
cross-incident access is prevented.

### Phase 3A — evidence-linked timeline observations (complete)

- Existing TimelineEvent extended through migration 0004; legacy records preserved.
- Three additive v2 APIs create/query/read investigator observations with ownership checks.
- Submission deduplication, UTC/reporting-time distinction and atomic custody appends.
- Timeline UI shares the existing in-memory operator client; no evidence analysis.
- 82 Python tests, 16 frontend service tests, 21 browser workflows and production build pass.

See [the guide](phase3a.md) and [completion report](phase3a-report.md).

### Phase 3B — authorized evidence retrieval (implemented)

One additive operator-only POST prepares and serves a size/SHA-256-verified copy,
with safe storage handles, transactional custody, and an explicit frontend save action.
Database remains at 0004; uploads, timeline and collectors are unchanged.
See [the guide](phase3b.md) and [completion report](phase3b-report.md).
Integrity workers, timeline correction/supersession, automatic extraction, preview,
malware/AI analysis, resumable downloads and Linux collection remain outside this slice.

## Later phases — Investigation capabilities (planned)

### Phase 4A — Case management (complete)

- Reuse Incident with a single revision column, preserving the 0004 upgrade path.
- Add operator-authorized owned-case list/detail/create/update APIs, explicit
  lifecycle transitions and atomic revision conflict detection.
- Add Cases navigation, search/list/create/detail/edit and scoped reuse of existing
  evidence, custody and timeline components, using in-memory operator credentials.
- Verify migration preservation, authorization, rollback, conflicts and prior suites.

See [the completion report](phase4a-report.md). Phase 4B investigator workspace
enhancements, Phase 4C evidence relationships and Phase 4D advanced timeline views
require separate approval and have not started.

- Detection engine and file analysis.
- Reports and incident export.
- AI investigation assistant with explicit evidence-access boundaries and citations.
- Deployment automation, operational monitoring, backups, and retention policies.

Scope and acceptance criteria for these phases will be defined before implementation.
