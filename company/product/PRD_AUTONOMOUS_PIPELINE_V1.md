# Product Requirement Document (PRD)
## Product: Autonomous Background Ingestion Pipeline v1.0
**Document Version:** 1.0.0  
**Status:** Approved for Engineering & QA Implementation  
**Author:** VP of Product & Production  
**Target Delivery Window:** Sprint 8 (Q1 2027)  
**Distribution:** CEO, CTO (Lead Coder), CQO (QA Auditor), CCO (Growth Manager), Head of Research  

---

## 1. Executive Summary & Strategic Rationale

### 1.1 Vision & The "Drop-and-Forget" Paradigm
**Autonomous Background Ingestion Pipeline v1.0** marks the transition of the IT Solutions product suite (CorePulse, NexusShield, EchoStream) from interactive toolsets into a true **autonomous ambient computing engine**.

Until now, processing meeting audio transcripts, voice notes, and action items required human manual intervention: opening a dashboard, clicking upload, or running interactive CLI commands. The Autonomous Ingestion Pipeline eliminates this cognitive overhead completely. By continuously monitoring a designated local drop directory (e.g., `data/transcripts/`), the pipeline autonomously intercepts incoming transcript files, audio logs, and voice dumps, subjects them to **VoiceGuard DLP** secret redaction, parses speakers, decisions, and action items, and injects prioritized tasks directly into the **CorePulse Backlog**—all without a single human click.

### 1.2 Strategic Objectives
1. **Zero-Click Autonomous Intake**: Files dropped from mobile voice recorders, Zoom/Teams transcript downloads, Slack huddle exports, or smart dictation devices are ingested and organized in under 500 milliseconds.
2. **In-Flight DLP Protection**: Every incoming transcript is audited by VoiceGuard *prior* to task extraction. Secrets (API keys, passwords, database URIs, AWS tokens) are redacted and logged to the security audit trail before any task reaches the database.
3. **Multi-Format Ingestion**: Native parsing support for raw text (`.txt`), structured JSON (`.json`), Markdown notes (`.md`), and standard subtitle/caption formats (`.vtt`, `.srt`).
4. **Idempotency & Safe Lifecycle**: Guaranteed exactly-once task injection with SHA-256 deduplication, automatic archival of processed files to `data/transcripts/processed/`, and isolation of corrupted or high-risk files into `data/transcripts/quarantine/`.
5. **Seamless Triad Convergence**: Delivers the programmatic bridge between EchoStream (Perception), NexusShield (Defense), and CorePulse (Action).

---

## 2. Target Personas & Core Problems Solved

### 2.1 Target Personas

```mermaid
graph LR
    P1["Persona A: Dev Lead & Architect"]
    P2["Persona B: Mobile Field Executive"]
    P3["Persona C: Multi-Device Power Builder"]

    P1 --> Need1["Automated Standup & Zoom Transcript Ingestion"]
    P2 --> Need2["Asynchronous Voice Memo Dumps from Phone"]
    P3 --> Need3["Zero-Click Backlog Automation & Pre-Ingestion DLP"]
```

#### Persona A: Alex — Engineering Lead / Tech Founder
- **Context**: Participates in 4–6 video calls daily across Zoom, Teams, and Google Meet with automated transcription enabled on his local machine or cloud.
- **Pain Point**: At the end of the day, has 5 raw transcript files in his `Downloads` folder. Manually opening each, reading 45 minutes of dialogue, extracting action items, and adding them to CorePulse takes 30–45 minutes of tedious administrative labor.
- **Solution**: Alex configures his download directory or sync folder to `data/transcripts/`. The moment a meeting concludes and the file lands, tasks appear organized by priority in his CorePulse backlog.

#### Persona B: Marcus — Startup CEO / Mobile Operator
- **Context**: Conducts investor calls, customer interviews, and spontaneous voice notes while driving, walking, or travelling. Uses mobile dictation apps (Apple Voice Memos, Whisper mobile exports, Otter export dumps).
- **Pain Point**: Voice notes are synced to desktop via iCloud/Dropbox/Syncthing, but remain dormant audio or text files because Marcus lacks time to review them.
- **Solution**: Marcus sets his phone's auto-sync folder to `data/transcripts/`. When he arrives at his workstation, his spoken commitments are already parsed, prioritized, and waiting in CorePulse.

#### Persona C: Elena — Compliance-Minded Security Engineer
- **Context**: Oversees sensitive code and infrastructure discussions.
- **Pain Point**: Team members frequently drop transcripts containing staging passwords, test tokens, or client PII into shared directories, exposing the team to data breaches.
- **Solution**: The Autonomous Pipeline runs VoiceGuard DLP over every line, stripping credentials and generating security incidents in NexusShield before any task reaches persistent storage.

---

## 3. System Architecture & Ingestion Lifecycle

```mermaid
flowchart TD
    subgraph Drop Directory Layer
        DROP["Drop Directory: data/transcripts/<br/>(Monitored by Background Daemon)"]
        FILE_IN["Incoming Files: .txt, .json, .vtt, .srt, .md"]
    end

    subgraph Pipeline Stages (Autonomous Runtime)
        STAGE1["1. File Detection & Debounce<br/>(Wait for write completion / lock release)"]
        STAGE2["2. Hash & Deduplication Check<br/>(SHA-256 vs SQLite Processed Registry)"]
        STAGE3["3. VoiceGuard DLP Audit & Redaction<br/>(120+ secret patterns + Shannon entropy)"]
        STAGE4["4. Semantic Transcript Parser<br/>(Extract speakers, decisions, action items)"]
        STAGE5["5. CorePulse Backlog Ingestion<br/>(REST API / SQLite Direct Persistence)"]
        STAGE6["6. Lifecycle Archival<br/>(Move to /processed or /quarantine)"]
    end

    subgraph CorePulse & Cockpit Layer
        BACKLOG["CorePulse Backlog / Daily Pulse<br/>(Tasks with priority, due date, source tags)"]
        AUDIT["NexusShield Security Ledger<br/>(Redacted secrets & incident log)"]
        COCKPIT["Cockpit UI Pipeline Monitor<br/>(Live status, throughput, recent ingestions)"]
    end

    FILE_IN --> DROP
    DROP --> STAGE1
    STAGE1 --> STAGE2
    STAGE2 -->|"New Unprocessed File"| STAGE3
    STAGE2 -->|"Duplicate Hash"| STAGE6
    STAGE3 -->|"Clean / Redacted Text"| STAGE4
    STAGE3 -->|"Critical Security Incident"| AUDIT
    STAGE4 --> STAGE5
    STAGE5 --> BACKLOG
    STAGE5 --> STAGE6
    STAGE6 --> COCKPIT
```

### 3.1 The 6 Pipeline Execution Stages
1. **Detection & Debounce**: Detects new file creation or modification events. Implements an adaptive debounce timer (500ms) and checks file size stability to avoid reading partially written files.
2. **Deduplication Check**: Computes the SHA-256 digest of the raw content and queries the `pipeline_ingest_registry` SQLite table. If the file has already been ingested with an identical hash, it is archived immediately without duplicating tasks.
3. **VoiceGuard DLP Audit**: Passes raw content through the `VoiceGuard` engine. Detects AWS keys, Stripe tokens, OpenAI API keys, GitHub PATs, private keys, database URLs, and passwords. Replaces them with safe hashes `[REDACTED_SECRET: id]` and generates a security event record.
4. **Semantic Transcript Parsing**: Parses the sanitized content using `TranscriptParser`. Discovers speaker turns, filters conversational filler, extracts explicit/implicit action items, assigns priority (`critical`, `high`, `medium`, `low`), estimates duration, and identifies target deadlines.
5. **CorePulse Ingestion**: Dispatches parsed tasks into the CorePulse repository via `CorePulseDispatcher` (attempting REST API `POST /api/tasks`, with zero-downtime fallback to direct SQLite `database_sqlite.py` writes).
6. **File Lifecycle & Archival**: Moves the original file from the root drop folder into `data/transcripts/processed/YYYY-MM-DD/`, or `data/transcripts/quarantine/` if parsing encountered unrecoverable syntax errors or critical compliance blocks.

---

## 4. Comprehensive Feature Specifications

### 4.1 Directory Watcher Daemon

#### 4.1.1 Overview
An asynchronous, lightweight background thread or service running alongside CorePulse and EchoStream that polls or listens for file system events in the drop directory.

#### 4.1.2 Functional Requirements
- **FR-WATCH-01: Configurable Drop Path**:
  - Default path: `data/transcripts/` relative to project root.
  - Configurable via `config.py`, environment variable `COREPULSE_TRANSCRIPT_DROP_DIR`, or Cockpit UI settings.
  - Automatically initializes directory structure on boot:
    - `data/transcripts/` (Drop zone)
    - `data/transcripts/processed/` (Archive zone)
    - `data/transcripts/quarantine/` (Error / quarantine zone)
- **FR-WATCH-02: Zero-Dependency Polling & Inotify/ReadDirectoryChangesW**:
  - Employs resilient file-polling with adaptive sleep (1.0s interval when idle, 200ms when processing) with native OS event fallback.
  - Strictly zero mandatory external pip dependencies (runs entirely on standard Python 3.10+ libraries: `pathlib`, `os`, `shutil`, `hashlib`, `time`).
- **FR-WATCH-03: Write-Safety Debounce**:
  - Checks file size stability across two consecutive reads spaced 300ms apart before reading.
  - Verifies that file handle can be opened with exclusive read access to avoid locking collisions with active writers (e.g., active audio recorder exporting to disk).

---

### 4.2 Multi-Format Ingestion Engine

#### 4.2.1 Supported Formats & Parsing Matrix

| Extension | Format Description | Parsing Strategy |
| :--- | :--- | :--- |
| **`.txt`** | Plain text / Raw voice notes | Line-by-line speaker splitting or heuristic paragraph analysis. |
| **`.md`** | Markdown meeting minutes | Extracts bullet points under `# Action Items`, `# Next Steps`, or general conversational text. |
| **`.json`** | Structured transcript exports | Parses standard formats (EchoStream JSON, Otter JSON, Whisper JSON) extracting `transcript`, `segments`, and `speaker` keys. |
| **`.vtt`** | WebVTT subtitle files | Strips `WEBVTT` headers, timestamps (`00:01:20.000 --> 00:01:24.000`), and extracts voice text tags `<v Speaker>`. |
| **`.srt`** | SubRip subtitle files | Strips subtitle indices and timeline arrows (`-->`), collating dialogue blocks per speaker. |

#### 4.2.2 Functional Requirements
- **FR-FMT-01: Format Normalization**:
  - Standardizes all incoming formats into a unified internal representation:
    ```python
    {
        "source_file": "2026-10-31_sprint_retro.vtt",
        "format": "vtt",
        "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "text": "Full sanitized text...",
        "detected_speakers": ["Alex", "Sarah", "David"],
        "metadata": {"duration_seconds": 1840, "timestamp": "2026-10-31T20:30:00Z"}
    }
    ```
- **FR-FMT-02: Malformed File Handling**:
  - If a file is empty (0 bytes) or corrupted binary data, the pipeline moves it to `data/transcripts/quarantine/` and logs an explanatory warning without crashing the pipeline daemon.

---

### 4.3 VoiceGuard In-Flight DLP Audit & Security Ledger

#### 4.3.1 Overview
Every transcript ingested from the drop folder is audited before task extraction. VoiceGuard scrubs sensitive credentials from the text and reports security statistics to the Cockpit.

#### 4.3.2 Functional Requirements
- **FR-DLP-01: High-Fidelity Credential Interception**:
  - Scans for 120+ regex patterns (AWS, Stripe, OpenAI, Anthropic, GitHub PATs, private keys, database connection strings, passwords).
  - Employs Shannon entropy calculation on alphanumeric tokens exceeding 20 characters to catch random non-standard secrets.
- **FR-DLP-02: Lossless Task Extraction with Scrubbed Text**:
  - Replaces discovered credentials with `[REDACTED_SECRET: <ID>]` in both the stored transcript and any generated task descriptions.
  - Ensures tasks like *"Rotate the AWS key AKIAIOSFODNN7EXAMPLE"* become *"Rotate the AWS key [REDACTED_SECRET: SEC-AWS-KEY]"* to prevent credential leakage in CorePulse task lists.
- **FR-DLP-03: Security Incident Recording**:
  - Writes a security incident log to the local SQLite database (`nexus_incidents` table) noting the filename, timestamp, secret type, and severity (`Critical`, `High`, `Medium`).

---

### 4.4 Automated CorePulse Backlog Ingestion

#### 4.4.1 Functional Requirements
- **FR-ING-01: Automated Task Dispatches**:
  - For each extracted action item:
    - `title`: Extracted actionable summary (e.g., *"Audit payment webhook error handling"*).
    - `type`: `task`.
    - `category`: `Autonomous Ingestion` (or meeting context).
    - `priority`: Auto-classified based on urgency keywords (`critical`, `high`, `medium`, `low`).
    - `due_date`: Auto-classified relative date (e.g., `Today`, `Tomorrow`, `Friday`, or ISO date).
    - `tags`: `["autonomous-pipeline", "transcript", "<source_file_basename>"]`.
- **FR-ING-02: Duplicate Prevention (Idempotency)**:
  - Generates a composite hash for each task: `SHA-256(file_hash + title + assignee)`.
  - Discards exact duplicate tasks if the same file is re-processed or contains redundant repetitions.
- **FR-ING-03: Meeting Summary Attachment**:
  - If the transcript contains an executive summary or decision matrix, the pipeline attaches it as a Markdown note in CorePulse (`notes` table or workspace attachment).

---

### 4.5 File Lifecycle Management & Audit Trail

#### 4.5.1 Functional Requirements
- **FR-LIFE-01: Atomic Archival**:
  - After successful ingestion, moves the file using an atomic rename/move operation to `data/transcripts/processed/YYYY-MM-DD/<filename>`.
  - If a file of the same name exists in the archive, appends a timestamp suffix: `<filename>_<timestamp>.ext`.
- **FR-LIFE-02: Quarantine Isolation**:
  - Unparseable or corrupt files are moved to `data/transcripts/quarantine/<filename>` with a companion error file `<filename>.error.json` detailing the failure reason.
- **FR-LIFE-03: Ingestion Registry Table**:
  - Maintains a persistent record in SQLite:
    ```sql
    CREATE TABLE IF NOT EXISTS pipeline_ingest_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT NOT NULL,
        file_hash TEXT NOT NULL UNIQUE,
        format TEXT NOT NULL,
        tasks_extracted INTEGER NOT NULL DEFAULT 0,
        secrets_redacted INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL, -- 'success', 'quarantined', 'duplicate'
        error_message TEXT,
        ingested_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    ```

---

## 5. UI / Cockpit Visibility Guidelines

### 5.1 Cockpit Pipeline Status Card
In the CorePulse & Triad Cockpit UI (`index.html`), the pipeline status is displayed prominently in the telemetry bar and dedicated Ingestion widget.

```
+----------------------------------------------------------------------------------------------------+
|  AUTONOMOUS INGESTION PIPELINE                            [ STATUS: WATCHING ]  [ 1.2s POLLING ]    |
+----------------------------------------------------------------------------------------------------+
|  Drop Zone: e:/It solution/data/transcripts/                                                       |
|  Throughput: 18 Files Ingested  |  64 Tasks Created  |  3 Secrets Scrubbed  |  0 Quarantined       |
+----------------------------------------------------------------------------------------------------+
|  RECENT INGESTIONS                                                                                 |
|  * [14:22] sprint_planning_2026-10-31.vtt   -> 8 Tasks Created (DLP: 1 Secret Redacted) [PROCESSED] |
|  * [13:05] client_notes_david.txt           -> 3 Tasks Created (DLP: Clean)             [PROCESSED] |
|  * [11:40] quick_memo_mobile.json           -> 2 Tasks Created (DLP: Clean)             [PROCESSED] |
|  * [09:15] corrupt_audio_chunk.tmp          -> 0 Tasks (Unrecognized format)          [QUARANTINED]|
+----------------------------------------------------------------------------------------------------+
|  [ Open Drop Folder ]    [ Trigger Manual Rescan ]    [ View Ingest Audit Log ]                     |
+----------------------------------------------------------------------------------------------------+
```

---

## 6. The Habituation Loop (The Hook Model for Ingestion)

```mermaid
flowchart TD
    IT["<b>Internal Trigger</b><br/>Post-call relief; desire to offload notes without admin work"]
    ET["<b>External Trigger</b><br/>Meeting recorder finishes; user saves transcript to drop folder"]
    ACT["<b>Frictionless Action</b><br/>Save/Drop file once (or zero-touch background sync)"]
    VR["<b>Variable Reward</b><br/>Backlog automatically populated with clean, prioritized tasks & scrubbed secrets"]
    INV["<b>Investment</b><br/>Custom drop directory mappings, automated smart device sync rules"]

    IT & ET --> ACT
    ACT --> VR
    VR --> INV
    INV --> IT
```

- **Trigger**: The physical conclusion of a meeting or voice recording.
- **Action**: Simply saving or syncing a file into `data/transcripts/`.
- **Variable Reward**: Opening CorePulse to find all commitments already structured, prioritized, and ready to execute.
- **Investment**: Linking mobile voice memo automations and configuring custom team folders, creating zero incentive to ever switch back to manual entry.

---

## 7. Non-Functional & Performance SLAs

- **Processing Latency**: < 500ms for a standard 30-minute meeting transcript (approx. 5,000–8,000 words).
- **Idle System Overhead**: < 0.2% CPU utilization and < 15 MB RAM overhead when polling in background.
- **Zero-Dependency Guarantee**: Must execute on vanilla Python 3.10+ without requiring external pip packages (`watchdog`, `pandas`, etc.), ensuring instant portability and zero supply-chain risk.
- **Data Integrity**: Under zero circumstances may a file be deleted or truncated if parsing fails; unparseable files must be safely isolated to `data/transcripts/quarantine/`.
- **Crash Immunity**: Unhandled exceptions during a single file ingestion must be trapped, logged, and isolated without crashing the parent CorePulse server or pipeline daemon.

---

## 8. QA Validation Matrix & Acceptance Criteria

| Test ID | Test Scenario | Acceptance Criteria | Severity |
| :--- | :--- | :--- | :--- |
| **QA-PIPE-01** | Raw Text Ingestion | Dropping a `.txt` file containing 3 speaker commitments parses all 3 tasks into CorePulse backlog in < 500ms. | Critical |
| **QA-PIPE-02** | WebVTT Subtitle Ingestion | Dropping a `.vtt` file with timestamps and `<v Speaker>` tags strips headers and extracts tasks accurately. | Critical |
| **QA-PIPE-03** | In-Flight VoiceGuard DLP | Dropping a transcript containing `sk-proj-12345...` redacts the key to `[REDACTED_SECRET: SEC-OPENAI-KEY]` in CorePulse and logs a security incident. | Critical |
| **QA-PIPE-04** | Deduplication Protection | Dropping the identical file a second time identifies matching SHA-256 and archives it without creating duplicate tasks. | High |
| **QA-PIPE-05** | Write-Lock Safety | Simulating a slowly written file delays ingestion until file size stabilizes, avoiding half-written parsing. | High |
| **QA-PIPE-06** | Corrupt File Quarantine | Dropping an empty (0-byte) or binary `.exe` file moves it safely to `quarantine/` with an explanatory `.error.json` log. | High |
| **QA-PIPE-07** | Offline Server Fallback | If the CorePulse REST API is offline, pipeline falls back directly to SQLite `database_sqlite.py` writes with zero task loss. | High |

---

## 9. Release Milestones & Autonomous Handshake

```mermaid
flowchart LR
    M1["Milestone 1: Pipeline Core Daemon & Watcher (CTO)"] --> M2["Milestone 2: Multi-Format Parsers (.vtt, .srt, .json, .txt)"]
    M2 --> M3["Milestone 3: VoiceGuard In-Flight DLP Hook"]
    M3 --> M4["Milestone 4: CorePulse Ingestion & Lifecycle Archival"]
    M4 --> M5["Milestone 5: Cockpit Status UI & QA Signoff"]
```

- **Immediate Autonomous Handshake**:
  - **CTO / Lead Coder**: Implement the background watcher daemon (`pipeline.py` or `ingestion_daemon.py`), integrating `VoiceGuard`, `TranscriptParser`, and `CorePulseDispatcher` into an automated loop.
  - **CQO / QA Auditor**: Deploy automated test harness matching Section 8 validation criteria (`test_pipeline.py`).
  - **Growth Manager**: Update product documentation and onboarding copy to highlight the "Drop-and-Forget Ambient Backlog Engine".
