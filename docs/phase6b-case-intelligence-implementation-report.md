# Phase 6B — Case Intelligence Foundation Implementation

Date: 2026-09-12.

## Scope and architecture decision

Incident remains the Case entity. This phase adds a metadata-only investigation overview to the existing Case workspace. It does not interpret evidence or make investigation decisions.

Reviewed the Phase 6A audit, Incident detail/list/history routes and schemas, evidence/timeline authorization queries, custody recording, Case workspace, shared API client, and regression fixtures. Existing evidence and timeline searches return totals, but case history only returns revision-cursor pages. Timeline search orders forensic occurrence time rather than recording time. The existing contracts cannot provide a reliable latest recorded activity value or history row count without scanning potentially all pages (including custody histories).

The minimal backend correction is an opt-in summary on the **existing** case-detail GET. No new route, table, model entity, dependency, or framework was introduced. Evidence, Timeline and History remain the authoritative records; the aggregate service reuses existing evidence/timeline authorization queries. Existing paginated APIs and frontend consumers remain intact.

## API contract and metrics

`GET /api/v2/investigation/incidents/{id}?include_intelligence=true` returns the existing case fields plus `intelligence`:

- `evidence_count`: number of visible evidence records within this incident, including visible legacy records.
- `timeline_count`: visible TimelineEvent records, including legacy events and investigator observations; not an evidence count or a deduplicated incident count.
- `history_revision_count`: number of recorded CaseHistoryEvent rows. Includes creation/baseline records when present. It is not the current revision value or inferred earlier history.
- `history_started_revision`: minimum recorded history revision, or null when tracking has not started.
- `latest_activity_at`: maximum UTC recording timestamp across case creation/update, visible evidence registration, visible timeline recording, case history recording, and custody records for visible evidence.

The default detail GET omits the new property. Existing POST/PATCH payloads, optimistic concurrency, updated_at behavior and history pagination remain unchanged. Detail responses use `Cache-Control: no-store`. Summary database errors return a sanitized 503; unauthorized cases remain indistinguishable from missing cases (404), and missing operator credentials return 401.

Latest activity is not forensic occurrence time, source file modification time, proof of completed download delivery, or a statement that evidence integrity has just been checked. Notes/tags and other supported evidence actions contribute through their existing custody records. Unsupported direct database changes without recorded activity cannot be reconstructed.

## Frontend behavior

A reusable CaseIntelligencePanel appears below the existing case metadata header. It displays the three counts, investigator-assigned status/severity, latest recorded activity in UTC, the current revision, and history tracking limits. Existing title, description, owner and creation/update timestamps remain visible in the case header.

The panel loads independently, so summary failure does not replace the case workspace. Loading, unavailable, retry and true-zero states are distinct. It refreshes after case saves/reloads and has an explicit keyboard-accessible refresh button for other activity. Existing responsive metric styles are reused. No polling or background workflow was added.

## Security and compatibility

- Existing operator authorization is enforced before aggregation. Evidence and evidence-linked timeline/custody aggregates retain the stricter case-owner AND collection-requester visibility boundary.
- Summary reads perform no storage access, retrieval preparation, integrity execution, case mutation or custody/history append. Full table snapshots in a regression test confirm read immutability.
- The shared API client keeps credentials in its existing memory-only closure and Authorization header. Disconnect/401 handling and cancellation remain shared with evidence/timeline requests. No token URL, log, browser storage or build-variable handling was added.
- Existing custody semantics, original bytes, upload idempotency, verified-copy retrieval, timeline provenance and Windows collector compatibility remain unchanged.
- No AI, malware analysis, automation, teams/RBAC, background workers, case-history replacement or new authentication system was added.

## Database

No migration is required or created. The configured local SQLite database was opened using `mode=ro` for verification:

- Alembic revision: **0007**.
- `PRAGMA integrity_check`: **ok**.
- `PRAGMA foreign_key_check`: **0 violations**.

No application database mutation or migration command was run. Regression suites use isolated temporary databases. No migration backup was needed for this read-only schema-compatible change.

## Exact changed-file inventory

Modified:

1. `backend/app/api/routes/investigation_incidents.py` — opt-in detail summary, no-store and sanitized database failure handling.
2. `backend/app/schemas/incident.py` — response-only summary/detail schemas.
3. `frontend/src/features/cases/CaseWorkspace.tsx` — embed and refresh the summary with case state.
4. `frontend/src/features/cases/contracts.ts` — optional summary response types.
5. `frontend/src/features/evidence/service.ts` — one authenticated method for the existing detail route's opt-in query.

Added:

6. `backend/app/services/case_intelligence.py` — scoped read-only aggregate query.
7. `frontend/src/features/cases/CaseIntelligencePanel.tsx` — overview presentation and resource states.
8. `tests/test_case_intelligence.py` — four focused API/database regressions.
9. `frontend/tests/case-intelligence.test.mjs` — two client contract/security/error tests.
10. `frontend/tests/browser/case-intelligence.spec.ts` — three browser workflows.
11. `docs/phase6b-case-intelligence-implementation-report.md` — this report.

Source inventory was compared with the pre-implementation SHA-256 snapshot. No existing model, migration, collection, retrieval, custody, timeline service, configuration or dependency file changed. Generated frontend build/test artifacts are not source changes.

## Verification

- Full backend: `python -m unittest discover -s tests -p 'test_*.py' -v` with `PYTHONPATH=backend`: **133 passed, 0 failures, 0 errors**.
- Frontend services: `npm --prefix frontend test`: **37 passed, 0 failed, 0 skipped**.
- TypeScript: `npm --prefix frontend run typecheck`: **passed**.
- Production: `npm --prefix frontend run build`: **passed**, 58 modules transformed.
- Browser: `npm --prefix frontend run test:browser`: **47 passed, 0 failed** (1.2 minutes). The prior 46-workflow run also passed before the final empty-case/mobile check was added.
- Windows collector/upload: `test_real_cli_upload_and_repeat` passed within the full backend suite, alongside agent core, Windows file-selection/transport and upload/timeline/retrieval regressions.
- Existing Phase 2A/2B/3A/3B/4A/5A/5B/5C regressions and the existing Phase 5D browser/service workflows are included in these suites.

Focused coverage checks default response compatibility, zero counts, no-store, operator/owner denial, sanitized database errors, history row count versus revision, full-table read immutability, hidden collection-requester evidence/timeline/custody exclusion, and recording versus occurrence time. Browser coverage checks real server aggregates, loading/failure/recovery, new-case zero counts with one creation event, mobile width and refresh-button keyboard focus.

Initial focused test runs exposed fixture mistakes (missing required case-update fields, missing collection provenance, and assuming API edits generate migration baseline rows). These fixtures were corrected; no existing validation was weakened. An imported test class initially duplicated discovery and was changed to a module import before the full suite.

Warnings: existing Starlette/httpx TestClient deprecation; browser runner NO_COLOR/FORCE_COLOR warning. No dependency change was made to suppress existing warnings. Typecheck/build reported no failure.

## Limitations

The summary is a live read, not an immutable report or a transaction spanning separate browser requests. Case detail and aggregate reads, and other workspace views, can change between requests. Activity after a displayed result requires explicit refresh. Counts are not estimates, and unavailable values are never substituted with zero.

The aggregate query uses existing database records/indexes and returns constant-size data, but work still grows with case evidence, timeline and custody volume. No large-volume performance benchmark or materialized counter/cache was introduced. There is no global activity feed, evidence parsing, correlation engine, findings model, report export or automatic status recommendation.

Stop at Phase 6B. Later phases require separate approval.

