# Synthetic investigation demonstration

Use only a fresh isolated installation prepared with [Setup](setup.md). Do not run these steps against existing investigation data. Nothing is seeded automatically. The two files in [demo-data](demo-data/) are harmless invented text, not anonymized real evidence. AI stays disabled for this walkthrough.

## 1. Connect and create the case

Pause recording while provisioning/pasting the dedicated operator token. Open Cases and connect. Create:

- Title: `DEMO — Workstation log review`
- Description: `All files, indicators and occurrence events are synthetic training material. No real incident or network activity is represented.`
- Severity: low (investigator-selected, not automatically scored).

Open the case, note its generated ID and change status from open to investigating. Show the new revision/update time and Case History. Do not use proposed six-state lifecycles from historical design documents.

## 2. Collect one fixture

Collection uses the existing API and Windows CLI, not a browser upload wizard. Keep terminals and credentials out of recording. In PowerShell at the isolated repository root, first run this line and paste only the dedicated operator token at the hidden prompt:

```powershell
$demoSecret = Read-Host 'Demo operator token' -AsSecureString
```

Then run this block. It asks for the case ID created above, registers a demo agent, creates one explicit selected-file job and uploads the fixture. It does not print the agent credential or operator token. It creates real records in the isolated demo database through authorized APIs; it must not target the working database.

```powershell
$ErrorActionPreference = 'Stop'
$demoApi = 'http://127.0.0.1:8000/api/v1'
$demoCaseId = [guid](Read-Host 'Demo case ID')
$demoFile = (Resolve-Path -LiteralPath 'docs/demo-data/demo-workstation-log.txt').Path
$demoToken = [System.Net.NetworkCredential]::new('', $demoSecret).Password.Trim()
$demoHeaders = @{ Authorization = "Bearer $demoToken" }
try {
    $demoAgentBody = @{ name='Synthetic demo collector'; platform='windows'; collector_version='0.1.0' } | ConvertTo-Json
    $demoAgent = Invoke-RestMethod -Method Post -Uri "$demoApi/agents" -Headers $demoHeaders -ContentType 'application/json' -Body $demoAgentBody
    $demoJobBody = @{
        incident_id=$demoCaseId.ToString()
        agent_id=$demoAgent.id
        files=@(@{ source_path=$demoFile; max_bytes=1048576 })
    } | ConvertTo-Json -Depth 4
    $demoJob = Invoke-RestMethod -Method Post -Uri "$demoApi/collection-jobs" -Headers $demoHeaders -ContentType 'application/json' -Body $demoJobBody
    $env:SHADOWVAULT_AGENT_TOKEN = $demoAgent.token
    .\backend\.venv\Scripts\python.exe agents/windows/collector.py --backend $demoApi --allow-http-local --job-id $demoJob.id --file $demoFile
    if ($LASTEXITCODE -ne 0) { throw 'Collection did not complete. Retain this terminal and staged retry; do not create another job blindly.' }
}
finally {
    Remove-Item Env:SHADOWVAULT_AGENT_TOKEN -ErrorAction SilentlyContinue
    $demoToken = $null
    $demoHeaders = $null
    $demoSecret = $null
}
```

The receipt contains a local source path, so do not publish terminal output. The current collector version is0.1.0; this field describes the existing collector, not a provider version. Keep the original fixture unchanged until collection finishes. The optional notes fixture can be collected through a separate explicitly approved job.

If upload fails temporarily, use the same terminal/job/file and existing staged copy. Do not regenerate the case, agent or manifest merely to retry:

```powershell
$env:SHADOWVAULT_AGENT_TOKEN = $demoAgent.token
try {
    .\backend\.venv\Scripts\python.exe agents/windows/collector.py --backend $demoApi --allow-http-local --job-id $demoJob.id --file $demoFile
    if ($LASTEXITCODE -ne 0) { throw 'Retry failed; inspect readiness and private storage before continuing.' }
}
finally { Remove-Item Env:SHADOWVAULT_AGENT_TOKEN -ErrorAction SilentlyContinue }
```

After success, clear `$demoAgent` and close the private terminal. Do not publish the credential or manually fabricate receipts/hashes. The collector calculates SHA-256 from the actual bytes and the backend independently verifies them.

## 3. Evidence, notes and timeline

Refresh Case evidence, open the fixture and show filename, size, digest and verification state. Add tags `demo,synthetic` and a note stating that the file is invented training text. Evidence acquisition verification is historical; it is not continuous monitoring or a maliciousness verdict.

From the evidence details, record a manual timeline observation for `2026-01-15T09:05:00+00:00`, title `Synthetic documentation-address reference`, description `Training text only; no actual network connection is asserted.` Show the case timeline and source link. Occurrence time is fictional and explicit; recording time remains server-generated.

Show custody separately from Case History. If demonstrating download, explicitly prepare/save the verified copy and explain that custody records preparation, not confirmed delivery/save. Never execute evidence.

## 4. Recorded indicators and correction

From the evidence context, add stored evidence SHA-256 and filename observations using the existing source options. Add the manual domain `telemetry.example` with a training-text locator. Do not connect to or enrich it.

For a correction example, add IP `192.0.2.11` with locator `Intentional training transcription error; see synthetic fixture`. Use the correction action to append `192.0.2.10` and explain the correction. Show both records and the evidence filter. An indicator is a recorded observation, not a threat verdict. Do not overwrite the original or add false custody/history entries.

## 5. Report and optional AI explanation

Create the report draft and expand evidence, timeline and indicator citations. Show case identity, snapshot time and limitations. Text saving is available, but drafts are not persisted/signed/PDF reports. View/download only synthetic material; local copies cannot be revoked.

Leave AI unconfigured in the ordinary demo and show its truthful unavailable state if needed. Explain metadata selection, server citations and guided navigation. A separately recorded existing deterministic browser-test fixture must be visibly labeled **Synthetic deterministic provider — not a live model result**. No normal demo configuration may use the synthetic OpenAI/Gemini adapters or their remote-count exception. This phase does not approve a live provider evaluation.

## 6. Finish and capture

Close the case explicitly if desired, show Case History, then disconnect. Leaving a case/reloading clears transient drafts and pending work. Do not promise persistent reports or automatic recovery across reload.

For a 6–8 minute walkthrough: connection/case → evidence/verification → timeline/custody → indicator correction → cited report → limitations. Capture a case hero, evidence detail, correction panel, timeline and report at consistent legible desktop size; add one mobile shot. Keep safety/snapshot disclosures visible. Pause credential entry and suppress unrelated notifications/tabs. Review every frame for paths, identities and credentials before publication. No screenshot, video or public deployment is supplied by these text fixtures.
