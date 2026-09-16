# ShadowVault AI architecture

Current implementation through Phase8B; schema **0008**. Phase8C preparation changes documentation/fixtures only. Historical phase reports retain their original scope.

## Components and boundaries

The [README diagram](../README.md#architecture) maps both API versions and the optional AI boundary. FastAPI composes request-scoped SQLAlchemy sessions, body/privacy middleware and lifespan-owned admission controls. SQLite foreign keys are enabled. Writes commit explicitly and failures roll back. Startup never migrates tables.

React uses owner-authorized investigation APIs under `/api/v2/investigation`. Operator/device acquisition lives under `/api/v1`; old domain/authentication placeholders remain501. The existing bearer-token UI works without a password/session endpoint.

## Data model

- **Incident is Case:** creating-user ownership, open/investigating/closed lifecycle, revisions, server timestamps and atomic case history. No separate Case table.
- **Evidence:** incident scope plus collection-requester authorization where applicable. Acquisition facts/storage identity are separate from notes/tags and review metadata.
- **TimelineEvent:** the only timeline system; authorized evidence-linked investigator observations with occurrence/recording times and provenance. Legacy records remain distinguishable.
- **CustodyEvent:** attributed evidence operations with sequence/head concurrency checks and hash chaining. Not case history or an externally anchored ledger.
- **CaseHistoryEvent:** append-only case changes committed with the mutation, SQLite guards and legacy baseline disclosure.
- **IndicatorObservation:** evidence-linked hash/IP/domain/filename observations and corrections. No verdicts or enrichment.
- **Reports and briefings:** transient snapshots, not persisted case entities.

## Acquisition and retrieval

The operator approves exact selected paths and byte limits in a collection job. The Windows CLI stages privately, hashes and uploads only approved selected files. The backend verifies bytes, rechecks device/job access and supports identical retries through job/item uniqueness. Storage uses opaque generated keys. No uploaded evidence is executed or analyzed.

Explicit retrieval validates regular-file handles and link/reparse boundaries, verifies a temporary copy, reauthorizes and commits custody before serving an attachment. The event proves preparation, not receipt/save. No resumable downloads or background integrity execution exists. Filesystem/database operations cannot form one atomic transaction; crash orphans require conservative review.

Custody can begin at first annotation/retrieval and is not a fabricated full acquisition history. Administrators remain trusted; a hash chain anchored in the same database cannot prevent privileged rewriting. Host ACLs, encryption, backups and retention are operational controls.

## Authentication and frontend state

Operator tokens are compared against a configured digest for an active user. Agents have separate expiring/revocable credentials. Server services enforce ownership; UUIDs and frontend routes do not grant permission.

The investigation client holds the token in a closure, omits cookies, rejects redirects and avoids caching. Disconnect/401 abort pending requests. No token enters application browser storage or URLs.

Case-keyed panels preserve appropriate same-case pending work and successful snapshots. Changing case/disconnecting/reloading clears transient data. Access refresh hides retained content; definitive denial clears it. Downloaded or already viewed data cannot be erased remotely.

Dashboard counts use authorized server totals, not page length. Newest cases are not a global activity feed. Reports organize stored metadata/notes and expose citations and text saving; they read no raw evidence files.

## AI

The fixed briefing request builds a bounded allowlisted case context; raw files and note bodies are excluded. Providers select aliases rather than arbitrary prose/actions. The server resolves fields/citations and correction context, rechecks access and rejects stale or malformed output. Traceability does not prove truth, completeness or relevance.

Phase7I controls include local-only production counting, input/output/time limits, cancellation, usage admission and no automatic retries. Reviewed adapter scripts have minimal environments and no shell, but remain trusted executable code rather than an OS sandbox. Guided review is fixed navigation, not an autonomous agent.

OpenAI/Gemini adapters in tests are synthetic-only tools. Remote-count exceptions require exact fixtures and explicit opt-in. OpenAI's live-generation gate remains incomplete; Gemini's four passing scenarios do not authorize real metadata disclosure. No raw evidence analysis, threat verdict, memory, enrichment or automatic case mutation is implemented.

## Operations and verification

API privacy headers and safe error handling are implemented. The private logging profile is opt-in and sacrifices diagnostics; it cannot configure a proxy/static server or OS. Single-process limits are not global billing quotas.

See [Security operations](security-operations.md) for TLS/CORS/frontend headers, secret rotation, private storage and backup/restore gates. Schema changes require reviewed migrations; do not stamp unknown databases or downgrade custody/history to hide incompatibility.

Backend tests cover authorization, concurrency, migrations, custody/storage/retrieval, indicators/reports, AI safety and Windows upload/repeat. Frontend/browser tests cover case isolation, retries, navigation and accessibility. See [Phase8C results](phase8c-demo-completion-report.md).

Use [current setup](setup.md) and [demo guide](demo-guide.md), rather than historical phase-specific instructions, for a fresh demonstration.
