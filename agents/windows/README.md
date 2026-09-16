# Windows Agent v1

Operator-launched, selected-file collector. Requires Windows and Python 3.13+;
uses only the Python standard library. No installation or third-party packages
are needed. It does not run as a service, poll for tasks, execute remote commands,
collect memory, or analyze evidence.

First register the agent and create an incident-scoped job using the
[Phase 2A setup guide](../../docs/phase2a.md). The server returns the agent token
once. Supply it through the hidden token prompt or `SHADOWVAULT_AGENT_TOKEN`;
do not put tokens in command-line arguments.

From the repository root, for local development:

```powershell
python agents/windows/collector.py --backend http://127.0.0.1:8000/api/v1 --allow-http-local --job-id <job-UUID> --file "C:\Cases\selected.bin"
```

For a remote backend, use its HTTPS URL and omit `--allow-http-local`. Private
certificate authorities can be configured with `--ca-file`; certificate validation
cannot be disabled. HTTP is permitted only for explicit loopback development.
Redirects are never followed.

Repeat `--file` for each selected file. Every path must be explicitly selected
locally and present in the server-approved job manifest. Directories, symlinks,
junctions/reparse points, UNC paths, device names, wildcards, and alternate data
streams are unsupported. Source files are read without modification. The agent
checks identity, size, and modification time for changes during acquisition;
this is a live-file acquisition, not an atomic forensic disk snapshot.

## Staging and retries

- Files stream through a 1 MiB buffer into `.spool/` beside the collector by
  default. Override with `--spool <private-directory>`.
- The local per-file limit is 100 MiB, further restricted by the job's approved
  limit. Files are processed sequentially.
- Python 3.13+ creates a new `mode=0o700` directory with Windows access limited
  to its owner and administrators. Existing directory ACLs are not rewritten;
  use a dedicated private directory. Protect the endpoint disk with encryption.
- Each staged file has a SHA-256 digest and a manifest. No credentials are saved
  in the spool. Metadata still includes sensitive source paths.
- A failed upload retains the staged bytes. Rerun the same command to resend the
  same bytes, even if the source has subsequently changed.
- After a matching verified receipt, the receipt is saved durably before the
  staged bytes are deleted. Later runs return that receipt without reacquiring
  the file. A new acquisition requires a new job.
- Per-item Windows file locks prevent concurrent collectors from overwriting
  each other's staging. OS locks release on exit; small `.lock` files remain.
- A crash during initial staging can leave `.partial` or unpaired `.bin` files.
  Preserve and inspect these locally; the collector refuses to overwrite an
  unpaired staged file. It does not silently delete uncertain artifacts.

Exit status is zero only when all explicitly selected items succeed or already
have verified receipts. Failures return status one and retain pending data.
# Phase 2B-2 compatibility note

The existing collector command, flags, environment variable, spool location,
staging/receipt formats and retries are unchanged. Hashing and transport are now
imported from `agents/core`; distribute the `agents` directory together rather
than copying only `collector.py`. File selection, reparse-point checks, locking,
permissions and acquisition remain Windows-specific. No Linux collector is included.
