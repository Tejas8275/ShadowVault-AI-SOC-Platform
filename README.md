# ShadowVault_AI
### AI-Powered Cybersecurity Monitoring & Threat Protection Platform

[![Python](https://img.shields.io/badge/Python-3.13%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%203%20(Alembic%200008)-003B57?logo=sqlite&logoColor=white)](https://sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Security Hardened](https://img.shields.io/badge/Security-Hardened%20DFIR%20Standards-critical)](#-authentication--security)

---

## 📌 Overview

**ShadowVault_AI** is a specialized, local-first Digital Forensics and Incident Response (DFIR) workspace and security monitoring platform. Engineered for Security Operations Center (SOC) teams, incident handlers, and cybersecurity analysts, ShadowVault_AI bridges the gap between low-level endpoint evidence acquisition and high-level incident intelligence.

### The Cybersecurity Problem It Addresses

Modern incident response faces critical operational hurdles:
1. **Disconnected Evidence Silos & Chain-of-Custody Gaps:** Traditional incident tools often lack cryptographic lineage tracking between collected files, investigator actions, and final reporting.
2. **AI Hallucinations & Information Leakage:** Incorporating Large Language Models (LLMs) into security operations carries extreme risks of hallucinated indicators, uncontrolled data exfiltration of sensitive payloads, and non-traceable conclusions.
3. **Investigation Workflow Friction:** Analysts must juggle fragmented command-line utilities, manual timeline spreadsheets, and unverified indicator lists, risking missed correlations during active threats.

### The Solution: Secure Monitoring, Analysis & Protection

ShadowVault_AI delivers an integrated platform that empowers security teams to:
- **Monitor & Track Incidents:** Organize security investigations into an atomic **Incident-as-Case** model with strict state lifecycles (`open`, `investigating`, `closed`) and optimistic revision control.
- **Collect & Verify Evidence:** Acquire endpoint files through an isolated, zero-dependency Windows collector CLI that computes SHA-256 digests prior to encrypted staging and authenticated upload.
- **Maintain Cryptographic Chain of Custody:** Track evidence access, review states, annotations, and verified-copy retrievals through an immutable, hash-chained ledger.
- **Correlate Indicators & Events:** Analyze Indicators of Compromise (IoCs) across four core categories—Cryptographic Hashes, IP Addresses, Domains, and Filenames—with full supersession and correction lineage.
- **Safe, Explainable AI Review:** Generate bounded AI threat briefings where every assertion is strictly anchored to server-resolved metadata citations without ever exposing raw binary evidence to external models.

### Purpose: AI, Automation & Security Engineering

ShadowVault_AI unites rigorous security engineering principles with practical AI assistance:
- **Zero Raw Payload Exposure:** AI models never ingest or process raw endpoint bytes; only sanitized, allowlisted metadata is submitted.
- **Traceability Over Unchecked Verdicts:** The system emphasizes traceable citations over autonomous verdicts. Human investigators retain full authority and accountability.
- **Deterministic Defensive Engineering:** Tamper-evident databases, strict memory-only credential lifespans, and restrictive operating system permissions ensure forensically defensible outcomes.

---

# 🚀 Key Features

ShadowVault_AI includes only fully implemented, verified capabilities natively built into the repository.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             SHADOWVAULT_AI SOC                              │
├──────────────────────┬──────────────────────┬───────────────────────────────┤
│  Security Monitoring │  Threat Detection    │  Incident Management          │
│  • Event Chronology  │  • IoC Normalization │  • Incident-as-Case Workflow  │
│  • SOC Telemetry Bar │  • SHA-256 Matching  │  • Revision History Tree      │
│  • System Diagnostics│  • Citation Tracking │  • Transient Report Engine    │
├──────────────────────┼──────────────────────┼───────────────────────────────┤
│  AI Threat Analysis  │  Chain of Custody    │  Endpoint Collection          │
│  • Bounded Context   │  • Hash-Chained Log  │  • Live Selected-File CLI     │
│  • Server Citations  │  • Verified Copy     │  • Pre-Staging Verification   │
│  • Advisory Scoring  │  • Integrity Checks  │  • Retries with Receipts      │
└──────────────────────┴──────────────────────┴───────────────────────────────┘
```

## Security Monitoring

- **Security Event Monitoring:** Centralized monitoring of active investigations, system health diagnostics, and operational status indicators.
- **Threat Activity Tracking:** Chronological, evidence-linked timeline events (`TimelineEvent`) capturing both forensic occurrence timestamps and system recording timestamps with explicit provenance.
- **System Visibility:** Live SOC Command Center topbar equipped with a real-time synchronized UTC operational clock, connection health status beacon, and dynamic case telemetry tiles.
- **Security Analysis Workflow:** Step-by-step investigative progression from initial incident registration to evidence indexing, timeline sequencing, and peer-reviewable case reporting.

## AI-Powered Threat Analysis

- **Bounded AI Context Engine:** Extracts allowlisted case metadata (excluding raw binaries and private analyst note bodies) into an immutable JSON context with a verification digest.
- **Threat Pattern Analysis:** Correlates observed hashes, IP addresses, domains, and filenames against existing case evidence to reveal recurring threat signatures.
- **Risk Evaluation:** Dynamic risk scoring and proportional multi-segment severity distribution meters (`Critical`, `High`, `Medium`, `Low`) reflecting real-time threat exposure.
- **Intelligent Security Insights:** Generates structured AI briefings with server-resolved citation linkages (`incident:{id}`, `evidence:{id}`), explicitly highlighting operational limitations and analytical uncertainties.

## Threat Detection & Protection

- **Threat Identification:** Captures and classifies Indicators of Compromise (IoCs) across four standardized formats:
  - `SHA-256`: 64-character hexadecimal cryptographic digests
  - `IP`: IPv4 and IPv6 network addresses
  - `Domain`: Fully qualified ASCII domain names
  - `Filename`: Endpoint file artifacts and execution names
- **Suspicious Activity Analysis:** Detailed inspection of file properties (byte size, MIME types, collection origin, and upload timestamps).
- **Security Alerts & Indicators:** Real-time visual threat badges, severity strips, and conflict warnings for concurrent modifications.
- **Detection Workflow:**
  $$\text{Target File} \xrightarrow{\text{SHA-256 Hash}} \text{Collection Verification} \xrightarrow{\text{Schema Normalization}} \text{Evidence Linkage} \xrightarrow{\text{Investigation Correlation}}$$

## Authentication & Security

- **User Authentication:** Token-based authentication using cryptographically strong operator tokens. Tokens are matched on the server using `SHA-256` digests; raw tokens are never persisted in the database.
- **Authorization System:** Strict owner-authorized scoping (`authorized_query`) on all `/api/v2/investigation` endpoints. Investigators access only cases and evidence within their authorized purview.
- **Secure API Communication:** RESTful API protected by custom privacy middleware, CORS restrictions, strict cache controls (`Cache-Control: no-store`), and privacy-preserving error responses that avoid echoing rejected inputs.
- **In-Memory Credential Security:** Operator tokens are held exclusively in browser memory closures. Tokens are **never** stored in `localStorage`, `sessionStorage`, or URL parameters, and are cleared instantly upon tab closure or disconnection.

## Security Dashboard

- **Security Overview Dashboard:** High-contrast SOC command center providing an instant bird's-eye view of authorized cases, connection health, and recent investigations.
- **Monitoring Interface:** Real-time summary of case distributions by operational status: `open`, `investigating`, and `closed`.
- **Threat Visualization:** Multi-segment proportional Risk Profile meter displaying the exact distribution of incident severities across the entire authorized portfolio.
- **Analytics Components:** High-density telemetry cards tracking total evidence items, recorded timeline observations, case revision depths, and timestamp of the latest recorded activity.

## Incident Management

- **Incident-as-Case Workflow:** Unifies incidents and cases into an atomic data model with optimistic concurrency control (`revision` tracking) to prevent accidental overwrites.
- **Alert Investigation:** Contextual workspaces featuring dedicated sub-panels for evidence records, chronologies, indicator tracking, and AI-assisted briefings.
- **Security Response Workflow:** Traceable state transitions accompanied by mandatory change reasons recorded in an append-only audit log (`CaseHistoryEvent`).
- **Evidence/Details View:** Comprehensive Evidence Inspector featuring original upload verification digests, subsequent on-demand integrity checks (`Matches` ✓), and acquisition metadata copy widgets.

## Data Management

- **Database Integration:** SQLite 3 persistence powered by SQLAlchemy 2.0 ORM with enforced foreign keys (`PRAGMA foreign_keys = ON`) and Alembic migration tracking (revisions `0001` through `0008`).
- **Data Storage Workflow:** Segregated local storage directories (`backend/var/evidence` and `backend/var/retrieval`) utilizing opaque generated UUIDs and filesystem permissions restricted to owner-only access (`mode=0o700`).
- **Security Event Management:** Attributed chain of custody (`CustodyEvent`) maintaining an SHA-256 linked cryptographic hash chain recording all retrieval and annotation operations.

---

# 🏗️ System Architecture

ShadowVault_AI is organized into a modular, decoupled architecture adhering to strict defense-in-depth principles:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                 │
│               React 19 SPA + TypeScript + SOC Cyber Theme                   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS / JSON (In-Memory Bearer Token)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND APPLICATION                              │
│         Vite Development & Production Bundle (Zero Web Storage Tokens)      │
│         Features: Cases, Evidence, Threat Indicators, Timeline, Briefings   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ RESTful API Calls
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             BACKEND API LAYER                               │
│                         FastAPI + Uvicorn Engine                            │
│  ├── /api/v1 (Acquisition & Collection Endpoints)                           │
│  └── /api/v2/investigation (Owner-Authorized Investigation Workspace)       │
└──────────────────┬───────────────────────────────────────┬──────────────────┘
                   │                                       │
                   ▼                                       ▼
┌─────────────────────────────────────┐ ┌─────────────────────────────────────┐
│  AUTHENTICATION & SECURITY LAYER    │ │       THREAT ANALYSIS ENGINE        │
│  • SHA-256 Token Digest Validation  │ │  • Bounded Context Builder          │
│  • Request-Scoped SQLAlchemy Session│ │  • Citation Resolver & Validator    │
│  • Privacy Middleware & No-Store    │ │  • Optional Reviewed AI Adapters    │
└──────────────────┬──────────────────┘ └──────────────────┬──────────────────┘
                   │                                       │
                   ▼                                       │
┌─────────────────────────────────────────────────────────┐│
│                PERSISTENCE & STORAGE LAYER              ││
│  ├── SQLite 3 (Foreign Keys ON, Schema Revision 0008)   ││
│  ├── Append-Only Case History & Custody Hash Chains     ││
│  └── Isolated Storage (backend/var/evidence, mode 0o700)││
└──────────────────┬──────────────────────────────────────┘│
                   │                                       │
                   ▼                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   SECURITY MONITORING & INCIDENT RESPONSE                   │
│   • Windows Endpoint Collector CLI (Python stdlib, SHA-256 verified)        │
│   • Traceable Evidence Custody Preparation & Delivery Verification           │
│   • Transient Cited Metadata Reports (.txt export, zero persistent drift)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 🛠️ Technology Stack

ShadowVault_AI is built with modern, battle-tested technologies selected for security, performance, and deterministic reliability.

### Frontend
- **Framework:** [React 19.0](https://react.dev/)
- **Language:** [TypeScript 5.9](https://www.typescriptlang.org/)
- **Build Tool:** [Vite 7.3](https://vite.dev/)
- **Styling:** Custom Vanilla CSS (Enterprise SOC Dark Palette: Void `#06090f`, Dark Card `#0c1322`, Cyber Cyan `#00e5ff`, Status Badges)
- **Testing:** [Playwright 1.63](https://playwright.dev/) & Node.js Native Test Runner

### Backend
- **Language:** [Python 3.13+](https://www.python.org/)
- **Framework:** [FastAPI 0.115+](https://fastapi.tiangolo.com/)
- **Server:** [Uvicorn 0.34+](https://www.uvicorn.org/)
- **Validation & Settings:** [Pydantic Settings 2.7+](https://docs.pydantic.dev/)
- **ORM:** [SQLAlchemy 2.0.36+](https://www.sqlalchemy.org/)

### Database & Storage
- **Database:** SQLite 3 with strict foreign key constraints (`PRAGMA foreign_keys = ON`)
- **Migrations:** [Alembic 1.16+](https://alembic.sqlalchemy.org/) (active head: `0008`)
- **Evidence Storage:** Local filesystem storage protected by Windows ACLs and Python `mode=0o700` isolation

### Security & Cryptography
- **Hashing:** SHA-256 cryptographic digests across all evidence files, context snapshots, and chain-of-custody links
- **Authentication:** In-memory bearer token model with server-side SHA-256 matching
- **Data Protection:** No browser web-storage tokens (`localStorage`/`sessionStorage` strictly avoided)
- **Audit Trails:** Immutable append-only `CaseHistoryEvent` and sequentially chained `CustodyEvent` tables

### AI/ML
- **Architecture:** Bounded metadata context builder (excludes raw binary payloads and free-form note text)
- **Citations:** Server-resolved deterministic citation validation (`incident:{id}`, `evidence:{id}`)
- **Provider Adapters:** Modular adapter interface supporting Google Gemini and OpenAI models under strict opt-in local controls

---

# 📂 Project Structure

```
ShadowVault_AI/
├── .gitignore
├── README.md                           # Platform documentation
├── Screenshots/                        # Pre-captured high-resolution SOC UI screenshots
│   ├── Screenshot 2026-09-16 140746.png
│   ├── Screenshot 2026-09-16 140852.png
│   ├── Screenshot 2026-09-16 140914.png
│   ├── Screenshot 2026-09-16 140939.png
│   ├── Screenshot 2026-09-16 141023.png
│   ├── Screenshot 2026-09-16 141046.png
│   ├── Screenshot 2026-09-16 141104.png
│   └── Screenshot 2026-09-16 141124.png
├── agents/                             # Endpoint collection agents
│   ├── README.md
│   ├── core/                           # Shared hashing & transport logic
│   └── windows/                        # Windows selected-file collector CLI
│       ├── README.md
│       └── collector.py
├── backend/                            # FastAPI backend service
│   ├── pyproject.toml                  # Backend dependencies & metadata
│   ├── requirements.lock               # Pinned dependency versions
│   ├── logging.json                    # Opt-in sanitized logging configuration
│   ├── alembic.ini                     # Database migration configuration
│   ├── migrations/                     # Alembic schema migrations (0001–0008)
│   ├── app/
│   │   ├── main.py                     # Application entrypoint & middleware
│   │   ├── cli.py                      # Administrative CLI (operator provisioning)
│   │   ├── api/                        # Route controllers & API routers
│   │   │   └── routes/                 # Endpoint implementations (v1 & v2)
│   │   ├── core/                       # Security, config, and settings
│   │   ├── db/                         # Database connection & migration helpers
│   │   ├── models/                     # SQLAlchemy relational models
│   │   ├── schemas/                    # Pydantic request/response contracts
│   │   └── services/                   # Business logic (custody, AI, reports)
│   └── var/                            # Isolated private evidence storage (0o700)
├── frontend/                           # React 19 + TypeScript frontend
│   ├── package.json                    # Frontend dependencies & scripts
│   ├── vite.config.ts                  # Vite build configuration
│   ├── playwright.config.ts            # E2E browser test configuration
│   ├── src/
│   │   ├── App.tsx                     # Root component & route dispatcher
│   │   ├── main.tsx                    # React DOM bootstrap
│   │   ├── styles.css                  # Enterprise SOC Command Center CSS
│   │   ├── components/                 # Layout, navigation & shell components
│   │   ├── pages/                      # DashboardPage, LoginPage
│   │   ├── features/                   # Domain features
│   │   │   ├── cases/                  # Case overview, workspaces, history, reports
│   │   │   ├── evidence/               # Evidence search, custody ledger, downloads
│   │   │   ├── indicators/             # IoC tracking, normalizers, corrections
│   │   │   └── timeline/               # Chronological event sequencing
│   │   └── services/                   # HTTP client, authentication & health API
│   └── tests/                          # Frontend unit & Playwright browser specs
├── docs/                               # Engineering documentation & audit reports
│   ├── architecture.md                 # System boundaries & architectural design
│   ├── setup.md                        # Production & local installation guide
│   ├── demo-guide.md                   # Synthetic scenario demonstration guide
│   ├── security-operations.md          # Hardening, rotation & operational procedures
│   └── demo-data/                      # Non-sensitive synthetic test fixtures
└── tests/                              # Backend integration & test suites
```

---

# ⚙️ Installation & Setup

Follow these exact instructions to set up a local development and evaluation environment.

### Prerequisites
- **Operating System:** Windows 10/11 (Python 3.13+ recommended for private filesystem permission support)
- **Runtime Environments:**
  - Python `3.13` or `3.14`
  - Node.js `22.18+` & `npm`
  - Microsoft Edge or Chromium (for automated browser testing)

---

### Step 1: Backend Installation & Setup

1. **Navigate to the repository root and create a virtual environment:**
   ```powershell
   python -m venv backend/.venv
   ```

2. **Activate the virtual environment and install dependencies:**
   ```powershell
   .\backend\.venv\Scripts\python.exe -m pip install -c backend/requirements.lock -e "./backend[test]"
   ```

3. **Configure the environment file:**
   ```powershell
   if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
   ```

4. **Initialize the SQLite database schema to head (revision 0008):**
   ```powershell
   .\backend\.venv\Scripts\python.exe -m app.db.migrate
   ```

5. **Provision an authorized operator token:**
   ```powershell
   .\backend\.venv\Scripts\python.exe -m app.cli init-operator --email operator@example.test --name "Lead Investigator"
   ```
   > ⚠️ **Important:** Copy the generated raw token output. It will be printed only once. Add the returned `SHADOWVAULT_OPERATOR_USER_ID` and `SHADOWVAULT_OPERATOR_TOKEN_SHA256` to `backend/.env`.

6. **Start the backend server:**
   ```powershell
   .\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers --log-config backend/logging.json
   ```
   *Health checks:* Verify status at `http://127.0.0.1:8000/health` and API docs at `http://127.0.0.1:8000/docs`.

---

### Step 2: Frontend Installation & Setup

1. **In a new terminal (from the repository root), install npm dependencies:**
   ```powershell
   npm --prefix frontend ci
   ```

2. **Configure frontend environment variables:**
   ```powershell
   if (-not (Test-Path frontend/.env)) { Copy-Item frontend/.env.example frontend/.env }
   ```

3. **Launch the development server:**
   ```powershell
   npm --prefix frontend run dev
   ```

4. **Access the platform:**
   Open `http://127.0.0.1:5173` in your browser. Navigate to **Cases** and paste your provisioned operator token into the masked authentication field.

---

### Step 3: Endpoint Evidence Collection (Optional Live Verification)

To acquire a selected file using the native Windows collector:
```powershell
python agents/windows/collector.py --backend http://127.0.0.1:8000/api/v1 --allow-http-local --job-id <JOB-UUID> --file "C:\Path\To\Evidence.txt"
```

---

# 🔐 Security Workflow

ShadowVault_AI enforces a rigorous end-to-end investigative workflow designed for forensic defensibility:

```
[1. User Interaction]
       │
       ▼
[2. Operator Authentication]  ──> Validates Bearer Token against SHA-256 Digest in Memory
       │
       ▼
[3. Target Acquisition]       ──> Windows Agent stages file, computes SHA-256, verifies limits
       │
       ▼
[4. Ingestion & Verification] ──> Backend validates byte count, re-hashes, stores in mode 0o700
       │
       ▼
[5. Security Analysis]        ──> Investigator creates Timeline Events and links Evidence records
       │
       ▼
[6. Threat Detection]         ──> Ingests IoCs (SHA-256, IP, Domain, File), tracks supersessions
       │
       ▼
[7. Risk Evaluation]          ──> System calculates Threat Assessment Score and Severity Meter
       │
       ▼
[8. AI Briefing Review]       ──> Bounded context query generates server-resolved metadata citations
       │
       ▼
[9. Chain-of-Custody Lock]    ──> SHA-256 linked CustodyEvent created upon retrieval / review
       │
       ▼
[10. Report Generation]       ──> Transient metadata report drafted and exported locally (.txt)
```

1. **User Interaction & Access:** The analyst connects via the web interface using an in-memory operator token.
2. **Data Collection:** The Windows collector stages files locally, enforces directory permissions, validates byte counts, computes an SHA-256 digest, and transmits data over an authenticated API.
3. **Security Ingestion:** The server verifies incoming hashes against the payload, associates the exhibit with the approved job, and commits the evidence record.
4. **Contextual Analysis:** The analyst constructs an attributed timeline of events, cross-linking events with evidence exhibits.
5. **Threat Indicator Normalization:** Candidate indicators (hashes, IPs, domains, filenames) are normalized, validated, and linked to evidence sources with full correction history.
6. **Risk Evaluation:** Real-time metrics compute the case's threat assessment score and update the portfolio-wide risk profile.
7. **Advisory AI Briefing:** If requested, the system compiles an allowlisted metadata context, queries the reviewed AI provider, and maps responses to exact case citations.
8. **Custody & Export:** Verified copies are prepared and logged to the cryptographic chain of custody; case reports are rendered as transient drafts and exported locally.

---

# 📸 Screenshots Section

Pre-captured high-resolution screenshots from the platform's test suite and demonstration runs:

| Module / View | Focus Elements & Capabilities | Preview Reference |
| :--- | :--- | :--- |
| **Authentication Interface** | In-memory masked operator token authentication, privacy guidance | [View Screenshot](#authentication-interface) |
| **Main Dashboard** | Live operational UTC clock, connection diagnostics, telemetry cards | [View Screenshot](#main-dashboard) |
| **System Overview** | Authorized case portfolio, status distribution, and risk meter | [View Screenshot](#system-overview) |
| **Security Monitoring View** | Case workspace, evidence exhibits, and chronological timeline | [View Screenshot](#security-monitoring-view) |
| **Threat Analysis Panel** | Bounded AI Briefing panel with server-resolved metadata citations | [View Screenshot](#threat-analysis-panel) |
| **Alert Management** | IoC tracking (SHA-256, IP, Domain, Filename) & correction lineage | [View Screenshot](#alert-management) |

---

### Authentication Interface
<!-- Placeholder: Authentication Interface / Operator Connection -->
![Authentication Interface](Screenshots/Screenshot%202026-09-16%20140746.png)
*Figure 1: Operator connection interface with scoped in-memory token authentication.*

### Main Dashboard
<!-- Placeholder: Main Dashboard / SOC Command Center -->
![Main Dashboard](Screenshots/Screenshot%202026-09-16%20140852.png)
*Figure 2: SOC Command Center dashboard featuring live UTC clock, system connection status, and operational metrics.*

### System Overview
<!-- Placeholder: System Overview / Case Portfolio -->
![System Overview](Screenshots/Screenshot%202026-09-16%20140914.png)
*Figure 3: Portfolio overview displaying case distribution, risk profile severity bar, and recent investigations.*

### Security Monitoring View
<!-- Placeholder: Security Monitoring View / Case Workspace -->
![Security Monitoring View](Screenshots/Screenshot%202026-09-16%20140939.png)
*Figure 4: Incident command workspace with evidence manifest, threat score, and chronological timeline.*

### Threat Analysis Panel
<!-- Placeholder: Threat Analysis Panel / AI Briefing -->
![Threat Analysis Panel](Screenshots/Screenshot%202026-09-16%20141023.png)
*Figure 5: Bounded AI Briefing panel with explicit advisory boundaries and server-verified citations.*

### Alert Management
<!-- Placeholder: Alert Management / Threat Intelligence & Indicators -->
![Alert Management](Screenshots/Screenshot%202026-09-16%20141046.png)
*Figure 6: Indicator observations management, showing indicator types, source evidence links, and correction lineage.*

---

# 🧪 Testing & Verification

ShadowVault_AI maintains comprehensive test suites covering backend services, cryptographic hashing, database migrations, and end-to-end browser workflows.

```powershell
# 1. Run full backend unit and integration test suite
.\backend\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py' -v

# 2. Run frontend unit tests (Node.js native test runner)
npm --prefix frontend test

# 3. Perform static TypeScript type checking
npm --prefix frontend run typecheck

# 4. Verify production bundle build
npm --prefix frontend run build

# 5. Execute Playwright end-to-end browser tests
npm --prefix frontend run test:browser
```

### Existing Verification Modules

| Test Suite | File / Command | Verification Scope |
| :--- | :--- | :--- |
| **Backend Core** | `tests/test_backend_foundation.py` | FastAPI lifespan, session scoping, database connectivity |
| **Case & Incident API** | `tests/test_incidents.py`, `test_case_history.py` | Case lifecycle, optimistic locking, atomic history tracking |
| **Evidence & Custody** | `tests/test_collection.py`, `tests/test_retrieval.py` | SHA-256 verification, storage permissions, custody chains |
| **Threat Indicators** | `tests/test_indicators.py` | IoC normalization (hash, IP, domain, filename), supersessions |
| **AI Safety & Briefings**| `tests/test_ai_briefing.py`, `test_ai_safety.py` | Bounded context isolation, citation resolution, rate limits |
| **Windows Collector** | `tests/test_windows_agent.py` | Live file staging, 1 MiB chunk hashing, retry idempotency |
| **Browser E2E** | `frontend/tests/browser/*.spec.ts` | Complete user flows in Playwright (auth, cases, downloads, AI) |

---

# 🎯 Future Enhancements

The following roadmap items represent realistic engineering improvements designed for future development phases:

- **Cloud-Native Deployment:** Containerization via Docker, Kubernetes Helm charts, and remote object storage integration (AWS S3 / Azure Blob Storage with customer-managed keys).
- **Multi-Tenant Role-Based Access Control (RBAC):** Expanding beyond single-operator local authorization to tiered team roles (Viewer, Investigator, Lead Analyst, Administrator).
- **External Threat Intelligence Feeds:** Native connectors for STIX/TAXII, MISP, and VirusTotal to cross-reference recorded indicators against global threat feeds.
- **Cross-Platform Endpoint Collectors:** Extending the endpoint collection suite to Linux (via eBPF / auditd) and macOS (via Endpoint Security Framework).
- **Automated Security Orchestration (SOAR):** Webhook dispatchers and incident containment playbooks triggered on specific indicator matches.

---

# 👨‍💻 Developer

**Developer:** Tejas8275  
**GitHub Profile:** [https://github.com/Tejas8275](https://github.com/Tejas8275)  
**Repository:** [https://github.com/Tejas8275/ShadowVault-AI-SOC-Platform](https://github.com/Tejas8275/ShadowVault-AI-SOC-Platform)

---

# 📄 License

This project is licensed under the **MIT License**.

```text
MIT License

Copyright (c) 2026 Tejas8275

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
