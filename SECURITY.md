# Security Policy: IT Solutions Global Corporation

Security and privacy are non-negotiable foundations of the **IT Solutions Global Enterprise Suite**.

---

## Supported Versions

We provide security patches and dependency vulnerability updates for the following versions:

| Version | Supported |
| :--- | :--- |
| `1.0.x` | :white_check_mark: Active Production Support |
| `< 1.0.0` | :x: Deprecated / Prototype |

---

## 🛡️ In-Core Security Guarantees

Every product in our suite is built with defense-in-depth:
- **Zero Runtime Third-Party Dependencies**: Immune to npm/PyPI supply-chain injection attacks and typo-squatting.
- **Air-Gapped Local Execution**: All cryptographic operations, secret parsing, and SQLite storage execute on local hardware.
- **NexusShield Pre-Commit Interception**: Integrated high-entropy ($H \ge 4.5$) secret detection scanning for AWS, OpenAI, Stripe, and private keys before git commits.

---

## 🚨 Reporting a Vulnerability

If you discover a potential security vulnerability in any engine:

1. **Do NOT report security issues via public GitHub issues.**
2. Send a confidential report to our security engineering team at:  
   **`isgc@sedain.com`**
3. Please include:
   - Affected component (`CorePulse`, `NexusShield`, `EchoStream`, or `CLI`)
   - Steps to reproduce or proof-of-concept
   - Potential impact assessment
4. **Response SLA**:
   - Initial acknowledgement: **within 24 hours**.
   - Remediation patch and CVE assignment (if applicable): **within 72 hours**.

We practice responsible coordinated disclosure and will credit researchers in our official Release Notes.
