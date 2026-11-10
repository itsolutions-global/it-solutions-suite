# Contributing to IT Solutions Global Corporate Triad

Thank you for your interest in contributing to the **IT Solutions Global Corporate Triad** (`CorePulse`, `NexusShield`, and `EchoStream`).

We are committed to building an autonomous, local-first developer operating system with zero external runtime bloat.

---

## 🏛️ The Permanent Technical Doctrines

Before submitting a Pull Request, please ensure your code respects our core architectural doctrines:

1. **Zero External Runtime Dependencies**:
   - The entire production runtime MUST execute on the **Python standard library (Python 3.8+)**.
   - No `pip` runtime wheels may be added to `install_requires` in `setup.py`.
   - Dev/testing tools (e.g. `pytest`, `flake8`) are permitted for developer tooling, but core engines must run with zero third-party dependencies.

2. **100% Local-First Privacy (Zero Telemetry)**:
   - No analytics beacons, tracking cookies, or surveillance telemetry.
   - User data lives exclusively in local SQLite WAL databases (`*.sqlite3`) or local JSON vaults.

3. **Sub-15ms Latency & Lock-Free Concurrency**:
   - Database transactions must use SQLite WAL (`PRAGMA journal_mode=WAL`) and proper busy handlers.
   - Desktop HUD and Omnibar routines must spawn and react in under 15 milliseconds.

4. **100% Test Coverage Standard**:
   - Every new feature, endpoint, or security rule must include unit tests.
   - All tests must pass before merging.

---

## 🛠️ Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/itsolutions-global/it-solutions-suite.git
cd it-solutions-suite

# 2. Run test suites across all product engines
python -m unittest discover -s products/corepulse/tests
python -m unittest discover -s products/nexusshield/tests
python -m unittest discover -s products/echostream/tests

# 3. Launch CorePulse in local development mode
python products/cli.py pulse --port 8080 --debug
```

---

## 📋 Pull Request Guidelines

1. **Branch Naming**:
   - `feat/feature-name`
   - `fix/bug-description`
   - `perf/optimization`
   - `docs/clarification`

2. **Commit Conventions**:
   Follow Conventional Commits: `feat(corepulse): ...`, `fix(nexusshield): ...`, `docs: ...`.

3. **Air-Gap Quarantine Notice**:
   - Code submitted must never contain proprietary internal credentials, private tokens, or confidential sidecars.

---

## 💬 Community & Discussions

Have an idea or question? Open a thread on our [GitHub Discussions](https://github.com/itsolutions-global/it-solutions-suite/discussions) or submit feedback directly from the Cockpit UI (`[💬 Feedback]`).
