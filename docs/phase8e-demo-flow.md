# ShadowVault AI — Phase 8E SOC Demo Walkthrough Guide

This guide outlines the recommended demonstration flow for presenting the **ShadowVault AI** Cyber Security Operations Center (SOC) Command Center interface for portfolio reviews, stakeholder demos, and technical presentations.

---

## Prerequisites & Safety Notice

- Use an isolated environment running on `http://127.0.0.1:8000` (backend) and `http://127.0.0.1:5179` (frontend).
- All demonstration data must be synthetic test material (such as `docs/demo-data/demo-workstation-log.txt`).
- Never use production credentials, live forensic evidence, or private external networks during the demo.
- Keep operator tokens out of public video/screen recordings.

---

## Step-by-Step Demo Flow

### Step 1: Login & Operator Access Control
1. **Navigate to Application Root**:
   - Open browser at `http://127.0.0.1:5179/#dashboard`.
   - Highlight the **Operator Connection** panel: clean dark enterprise aesthetic, strict privacy notice ("Token stays in tab memory; never persisted to localStorage or cookies").
2. **Authenticate with Provisioned Token**:
   - Enter provisioned operator token (`sv_operator_...`).
   - Click **Connect operator**.
   - Observe the live connection transition: green status beacon appears with "Operator connected" feedback.

---

### Step 2: SOC Dashboard & Portfolio Overview
1. **Command Center Overview**:
   - Point out the **Live Topbar**:
     - Synchronized **UTC Operational Clock** (`HH:mm:ss UTC`).
     - Real-time **SOC ACTIVE** telemetry beacon.
     - Collapsible tactical sidebar (demonstrate toggle between 240px wide nav and 76px compact icon rail).
2. **System Health & Connection Widget**:
   - Show the **System connection** diagnostic card: real-time status LED and database connectivity pill.
3. **Investigation Portfolio Metrics**:
   - Walk through the 4 `.metric` telemetry tiles: Authorized Cases, Open, Investigating, and Closed counts.
   - Point out the **Risk Profile & Severity Distribution Bar**: colored multi-segment proportional meter reflecting Critical, High, Medium, and Low cases across the portfolio.
4. **Recent Cases Feed**:
   - Highlight the tactical case cards: severity chips, investigator-assigned status tags, and ISO timestamps.

---

### Step 3: Open Investigation Case Workspace
1. **Navigate to Case Workspace**:
   - Click on an active investigation (e.g., `Browser fixture` or `Workstation log review`) via `#cases/{id}`.
2. **Case Header Command Banner**:
   - Show the dynamic **Threat Assessment Score** (e.g., Critical: 95/100, High: 75/100, Medium: 50/100, Low: 25/100) with animated progress bar.
   - Point out the case metadata badges: Case ID, Status, Revision, Owner, Created, and Last Updated.
3. **Case Intelligence Panel**:
   - Highlight aggregate telemetry: Evidence Records count, Timeline Observations, Recorded History Revisions, and Investigation Status.
   - Point out the pulsing **Latest recorded activity** indicator.

---

### Step 4: Evidence Review & Custody Verification
1. **Examine Evidence**:
   - Toggle the **Case evidence** workspace tab.
   - Review the evidence results table with acquisition badges (`Verified at upload` vs `Legacy acquisition`).
2. **Inspect Individual Evidence Record**:
   - Click on an evidence exhibit (e.g., `retrieval-fixture.bin` or `sample.bin`).
   - Demonstrate the **Evidence Integrity** panel:
     - Initial upload verification timestamp.
     - Subsequent cryptographic check result (`Matches` with green checkmark or `Not checked`).
3. **Acquisition Metadata & Copy Controls**:
   - Demonstrate quick-copy buttons for Evidence ID, Incident ID, and SHA-256 with instant "Copied" feedback.
4. **Cryptographic Custody History**:
   - Scroll down to **Custody history** showing chronological chain-of-custody ledger, actor identities, previous hashes, and event hashes.
5. **Secure Binary Download Station**:
   - Demonstrate the **Retrieve evidence copy** station: click "Prepare download", observe verified preparation notice, and click "Save evidence copy" (`evidence-{id}.bin`). Explain that preparation is recorded in custody.

---

### Step 5: Threat Indicators & Incident Timeline
1. **Threat Intelligence Observations**:
   - Return to the Case Workspace and expand **Case Threat Intelligence**.
   - Show recorded observations (SHA-256 hashes, IP addresses, domains, filenames).
   - Emphasize the core SOC principle: *Observations are investigator-recorded candidates, not automated threat verdicts*.
   - Demonstrate correction workflow: original records remain preserved; corrections append new observations.
2. **Case Timeline**:
   - Switch to the **Case timeline** tab.
   - Inspect chronologically sequenced observations with explicit UTC occurrence timestamps and forensic event descriptions.

---

### Step 6: AI Briefing Safety Boundaries & Cited Metadata
1. **Expand AI Briefing Section**:
   - Click **AI Briefing — cited case metadata** inside the case workspace.
   - Highlight the **Advisory Notice**: *"AI output is advisory and is not a threat verdict. No raw evidence files, threat verdicts, or automatic actions."*
2. **Guided Review Protocols**:
   - Walk through the 3 review rules:
     1. Inspect recorded sources (citation establishes traceability, not truth).
     2. Compare occurrence and recording times.
     3. Compare selection against the complete report.
3. **Generate Briefing**:
   - Click **Generate AI Briefing**.
   - View structured metadata citations: Case revision, Snapshot timestamp, Context SHA-256 digest, and Model-selected vs Correction-context sources.
   - Demonstrate category filter dropdown (`All returned sources`, `Indicators`, `Timeline`, etc.).
   - Demonstrate traceability: click "Review section" or "Open source evidence" to directly pivot to the recorded source.
   - Point out the **Uncertainty and limitations** audit list.

---

### Step 7: Investigation Report Generation & Export
1. **Case Report Generation**:
   - Expand the **Case Report** panel.
   - Click **Create report draft**.
   - View the complete structured investigation summary: Case metadata, Evidence manifests, Timeline chronology, Indicator observations, and Investigator notes.
2. **Plain-Text Export**:
   - Click **Save text draft** to download `case-{id}-draft.txt`.
   - Explain that drafts are generated client-side from verified server records without external dependencies.
3. **Disconnect & Session Cleanup**:
   - Click **Disconnect operator** in the top connection bar.
   - Verify that all transient memory is immediately cleared and the interface returns to the clean, unauthenticated login state.
