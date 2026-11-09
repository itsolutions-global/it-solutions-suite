# EchoStream v1.0: Real-Time Audio & Thought Stream Perception Engine
### IT Solutions Enterprise Product #3

EchoStream is a zero-dependency, local-first perception and intake engine engineered for executives, engineering leaders, and high-velocity knowledge workers. It converts free-form spoken meeting transcripts and fragmented thought streams into structured, prioritized, actionable tasks and commitments—with real-time Voice Data Loss Prevention (DLP) to intercept and redact accidental spoken credentials.

---

## ⚡ Core Capabilities

1. **VoiceGuard Real-Time Spoken Credential DLP**:
   - High-fidelity regex and Shannon entropy scanner tuned for spoken transcripts.
   - Detects and masks AWS keys (`AKIA...`), OpenAI tokens (`sk-proj-...`), Stripe keys (`sk_live_...`), GitHub tokens (`ghp_...`), database connection strings (`postgres://...`), and high-entropy verbalized passwords.
   - Replaces secrets in-place with standardized compliance tokens (`[REDACTED_SECRET: <Type>]`).

2. **Semantic Speech & Thought Stream Parser**:
   - **Meeting Mode**: Extracts action items, speaker owners, key decisions/agreements, commitments, and parking lot/open questions.
   - **Thought Omnibar Mode**: Parses shorthand notes and voice memos with priority tags (`!p1`, `!urgent`), deadlines (`by friday`, `next tuesday`), categories (`#security`, `#devops`), and estimates (`~45m`).
   - Automatically determines session type (meeting transcript vs. thought stream) based on conversational cues and speaker attributions.

3. **Autonomous Background Ingestion Pipeline (Drop-and-Forget)**:
   - Continuously monitors `data/transcripts/` drop directory for incoming transcripts.
   - Native multi-format normalization: plain text (`.txt`), Markdown (`.md`), structured JSON (`.json` - Whisper, Otter, EchoStream), WebVTT (`.vtt`), and SubRip (`.srt`).
   - SHA-256 deduplication registry prevents duplicate task creation.
   - Write-safety debounce window prevents half-written reads on active recording dumps.
   - Automatic lifecycle archival to `data/transcripts/processed/YYYY-MM-DD/` and quarantine isolation to `data/transcripts/quarantine/`.

4. **CorePulse Autonomous Task Dispatcher**:
   - Dispatches parsed action items directly into CorePulse's local REST API (`/api/tasks`).
   - Seamless, in-process fallback to direct SQLite WAL database persistence when CorePulse server is offline. Zero lost tasks.

5. **Zero External Dependencies**:
   - 100% Python 3.8+ standard library.
   - No external speech heavyweights, network calls, or cloud SaaS required for parsing, security redaction, or directory watching.

---

## 🛠 Command Line Usage

### 1. Unified Suite CLI (`it-solutions`)
```bash
# Launch background autonomous transcript watcher daemon
it-solutions stream watch data/transcripts

# Run single one-shot ingestion sweep and exit
it-solutions stream watch data/transcripts --once --json

# Run live executive meeting triage simulation
it-solutions stream demo

# Scan spoken text for credentials and redact in real-time
it-solutions stream scan "My secret staging key was sk-proj-98723418726354128937123987123987" <!-- nexus-ignore: secret-scan -->

# Parse voice memo or thought stream with CorePulse auto-dispatch
it-solutions stream parse "Deploy auth service patch by Thursday !p1 #security" --dispatch

# Parse a meeting transcript file and export JSON
it-solutions stream parse meeting_notes.txt --json
```

### 2. Standalone EchoStream CLI
```bash
# Launch drop directory watcher
python products/echostream/main.py watch data/transcripts

# Single sweep
python products/echostream/main.py watch data/transcripts --once

# Live simulation
python products/echostream/main.py demo

# Voice DLP scan
python products/echostream/main.py scan "Spoken text with AWS AKIAIOSFODNN7ABCD1234 key" <!-- nexus-ignore: secret-scan -->

# Meeting transcript triage
python products/echostream/main.py parse transcript.txt --dispatch
```

---

## 🧪 Automated Test Verification

EchoStream includes comprehensive unit and integration test suites:

```bash
# Core perception engine test suite (11 tests)
python -m unittest products/echostream/tests/test_echostream.py -v

# Autonomous ingestion pipeline & multi-format test suite (8 tests)
python -m unittest products/echostream/tests/test_pipeline.py -v
```

Tests cover:
- Spoken credential interception & redaction
- High-entropy conversational token detection
- Semantic meeting transcript parsing (speakers, action items, decisions)
- Thought omnibar syntax parsing (`!p1`, `#tags`, `~30m`, due dates)
- CorePulse REST API dispatcher & offline DB fallback
- Autonomous drop directory polling & write-safety debounce
- Multi-format ingestion (`.txt`, `.md`, `.vtt`, `.srt`, `.json`)
- SHA-256 deduplication and idempotent archival
- Corrupt/empty file quarantine isolation
- Pipeline telemetry and persistent SQLite registry

