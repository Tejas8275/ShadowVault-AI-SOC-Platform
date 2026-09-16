# Phase 3B — authorized evidence retrieval

Phase 3B adds explicit retrieval of a verified copy. It keeps database revision
0004, existing models, upload flow, investigation contracts, TimelineEvent, and
Windows collector behavior. No package installation or new dependency is required.

## API

`POST /api/v2/investigation/evidence/{evidence_id}/download`

Send the provisioned operator token in the Authorization Bearer header. No request
body is required. The endpoint applies the same incident-owner and collection-job
requester checks as investigation metadata. Agent credentials cannot retrieve bytes.
Authorization and the evidence storage identity are checked again after preparation.

Success is HTTP 200 with the complete original bytes, `application/octet-stream`,
Content-Length, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, and
`Content-Disposition: attachment; filename="evidence-{UUID}.bin"`. The filename is
derived from the evidence UUID, never from untrusted acquisition filenames. The
original filename remains visible in metadata. There is no preview or execution.

- 401: missing, invalid, wrong-type credential, or inactive operator.
- 404: missing evidence or inaccessible incident/job ownership.
- 409: size/digest mismatch, evidence identity changed, or concurrent custody conflict.
- 413: evidence exceeds the configured retrieval limit (or existing request body limit).
- 416: Range header supplied; resumable retrieval is unsupported.
- 422: malformed evidence UUID.
- 429: per-process retrieval capacity exhausted; Retry-After is 5 seconds.
- 503: missing/unreadable/unsupported storage object, preparation timeout, or database failure.

GET/HEAD download operations are not implemented. There are no public file URLs,
redirects, range responses, retrieval-job endpoints, or additional status APIs.
Existing search/details/notes/custody GET operations remain read-only.

## Storage and transaction flow

1. Authorize the evidence and snapshot its server-owned key, size, and digest.
2. Release the read transaction before copying data.
3. Accept only the Phase 2A `32-lowercase-hex.blob` key format. Reject path traversal,
   absolute/UNC/alternate-stream keys, partial uploads, and unsupported legacy keys.
4. Reject linked/reparse storage directories and nonregular evidence. Windows uses
   CreateFileW with OPEN_REPARSE_POINT and read-only sharing, validates the final
   handle path, and denies concurrent writer/deleter handles while copying. The
   POSIX branch uses directory-relative O_NOFOLLOW; Windows is the verified platform.
5. Copy in 64 KiB chunks to a private temporary file while calculating SHA-256 and
   enforcing the expected size, byte policy, and preparation deadline. Reject a mismatch
   before response headers or content are emitted. Serve this same prepared handle.
6. Reauthorize, ensure the storage identity still matches, append custody events, and
   commit. Transaction failure closes the copy and releases capacity without serving it.
7. Stream the prepared handle; close it and release capacity on completion, transfer
   timeout, or disconnect. No original is opened for writing, renamed, or deleted.

The preparation check describes the copy at that point in time. It does not establish
continuous integrity. A later change to the original cannot alter the already prepared
copy. Initial verification and EvidenceIntegrityCheck rows remain unchanged.

## Custody meaning

An evidence item without custody receives `baseline_registered` with reason
`tracking_started_at_first_retrieval`. The baseline does not invent acquisition history.
The attributed `evidence_retrieval_prepared` event records a fresh operation UUID,
server UTC timestamp, expected/observed size and digest, and an explicit statement
that delivery/local saving are not confirmed. Events reuse the existing hash chain
and conditional head update. Metadata revision and timeline records do not change.

The baseline and preparation event commit atomically. Each successful preparation
creates a new event; retrieval retries are intentionally not deduplicated. Failure
before commit creates no event. A failure/disconnect after commit leaves the truthful
preparation event. No completion acknowledgement or durable failed-attempt log exists.
Do not interpret custody as proof that a browser saved a file or as externally anchored
tamper resistance; privileged database administrators remain trusted.

## Operator workflow

Open Evidence, connect with the existing operator token, and select evidence details.
Choose **Prepare download**. After the complete response arrives, choose **Save evidence
copy**, or **Discard copy** to release the in-memory copy. No download starts on a metadata
read. The UI refreshes custody after an attempt without changing annotation revisions.

Tokens remain only in the existing service closure and Authorization header. Requests
omit cookies, disallow redirects and use no-store. Blob URLs contain no token, are used
only by a download link, and are revoked on discard, replacement, navigation, disconnect,
or component removal. Received evidence is never rendered. Filenames end in `.bin`.

Cancel aborts the browser request and discards incomplete bytes. It cannot undo an
already committed preparation event. Backend preparation is synchronous within the
request; cancellation can be observed after preparation finishes rather than interrupting
an in-progress filesystem operation. Use Refresh custody if a late event is not yet shown.
There are no automatic retries; review custody before manually preparing another copy.

## Configuration and operational limits

Existing environment settings and dependencies are reused. New settings:

- `SHADOWVAULT_RETRIEVAL_DIR`: defaults to `backend/var/retrieval`; private temporary copies.
- `SHADOWVAULT_MAX_RETRIEVAL_BYTES`: default and maximum 104857600 bytes (100 MiB); may be lowered.
- `SHADOWVAULT_RETRIEVAL_TIMEOUT_SECONDS`: default 120, accepted range 1–3600; separate preparation
  and response-transfer deadlines. Preparation checks between synchronous filesystem calls;
  it cannot forcibly interrupt a hung filesystem call.
- `SHADOWVAULT_MAX_CONCURRENT_RETRIEVALS`: default 2, range 1–8, held through streaming cleanup.

Limits are per process, not global across application workers. Browser buffering has a
100 MiB content cap and a 240-second overall timeout; memory overhead can exceed content
size. A larger configured server timeout does not extend the browser timeout.

Windows requires Python 3.13+ for private-directory ACL support. New directories request
mode 0700. Existing storage/temporary-directory ACLs and trusted parent directories remain
deployment responsibilities; this phase does not repair them. Use private local storage,
TLS outside loopback, and sufficient temporary disk capacity. Do not configure network,
linked, or junction-based storage roots. Linux collection remains unimplemented.

Normal errors/disconnects close temporary handles. Abrupt process/OS failure and filesystem
failures are not a guarantee of physical erasure; no new background reconciliation/retention
worker was added. Browser evidence copies remain in memory until discarded/navigation/tab
closure, and user-saved copies remain under the user's control.

## Schema and exclusions

No migration or model changes. The database remains at revision 0004. Existing legacy
records remain searchable even if their storage keys are unsupported for retrieval; no
automatic remapping/backfill is performed. No AI, malware analysis, parsing, preview,
background jobs, resume, integrity-check worker, automatic timeline extraction, browser
session redesign, or collector changes are included. See [the report](phase3b-report.md).
