# Portfolio release checklist

Phase8C prepares documentation and manual synthetic fixtures; it does not publish, host, select a license or certify production readiness.

## Publication inventory and secrets

- [ ] Inspect the exact proposed source package and the actual Git history before publishing. This working directory has no visible Git metadata; a working-tree scan cannot clear repository history.
- [ ] Exclude actual `.env`, databases/WALs, private evidence/backup/retrieval roots, spool files, logs, saved reports, browser traces, node_modules, virtual environments and personal scratch files. Do not zip the working directory wholesale.
- [ ] Review root-level test text files and historical reports for personal paths/account references. Historical forensic records are not demo data. Prefer an explicit file allowlist and review history rather than destructive blanket cleanup.
- [ ] Run a local secret scanner against the intended package/history. Findings must report locations/categories, not credential values. Rotate any exposed credential. `.gitignore` is not proof of cleanliness.
- [ ] Confirm example provider-key assignments are blank, actual credentials remain backend-only, and public VITE settings contain URLs only. Inspect all images/video/text exports separately.
- [ ] Choose license and third-party attribution terms before publishing; no root LICENSE is currently supplied. No licensing decision is made by this checklist.

## Environment and installation

- [ ] Rehearse [Setup](setup.md) on a clean isolated source copy, using existing dependency locks and no copied secrets/database. A passing current-environment test suite is not a clean-install proof.
- [ ] Verify fresh migration head0008, SQLite integrity and FK checks. Do not stamp unknown schemas. Existing installations require backup/stopped writers.
- [ ] Use fresh privately provisioned demo credentials, AI disabled, dedicated storage and exact loopback origins. Never target the existing investigation database.
- [ ] Record Python/Node/Edge versions and `pip check`; verify package installation with registry access. No dependency upgrades are required by this preparation.
- [ ] Run complete backend/frontend/browser/typecheck/build suites on the release candidate; confirm final browser exit, not just individual passes. Include Windows collector upload/repeat.

## Demonstration

- [ ] Follow [Demo guide](demo-guide.md) with only the supplied synthetic text; all records go through existing authorized operations.
- [ ] Label manual observations/corrections and distinguish custody, timeline and case history.
- [ ] Keep actual source hashes/server timestamps, no fabricated metadata or screenshots.
- [ ] Describe reports as transient metadata drafts and AI as optional source selection, not autonomous analysis.
- [ ] Do not claim successful OpenAI live generation from its incomplete report or equate Gemini's fixed synthetic evaluation with permission to send real case data.
- [ ] Privacy-review screenshots/recordings and provide captions/alt text. Obtain approval before actual publication.

## Production limitations

A local portfolio demo needs no publicly exposed API. Hosting requires a separate [security operations](security-operations.md) review: TLS/proxy/CSP, secret handling, private storage/encryption, backup restore drill, ingress limits and logging. Browser sessions/RBAC, global quotas, external custody anchors, raw-evidence AI, automatic detection/enrichment, Linux collection and background workflows remain outside the implemented scope.

Phase 8D presentation materials and current verification are recorded in the [final preparation report](phase8d-final-release-preparation-report.md). Publication remains blocked until the actual Git index/history and release package are reviewed. Do not start Phase 8E without approval.

## GitHub release

- [ ] Review the actual tracked files and full history, resolve secret-scan findings and exclude working data/artifacts before choosing a tag.
- [ ] Choose a license; record tested versions, exact regression counts and remaining limitations in release notes.
- [ ] Link setup, manual demo, architecture and security operations. Verify links in the published source tree.
- [ ] Do not attach a development database, private logs, credentials or a whole-workspace ZIP. No release/tag/push is performed by this checklist.

## README screenshots

- [ ] Follow [Screenshot capture checklist](screenshot-checklist.md); use actual synthetic UI, never generated mock results.
- [ ] Use a case-workspace hero plus evidence, correction and report views; include captions and useful alt text.
- [ ] Keep uncertainty, verification and snapshot labels visible. Confirm image paths exist before linking them.

## LinkedIn post

- [ ] Use a short case-to-report story and 4–5 readable synthetic screenshots, with a plain statement that this is a local portfolio pilot.
- [ ] State the engineering contribution: authorization, SHA-256 verification, separate custody/history and cited metadata review.
- [ ] Avoid claims of automated detection, maliciousness scoring, production certification or successful live OpenAI evaluation.
- [ ] Label every deterministic AI example and review the full video, notifications and captions for secrets before posting. No social post is sent automatically.

## Portfolio presentation

- [ ] Include problem/scope, architecture/trust boundaries, synthetic workflow, test evidence and limitations slides.
- [ ] Distinguish selected-file collection from remote acquisition; metadata source selection from raw-evidence analysis; report drafts from final reports.
- [ ] Provide readable captions/transcript and a rehearsed offline fallback. Label recordings as recordings; do not fake a live success after an error.
- [ ] Rehearse disconnect/reload and explicit retry behavior without weakening access control. Obtain approval before publishing or hosting.
