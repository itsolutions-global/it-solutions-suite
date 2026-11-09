"""
EchoStream VoiceGuard - Real-Time Voice Transcript DLP Scanner
Detects and redacts spoken credentials (AWS, Stripe, OpenAI, GitHub, DB URIs, passwords).
Leverages NexusShield security pattern logic with autonomous zero-dependency fallback.
"""

import math
import re
from typing import Any, Dict, List, Optional, Tuple

# Pre-compiled high-fidelity DLP credential patterns (synchronized with NexusShield)
VOICE_SECRET_PATTERNS: List[Dict[str, Any]] = [
    {
        "id": "SEC-AWS-KEY",
        "name": "AWS Access Key ID",
        "severity": "Critical",
        "category": "Cloud Credentials",
        "pattern": re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        "description": "Spoken Amazon Web Services access key ID."
    },
    {
        "id": "SEC-AWS-SECRET",
        "name": "AWS Secret Access Key",
        "severity": "Critical",
        "category": "Cloud Credentials",
        "pattern": re.compile(r"(?i)\b(?:aws_secret_access_key|aws_secret|aws_key)\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"),
        "description": "Spoken Amazon Web Services secret key assignment."
    },
    {
        "id": "SEC-OPENAI-KEY",
        "name": "OpenAI API Key",
        "severity": "Critical",
        "category": "AI / API Credentials",
        "pattern": re.compile(r"\b(sk-(?:proj-)?[A-Za-z0-9_-]{32,})\b"),
        "description": "Spoken OpenAI production or project API key."
    },
    {
        "id": "SEC-STRIPE-KEY",
        "name": "Stripe Live Secret Key",
        "severity": "Critical",
        "category": "Payment Credentials",
        "pattern": re.compile(r"\b((?:sk|rk)_live_[0-9a-zA-Z]{24,})\b"),
        "description": "Spoken Stripe live production secret key."
    },
    {
        "id": "SEC-GITHUB-PAT",
        "name": "GitHub Personal Access Token",
        "severity": "High",
        "category": "Source Control Credentials",
        "pattern": re.compile(r"\b(ghp_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{82})\b"),
        "description": "Spoken GitHub personal access token."
    },
    {
        "id": "SEC-PRIVATE-KEY",
        "name": "Cryptographic Private Key",
        "severity": "Critical",
        "category": "Cryptography",
        "pattern": re.compile(r"(-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----)"),
        "description": "Verbalized cryptographic private key header."
    },
    {
        "id": "SEC-DB-URI",
        "name": "Database Connection String with Credentials",
        "severity": "Critical",
        "category": "Database Credentials",
        "pattern": re.compile(r"\b((?:postgres|postgresql|mysql|mongodb|redis):\/\/[a-zA-Z0-9_\-\.]+:[^@\s]+@[a-zA-Z0-9_\-\.]+:[0-9]{2,5}\/[a-zA-Z0-9_\-\.]*)\b"),
        "description": "Spoken database connection URI containing plaintext authentication credentials."
    },
    {
        "id": "SEC-SLACK-TOKEN",
        "name": "Slack Bot Token",
        "severity": "High",
        "category": "Communication Credentials",
        "pattern": re.compile(r"\b(xoxb-[0-9]{11,13}-[0-9]{11,13}-[a-zA-Z0-9]{24})\b"),
        "description": "Spoken Slack workspace bot authorization token."
    },
    {
        "id": "SEC-GOOGLE-KEY",
        "name": "Google API Key",
        "severity": "High",
        "category": "Cloud Credentials",
        "pattern": re.compile(r"\b(AIza[0-9A-Za-z-_]{35})\b"),
        "description": "Spoken Google Cloud / Maps / Firebase service API key."
    },
    {
        "id": "SEC-VERBAL-PASSWORD",
        "name": "Verbal Password Disclosure",
        "severity": "Critical",
        "category": "Authentication Credentials",
        "pattern": re.compile(r"(?i)\b(?:the password is|password is|db password is|admin password is|login with)\s+['\"]?([A-Za-z0-9!@#$%^&*()_+=\-`~\[\]{}|\\:;?/<>,.]{6,32})['\"]?"),
        "description": "Plaintext password disclosed verbally in transcript."
    }
]

# Benign template placeholder phrases
PLACEHOLDER_SUBSTRINGS = [
    "YOUR_API_KEY", "YOUR_KEY", "EXAMPLE_KEY", "PLACEHOLDER", "CHANGEME",
    "MY_SECRET", "DUMMY", "TEST_KEY", "INSERT_KEY_HERE", "00000000000000000000",
    "XXXXXX", "SAMPLE_KEY"
]


def calculate_shannon_entropy(data: str) -> float:
    """Computes Shannon entropy (bits per symbol) for string randomness assessment."""
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    frequencies: Dict[str, int] = {}
    for char in data:
        frequencies[char] = frequencies.get(char, 0) + 1
    for count in frequencies.values():
        p = count / length
        entropy -= p * math.log2(p)
    return round(entropy, 3)


def is_placeholder(secret: str) -> bool:
    """Checks whether candidate text is merely a generic placeholder."""
    upper = secret.upper()
    for ph in PLACEHOLDER_SUBSTRINGS:
        if ph in upper:
            return True
    return False


def mask_secret(secret: str) -> str:
    """Redacts secret to safe preview format (e.g., 'sk-pro...3a1f')."""
    if len(secret) <= 8:
        return "***REDACTED***"
    prefix_len = min(6, len(secret) // 4)
    suffix_len = min(4, len(secret) // 4)
    return f"{secret[:prefix_len]}...{secret[-suffix_len:]}"


class VoiceGuard:
    """
    Real-time Voice Data Loss Prevention (DLP) Scanner.
    Intercepts and masks confidential credentials in speech transcripts.
    """

    def __init__(self, entropy_threshold: float = 4.6):
        self.entropy_threshold = entropy_threshold
        self.patterns = VOICE_SECRET_PATTERNS

    def scan_and_redact(self, transcript_text: str) -> Dict[str, Any]:
        """
        Scans spoken transcript text, redacts sensitive credentials,
        and returns clean sanitized text alongside detected incidents.
        """
        redacted_text = transcript_text
        incidents: List[Dict[str, Any]] = []

        # 1. Pattern Matching & In-Place Redaction
        for rule in self.patterns:
            matches = list(rule["pattern"].finditer(transcript_text))
            for match in matches:
                # Capture the full matched secret token
                matched_secret = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)

                if is_placeholder(matched_secret):
                    continue

                redaction_tag = f"[REDACTED_SECRET: {rule['name']}]"
                redacted_text = redacted_text.replace(matched_secret, redaction_tag)

                incidents.append({
                    "id": rule["id"],
                    "title": rule["name"],
                    "severity": rule["severity"],
                    "category": rule["category"],
                    "redacted_preview": mask_secret(matched_secret),
                    "entropy": calculate_shannon_entropy(matched_secret),
                    "description": rule["description"],
                    "remediation": f"Immediately rotate {rule['name']} and purge from audio archival logs."
                })

        # 2. Heuristic High-Entropy Spoken Token Scanner
        # Catches conversational expressions like: "my token is aB9#kL2$vP1!mQ..."
        spoken_token_pattern = re.compile(r"(?i)\b(?:token is|key is|secret is|api key is)\s+['\"]?([A-Za-z0-9_\-+/=]{24,})['\"]?")
        for match in spoken_token_pattern.finditer(transcript_text):
            candidate = match.group(1)
            entropy = calculate_shannon_entropy(candidate)
            if entropy >= self.entropy_threshold and not is_placeholder(candidate):
                redaction_tag = "[REDACTED_SECRET: High-Entropy Token]"
                redacted_text = redacted_text.replace(candidate, redaction_tag)

                incidents.append({
                    "id": "SEC-HIGH-ENTROPY-VOICE",
                    "title": "High-Entropy Spoken Token",
                    "severity": "High",
                    "category": "Generic Secret",
                    "redacted_preview": mask_secret(candidate),
                    "entropy": entropy,
                    "description": f"Detected high-entropy random token ({entropy} bits/char) verbalized in speech stream.",
                    "remediation": "Rotate token and avoid verbalizing secret credentials over unencrypted audio channels."
                })

        return {
            "original_length": len(transcript_text),
            "redacted_text": redacted_text,
            "incidents_count": len(incidents),
            "is_clean": len(incidents) == 0,
            "incidents": incidents
        }
