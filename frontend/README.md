# Frontend

React + TypeScript dashboard built with Vite. Requires Node 22.18+.

From this directory:

```powershell
npm ci
Copy-Item .env.example .env
npm run dev
```

Copy `.env.example` only on first setup. The development server uses
`http://127.0.0.1:5173` and refuses to silently switch ports, keeping the backend
CORS allowlist predictable. Start the backend separately using its README.

- `#dashboard`: workspace overview and live database-readiness check.
- `#login`: login form wired to the backend's explicit HTTP 501 placeholder.
- `src/components`: shared responsive layout.
- `src/pages`: dashboard and login views.
- `src/services/http.ts`: JSON requests, timeout, and API error handling.
- `src/services/api.ts`: configurable API base URL.
- `src/services/auth.ts` and `health.ts`: domain-specific service entry points.

Hash navigation covers overview, sign-in, evidence search, and evidence details without a router
dependency. The overview is a public development preview with no private data.
The login form does not create a session, redirect to an authenticated workspace,
or store credentials/tokens in browser storage. Use test credentials only.

`VITE_API_BASE_URL` defaults to `http://127.0.0.1:8000/api/v1`. Vite embeds this
value in the browser bundle; never put secrets in a `VITE_*` variable. Restart
the development server or rebuild after changing it.

Phase 3A adds Timeline navigation and an Add timeline observation form on evidence
details. It uses the same in-memory operator connection and v2 base URL. Enter an
explicit ISO occurrence timestamp with timezone; acquisition times are never
substituted. Unconfirmed submissions retain a frozen payload and UUID for manual,
idempotent retry. A review button reads current observations without leaving the
draft. Navigating away or reloading discards in-memory drafts. See [the guide](../docs/phase3a.md).

```powershell
npm test
npm run typecheck
npm run build
```

Tests use Node's built-in runner and native TypeScript stripping. The production
build also runs strict TypeScript checks. Playwright browser workflows run with
`npm run test:browser` using installed Microsoft Edge and isolated local API/Vite
servers on ports 8769/5179. Run on Windows with the backend environment installed.
`package-lock.json` pins the installed dependency tree; use `npm ci`
for repeatable installs.

`VITE_INVESTIGATION_API_BASE_URL` independently configures the investigation API
and defaults to `http://127.0.0.1:8000/api/v2/investigation`. This is a public URL,
never a token. Open Evidence and use Connect operator with an already provisioned
API token. It stays in memory and is cleared on disconnect, authentication failure,
or reload. Search filters and drafts are also held in memory. No backend login
contract changed. See [Phase 2B-2](../docs/phase2b2.md).

Phase 3B adds Prepare download / Cancel download / Save evidence copy / Discard copy
to evidence details. Binary retrieval shares the in-memory operator client; no token
is placed in a URL or storage. The browser buffers at most 100 MiB of content, checks
response size/format, and revokes temporary download URLs on discard/navigation.
Custody is refreshed after attempts. Preparation does not prove local saving and does
not update subsequent integrity status. See [Phase 3B](../docs/phase3b.md).
