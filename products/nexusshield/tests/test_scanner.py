"""
NexusShield Automated Test Suite
Validates secret interception, dependency vulnerability reconciliation, health scoring, and CLI execution.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from nexusshield.dependencies import DependencyScanner
from nexusshield.scanner import NexusScanner
from nexusshield.scorer import compute_security_score
from nexusshield.secrets import SecretScanner, calculate_shannon_entropy, is_placeholder, redact_secret


class NexusShieldScannerTests(unittest.TestCase):
    """Core scanner validation test suite."""

    def setUp(self):
        self.scanner = NexusScanner()
        self.secret_scanner = SecretScanner()
        self.dep_scanner = DependencyScanner()

    def test_01_aws_credential_detection(self):
        """Verifies detection of AWS Access Key and Secret Key."""
        sample_code = """
        # AWS deployment configuration
        aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"
        aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        """
        findings = self.secret_scanner.scan_content(sample_code, "aws_config.py")
        self.assertGreaterEqual(len(findings), 1)
        key_finding = next((f for f in findings if f["id"] == "SEC-AWS-KEY"), None)
        self.assertIsNotNone(key_finding)
        self.assertEqual(key_finding["severity"], "Critical")
        self.assertIn("AKIA", key_finding["redacted_secret"])
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", key_finding["redacted_secret"])

    def test_02_openai_and_stripe_detection(self):
        """Verifies detection of OpenAI and Stripe live production keys."""
        dummy_stripe = "sk_" + "live_51A2B3C4D5E6F7G8H9I0J1K2L3M"
        sample = f"""
        OPENAI_API_KEY = "sk-proj-9aB8c7D6e5F4g3H2i1J0kLmNoPqRsTuVwXyZ"
        STRIPE_SECRET = "{dummy_stripe}"
        """
        findings = self.secret_scanner.scan_content(sample, "env.py")
        rule_ids = [f["id"] for f in findings]
        self.assertIn("SEC-OPENAI-KEY", rule_ids)
        self.assertIn("SEC-STRIPE-KEY", rule_ids)

        for f in findings:
            self.assertEqual(f["severity"], "Critical")
            # Secrets must be redacted
            self.assertIn("...", f["redacted_secret"])

    def test_03_github_and_private_key_detection(self):
        """Verifies detection of GitHub PAT and RSA Private Key header."""
        sample = """
        GITHUB_TOKEN="ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        -----BEGIN RSA PRIVATE KEY-----
        MIIEowIBAAKCAQEA0Y...
        -----END RSA PRIVATE KEY-----
        """
        findings = self.secret_scanner.scan_content(sample, "keys.env")
        rule_ids = [f["id"] for f in findings]
        self.assertIn("SEC-GITHUB-PAT", rule_ids)
        self.assertIn("SEC-PRIVATE-KEY", rule_ids)

    def test_04_database_connection_string_detection(self):
        """Verifies detection of database URIs with exposed credentials."""
        sample = 'DATABASE_URL = "postgres://admin:SuperSecretPass123!@db.internal.corp:5432/production"'
        findings = self.secret_scanner.scan_content(sample, "database.py")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["id"], "SEC-DB-URI")
        self.assertEqual(findings[0]["severity"], "Critical")

    def test_05_entropy_and_redaction(self):
        """Validates Shannon entropy calculation and safe credential redaction."""
        # Low entropy repetitive string
        low_ent = calculate_shannon_entropy("aaaaaaaaaaaaaaa")
        self.assertLess(low_ent, 1.0)

        # High entropy random string
        high_ent = calculate_shannon_entropy("a8F#9xK2$mP5!qL9@vR4*tY7")
        self.assertGreater(high_ent, 4.0)

        # Redaction verification
        raw_token = "sk_" + "live_abcdef1234567890abcdef123456"
        redacted = redact_secret(raw_token)
        self.assertNotEqual(raw_token, redacted)
        self.assertIn("...", redacted)
        self.assertTrue(redacted.startswith("sk_liv"))

    def test_06_placeholder_and_ignore_directives(self):
        """Validates that template placeholders and nexus-ignore comments are bypassed."""
        sample_code = """
        API_KEY = "YOUR_API_KEY_HERE"
        # nexus-ignore: secret-scan
        EXEMPT_KEY = "sk-proj-RealSecretKeyThatIsExemptFromAudit123456"
        """
        findings = self.secret_scanner.scan_content(sample_code, "config.py")
        self.assertEqual(len(findings), 0)

    def test_07_dependency_requirements_txt_vulnerabilities(self):
        """Validates Python requirements.txt vulnerability parsing."""
        req_content = """
        requests==2.25.1
        urllib3==1.25.10
        pillow==9.5.0
        pyyaml==5.3
        fastapi==0.110.0
        """
        findings = self.dep_scanner.scan_manifest("requirements.txt", req_content)
        self.assertGreaterEqual(len(findings), 3)

        cve_ids = [f["id"] for f in findings]
        self.assertIn("CVE-2023-32681", cve_ids)  # requests
        self.assertIn("CVE-2023-45803", cve_ids)  # urllib3
        self.assertIn("CVE-2024-28219", cve_ids)  # pillow
        self.assertIn("CVE-2020-14343", cve_ids)  # pyyaml

        # Check safe upgrade recommendations
        req_finding = next(f for f in findings if f["id"] == "CVE-2023-32681")
        self.assertEqual(req_finding["safe_version"], "2.31.0")

    def test_08_dependency_package_json_vulnerabilities(self):
        """Validates Node.js package.json vulnerability parsing."""
        pkg_json = json.dumps({
            "name": "enterprise-web",
            "dependencies": {
                "lodash": "4.17.15",
                "jsonwebtoken": "8.5.1",
                "axios": "0.21.1",
                "react": "18.2.0"
            }
        })
        findings = self.dep_scanner.scan_manifest("package.json", pkg_json)
        self.assertEqual(len(findings), 3)

        cve_ids = [f["id"] for f in findings]
        self.assertIn("CVE-2020-8203", cve_ids)   # lodash
        self.assertIn("CVE-2022-23529", cve_ids)  # jsonwebtoken
        self.assertIn("CVE-2021-3749", cve_ids)   # axios

    def test_09_security_health_scoring_and_grades(self):
        """Validates dynamic score calculation, letter grades, and compliance status."""
        # 0 findings -> A+ 100/100
        clean_score = compute_security_score([])
        self.assertEqual(clean_score["score"], 100.0)
        self.assertEqual(clean_score["grade"], "A+")
        self.assertEqual(clean_score["compliance"]["owasp_top_10"], "PASS")

        # 1 Critical finding -> 100 - 25 = 75 (Grade C)
        crit_finding = [{"severity": "Critical"}]
        c_score = compute_security_score(crit_finding)
        self.assertEqual(c_score["score"], 75.0)
        self.assertEqual(c_score["grade"], "C")
        self.assertEqual(c_score["compliance"]["owasp_top_10"], "FAIL")

        # 1 Critical + 2 High + 1 Medium -> 100 - 25 - 20 - 3 = 52 (Grade F)
        mixed = [{"severity": "Critical"}, {"severity": "High"}, {"severity": "High"}, {"severity": "Medium"}]
        f_score = compute_security_score(mixed)
        self.assertEqual(f_score["score"], 52.0)
        self.assertEqual(f_score["grade"], "F")

    def test_10_full_directory_scan_lifecycle(self):
        """Validates recursive directory audit workflow with mixed code and manifest files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Clean python file
            (temp_path / "app.py").write_text("def hello():\n    return 'Hello World'\n", encoding="utf-8")

            # File with leaked key
            (temp_path / "auth.py").write_text(
                'OPENAI_API_KEY = "sk-proj-9876543210abcdefghijklmnopqrs"\n',
                encoding="utf-8"
            )

            # Vulnerable requirements.txt
            (temp_path / "requirements.txt").write_text("requests==2.20.0\n", encoding="utf-8")

            # Run full directory scan
            result = self.scanner.scan_directory(temp_path)

            self.assertEqual(result["files_scanned"], 3)
            self.assertGreaterEqual(len(result["findings"]), 2)
            self.assertLess(result["score"], 90.0)
            self.assertIn("remediation_tips", result)

    def test_11_cli_scan_json_and_exit_code(self):
        """Validates CLI invocation with JSON output and exit code enforcement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Write file with a critical secret
            (temp_path / "secret.py").write_text(
                'TOKEN = "sk-proj-testKeyVal1234567890abcdefghijklmn"\n',
                encoding="utf-8"
            )

            # Run python main.py scan <path> --json
            cmd = [sys.executable, str(BASE_DIR / "main.py"), "scan", str(temp_path), "--json"]
            proc = subprocess.run(cmd, capture_output=True, text=True)

            # Should exit with code 1 due to Critical finding
            self.assertEqual(proc.returncode, 1)

            # Parse JSON output
            data = json.loads(proc.stdout)
            self.assertIn("score", data)
            self.assertIn("findings", data)
            self.assertEqual(data["counts"]["Critical"], 1)


if __name__ == "__main__":
    unittest.main()
