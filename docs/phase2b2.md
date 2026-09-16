# Phase 2B-2 evidence workspace

The evidence dashboard uses the existing Phase 2B-1 investigation API. No endpoint,
schema migration, upload behavior, or browser login contract was changed.

## Run and connect

Use the backend environment and operator provisioning described in [Phase 2A](phase2a.md).
The database must already be upgraded to revision 0003. Start backend and frontend
using the existing setup instructions. In the browser choose Evidence, then
Connect operator, and enter an existing provisioned operator token.

`VITE_API_BASE_URL` remains the Phase 1 v1 API URL. The independent public setting
`VITE_INVESTIGATION_API_BASE_URL` defaults to
`http://127.0.0.1:8000/api/v2/investigation`. Restart Vite/rebuild after changing it.
The URL must use HTTPS except loopback development, with no credentials, query,
or fragment. Never put tokens in configuration, build variables, URLs or storage.

The operator client owns the token in a closure. Request headers carry it only
to the configured API; redirects are rejected, cookies omitted, and cache disabled.
Disconnect or a 401 clears the token, aborts outstanding requests, and removes
investigation state. Reloading the tab requires reconnecting. Browser sign-in
remains a separate, unimplemented Phase 1 form. This is a local operator pilot,
not a new production session system; an XSS-compromised browser remains outside
the protection offered by memory-only credential handling.

## Investigator workflow

1. Search by text, hash, IDs or comma-separated tags. Advanced filters include
   review state, initial verification, subsequent integrity, dates and byte sizes.
   Date controls show local input time; requests normalize it to UTC.
2. Review server-authorized totals and use cursor-based Next/Previous pages.
   Filters stay in memory when opening details and returning. They are not placed
   in the page URL or persistent browser storage. Results remain a live view.
3. Open an evidence record. Original acquisition metadata is read-only. Copy IDs
   and SHA-256 when needed; clipboard failure offers manual selection.
4. Edit display title, review state or tags, then Save annotations. Remove a tag
   from the comma-separated list to remove it; clear the list to remove all tags.
5. Add plain-text notes. Notes cannot be edited or deleted. The backend records
   the authenticated author, time, and custody event in the same transaction.
6. Review custody events and expandable hash/identifier details. Migration baselines
   and first-annotation baselines are labeled separately. History display does not
   independently validate its hash chain or reconstruct missing acquisition events.
7. Read initial verification separately from subsequent integrity status. A match
   describes the recorded check time, not continuous monitoring. Check execution
   and pending-check state are unavailable; there is no Verify now action.

Every write includes the current metadata revision. A conflict preserves the draft
and blocks submission until current metadata/notes are reloaded. An unconfirmed
write also requires reload before any retry. Review the reloaded data alongside
the retained draft; never assume a timeout means the backend did not commit.
Successful writes refresh the affected metadata/history. Navigation away from an
evidence detail or a tab reload discards unsaved drafts; drafts are not persisted.

Notes, filenames, titles and custody details render as escaped text. No preview,
download, file execution, AI analysis or malware analysis is included. Incident,
agent and job filters accept IDs because directory APIs were not added.

## Shared agent core

`agents/core/hashing.py` provides streaming hashing of staged files; `uploader.py`
retains bounded HTTPS transport and refusal of redirects; `config.py` owns shared
URL/token validation and timeout; `errors.py` owns CollectorError. These modules
use only the Python standard library. Windows source validation, identity checks,
staging, permissions, locks, manifest selection and receipt handling stay in the
Windows adapter. CLI arguments, token environment/prompt handling, spool defaults,
headers and receipt formats are unchanged.

Continue invoking `agents/windows/collector.py` exactly as before, but distribute
the whole `agents` directory together because it now imports `agents.core`.
Historical ApiClient, CollectorError and digest_file imports remain available from
the Windows module. `agents/linux/README.md` is preparation only; no Linux collector exists.

## Verification

```powershell
$env:PYTHONPATH='backend'
backend/.venv/Scripts/python.exe -m unittest discover -s tests -v
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:browser
```

Browser tests require installed Microsoft Edge on Windows and free ports 5179/8769.
Playwright starts isolated Vite/FastAPI servers and uses fabricated test identities.
No production credentials or development records are involved. Traces, video, and
screenshots are disabled to avoid recording request credentials. Normal test failure
output can contain fabricated fixture metadata. Windows forceful server shutdown
can leave `backend/browser-test-*` fixture directories; inspect before removing them.
Do not run the fixture server as an application deployment.

Full results and file inventory are in [the completion report](phase2b2-report.md).
