"""
NexusShield Secret Scanner Engine
High-precision pattern matcher and Shannon entropy calculator for detecting leaked credentials.
"""

import math
import re
from typing import Any, Dict, List, Optional, Tuple

# Pre-compiled high-fidelity credential detection patterns
SECRET_PATTERNS: List[Dict[str, Any]] = [
    {
        "id": "SEC-AWS-KEY",
        "name": "AWS Access Key ID",
        "severity": "Critical",
        "category": "Cloud Credentials",
        "pattern": re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        "description": "Exposed Amazon Web Services access key id."
    },
    {
        "id": "SEC-AWS-SECRET",
        "name": "AWS Secret Access Key",
        "severity": "Critical",
        "category": "Cloud Credentials",
        "pattern": re.compile(r"(?i)\b(?:aws_secret_access_key|aws_secret|aws_key)\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"),
        "description": "Exposed Amazon Web Services secret key assignment."
    },
    {
        "id": "SEC-OPENAI-KEY",
        "name": "OpenAI API Key",
        "severity": "Critical",
        "category": "AI / API Credentials",
        "pattern": re.compile(r"\b(sk-(?:proj-)?[A-Za-z0-9_-]{32,})\b"),
        "description": "Exposed OpenAI production or project API key."
    },
    {
        "id": "SEC-STRIPE-KEY",
        "name": "Stripe Live Secret Key",
        "severity": "Critical",
        "category": "Payment Credentials",
        "pattern": re.compile(r"\b((?:sk|rk)_live_[0-9a-zA-Z]{24,})\b"),
        "description": "Exposed Stripe production live secret key."
    },
    {
        "id": "SEC-GITHUB-PAT",
        "name": "GitHub Personal Access Token",
        "severity": "High",
        "category": "Source Control Credentials",
        "pattern": re.compile(r"\b(ghp_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{82})\b"),
        "description": "Exposed GitHub personal access token."
    },
    {
        "id": "SEC-PRIVATE-KEY",
        "name": "Cryptographic Private Key",
        "severity": "Critical",
        "category": "Cryptography",
        "pattern": re.compile(r"(-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----)"),
        "description": "Exposed unencrypted cryptographic private key header."
    },
    {
        "id": "SEC-DB-URI",
        "name": "Database Connection String with Credentials",
        "severity": "Critical",
        "category": "Database Credentials",
        "pattern": re.compile(r"\b((?:postgres|postgresql|mysql|mongodb|redis):\/\/[a-zA-Z0-9_\-\.]+:[^@\s]+@[a-zA-Z0-9_\-\.]+:[0-9]{2,5}\/[a-zA-Z0-9_\-\.]*)\b"),
        "description": "Exposed database connection URI containing plaintext authentication credentials."
    },
    {
        "id": "SEC-SLACK-TOKEN",
        "name": "Slack Bot Token",
        "severity": "High",
        "category": "Communication Credentials",
        "pattern": re.compile(r"\b(xoxb-[0-9]{11,13}-[0-9]{11,13}-[a-zA-Z0-9]{24})\b"),
        "description": "Exposed Slack workspace bot authorization token."
    },
    {
        "id": "SEC-GOOGLE-KEY",
        "name": "Google API Key",
        "severity": "High",
        "category": "Cloud Credentials",
        "pattern": re.compile(r"\b(AIza[0-9A-Za-z-_]{35})\b"),
        "description": "Exposed Google Cloud / Maps / Firebase service API key."
    }
]

# Patterns recognized as common benign placeholders
PLACEHOLDER_SUBSTRINGS = [
    "YOUR_API_KEY", "YOUR_KEY", "EXAMPLE_KEY", "PLACEHOLDER", "CHANGEME",
    "MY_SECRET", "DUMMY", "TEST_KEY", "INSERT_KEY_HERE", "00000000000000000000",
    "XXXXXX", "SAMPLE_KEY"
]


def calculate_shannon_entropy(data: str) -> float:
    """
    Computes Shannon entropy (bits per symbol) for an arbitrary string.
    High entropy (> 4.5) in strings of moderate length typically indicates cryptographic keys.
    """
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    frequencies = {}
    for char in data:
        frequencies[char] = frequencies.get(char, 0) + 1
    for count in frequencies.values():
        p = count / length
        entropy -= p * math.log2(p)
    return round(entropy, 3)


def is_placeholder(secret: str) -> bool:
    """Checks whether the detected string is merely a dummy template placeholder."""
    upper = secret.upper()
    for ph in PLACEHOLDER_SUBSTRINGS:
        if ph in upper:
            return True
    return False


def redact_secret(secret: str) -> str:
    """
    Safely redacts a sensitive secret string so that it can be displayed in audit reports
    without disclosing the actual confidential credential.
    """
    if len(secret) <= 8:
        return "***REDACTED***"
    prefix_len = min(6, len(secret) // 4)
    suffix_len = min(4, len(secret) // 4)
    return f"{secret[:prefix_len]}...{secret[-suffix_len:]}"


class SecretScanner:
    """Zero-dependency high-throughput secret detection engine."""

    def __init__(self, entropy_threshold: float = 4.6):
        self.entropy_threshold = entropy_threshold
        self.patterns = SECRET_PATTERNS

    def scan_line(self, line: str, line_number: int, file_path: str = "") -> List[Dict[str, Any]]:
        """Scans a single line of text for credential leaks."""
        findings = []

        # Check for inline ignore directives
        if "nexus-ignore" in line or "nexusshield-ignore" in line:
            return []

        # 1. Pattern Matching
        for rule in self.patterns:
            matches = rule["pattern"].findall(line)
            for match in matches:
                matched_secret = match if isinstance(match, str) else match[0]
                if is_placeholder(matched_secret):
                    continue

                findings.append({
                    "id": rule["id"],
                    "title": rule["name"],
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "type": "secret_leak",
                    "file": file_path,
                    "line": line_number,
                    "redacted_secret": redact_secret(matched_secret),
                    "entropy": calculate_shannon_entropy(matched_secret),
                    "description": rule["description"],
                    "remediation": f"Immediately revoke {rule['name']}, remove from source control, and inject via environment variable."
                })

        # 2. Heuristic High-Entropy String Scanner (assignment patterns)
        if not findings:
            assignment_match = re.search(r"(?i)\b(?:secret|token|api_key|apikey|private_key|auth_token)\s*[:=]\s*['\"]([A-Za-z0-9_\-+/=]{24,})['\"]", line)
            if assignment_match:
                candidate = assignment_match.group(1)
                entropy = calculate_shannon_entropy(candidate)
                if entropy >= self.entropy_threshold and not is_placeholder(candidate):
                    findings.append({
                        "id": "SEC-HIGH-ENTROPY",
                        "title": "High-Entropy Credential Assignment",
                        "severity": "High",
                        "category": "Generic Secret",
                        "type": "secret_leak",
                        "file": file_path,
                        "line": line_number,
                        "redacted_secret": redact_secret(candidate),
                        "entropy": entropy,
                        "description": f"Detected high-entropy random token ({entropy} bits/char) assigned to a sensitive variable name.",
                        "remediation": "Move credential out of source code and store securely in a secret manager or .env file."
                    })

        return findings

    def scan_content(self, content: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Scans multi-line source code content line-by-line, honoring preceding and inline ignore directives."""
        findings = []
        lines = content.splitlines()
        ignore_next_line = False

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            # If preceding line was an ignore directive comment
            if stripped.startswith(("#", "//", "/*")) and ("nexus-ignore" in stripped or "nexusshield-ignore" in stripped):
                ignore_next_line = True
                continue

            if ignore_next_line:
                ignore_next_line = False
                continue

            line_findings = self.scan_line(line, idx, file_path)
            findings.extend(line_findings)
        return findings
