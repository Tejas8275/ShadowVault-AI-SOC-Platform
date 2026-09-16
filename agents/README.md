# Agents

The [Windows v1 collector](windows/README.md) supports explicitly selected regular
files, local staging, SHA-256 hashing, authenticated uploads, and receipt-based
retries. It uses Python's standard library only.

`core/` now contains shared hashing, HTTPS upload transport, configuration
validation, and error types. `windows/collector.py` retains platform-specific
selection, staging and locking, and its historical CLI/import surface. Keep the
repository package layout when distributing the collector; the entry point now
imports `agents.core`. `linux/README.md` describes a future adapter only.

Linux collectors, background services, memory acquisition, remote execution, and
AI analysis are not implemented.
