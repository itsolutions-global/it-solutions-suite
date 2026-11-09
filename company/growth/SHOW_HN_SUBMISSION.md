# Show HN: CorePulse – Open-core, local-first system of action with SQLite WAL & CRDT sync

**URL to Submit**: `https://it-solutions-global.vercel.app`  
**Alternative / GitHub URL**: `https://github.com/itsolutions-global/it-solutions-suite`  
**Target Community**: Hacker News (`Show HN`)  
**Target Date**: Mid-Week (Tuesday/Wednesday 08:00 AM PT / 11:00 AM ET)  

---

## 1. Title Options

* **Primary (Recommended)**:  
  `Show HN: CorePulse – Open-core, local-first system of action with SQLite WAL & CRDT sync`
* **Alternative (Emphasis on Zero Bloat)**:  
  `Show HN: We built a local-first executive OS in pure Python with zero dependencies`
* **Alternative (Emphasis on Cognitive Architecture)**:  
  `Show HN: An autonomous triad (action, security, DLP perception) that runs 100% on your machine`

---

## 2. Opening Submission Text / Top Comment (by Author)

Hey HN!

I’m the founder of IT Solutions Global. We built **CorePulse** and the **Enterprise Triad** because we were tired of modern productivity software: 400MB Electron memory sinks, cloud lock-in, latency spikes when saving a simple task, and intrusive background telemetry capturing private workflows.

Humans spend ~40% of their day on cognitive coordination drudgery. Our goal was to create an ultra-low-latency, 100% private workstation companion that executes instantly, stores everything locally in SQLite WAL mode, and syncs peer-to-peer using deterministic CRDTs.

### Architecture & Philosophy:

1. **Zero External Runtime Dependencies**:
   * Written in 100% pure Python standard library (`sqlite3`, `http.server`, `urllib`, `ctypes`, `dataclasses`, `hmac`, `hashlib`).
   * No heavy virtualenvs required. Instant startup. Cold boot in < 80ms.

2. **Local-First & Multi-Process SQLite WAL**:
   * All task matrix entries, habit streaks, and audit logs live in a local SQLite database configured with `PRAGMA journal_mode=WAL` and `synchronous=NORMAL`.
   * High-concurrency support: concurrent readers and writers never lock the UI thread.

3. **Autonomous Perception (EchoStream)**:
   * Native system audio loopback capture without third-party meeting bots.
   * In-flight **VoiceGuard DLP**: client-side regex & Shannon entropy sanitization that redacts API keys, credentials, and PII before notes ever hit disk.

4. **Transparent Physical OS HUD (NexusBridge)**:
   * A click-through on-screen HUD frame (`WS_EX_LAYERED`, `WS_EX_TRANSPARENT`) running at 30Hz via Win32 ctypes.
   * Sub-10ms hardware emergency killswitch (`Ctrl+Alt+Escape`).

5. **Cloud Federation (Without Cloud Lock-in)**:
   * Multi-device synchronization via encrypted PBKDF2/HMAC-CTR payloads and Lamport logical clocks over Supabase / PostgreSQL.
   * If the cloud goes down, 100% of the app remains fully functional offline.

### Try it in 5 seconds:

* **Windows**:
  ```powershell
  irm https://it-solutions-global.vercel.app/install.ps1 | iex
  ```
* **macOS / Linux**:
  ```bash
  curl -fsSL https://it-solutions-global.vercel.app/install.sh | bash
  ```
* **PyPI**:
  ```bash
  pip install it-solutions-suite
  python -m corepulse.main
  ```
* **Docker Multi-Arch (`amd64` / `arm64`)**:
  ```bash
  docker run -d -p 8080:8080 itsolutionsglobal/corepulse:latest
  ```

* **Live Web Showcase**: [https://it-solutions-global.vercel.app](https://it-solutions-global.vercel.app)
* **GitHub Repository**: [https://github.com/itsolutions-global/it-solutions-suite](https://github.com/itsolutions-global/it-solutions-suite)

We are releasing CorePulse under a permissive Open-Core model (MIT core, fully self-hostable forever). We’d love your feedback on the architecture, the offline sync model, and the local-first philosophy!

---

## 3. Anticipated HN Questions & Answers (FAQ Prep)

**Q: Why Python standard library instead of Rust / Go / C++?**  
A: Python is pre-installed on virtually every developer machine, data science workstation, and Linux server. By writing strictly to the standard library with zero third-party wheels, CorePulse installs instantly in seconds with zero build toolchain (`cargo`, `gcc`, `node_modules`) overhead. The execution bottlenecks in productivity apps are I/O, rendering, and IPC, not CPU loops — SQLite WAL handles 20,000+ ops/sec effortlessly.

**Q: How does offline CRDT sync handle concurrent task edits?**  
A: We implement Lamport logical clocks combined with deterministic Last-Write-Wins (LWW) conflict resolution at the attribute level. Each entity has an updated timestamp, clock generation counter, and cryptographic hash vector. In conflicting writes, the higher Lamport clock wins, and ties break deterministically on node ID hashes.

**Q: What is the monetization model?**  
A: The core engine, CLI, desktop Omnibar, local SQLite database, and direct P2P sync are free and open-source forever (MIT). For teams and non-technical users who want zero-maintenance managed cloud relays, multi-device backup, and team workspace aggregation, we offer Cloud Sync Pro ($9.99/mo).
