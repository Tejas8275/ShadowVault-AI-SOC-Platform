# Use the AI Briefing button with fixed synthetic cases

This is an explicitly invoked browser evaluation, not production AI enablement. It uses the same four fixed fixtures and Gemini adapter as the approved synthetic evaluator. No normal case/database data is sent. No `.env` setting is changed by the launcher.

From the repository root, run a separate backend terminal:

```powershell
.\backend\.venv\Scripts\python.exe -B tests/gemini_browser_demo.py --run-approved-synthetic
```

It privately uses the existing Gemini key/model and operator digest. It creates only an in-memory fixture database and binds to loopback8010. The ordinary backend and database are not replaced. Shutdown discards all fixture state. Uploads, edits, notes, indicator submissions and downloads are deliberately blocked. Existing authorization still protects reads and AI generation; the configured operator token authenticates against a synthetic identity in this isolated database.

In a second terminal at the repository root:

```powershell
$env:VITE_API_BASE_URL='http://127.0.0.1:8010/api/v1'
$env:VITE_INVESTIGATION_API_BASE_URL='http://127.0.0.1:8010/api/v2/investigation'
try { npm --prefix frontend run dev -- --port 5180 --strictPort }
finally {
    Remove-Item Env:VITE_API_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:VITE_INVESTIGATION_API_BASE_URL -ErrorAction SilentlyContinue
}
```

Use a new terminal without pre-existing URL overrides; close it after stopping the demo. Open **http://127.0.0.1:5180/#cases**, connect with your existing operator token privately, and open **Synthetic Phishing Investigation A**. Expand **AI Briefing** and click **Generate AI Briefing** once. The server calls Gemini only for exact fixture metadata and resolves its selected citations. It does not produce free-form chat or verdicts.

Requests retain the existing30-second deadline, token/output limits, one-request capacity, cooldown and process usage budget. Provider failures may still occur; wait and retry explicitly. No automatic retry or remote call occurs merely by opening a case. Do not restart to evade usage controls.

The fixed synthetic titles are part of the evaluated fixtures, not threat determinations. The injection case contains intentionally hostile training text, which remains untrusted data. Original-file storage keys are fictional, not real evidence; acquisition hashes are fixture metadata. Do not claim these fixtures were collected or verified uploads.

This browser mode reuses the approved synthetic remote-count exception only for fixed fixtures. Production local-only counting, normal authentication/configuration, OpenAI/Gemini adapter code and database0008 remain unchanged. Do not point a normal deployment at this test server or adapter. No external host binding option is supplied.

Verification: 226 backend tests passed, including the two isolated browser-demo safety tests and existing Windows collector regressions. The demo API health check and frontend HTTP check passed. The existing database remains at revision 0008; SQLite integrity is ok with zero foreign-key violations. Live Gemini generation remains subject to provider availability and quota.

