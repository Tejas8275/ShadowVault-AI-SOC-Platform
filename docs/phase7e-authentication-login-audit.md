# Phase 7E — Authentication and Login UX Architecture Audit

Date: 2026-09-13. Audit/design only. No authentication implementation or behavior change.

## Recommendation

Phase 7F should provide **one clear operator connection experience using the existing bearer-token contract**. Replace the misleading email/password entry screen with the same supported operator connection presentation used by protected workspaces. Keep the existing authentication owner, service closure, backend checks and in-memory lifetime. A professional interface does not require a new login method.

Do not add username, operator ID, email or password inputs: none authenticates a browser investigator today. Do not add a reveal-token control under the requirement that credentials must not be exposed in the UI. Keep token entry masked. No backend endpoint, database migration or dependency is required.

## Inspection basis and limits

Inspected `frontend/src/App.tsx`, `components/Layout.tsx`, `pages/LoginPage.tsx`, `features/evidence/InvestigationWorkspace.tsx`, `features/evidence/service.ts`, `services/{auth,api,http}.ts`, `styles.css`, the Phase 7D case/report boundaries, and authentication-related service/browser tests. Backend inspection covered `core/{security,config}.py`, `cli.py`, `schemas/auth.py`, `api/routes/auth.py`, application/CORS setup, investigation route dependencies, owner/evidence predicates, and existing API/collection/case tests. Reviewed logging call sites and prior documentation.

This is a source-based audit, not a new browser execution, accessibility certification, penetration test or infrastructure log inspection. No live credentials were read, reproduced or submitted. No application API mutation, token provisioning/rotation, collector operation or test suite was run. UI descriptions below follow current components/styles; historical screenshots are not treated as current verification.

## Current authentication architecture and backend contract

```text
Trusted local provisioning/configuration
    -> active User ID + configured operator token SHA-256

Masked operator input
    -> InvestigationWorkspace -> createInvestigationService closure
    -> GET /api/v2/investigation/evidence?limit=1
       Authorization: Bearer [credential held only in memory]
    -> require_operator
       SHA-256 + constant-time comparison + configured active User
    -> owner/requester-scoped services -> authorized response
    -> connected workspace -> each later request reauthenticates

Legacy email/password form
    -> POST /api/v1/auth/login -> 501, no session/token
    GET /api/v1/auth/me       -> 501, no current-user session contract
```

`require_operator` rejects missing/oversized credentials, mismatched digest, absent configured user and inactive user with 401, a generic “Invalid or expired credential” response and `WWW-Authenticate: Bearer`. It compares the SHA-256 digest with `hmac.compare_digest`. The configured User supplies actor identity; an input username or selected ID must never substitute for it.

The browser connection probe is the existing authorized evidence search, not `/auth/login` or `/auth/me`. An empty authorized evidence result is a valid connection. The probe does not create records or custody. There is no successful password authentication, cookie issuance, refresh token, JWT session, server logout, user profile endpoint or role selection in this workflow.

Device authentication is separate: agent digest, active status, explicit token expiration and active registering user. Operator and device credentials are not interchangeable. The agent default lifetime is 24 hours; **that is not an operator session lifetime**.

## Current frontend components, routing and appearance

- `LoginPage.tsx` is a narrow, centered panel in the shared dark workspace shell. It displays “Sign in”, a warning that password sign-in is unavailable, email/password controls and a submit button. The password is masked and cleared after submission, but a user can still submit credentials to an endpoint that cannot authenticate them. A link points to the dashboard operator connection.
- `authService` uses the legacy generic v1 client. Valid login payloads receive 501; malformed payloads can receive 422. The backend LoginRequest includes a SecretStr password, but the route does not verify it or issue credentials. Even an unexpected successful response leaves this UI saying sign-in is unavailable.
- `InvestigationWorkspace.tsx` owns the actual connection state and service instance. Its disconnected panel has one masked Operator token field, explanation, Connect operator button and generic failure alert. The field is required, capped at 256 characters and marked `autoComplete="off"`. The input is emptied before awaiting connection; input/button are disabled while connecting.
- Connected workspaces display “Operator connected” and Disconnect operator. There is no supported authenticated display-name response; do not invent a name, role or operator ID display from token contents.
- `App.tsx` uses existing hash routing for overview, cases, case evidence, standalone evidence and timeline. Disconnected protected destinations render the connection gate at that route; successful connection then displays the requested destination. There is no separate redirect/session framework.
- `#login` renders the legacy page and hides, rather than unmounts, InvestigationWorkspace. Visiting it is **not logout**. With a connected operator, the current route props select the hidden standalone EvidenceSearch branch, which can issue an unnecessary authorized read behind the login page. Navigating there also leaves the case workspace, so its transient case work is discarded under current semantics.
- Layout provides the SV mark, dark palette, navigation, skip link, focusable main region and Development badge. Its “Sign in” link conflicts with the supported “Connect operator” wording despite the availability footnote.

## Token/session lifecycle and disconnect

The investigation client validates the supplied token format before sending it, stores it in a private closure, and probes the authorized endpoint. Failure clears the credential. It does not trim input or normalize a secret; preserve that behavior and explain “paste only the provisioned token” without displaying an example credential.

Requests use Authorization headers, `credentials: 'omit'`, `cache: 'no-store'`, redirect rejection, a fixed validated API base and abort signals. The client rejects non-HTTPS destinations except loopback HTTP and rejects base-URL credentials/query/fragment. Ordinary requests have a ten-second timeout; retrieval has its separate existing timeout/bounds. No automatic write retry exists.

Operator credentials have **no implemented time-based expiry or idle timer**. “Expired or rejected” is generic 401 wording, not proof a timer expired. A configured digest change takes effect when the running application reloads its settings; changing a file alone is not an instant revocation of a running process. Local provisioning creates a new API-only user and prints its token once; it does not rotate an existing identity. Future operational rotation must preserve the intended user ID/ownership and update the configured digest through the existing trusted process, not create a new case owner as a shortcut.

Disconnect empties the service token, aborts its pending requests and clears filters/connected state while advancing the existing generation boundary. A 401 invokes the same service clearing and workspace rejection path. Case components keyed by generation/case ID unmount, removing pending indicator/report state. Reloading the tab also loses the connection. Abort checks prevent delayed responses from republishing data. Disconnect is local to this tab; it does not revoke the configured credential in another tab/device or erase already downloaded files. No background expiration/revocation polling exists.

## Protected-route authorization and data ownership

Frontend gates prevent normal disconnected rendering; they are not the security authority. Every investigation route uses the Operator dependency. Cases are scoped by Incident.created_by_id; unauthorized and missing cases return the same 404 behavior. Evidence additionally checks its collection job requester where applicable. Timeline, indicators, histories and report sources inherit their existing case/evidence boundaries; retrieval and report workflows retain their additional rechecks.

Phase 7D retains same-case panels only within the authenticated workspace. It hides/inerts them during case revalidation, clears them on definitive case denial, and clears reports on report access denial. The login UX change must preserve those keys, clearing rules and manual retries. Do not create a global cache, retain private data across reconnect, change a case owner, or turn 403/404 into evidence that another case exists.

Public readiness/health does not prove operator authentication. A connected client flag reflects a previously accepted request, not a fresh backend liveness or perpetual-access guarantee.

## UX, accessibility and responsive findings

1. **Highest priority: unsupported credential entry.** A prominent email/password form suggests usable authentication despite warning text. It can encourage accidental submission of a real password. Remove credential-entry controls from this placeholder as an explicitly approved UI change; preserve its backend 501 contract.
2. **Two conflicting entry paths.** Sign in and Connect operator make users choose between a dead end and the working workflow. Use one naming convention and one reusable masked connection form, with clear local-provisioning guidance. Do not add sign-up, reset-password, remember-me or SSO controls without contracts.
3. **Hidden connected workspace on #login.** Connection state and disconnect controls are not visible there, while a hidden read can run. An explicit connection-only route should show the current connection or form and avoid mounting hidden investigation content. This is a presentation/composition correction, not logout or new authentication.
4. **Error ambiguity.** The connection catch collapses format rejection, 401, timeout and network/backend unavailability into one alert. A request-time 401 has more useful wording. Provide safe constant messages for invalid input, rejected connection and temporary unavailability; never echo error bodies, token substrings, URLs or account-existence claims. Do not claim every 401 is expiry.
5. **Loading/focus gaps.** Disabled controls and changing button text exist, but the form lacks an explicit busy/live progress region and error association to the field. Focus after failure, success, disconnect and asynchronous 401 is not deliberately managed. Add semantic status, linked instructions/errors and post-render focus targets. Guard repeated submission without introducing automatic retries or changing credential validation.
6. **Basic accessibility exists.** Native labels, password masking, alerts, skip link, visible focus outlines, hash-navigation main focus and reduced-motion rules are reusable. Error color must remain supplementary to text. Do not focus hidden/unmounted controls or move focus repeatedly on ordinary renders.
7. **Mobile foundation exists; login-specific proof is thin.** Layout becomes one column under 900px, navigation wraps, and operator padding reduces under 600px. Body minimum width is 320px. Existing tests cover 390px investigation layout and visiting legacy sign-in; they do not comprehensively verify disconnected/error/loading states, small widths, zoom or screen-reader announcements. Long explanatory copy and the full navigation shell can push the connection action down the screen. Prefer a compact branded panel, wrapping text and controls, no fixed-height/overflow-hidden layout, and visible focus at narrow widths.

## Security risks and invariants

The working client does not echo backend error bodies and does not persist credentials. No application credential logger was found in the inspected frontend/backend call sites. The local provisioning CLI intentionally prints a newly generated token once; this is a sensitive administrative output, not something to embed in UI, telemetry, screenshots or application logs. Do not claim that external proxy/process logs or browser extensions were audited.

The legacy generic client can display a string `detail` response verbatim and lacks the investigation client's destination/redirect policy. It currently carries no operator credential, but its unnecessary password form creates an avoidable disclosure surface. Its 422-array UI sanitizer does not establish that the raw server response cannot contain validation input. Existing backend tests verify a valid placeholder login does not echo the password; malformed-secret response coverage is limited. Do not broaden backend behavior silently in a UI-only phase; remove the production UI's password submission and record any later API redaction hardening separately.

Masked input and `autoComplete="off"` are usability/privacy controls, not protection against a compromised browser, extensions or XSS. Preserve inert rendering of case text and existing transport restrictions. No token reveal/copy button, token fragments in status, browser storage, URL token, build-time credential, credential analytics or hardcoded production/test token in application code is permitted. Fixed test-only credentials belong only in isolated tests.

No server-side operator rate-limit/session-management capability was found in this flow. Do not add fake lockout timers, idle countdowns or client-only security claims. Remote deployment, identity management, password authentication and revocation infrastructure require separate approval.

## Exact minimal proposal: Phase 7F

1. Repurpose the existing LoginPage presentation as a reusable, branded **Operator connection** view. One masked token field, concise explanation, connection action, safe state messages and provisioning guidance. Remove email/password inputs and calls to authService from this view. Do not delete/change the backend placeholder or generic API contracts.
2. Keep InvestigationWorkspace as the sole owner of the service instance/credential connection. Pass only presentation callbacks/state to the reusable view; do not lift the token into App, context, URLs or storage.
3. Use #login as an explicit connection-only surface within that existing owner. Disconnected users see the same form as protected destinations. Connected users see connection status, Disconnect operator and an explicit Open cases link. Do not mount hidden EvidenceSearch on this route. Do not automatically disconnect on navigation or automatically generate reports/submit writes.
4. Keep direct protected-route gating in place, so connecting at a case/evidence link preserves the destination without an external return URL or new router. Keep the current case/generation keys and case-leaving state boundary. Visiting the connection page is still leaving a case, not a new persistence feature.
5. Rename the navigation/title to Operator connection. Reuse existing ShadowVault mark/colors/typography and responsive styles. Add no stock SOC statistics, unsupported security badges, identity fields or fake authentication choices.
6. Provide accessible busy/error states and deliberate focus after connection outcomes/disconnect. Use existing required/length and service validation; do not silently trim or reinterpret secrets. Keep the token masked and clear it on submission. Use safe status-based messages and manual re-entry/retry. Explain that disconnect/reload clears transient work; do not block urgent disconnect with a confirmation requirement.

### Proposed file inventory

- `frontend/src/pages/LoginPage.tsx`: replace the unused password-auth presentation with reusable operator-connection presentation.
- `frontend/src/features/evidence/InvestigationWorkspace.tsx`: reuse that presentation, retain existing auth ownership, safe outcome/focus handling, and connection-only rendering.
- `frontend/src/App.tsx`: route #login through that owner rather than render a second login form beside a hidden workspace; update title.
- `frontend/src/components/Layout.tsx`: align the entry label and supported-method guidance.
- `frontend/src/styles.css`: scoped connection-page responsive/accessibility refinements.
- `frontend/tests/browser/authentication.spec.ts` (new): focused connection/navigation/privacy/state workflows.
- `frontend/tests/browser/investigation.spec.ts`: update the existing legacy-sign-in UI expectation to the newly approved entry experience, retaining its mobile regression coverage.
- `frontend/tests/investigation.test.mjs`: add contract regressions if needed for connection validation/failure/cancellation coverage; do not alter the service merely to fit UI tests.
- `docs/phase7f-authentication-login-implementation-report.md` (new): implementation inventory, results and boundaries.

No changes are expected to `features/evidence/service.ts`, `services/{auth,http,api}.ts`, backend authentication/configuration/models/routes, migrations, agents or dependency files. Reassess any demonstrated need rather than quietly expanding this inventory. No new current-user endpoint is needed merely to show “Operator connected.”

## Testing plan for the proposed implementation

Retain backend tests for login 501/no cookie/no valid-password echo, invalid payloads, wrong credential types, inactive operators, expired/revoked agents and cross-case/evidence authorization. No backend mutation is proposed. Keep existing service tests for header-only credentials, unsafe destination rejection, sanitized 401, disconnect, aborted late responses and no automatic writes.

Add browser coverage for direct #login and protected deep links; masked entry/no password or username controls; empty/invalid token, rejected token, timeout/network failure and manual retry; success with zero evidence; busy status and duplicate-submit prevention; disconnect/401 clearing and focus; connected #login without hidden evidence fetch; preserved destination after connection; no private data/token in rendered messages, URLs, storage or browser console; no /auth/login request; keyboard Enter/Tab/skip link; 320px/390px responsive states and zoom review. Use fake credentials only in isolated fixtures, never real operator input or recorded browser traces.

Rerun the full backend, frontend services, TypeScript/build and complete browser suite for Phase 7F, including Phase 7D same-case continuity, case isolation and report/indicator retry tests. Keep Windows collector/upload regression and read-only database integrity/revision checks. The existing Phase 7D baseline is **152 backend, 44 frontend service, 65 browser tests passing**, with TypeScript/build and Windows regression passed. These counts are prior results, not tests executed during this audit.

## Database, dependencies and rollback

Database remains **0008**. No schema, records, migration, new dependency or framework change is required. A database backup/migration operation is unnecessary for this UI-only proposal. Do not add a session table or persistent token/report store.

Rollback would restore only the approved frontend changes and associated test expectations to the pre-Phase-7F state. No database downgrade or ownership/custody/history rollback is involved. A deployment/tab reload itself clears transient state, so communicate that boundary; do not add storage to bypass it. If implementation requires new authentication semantics or backend identity data, stop and obtain separate scope approval.

## Audit verification and conclusion

Read-only SQLite inspection returned **0008**, `integrity_check = ok`, and **0 foreign-key violations**. Database SHA-256 is unchanged:

`8f8e520eb9e23d2354652990d114fcb5895f7f1b5e293f0135299f279acde969`

Only `docs/phase7e-authentication-login-audit.md` was created. Before/after fingerprints verify source, configuration, dependencies, migrations, prior documentation and the database remain unchanged. No tests were run for this documentation-only task. No login/authentication implementation, AI, automation, teams/RBAC or background workflow was added.

Phase 7E Authentication & Login UX Audit complete — awaiting approval before implementation.
