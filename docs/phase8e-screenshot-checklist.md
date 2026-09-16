# ShadowVault AI — Phase 8E Screenshot Checklist

This checklist defines the visual assets and screen captures required for the official portfolio release, documentation, and stakeholder slide deck.

---

## Technical Capture Standards

- **Resolution**: 1920×1080 (16:9 full HD) or 2560×1440 (QHD) for desktop; 390×844 for mobile responsive captures.
- **Color Profile**: sRGB, Dark Mode default.
- **Theme**: ShadowVault AI SOC Dark Palette (`#06090f` void, `#00e5ff` cyber cyan accents).
- **Format**: PNG (lossless, clean raster rendering).
- **Sanitization**: Ensure no production keys, personal directories, or real-world incident records appear. Only use synthetic fixtures.

---

## Required Screenshot Targets

### 1. Operator Connection (Login Screen)
- **Route**: `/#login`
- **Focus Elements**:
  - `Connect operator` panel centered on the page.
  - Glowing `SV` brand mark and `Investigation access` subhead.
  - Password-masked Operator Token input field.
  - Security footnote: *"The token stays in this tab’s memory and is never saved to browser storage."*
- **Filename**: `docs/screenshots/01-operator-login.png`

---

### 2. SOC Command Center Dashboard
- **Route**: `/#dashboard`
- **State**: Operator authenticated, live backend connected.
- **Focus Elements**:
  - Topbar with live **UTC Operational Clock** and **SOC ACTIVE** pulsing status dot.
  - Collapsible sidebar with high-contrast active route indicator (`Overview`).
  - **System connection** card with green `Backend and database connected` status LED.
  - 4 **Telemetry Metric Tiles**: Authorized Cases, Open, Investigating, Closed.
  - **Risk Profile & Severity Distribution Bar**: Proportional gradient meter showing distribution of Critical, High, Medium, and Low cases.
  - Tactical **Investigation Shortcuts** (`Cases`, `Evidence`, `Timeline`).
  - **Newest Cases** grid with severity badges and ISO creation/update timestamps.
- **Filename**: `docs/screenshots/02-soc-dashboard.png`

---

### 3. Case Workspace & Threat Assessment
- **Route**: `/#cases/{id}`
- **State**: Case loaded with metadata, telemetry, and evidence.
- **Focus Elements**:
  - **Incident Command Header**: Case title, Severity badge, Status badge, and dynamic **Threat Assessment Score** (e.g. 75/100 or 95/100).
  - Metadata row: Case ID, Status, Revision, Owner, Created, and Last updated UTC times.
  - **Investigation Overview Panel**: Evidence Records, Timeline Observations, Recorded History Revisions, and Investigation Status.
  - Pulsing **Latest recorded activity** indicator.
  - Workspace tabs (`Case evidence` vs `Case timeline`).
  - Case management sidebar with Case History audit tree.
- **Filename**: `docs/screenshots/03-case-workspace.png`

---

### 4. Evidence Inspection & Chain of Custody
- **Route**: `/#cases/{id}/evidence/{evidence_id}` or `/#evidence/{id}`
- **State**: Evidence details loaded with acquisition fields and custody ledger.
- **Focus Elements**:
  - Evidence exhibit title, file size, review state badge (`unreviewed`, `in_review`, `reviewed`).
  - **Evidence Integrity Panel**: Initial upload verification timestamp and subsequent cryptographic check status (`Matches` ✓).
  - **Acquisition Metadata Grid**: SHA-256 hash, Evidence ID, Incident ID, Agent ID, and quick-copy buttons.
  - **Retrieve Evidence Copy** station: Verified preparation feedback and `Save evidence copy` button.
  - **Custody History Timeline**: Sequential chain-of-custody ledger with actor references, hash linkages, and previous hash verification.
- **Filename**: `docs/screenshots/04-evidence-custody.png`

---

### 5. AI Briefing & Safety Boundaries Panel
- **Route**: `/#cases/{id}` (AI Briefing section expanded)
- **State**: AI Briefing generated for the incident.
- **Focus Elements**:
  - Advisory warning card: *"AI output is advisory and is not a threat verdict."*
  - Guided cited review steps (1, 2, 3).
  - Snapshot metadata card: Case title, Case revision, Snapshot timestamp, and Context SHA-256 digest.
  - Source category filter selector (`All returned sources`, `Indicators`, `Timeline`, etc.).
  - Structured `.report-source` citation cards: Source citations (`incident:{id}`, `evidence:{id}`), model selection vs correction context tags, and metadata definition list.
  - Uncertainty and limitations audit list.
- **Filename**: `docs/screenshots/05-ai-briefing-panel.png`

---

### 6. Investigation Report View
- **Route**: `/#cases/{id}` (Case Report section expanded)
- **State**: Report draft generated and ready for export.
- **Focus Elements**:
  - Complete case report header and revision snapshot.
  - Formatted sections for Case Metadata, Evidence Manifest, Timeline Events, Indicator Observations, and Investigator Notes.
  - Export controls: `Save text draft` button (`case-{id}-draft.txt`) and `Close report draft`.
- **Filename**: `docs/screenshots/06-investigation-report.png`

---

### 7. Mobile Responsive View (Bonus)
- **Viewport**: 390×844 (iPhone 14 / standard mobile portrait).
- **Route**: `/#dashboard` and `/#cases/{id}`
- **Focus Elements**:
  - Zero horizontal overflow (`scrollWidth <= innerWidth`).
  - Responsive stacking of metric cards, severity strips, and action buttons.
  - Touch-friendly button hit targets.
- **Filename**: `docs/screenshots/07-mobile-responsive.png`
