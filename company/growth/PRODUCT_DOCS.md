# Enterprise Solutions Official Documentation: The Corporate Triad
### CorePulse • NexusShield • EchoStream
**IT Solutions Global Corporation — Technical Documentation & Growth Division**  
*Document Version: 1.3.0 | Systems: `CorePulse v1.0`, `NexusShield v1.0`, `EchoStream v1.0` | Target Audience: Developers, DevOps, & Technology Executives*

---

## 1. Executive Platform Overview: The Corporate Triad

The IT Solutions Global Enterprise Suite addresses the triple crises of modern technical knowledge work:
1. **Cognitive Drudgery & Context-Switching**: Solved by **CorePulse** (*The System of Action*).
2. **Software Supply-Chain & Credential Leak Risks**: Solved by **NexusShield** (*The System of Defense*).
3. **Meeting Intake Overload & Lost Commitments**: Solved by **EchoStream** (*The System of Perception*).

```mermaid
graph TD
    subgraph Enterprise_Workstation ["Unified Enterprise Workstation Cockpit"]
        ES["EchoStream v1.0<br/><b>System of Perception & Audio Triage</b>"]
        CP["CorePulse v1.0<br/><b>System of Action & Habit Orchestrator</b>"]
        NS["NexusShield v1.0<br/><b>System of Defense & Secret Interceptor</b>"]
    end
    
    subgraph Intake_Engine ["Frictionless Intake & Execution"]
        Omni["Global Quick-Capture Omnibar<br/>(Ctrl+Shift+Space)"] --> CP
        Drop["Ambient Folder Drop<br/>(data/transcripts/)"] --> ES
        Palette["Command Palette<br/>(Ctrl+Space / Cmd+K)"] --> CP
        GitHook["Pre-Commit & CI Gates"] --> NS
    end

    subgraph Core_Convergence ["Autonomous In-Memory Convergence"]
        ES -- "Zero-Click Staged Tasks" --> CP
        ES -- "VoiceGuard DLP Alerts" --> NS
        CP -- "1-Click Security Audit" --> NS
        CP -- "Concurrent SQLite WAL" --> DB[("Local SQLite WAL Store")]
        NS -- "Immutable Audit Logs" --> Audit[("Local Security Audit")]
    end

    subgraph Pro_Continuity ["Pro Cloud Relay (Zero-Knowledge)"]
        CP -. "Client-Side Encrypted Sync (AES-256-GCM)" .-> Relay[("Blind Cloud Relay<br/>0 Plaintext Stored")]
        Relay -. "Sync to Linked Devices" .-> Mobile["Mobile Companion / 2nd Laptop"]
    end
```

### Core Architectural Doctrines
1. **Zero External Runtime Dependencies**: Standard library Python 3.8+ execution without `pip install` bloat or third-party supply chain risks.
2. **100% Local-First Privacy**: Intellectual property, secrets, voice streams, tasks, and telemetry remain entirely on the developer's hardware.
3. **Sub-Millisecond Responsiveness**: Instantaneous command execution, SQLite WAL concurrency, and ultra-low RAM footprint.
4. **Zero-Knowledge Cloud Relay**: When multi-device sync is activated, all payloads are encrypted client-side before touching the network.

---

## 2. CorePulse: Quickstart, Shortcuts & Workflow Guide

CorePulse is an autonomous desktop workspace orchestrator, daily habit loop engine, and executive life OS.

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer / Operator
    participant Omni as Quick-Capture Omnibar (Ctrl+Shift+Space)
    participant HUD as Command Palette (Ctrl+Space)
    participant Engine as CorePulse Orchestrator
    participant DB as SQLite WAL Store

    Dev->>Omni: Press Ctrl+Shift+Space anywhere
    Omni-->>Dev: Floating Omnibar spawns in <15ms
    Dev->>Omni: Type "Deploy auth patch by 4 PM !p1 #security ~30m"
    Omni->>Engine: Stream parsed via Edge NLP in <800ms
    Engine->>DB: Task staged directly into SQLite WAL
    Omni-->>Dev: Success Chime: "Task Staged! Streak Active 🔥"
```

### 2.1 Quickstart Installation & Server Launch

CorePulse runs directly from standard library Python on Windows, macOS, and Linux:

```powershell
# 1. Navigate to the CorePulse repository
cd "e:\It solution\products\corepulse"

# 2. Launch the multi-threaded CorePulse server
python main.py

# 3. (Optional) Custom binding for internal network or debugging
python main.py --host 127.0.0.1 --port 8080 --debug
```

Access the Executive Glassmorphism Cockpit at:  
👉 **`http://127.0.0.1:8080/`**

---

### 2.2 Global Desktop Quick-Capture Omnibar (`Ctrl+Shift+Space`)

The **Quick-Capture Omnibar** is an ambient desktop input HUD that allows instant task, thought, and habit capture in under **800 milliseconds** from any application without context switching.

| Shortcut (Windows / Linux) | Shortcut (macOS) | Action / Context |
| :--- | :--- | :--- |
| **`Ctrl + Shift + Space`** | **`Cmd + Shift + Space`** | **Universal Omnibar Summon**: Floats quick-capture omnibar over any active window in <15ms. |
| **`Enter ↵`** | **`Return ↵`** | Parse shorthand syntax and dispatch directly to CorePulse task backlog. |
| **`Esc`** | **`Esc`** | Dismiss Omnibar immediately. |

#### Omnibar Smart Shorthand Syntax
The Omnibar parses natural stream-of-consciousness thoughts using semantic tags:
- **Priority Tags**: `!p1` (Critical), `!p2` (High), `!p3` (Medium), `!p4` (Low).
- **Categorization Tags**: `#security`, `#dev`, `#meeting`, `#ops`, `#client`.
- **Time Estimates**: `~15m`, `~30m`, `~1h`, `~2h` (automatically sets estimated duration).
- **Due Date Expressions**: `today`, `tomorrow`, `by 4 PM`, `by Friday`.
- **1-Click Security Audit Trigger**: Type `/scan` or `!scan` into the Omnibar to trigger an instant NexusShield security scan across the current workspace without opening a terminal!

```powershell
# Examples of valid Omnibar input:
"Review PR #142 by 3 PM !p1 #engineering ~45m"
"Refactor auth session cookies before deploy tomorrow #security !p2"
"/scan"  # Instantly triggers NexusShield workspace security scan
```

---

### 2.3 Universal Command Palette & Keyboard Shortcuts

Control your entire workstation without lifting your hands from the keyboard:

| Shortcut (Windows / Linux) | Shortcut (macOS) | Action / Context |
| :--- | :--- | :--- |
| **`Ctrl + Space`** | **`Cmd + K`** | **Command Palette HUD**: Toggles full search & automation HUD over any window. |
| **`Ctrl + Shift + Space`** | **`Cmd + Shift + Space`** | **Quick-Capture Omnibar**: 800ms ambient thought and task intake HUD. |
| **`Enter ↵`** | **`Return ↵`** | Execute selected workflow, task creation, or command. |
| **`Alt + 1`** | **`Option + 1`** | Instant Trigger: **Morning Focus Protocol** (`morning_focus_init`). |
| **`Alt + 2`** | **`Option + 2`** | Instant Trigger: **Inbox Zero Triage** (`inbox_zero_triage`). |
| **`Alt + 3`** | **`Option + 3`** | Instant Trigger: **Deep Work Distraction Shield** (`deep_work_shield`). |
| **`Alt + 4`** | **`Option + 4`** | Instant Trigger: **Weekly Velocity & Habit Audit** (`weekly_audit_report`). |
| **`Ctrl + N`** | **`Cmd + N`** | Focus task creation input field. |
| **`Space`** | **`Space`** | When focused on habit/task row: Toggle completion state and increment streak. |
| **`Esc`** | **`Esc`** | Dismiss modal, palette, or omnibar. |

---

### 2.4 Built-in Workflow Automation Engine

CorePulse automates multi-step routines that eliminate manual clicking:
1. **Morning Focus Protocol (`morning_focus_init`)**: Compacts calendar fragments, engages focus shields, and launches project terminals (`Reclaims ~25 mins`).
2. **Inbox Zero Triage (`inbox_zero_triage`)**: Auto-archives promotional clutter and extracts VIP client action items (`Reclaims ~40 mins`).
3. **Deep Work Distraction Shield (`deep_work_shield`)**: Activates domain firewalls and Pomodoro acoustic soundscapes (`Reclaims ~35 mins`).
4. **Weekly Velocity & Habit Audit (`weekly_audit_report`)**: Computes habit consistency, task velocity, time reclaimed, and exports executive debrief (`Reclaims ~40 mins`).

---

## 3. EchoStream: Ambient "Drop-and-Forget" Ingestion Pipeline

EchoStream is the *System of Perception*—capturing speech, meeting transcripts, and thought streams with zero bot disruption and sub-150ms edge latency.

```mermaid
flowchart TD
    DropFile["Drop Transcript into<br/>data/transcripts/ (*.txt, *.json, *.vtt)"] --> Pipeline["Autonomous Ingestion Pipeline<br/>(Background Sentry / API Sweep)"]
    Pipeline --> DLP["VoiceGuard DLP Engine<br/>(Shannon Entropy & Regex Scan)"]
    DLP -- "Redact Exposed Secrets" --> Parser["SemanticStreamParser<br/>(Action Item & Metadata Extraction)"]
    Parser --> Dispatch["Direct Dispatch to CorePulse<br/>(Atomic JSON + SQLite WAL Store)"]
    Dispatch --> Telemetry["Execution Receipt Archived<br/>(0 Cloud Egress • 45 Mins Saved)"]
```

### 3.1 Ambient Folder Drop Ingestion (`data/transcripts/`)

With our **Drop-and-Forget Ingestion Pipeline**, users never have to manually copy, paste, format, or type meeting action items.

#### How It Works:
1. **Drop Any File**: Export or drop meeting transcripts, audio logs, or rough notes (`.txt`, `.json`, `.vtt`, `.srt`) into:
   ```
   e:\It solution\data\transcripts\
   ```
2. **Autonomous Background Sentry**:
   - The autonomous pipeline continuously monitors the directory or executes on-demand sweeps via API (`POST /api/tools/pipeline/scan`).
3. **VoiceGuard Credential Sanitization**:
   - Every file is pre-scanned by EchoStream's **VoiceGuard DLP** engine. Leaked AWS keys, OpenAI tokens (`sk-proj-`), or database URIs are redacted before parsing.
4. **Zero-Click Task Creation**:
   - Extracted deliverables, priorities (`!p1`), due dates, and time estimates are automatically parsed and staged directly into the CorePulse database and SQLite WAL store.
   - The original file is tagged with an execution receipt, preventing duplicate processing.

---

## 4. NexusShield: Code Security, Secret Interceptor & Pre-Commit

NexusShield is an autonomous local-first static application security testing (SAST), secret leak interception, and dependency vulnerability scanner.

```mermaid
flowchart TD
    Action["Git Commit OR Omnibar /scan"] --> Engine["NexusShield Scanner Engine"]
    Engine --> Entropy["Shannon Entropy Analysis (H >= 4.5)"]
    Engine --> CVE["Offline Dependency CVE Audit"]
    Entropy --> Score["Deterministic Security Health Score"]
    CVE --> Score
    Score --> Gate{"Score >= 85?"}
    Gate -- Yes --> Pass["Commit Allowed / Clean Receipt"]
    Gate -- No --> Fail["Block Commit (Exit Code 1)<br/>Masked Preview & Fix Advisories"]
```

### 4.1 CLI Quickstart & Quality Gate Reference

```powershell
cd "e:\It solution\products\nexusshield"

# 1. Print Engine Version
python main.py version

# 2. Run standard audit on codebase
python main.py scan .

# 3. Output Machine-Readable JSON
python main.py scan . --json --output nexus_audit.json

# 4. Enforce CI/CD Quality Gate (Fails with Exit Code 1 if below threshold)
python main.py scan . --fail-under 85
```

---

### 4.2 High-Entropy Secret Detection & Safe Masking

NexusShield combines regex assignment heuristics with **Shannon Entropy** calculations:

$$H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i)$$

| Credential Type | Regex / Heuristic | Severity | Masked Preview |
| :--- | :--- | :--- | :--- |
| **AWS Access Key** | `AKIA[0-9A-Z]{16}` | **Critical** | `AKIA...7890` |
| **OpenAI Secret Key** | `sk-(?:proj-)?[A-Za-z0-9_-]{32,}` | **Critical** | `sk-proj-ab...7890` |
| **Stripe Live Secret Key** | `sk_live_[0-9a-zA-Z]{24,}` | **Critical** | `sk_live_...ef12` |
| **GitHub Personal Token**| `ghp_[0-9a-zA-Z]{36}` | **Critical** | `ghp_...4567` |
| **Private Keys** | `-----BEGIN (?:RSA\|EC )?PRIVATE KEY-----` | **Critical** | `-----BEGIN PRIVATE KEY...` |
| **Database URIs** | `(?:postgres\|mysql\|mongodb):\/\/[^:\s]+:...` | **High** | `postgres://user:***@host/db` |

---

### 4.3 Git Pre-Commit Hook Integration

Drop this script into `.git/hooks/pre-commit` to prevent accidental credential leakage:

```bash
#!/usr/bin/env bash
# .git/hooks/pre-commit
echo "[NexusShield] Auditing staged code for leaked secrets and CVEs..."
python "e:/It solution/products/nexusshield/main.py" scan . --fail-under 85
if [ $? -ne 0 ]; then
    echo "❌ [NexusShield] Security audit failed! Commit rejected."
    exit 1
fi
echo "✅ [NexusShield] Audit passed. Proceeding with commit."
exit 0
```

---

## 5. Zero-Knowledge Cloud Sync Relay (Pro & Triad Continuity)

For professionals operating across multiple workstations, laptops, or mobile devices, the **Cloud Sync Relay** provides instant cross-device continuity without compromising our local-first privacy doctrine.

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer (Primary Device)
    participant Local1 as Primary SQLite WAL
    participant Crypto as Local Crypto Engine (AES-256-GCM)
    participant Relay as Blind Cloud Relay
    participant Local2 as Secondary Device (Laptop/Phone)

    Dev->>Crypto: Generates Local Device Keypair (PBKDF2)
    Dev->>Relay: Posts Blind Encrypted Blob (Ciphertext Only)
    Note over Relay: Relay sees ONLY random ciphertext.<br/>Zero plaintext, zero tasks, zero keys.
    Local2->>Relay: Fetches Encrypted Blob using paired key
    Local2->>Local2: Decrypts locally & merges via CRDT
    Local2-->>Dev: Seamless multi-device synchronization verified
```

### 5.1 The Zero-Knowledge Privacy Guarantee

Traditional cloud task and productivity platforms (Notion, Todoist, Asana) store user data in plaintext on remote cloud databases where employees, sub-processors, or government warrants can inspect every task, note, and conversation.

**Our Zero-Knowledge Architecture Guarantees:**
1. **Client-Side Encryption (AES-256-GCM)**: All tasks, custom playbooks, habit streaks, and meeting extracts are encrypted on your local machine using an encryption key derived from your local device pairing phrase.
2. **Blind Relay Mailbox**: The remote relay server operates strictly as an encrypted pub/sub mailbox. Neither IT Solutions Global Corporation, nor AWS/Cloudflare, nor any hostile cloud eavesdropper possesses the cryptographic key required to decrypt your data.
3. **Zero Plaintext Storage**: If our relay servers were seized, audited, or breached, attackers would obtain only random, authenticated high-entropy ciphertext blobs.
4. **Offline Resilience & CRDT Conflict Resolution**: You can work completely offline on an airplane or in air-gapped facilities. When reconnected, local SQLite WAL state changes automatically reconcile with paired devices using Conflict-free Replicated Data Types (CRDTs).

---

### 5.2 Step-by-Step Device Pairing Instructions

Pairing a secondary laptop, desktop, or mobile device takes **less than 30 seconds** using our unified CLI tool:

#### Step 1: Initiate Pairing on Your Primary Workstation
On your primary machine running CorePulse:
```powershell
it-solutions sync pair
```
**Output**:
```
============================================================
IT SOLUTIONS CLOUD SYNC — DEVICE PAIRING
============================================================
Primary Device:      DESKTOP-ARCH-01 (Registered)
Pairing Code:        PULSE-7482-9104
Pairing Expiration:  04m 58s (Single-use cryptographic nonce)
Fingerprint:         SHA256:e3b0c44298fc1c149afbf4c8996fb92427ae41e...

[QR CODE GENERATED FOR MOBILE COMPANION APP]

Waiting for secondary device handshake...
```

#### Step 2: Link Your Secondary Device (Laptop / Second Machine)
On your secondary workstation or laptop:
```powershell
it-solutions sync link PULSE-7482-9104
```
**Output**:
```
Connecting to Blind Relay...
Exchanging cryptographic keypair via Diffie-Hellman handshake...
Verifying device fingerprint...
✓ Pairing Successful!
Device 'LAPTOP-WORK-02' linked to encrypted sync mesh.
Initial state synchronized: 14 tasks, 4 habit streaks, 2 playbooks.
```

#### Step 3: Verify Sync Mesh Status
Check the status of your paired device mesh at any time:
```powershell
it-solutions sync status
```
**Output**:
```
Sync Mesh:           Active (2 Devices Connected)
Encryption:          AES-256-GCM (Zero-Knowledge)
Last Sync:           1.4s ago (Latency: 42ms)
Pending Changes:     0 (Synchronized)
Relay Health:        100% Operational (Blind Relay Mode)
```

---

## 6. Habituation Architecture: Doubling Daily Productive Velocity

Modern knowledge workers waste **40% of their workday** on tool switching, manual file ingestion, and terminal drudgery.

```mermaid
journey
    title 24-Hour Habituation Flow with CorePulse, EchoStream & NexusShield
    section Morning
      OS Boot & Omnibar Trigger (Ctrl+Shift+Space): 5: Developer
      Morning Focus Protocol (800ms): 5: CorePulse
      Unbroken 90-min Deep Work Block: 5: Developer
    section Midday
      Client Meeting Audio Dropped to data/transcripts/: 5: Developer
      Zero-Click Action Item Ingestion: 5: EchoStream
      Review Staged Backlog in Cockpit: 5: Developer
    section Afternoon
      Quick /scan Security Verification: 5: Omnibar
      Git Pre-Commit Quality Gate: 5: NexusShield
      Daily Closure Audit & Streak Accrual: 5: CorePulse
```

### The 4-Phase High-Velocity Rhythm

1. **Phase 1 (08:30 AM) — Morning Boot**: Hit `Alt+1` to run the **Morning Focus Protocol**. Terminals spawn, calendar timeboxes compact, and notifications mute in <800ms.
2. **Phase 2 (11:00 AM) — Ambient Meeting Ingestion**: Drop meeting notes into `data/transcripts/`. Tasks automatically populate CorePulse without typing or context switching (`Saves ~45 mins`).
3. **Phase 3 (02:30 PM) — Omnibar Speed**: Hit `Ctrl+Shift+Space` whenever an insight strikes. Capture thoughts with `#tags` and priority in <800ms.
4. **Phase 4 (05:00 PM) — Security & Shutdown Audit**: Run `/scan` in the Omnibar to verify zero leaked keys, check off remaining habit streaks, and disconnect cleanly.

---

## 7. Enterprise Tier Matrix & Pricing

| Feature / Capability | Free Core (Forever) | Pro Tier ($9.99/mo) | Triad Bundle ($19/mo) | Enterprise Elite ($49/seat/mo) |
| :--- | :--- | :--- | :--- | :--- |
| **Task & Habit Engine** | Full (Up to 20 items) | **Unlimited** | **Unlimited** | **Unlimited** |
| **Workflow Automations** | 3 executions / day | **Unlimited runs** | **Unlimited runs** | **Unlimited runs** |
| **Quick-Capture Omnibar**| Standard capture | Full Shorthand NLP | **Full Shorthand + /scan** | **Full Shorthand + Team Sync** |
| **Ambient Folder Drop**  | Manual API sweep | Automated Sentry | **Automated + VoiceGuard** | **Multi-Folder Sentry + Webhooks** |
| **NexusShield SAST**     | Full Local Scanner | Full Local Scanner | **Full + Pre-Commit Gate** | **Enterprise CI/CD + Audit Vault** |
| **Zero-Knowledge Cloud Sync** | — | **Included (AES-256-GCM)**| **Included (AES-256-GCM)**| **Dedicated VPC Relay** |
| **Storage Architecture** | Local Atomic JSON | **SQLite WAL Engine** | **SQLite WAL Engine** | **SQLite WAL + Distributed Sync** |
| **Support & SLA**        | Community Issues | Priority Email (<12h)| Priority (<4h) | **Dedicated Slack + 99.95% SLA** |

---

## 8. Verification & Automated Test Suites

```powershell
# 1. Test CorePulse REST API, SQLite WAL Concurrency, & Security
cd "e:\It solution\products\corepulse"
python -m unittest discover tests -v

# 2. Test NexusShield Secret Interception & CVE Auditing
cd "e:\It solution\products\nexusshield"
python -m unittest discover tests -v

# 3. Test EchoStream VoiceGuard DLP, Semantic Parser, & Pipeline
cd "e:\It solution\products\echostream"
python -m unittest discover tests -v
```

*All automated test suites execute in <3.0 seconds with 100% pass rates.*

---
*Authorized by: Chief Commercial & Growth Officer*  
*IT Solutions Global Corporation*
