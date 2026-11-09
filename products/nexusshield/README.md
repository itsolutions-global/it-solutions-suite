# NexusShield v1.0
### Autonomous Local-First Code Security, Secret Interceptor & Vulnerability Auditor

NexusShield is an enterprise-grade, zero-dependency static application security testing (SAST), secret leak interception, and dependency vulnerability audit engine. Built in pure standard library Python 3, NexusShield operates 100% locally on the developer's workstation—ensuring intellectual property never leaves the machine.

---

## ⚡ Key Highlights

- **Zero-Dependency Architecture**: Runs out of the box on Python 3.8+ without `pip install` or external library requirements.
- **High-Entropy Secret Scanner**: Detects exposed AWS keys, OpenAI keys (`sk-proj-...`), Stripe live keys (`sk_live_...`), GitHub PATs (`ghp_...`), database URIs, RSA/EC private keys, and arbitrary high-entropy credentials via Shannon entropy calculations.
- **Safe Redaction Engine**: Never exposes raw confidential credentials in reports, logs, or JSON payloads.
- **Dependency CVE Auditor**: Automatically cross-references `requirements.txt` and `package.json` against known CVE advisories (e.g. `requests`, `urllib3`, `pillow`, `pyyaml`, `lodash`, `jsonwebtoken`, `axios`, `minimatch`), providing non-breaking safe upgrade paths.
- **Dynamic Security Health Score**: PRD-mandated weighted scoring formula:
  $$\text{Score} = 100 - (\text{Critical} \times 25) - (\text{High} \times 10) - (\text{Medium} \times 3) - (\text{Low} \times 0.5)$$
- **Compliance Benchmarking**: Instant assessment against **OWASP Top 10**, **SOC 2 Type II readiness**, and **ISO/IEC 27001 baseline**.
- **Dual CLI Output Modes**: Clean, colored terminal audit reports and machine-readable JSON for CI/CD pipeline integration.

---

## 🏗️ Architecture & Directory Structure

```
nexusshield/
├── nexusshield/
│   ├── __init__.py           # Package versioning and metadata
│   ├── secrets.py            # Regex pattern matcher & Shannon entropy engine
│   ├── dependencies.py       # Manifest parser & offline CVE advisory database
│   ├── scorer.py             # Security score, letter grade, & compliance matrix
│   └── scanner.py            # Unified NexusScanner orchestrator
├── tests/
│   └── test_scanner.py       # Comprehensive automated test suite (11/11 tests)
├── main.py                   # CLI entrypoint supporting scan, JSON, & fail thresholds
└── README.md                 # Complete documentation and API specification
```

---

## 🚀 Quick Start & CLI Usage

### 1. View Version & Engine Status
```powershell
python main.py version
```

### 2. Audit a Project or Directory
```powershell
python main.py scan <path_to_codebase>
```

### 3. Generate Machine-Readable JSON Output
```powershell
python main.py scan <path_to_codebase> --json
```

Save output directly to a file:
```powershell
python main.py scan <path_to_codebase> --json --output audit_report.json
```

### 4. Enforce CI/CD Quality Gates
Fail your continuous integration build if the codebase security score falls below 85:
```powershell
python main.py scan . --fail-under 85
```

---

## 📡 Python API Usage

NexusShield can be imported and executed programmatically within Python services:

```python
from nexusshield.scanner import NexusScanner

scanner = NexusScanner()

# Scan an entire directory
report = scanner.scan_directory("path/to/project")
print(f"Health Score: {report['score']} (Grade: {report['grade']})")
print(f"Findings: {len(report['findings'])}")

# Scan in-memory code snippet
snippet_report = scanner.scan_content("""
import os
OPENAI_KEY = "sk-proj-exampleKey9876543210abcdefghijklmnop"  # nexus-ignore: secret-scan
""")
print(snippet_report["findings"])
```

---

## 🧪 Automated Test Suite

Run the full automated test suite:

```powershell
python -m unittest discover tests -v
```

**Test Coverage (`tests/test_scanner.py`)**:
- `test_01_aws_credential_detection`: Verified AWS Access Key ID & Secret Key interception
- `test_02_openai_and_stripe_detection`: Verified OpenAI & Stripe production keys
- `test_03_github_and_private_key_detection`: Verified GitHub PAT & RSA private keys
- `test_04_database_connection_string_detection`: Verified plaintext DB URI detection
- `test_05_entropy_and_redaction`: Verified Shannon entropy & safe preview redaction
- `test_06_placeholder_and_ignore_directives`: Verified template placeholders & `# nexus-ignore`
- `test_07_dependency_requirements_txt_vulnerabilities`: Verified Python CVE reconciliation
- `test_08_dependency_package_json_vulnerabilities`: Verified Node.js CVE reconciliation
- `test_09_security_health_scoring_and_grades`: Verified mathematical score & grade formula
- `test_10_full_directory_scan_lifecycle`: Verified end-to-end multi-file directory scans
- `test_11_cli_scan_json_and_exit_code`: Verified CLI arguments, JSON output, & exit codes

**Result: 11/11 tests passed (100% pass rate).**
