# CorePulse v1.0
### Autonomous Productivity Engine & Executive Life OS

CorePulse v1.0 is an enterprise-grade, zero-dependency personal productivity platform designed for high-performing executives and technology leaders. It integrates strategic task triage, daily habit streak tracking, intelligent workflow automation routines, and live ROI telemetry into a unified, glassmorphic executive cockpit.

---

## ⚡ Key Highlights

- **Zero-Dependency Python 3 Architecture**: Runs out of the box on standard Python 3.8+ without `pip install` or external package overhead.
- **Multi-Threaded REST API**: Built on Python's `http.server.ThreadingHTTPServer` with asynchronous concurrent request handling, full CORS support, and JSON parsing.
- **Executive Glassmorphism UI**: High-end enterprise dark-mode Single Page Application (SPA) with responsive design, glowing ambient backdrops, flame streak badges, and a live terminal runner.
- **Autonomous Workflow Automation**: Instant trigger execution for executive routines (e.g. *Morning Focus Protocol*, *Inbox Zero Triage*, *Deep Work Distraction Shield*, and *Weekly Velocity Audits*) with live audit log streaming and automatic ROI time-saved computation.
- **Desktop Quick-Capture Omnibar v1.0**: System-wide floating native command capsule (`Ctrl+Shift+Space`) engineered with Python standard library (`tkinter` + `ctypes` Win32 message pump) for sub-30ms pop-up quick task capture, 1-click NexusShield SAST audits, EchoStream VoiceGuard DLP sanitization, and workflow routine execution with zero-latency SQLite WAL fallback.
- **Local Desktop Notification & Habit Sentry Companion**: Zero-dependency cross-platform desktop notification agent (`companion.py`) with Morning Focus Protocol triggers, habit streak lapse alerts, and background daemon scheduling.
- **Enterprise SQLite WAL Backend**: High-throughput SQLite persistence utilizing `PRAGMA journal_mode=WAL` with sub-millisecond concurrent read/write transactions and strict thread-safety.
- **Dual-Storage Contract**: Implements interchangeable storage interfaces (`database.py` atomic JSON and `database_sqlite.py` SQLite WAL engine) sharing the identical API contract.
- **Feature Gating & Tier Matrix**: Built-in subscription verification supporting *Starter*, *Professional*, and *Enterprise Elite* tiers with live in-app plan upgrades.

---

## 🏗️ Architecture & Directory Structure

```
corepulse/
├── corepulse/
│   ├── __init__.py           # Package versioning and metadata
│   ├── config.py             # Runtime config, ports, paths, and tier gates
│   ├── database.py           # Thread-safe persistent JSON store & metrics engine
│   ├── database_sqlite.py    # Enterprise SQLite WAL-mode high-concurrency storage engine
│   ├── workflows.py          # Automation routine definitions and execution runner
│   ├── api_handler.py        # Custom BaseHTTPRequestHandler with REST routing & SPA server
│   └── static/
│       ├── index.html        # Enterprise Executive Cockpit SPA
│       ├── css/
│       │   └── dashboard.css # Glassmorphism dark-mode stylesheet
│       └── js/
│           └── dashboard.js  # Reactive client, workflow terminal, API bridge
├── data/
│   ├── corepulse_store.json  # Atomic JSON database state
│   └── corepulse.sqlite3     # Enterprise SQLite WAL-mode database
├── tests/
│   ├── test_api.py           # Full-stack REST API integration & security test suite (10 tests)
│   ├── test_sqlite.py        # SQLite WAL concurrency and contract unit test suite (10 tests)
│   ├── test_companion.py     # Desktop notification & streak sentry test suite (10 tests)
│   └── test_omnibar.py       # Desktop Quick-Capture Omnibar multi-modal test suite (15 tests)
├── companion.py              # Zero-dependency desktop notification & streak sentry companion
├── omnibar.py                # Desktop Quick-Capture Omnibar v1.0 (GUI + hotkey listener + multi-modal router)
├── main.py                   # CLI entrypoint with graceful signal shutdown
└── README.md                 # Complete documentation and API specification
```

---

## 🚀 Quick Start

### 1. Run CorePulse
From the project root:

```powershell
python main.py
```

Optional CLI parameters:
```powershell
python main.py --host 0.0.0.0 --port 8080 --debug
```

### 2. Access the Cockpit
Open your browser to:
[http://127.0.0.1:8080/](http://127.0.0.1:8080/)

### 3. Launch Desktop Notification & Habit Sentry Companion
Run the companion script for active habituation and streak protection:

```powershell
# View current habit consistency & streak status
python companion.py

# Trigger Morning Focus Protocol notification & workflow
python companion.py --morning

# Audit habit streaks and notify if any are at risk of lapsing
python companion.py --streaks

# Run background habituation daemon (checks morning pulse & evening streak sentry)
python companion.py --daemon --interval 60

# Send custom test notification
python companion.py --notify "CorePulse" "Deep focus block active."
```

### 4. Launch Desktop Quick-Capture Omnibar v1.0
System-wide quick-capture capsule and multi-modal command surface:

```powershell
# Launch background global hotkey daemon (Ctrl+Shift+Space)
python omnibar.py --daemon

# Open floating quick-capture window immediately
python omnibar.py --popup

# Execute a command headlessly via CLI
python omnibar.py -c "task Refactor auth @p1 #backend tomorrow ~45m" --json
python omnibar.py -c "scan ." --json
python omnibar.py -c "run morning" --json
python omnibar.py -c "voice Remind Marcus to rotate token sk-proj-12345 by Friday" --json
python omnibar.py -c "status" --json

# Or invoke through the unified suite CLI harness:
it-solutions pulse --omnibar
it-solutions pulse -c "status" --json
```

---

## 📡 REST API Reference

All responses return standard JSON.

### 1. System Health
- **`GET /api/health`**
  - **Description**: Returns system heartbeat, uptime, version, and DB synchronization status.
  - **Sample Response**:
    ```json
    {
      "status": "healthy",
      "service": "CorePulse Engine",
      "version": "1.0.0",
      "build_id": "CP-2026-RELEASE-1.0",
      "uptime_seconds": 124.5,
      "uptime_human": "00h 02m 04s",
      "timestamp": "2026-10-26T14:02:00Z",
      "db_status": "synced",
      "records_tracked": 6,
      "thread_count": 3
    }
    ```

### 2. Tasks & Habit Routines
- **`GET /api/tasks`**
  - **Query Params**: `?type=task|habit`, `?completed=true|false`
  - **Description**: Lists all active deliverables and habits.
- **`POST /api/tasks`**
  - **Payload**:
    ```json
    {
      "title": "Architect Zero-Trust Mesh",
      "type": "task",
      "category": "Architecture",
      "priority": "critical",
      "estimated_minutes": 60
    }
    ```
- **`POST /api/tasks/toggle`**
  - **Payload**: `{"id": "task-001"}`
  - **Description**: Toggles completion and recalculates habit streak counts.
- **`DELETE /api/tasks?id={id}`**
  - **Description**: Removes task from active backlog.

### 3. Workflow Automation Engine
- **`GET /api/workflows`**
  - **Description**: Returns catalog of executable automation routines.
- **`POST /api/workflows/run`**
  - **Payload**: `{"workflow_id": "morning_focus_init"}`
  - **Available Workflows**:
    - `morning_focus_init`: Sets up daily calendar timeboxes and silences distractions.
    - `inbox_zero_triage`: Classifies inbound emails and auto-generates VIP action items.
    - `deep_work_shield`: Engages distraction firewall and initiates focus tracking.
    - `weekly_audit_report`: Calculates velocity, habit consistency, and generates report.
  - **Sample Response**:
    ```json
    {
      "execution_id": "wf-run-7a8f12c4",
      "workflow_id": "morning_focus_init",
      "workflow_name": "Morning Focus Protocol",
      "status": "success",
      "time_saved_minutes": 25,
      "steps_executed": 5,
      "logs": [
        {"step": 1, "message": "Synchronizing Google & Outlook calendars...", "status": "completed"},
        {"step": 2, "message": "Detecting meeting fragmentation...", "status": "completed"}
      ],
      "summary": "Successfully executed 'Morning Focus Protocol'. Reclaimed 25 minutes of executive time."
    }
    ```

### 4. Productivity Metrics & Streaks
- **`GET /api/metrics`**
  - **Description**: Real-time calculated velocity, productivity score (0-100), habit streaks, and total hours saved.

### 5. Subscription & Feature Gates
- **`GET /api/subscription`**
  - **Description**: Returns active tier (*Starter*, *Pro*, *Enterprise*) and associated feature gating limits.
- **`POST /api/subscription/upgrade`**
  - **Payload**: `{"tier": "enterprise"}`
  - **Description**: Instantly unlocks feature gates.

---

## 🧪 Test Suite

```powershell
# Run API Integration tests
python -m unittest tests/test_api.py -v

# Run SQLite WAL Concurrency & Contract tests
python -m unittest tests/test_sqlite.py -v

# Run Desktop Notification & Habit Sentry Companion tests
python -m unittest tests/test_companion.py -v

# Run All Tests across the product
python -m unittest discover tests -v
```

**Desktop Companion Test Coverage (`test_companion.py`)**:
- `test_01_notification_result_contract`: Validates result serialization & representation
- `test_02_notifier_dry_run_dispatch`: Zero OS side-effects in dry-run mode
- `test_03_notifier_console_fallback`: Resilient fallback alerting on non-GUI/headless environments
- `test_04_habit_streak_sentry_lapsing_detection`: Identifies uncompleted habits and ranks by streak risk
- `test_05_habit_streak_sentry_all_completed`: Zero alert noise when habits are completed
- `test_06_habit_streak_sentry_alert_dispatch`: Dispatches urgency-tiered alerts for habit streaks
- `test_07_morning_pulse_trigger_with_workflow`: Automated morning focus protocol execution
- `test_08_morning_pulse_trigger_without_workflow`: Standalone morning notification trigger
- `test_09_companion_daemon_tick`: Scheduled routine logic and repeat execution guards
- `test_10_cli_execution_flags`: CLI execution with --dry-run, --notify, --streaks, and --json

**SQLite WAL Test Coverage (`test_sqlite.py`)**:
- `test_01_wal_mode_enabled`: Verified PRAGMA journal_mode=WAL
- `test_02_seed_data_initialization`: Seed data parity & verification
- `test_03_tasks_filtering_and_sorting`: Priority and completion status ordering
- `test_04_create_and_update_task`: In-place field updates and persistence
- `test_05_toggle_task_and_habit_streaks`: Dynamic streak counters for habits
- `test_06_delete_task`: Deletion semantics and metrics updates
- `test_07_workflow_execution_and_metrics_increment`: Telemetry recording
- `test_08_subscription_management_and_feature_gates`: Tier gating transitions
- `test_09_tier_feature_gate_enforcement`: Max task/habit limits per tier
- `test_10_high_concurrency_wal_throughput`: 20 threads, 300 mixed read/write ops with 0 errors

---

## 🛡️ Production & Security Considerations

1. **Path Traversal Protection**: Static asset resolver enforces strict boundary checks (`relative_to` validation) preventing directory traversal attacks.
2. **Atomic JSON State Updates**: State changes are written to `.tmp` files before being atomically replaced to protect against corruption during power or process interruptions.
3. **Multi-Threaded Concurrency**: Re-entrant locks (`RLock`) prevent race conditions during high-concurrency task mutations and workflow metric increments.
