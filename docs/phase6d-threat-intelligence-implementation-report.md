# Phase 6D — Threat Intelligence Foundation Implementation

Date: 2026-09-12. Based on the approved Phase 6C audit. Scope: investigator-recorded, evidence-linked IOC observations only.

## Delivered behavior

The Case workspace now includes a Case Threat Intelligence panel with a paginated indicator list, explicit add form, source-evidence links and provenance. It supports manual SHA-256 hashes, single IPv4/IPv6 addresses, conservative ASCII domains and filenames. Investigators may explicitly copy a stored evidence hash or filename instead of entering a manual value. The backend supplies metadata-derived values and locators.

Each observation is linked to an existing Evidence record and its Incident-as-Case. A case without evidence can display an empty list but cannot create a case-only observation. This follows the approved evidence-linked design. Investigators copy an evidence ID from the existing case evidence details into the form; no new evidence picker/search service was introduced.

The list shows normalized value, original spelling when different, kind, manual versus metadata source, actor, UTC registration time, policy version, source citation, observation ID and evidence link. Domain values are plain text and are never contacted. SHA-256 observations can populate the existing case-scoped evidence search; this resets the displayed search fields and pagination together.

Observations are not threat verdicts. Registration does not imply compromise, safe content, a fresh integrity check or verified manual provenance. Equal filenames do not imply identical contents. No external feeds, enrichment, DNS lookup, AI, automation, workers or teams/RBAC were added.

## Backend architecture and API additions

One new model/table, `IndicatorObservation` / `indicator_observations`, stores the bounded typed assertion, raw/normalized value, metadata/manual source, optional citation, actor attribution, UTC creation time, schema version, submission identity/fingerprint and optional supersedes reference. Incident remains the Case entity. Evidence remains owned by one Incident; there is no global indicator catalog or new ownership model.

Two additive routes use the existing operator dependency and investigation service architecture:

- `POST /api/v2/investigation/evidence/{evidence_id}/indicators`: register one observation or correction. Returns 201 with the observation, including for a successful identical retry. Body fields: kind, source_kind, optional raw_value/source_locator for manual input, submission_id, optional supersedes_id. Actor, incident, timestamps and stored acquisition values are server-owned.
- `GET /api/v2/investigation/incidents/{incident_id}/indicators`: paginated list, default 50 and maximum 100 rows, with optional evidence_id, kind, exact value and bound cursor. Exact-value filtering requires kind. The initial panel uses case list pagination; advanced API filters are available without a new frontend filtering system.

Responses use no-store. No PATCH/DELETE operation exists. All existing API contracts remain intact. Indicators are excluded from Phase 6B evidence/timeline/history counts and latest-activity semantics; those definitions have not silently changed.

## Validation, security and concurrency

- SHA-256: exactly 64 hexadecimal characters after surrounding whitespace removal; normalized lowercase. No MD5/SHA-1 or extra byte hashing.
- IP: Python standard-library literal validation and normalization; reject CIDR, ports, zone identifiers and ambiguous shorthand. Private addresses are valid observations, not threat classifications.
- Domain: lowercase ASCII labels with explicit length bounds, at least two labels, alphabetic start of final label, and optional removal of one final dot. URLs, wildcards, IP literals, Unicode and defanged forms are rejected. No network access.
- Filename: preserve case/spelling; reject empty names, dot/dot-dot, path separators and colon. Full paths and alternate streams are outside this filename feature.
- Values/citations reject Unicode control-category characters. Values are limited to 255 characters, citations to 512. Domains have their own stricter label/total bounds.
- Every write and retry requires authorized evidence. List queries apply existing Incident-owner AND collection-requester visibility. Composite evidence/incident foreign keys prevent cross-case links. The UI also checks the evidence's incident before submitting; this is a UX guard, not a replacement for backend authorization.
- Operator tokens remain in the shared client's memory-only closure and Authorization header. Disconnect/expiry cancels requests. No token storage, logging or URL transport was added.
- Actor/submission uniqueness makes identical explicit retries return the same row. Changed reuse returns 409. Concurrent insertion conflicts return sanitized 409; database failures return sanitized 503 and roll back. The form retains the original pending submission for manual retry and warns before starting a different submission after an uncertain outcome.
- Corrections append a new row referencing the same authorized evidence's prior observation. A unique supersedes target prevents two competing successors. No original row is replaced. Corrections may form a chain; existing rows remain visible and later pages may contain successors.
- ORM guards and SQLite UPDATE/DELETE triggers enforce append-only behavior for normal application/database operations. They are not protection against a privileged administrator who can remove triggers.

Registration/read operations do not read storage, open files, prepare downloads, mutate evidence metadata, advance custody, append case history or create timeline events. Tests compare all other table contents before and after registration/read/failure. Existing custody/hash chains and case revisions are preserved.

## Backup and migration

Before implementation, the configured SQLite database was backed up using SQLite's backup API and the backup passed integrity checking:

- Backup: `backend/backups/phase6d-before-0008-20260912T060644Z.db`.
- Backup SHA-256: `4b99f5734c31d204c96b7e1fa6a8f64caad296eae686e38bec07c68adb709fd9`.
- The backup contains application data and must be handled as private local material; it is covered by existing database ignore patterns and is not a public artifact.

Migration **0008**, with predecessor **0007**, adds only the indicator table, indexes, constraints and append-only triggers. It does not alter original tables or backfill fabricated observations. SQLite is the supported migration target, consistent with the existing history guards. Downgrade is explicitly forward-only; restoring the reviewed backup is a deliberate recovery operation and would discard later data, so it is not automatic.

The configured development database was upgraded after focused migration/backend verification. The backup was compared with the pre-upgrade original table rows before upgrading. Post-upgrade results:

- Revision **0008**.
- **11 original tables / 12 original rows preserved**.
- New indicator rows: **0**.
- SQLite integrity: **ok**.
- Foreign-key violations: **0**.

No restoration or evidence-storage migration was performed. A running backend process needs to load the updated application code before the new routes are usable; restart an existing non-reloading development server if necessary.

## Exact changed-file inventory

New application/migration files:

1. `backend/app/models/indicator.py`
2. `backend/app/schemas/indicator.py`
3. `backend/app/services/indicators.py`
4. `backend/app/api/routes/investigation_indicators.py`
5. `backend/migrations/versions/0008_indicators.py`
6. `frontend/src/features/indicators/contracts.ts`
7. `frontend/src/features/indicators/CaseThreatIntelligence.tsx`

Modified application files:

8. `backend/app/models/__init__.py` — model registration.
9. `backend/app/main.py` — route registration.
10. `frontend/src/features/evidence/service.ts` — two authenticated indicator methods.
11. `frontend/src/features/cases/CaseWorkspace.tsx` — panel integration and explicit hash-pivot reset.

New tests:

12. `tests/test_indicators.py`
13. `tests/test_indicator_migration.py`
14. `frontend/tests/indicators.test.mjs`
15. `frontend/tests/browser/indicators.spec.ts`

Updated regression expectations:

16. `tests/test_migrations.py` — current head 0008.
17. `tests/test_models.py` — new table included in model inventory.
18. `tests/test_retrieval.py` — current head assertion 0008; retrieval checks retained.
19. `tests/test_timeline_migrations.py` — current head assertion 0008; preservation checks retained.
20. `tests/test_case_history_migration.py` — pin the historical 0006-to-0007 baseline/downgrade test to its intended revision instead of upgrading to the moving head.

Documentation:

21. `docs/phase6d-threat-intelligence-implementation-report.md`.

Runtime data: the configured `backend/shadowvault.db` schema advanced to 0008 and the backup listed above was added. Generated frontend build/test artifacts and temporary verification logs are not application source changes. No configuration, dependency, collector, custody, case-history service or timeline service file changed.

## Verification results

- Full Python backend: **142 passed, 0 failures, 0 errors** (49.609 seconds), using `PYTHONPATH=backend` and `python -m unittest discover -s tests -p 'test_*.py' -v`.
- Frontend services: **39 passed, 0 failed**, `npm --prefix frontend test`.
- TypeScript: **passed**, `npm --prefix frontend run typecheck`.
- Production build: **passed**, `npm --prefix frontend run build`.
- Final full browser suite: **50 passed, 0 failed** (1.7 minutes), `npm --prefix frontend run test:browser`.
- Focused final indicator browser workflows: **3 passed**.
- Windows collector: `test_real_cli_upload_and_repeat` passed in the complete backend suite. Agent core, selected-file validation, staging/retry, upload, timeline and verified-copy retrieval regressions also passed in that suite.

New backend coverage includes all four manual kinds, stored hash/filename promotion, server attribution and UTC time, invalid formats and spoofed fields, owner/requester denial, pagination/filter binding, idempotency, correction scope, concurrent submissions/corrections, rollback, append-only SQL/ORM protection and preservation of all original tables. The migration test verifies populated 0007 preservation, repeatable upgrade, integrity/foreign keys and forward-only behavior.

Browser coverage registers all four manual kinds, checks source links/plain-text values/mobile width, hash pivot, unchanged retry payload, corrections, error/empty/pagination/expiry behavior. Service tests verify header-only authentication, no-store, unchanged retry payload and sanitized conflicts without automatic retries.

During verification, the first full browser run had 48 passes and 2 failures due to select label lookup. Explicit label associations fixed the form. A focused rerun then exposed a stale visible hash-search field after a pivot; remounting that search on explicit pivots now resets both draft fields and pagination. The three focused workflows subsequently passed. These fixes did not alter evidence search API semantics.

Warnings: existing Starlette/httpx TestClient deprecation and Playwright NO_COLOR/FORCE_COLOR environment warning. No dependency upgrade was introduced to suppress them.

## Remaining limitations and stopping boundary

Observations require evidence; there is no case-only indicator entry or cross-case matching. The form accepts an evidence ID rather than providing a new picker. Values are local investigator assertions, with no reputation or confidence score. Corrections preserve historical rows; there is no deletion, withdrawal state or automatic collapsing into a current verdict. Explicit refresh is required after activity outside this panel, and pages are a live view rather than a frozen report.

Domain policy is deliberately conservative and may reject otherwise usable international/internal names. Filename observations are weak identity signals. There is no file-content extraction/parsing, source preview, IOC scanning, external lookup/feed, AI, automatic enrichment, automation, background workers, teams/RBAC or new authentication system. No architecture replacement or change to case-history, custody or timeline behavior was made.

Stop after Phase 6D. No later phase is started automatically.
