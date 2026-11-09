# IT Solutions Enterprise Product Suite
### Unified Corporate 1-Click Distribution & CLI Harness

This directory contains the flagship corporate products of **IT Solutions** alongside our unified multi-platform 1-click installation harness and central command-line tool `it-solutions`.

---

## 📦 Products Included

| Product | Version | Category | Description | Primary Interface |
| :--- | :--- | :--- | :--- | :--- |
| **CorePulse** | `1.0.0` | Autonomous Productivity OS | Executive task & habit cockpit, automated workflow routines, SQLite WAL persistence. | Web GUI (`:8080`) & REST API |
| **NexusShield** | `1.0.0` | Code Security & SAST Auditor | Local-first credential interceptor, offline dependency CVE auditor, health scoring. | CLI & CI/CD Pipelines |
| **EchoStream** | `1.0.0` | Speech & Thought Stream Perception | Spoken transcript parser, VoiceGuard credential DLP redaction, CorePulse task dispatcher. | CLI (`stream`) & REST Client |
| **QuantPulse** | `1.0.0` | Autonomous AI Trading Suite | Indian stock market autonomous trading engine via Flattrade OMS, Gemini 2.5 Flash deliberation, and iron risk guardian. | Web Cockpit (`:8080`) & CLI (`trade`) |

---

## ⚡ 1-Click Installation

### Windows PowerShell
Run the 1-click installer:
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

### Linux / macOS (Unix)
Run the 1-click shell installer:
```bash
chmod +x ./install.sh
./install.sh
```

---

## 🚀 Unified CLI Harness: `it-solutions`

The `it-solutions` tool orchestrates all corporate products from a single entrypoint:

```powershell
# Check corporate infrastructure health across all products
.\it-solutions.bat health

# Check suite and product versions
.\it-solutions.bat version

# Launch CorePulse Productivity Cockpit & REST API
.\it-solutions.bat pulse --port 8080

# Audit any directory or repository with NexusShield
.\it-solutions.bat shield scan <path_to_codebase>

# Intercept and redact spoken credentials with EchoStream VoiceGuard
.\it-solutions.bat stream scan "My staging key is sk-proj-98723418726354128937123987123987" <!-- nexus-ignore: secret-scan -->

# Parse meeting transcript or thought stream and dispatch to CorePulse
.\it-solutions.bat stream parse "Deploy auth patch by Thursday !p1 #security" --dispatch

# Run live EchoStream meeting triage simulation
.\it-solutions.bat stream demo

# Launch Autonomous Transcript Ingestion Pipeline watcher
.\it-solutions.bat stream watch data/transcripts

# Launch QuantPulse AI Trading Cockpit & Engine (Debian VPS or local)
.\it-solutions.bat trade --port 8080 --mode paper

# Trigger single market scan and AI deliberation cycle
.\it-solutions.bat trade --scan-once

# Trigger Emergency Kill Switch and liquidate all positions
.\it-solutions.bat trade --kill-switch
```

*(On Linux / macOS, use `./it-solutions <command>`)*

---

## 🧪 Corporate Test Suite

Run the unified test harness:
```powershell
python -m unittest tests/test_cli.py -v
```
Run individual product test suites:
- CorePulse API & Tools: `python -m unittest corepulse/tests/test_api.py -v`
- CorePulse SQLite WAL: `python -m unittest corepulse/tests/test_sqlite.py -v`
- NexusShield Scanner: `python -m unittest nexusshield/tests/test_scanner.py -v`
- EchoStream Core Engine: `python -m unittest echostream/tests/test_echostream.py -v`
- EchoStream Ingestion Pipeline: `python -m unittest echostream/tests/test_pipeline.py -v`
