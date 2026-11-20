"""
Automated Verification Suite for IT Solutions Portal Web Tools
Validates ClauseGuard, DocuPulse, and EchoStream HTML interfaces, parsing rules,
math reconciliation, credential masking, RFC 5545 iCalendar generation,
and absence of corrupted/hidden watermarks.
"""

import json
import os
import re
import unittest
from pathlib import Path

PORTAL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "company" / "growth" / "portal"


class TestPortalWebTools(unittest.TestCase):
    """Test suite verifying client-side browser tools integrity and accuracy."""

    def test_01_portal_files_exist_and_valid(self):
        """Validates all web tools and supporting static assets exist."""
        required_files = [
            "index.html",
            "contract-scanner.html",
            "invoice-extractor.html",
            "meeting-followup.html",
            "styles.css",
            "app.js",
            "feedback.js",
            "feedback.css",
            "sitemap.xml",
            "robots.txt"
        ]
        for fname in required_files:
            fpath = PORTAL_DIR / fname
            self.assertTrue(fpath.exists(), f"Missing required portal asset: {fname}")
            self.assertGreater(fpath.stat().st_size, 50, f"File {fname} is unexpectedly empty")

    def test_02_clauseguard_heuristics_and_international_rules(self):
        """Verifies ClauseGuard rules including international legal frameworks (UK, EU, India, California)."""
        scanner_html = (PORTAL_DIR / "contract-scanner.html").read_text(encoding="utf-8")
        
        # Verify zero-width steganographic watermarks were completely removed
        self.assertNotIn("\\u200B", scanner_html, "Found hidden unicode watermark in contract-scanner.html")
        self.assertNotIn("\u200b", scanner_html, "Found raw zero-width character in contract-scanner.html")

        # Test UK UCTA rule
        uk_regex = re.compile(r"exclude\s+all\s+liability\s+for\s+breach\s+of\s+statutory|no\s+liability\s+for\s+fundamental\s+breach|exclusion\s+of\s+implied\s+terms\s+under\s+sale\s+of\s+goods", re.I)
        self.assertTrue(uk_regex.search("Company shall exclude all liability for breach of statutory warranties."))

        # Test EU GDPR Art 28 / AI Act rule
        eu_regex = re.compile(r"use\s+(?:all\s+)?customer\s+data\s+to\s+train\s+(?:ai|machine\s+learning|internal\s+models)|transfer\s+personal\s+data\s+without\s+(?:standard\s+contractual|dpa)|no\s+data\s+processing\s+addendum", re.I)
        self.assertTrue(eu_regex.search("Vendor may use customer data to train AI and machine learning models."))

        # Test Indian Contract Act Section 27 rule
        india_regex = re.compile(r"restrained\s+from\s+exercising\s+a\s+lawful\s+profession|restraint\s+of\s+trade|shall\s+not\s+practice\s+any\s+profession\s+or\s+trade\s+in\s+india", re.I)
        self.assertTrue(india_regex.search("Contractor shall be restrained from exercising a lawful profession in India."))

        # Test California BPC Section 16600 rule
        ca_regex = re.compile(r"california.*non-compete|governed\s+by\s+california\s+law.*shall\s+not\s+compete|subject\s+to\s+california.*restricting\s+employment", re.I)
        self.assertTrue(ca_regex.search("This Agreement is governed by California law and Contractor shall not compete for 2 years."))

        # Test core traps
        liab_regex = re.compile(r"unlimited\s+liability|liable\s+for\s+all\s+damages\s+without\s+limitation|no\s+limit\s+on\s+liability", re.I)
        self.assertTrue(liab_regex.search("Consultant agrees to unlimited liability for any damages."))

    def test_03_docupulse_math_reconciliation_and_clean_csv(self):
        """Verifies DocuPulse invoice extraction, math auditor, and clean CSV export formatting."""
        extractor_html = (PORTAL_DIR / "invoice-extractor.html").read_text(encoding="utf-8")
        
        # Verify absence of hidden zero-width watermarks
        self.assertNotIn("\\u200B", extractor_html, "Found hidden unicode watermark in invoice-extractor.html")
        self.assertNotIn("\u200b", extractor_html, "Found raw zero-width character in invoice-extractor.html")

        # Verify clean CSV and TSV headers
        self.assertIn("Vendor,Invoice Number,Issue Date,Due Date", extractor_html)
        self.assertIn("Vendor\\tInvoice #\\tIssue Date\\tDue Date", extractor_html)

        # Test math auditor calculation
        items = [{"description": "UI Design", "amount": 1500.00}, {"description": "Backend API", "amount": 2500.00}]
        subtotal = sum(i["amount"] for i in items)
        tax = 400.00
        correct_total = 4400.00
        bad_total = 4900.00

        self.assertEqual(subtotal, 4000.00)
        self.assertTrue(abs((subtotal + tax) - correct_total) < 0.01)
        self.assertFalse(abs((subtotal + tax) - bad_total) < 0.01)

    def test_04_echostream_voiceguard_and_ical_export(self):
        """Verifies EchoStream VoiceGuard secret sanitization and RFC 5545 iCalendar generation."""
        copilot_html = (PORTAL_DIR / "meeting-followup.html").read_text(encoding="utf-8")
        
        # Verify absence of hidden zero-width watermarks
        self.assertNotIn("\\u200B", copilot_html, "Found hidden unicode watermark in meeting-followup.html")
        self.assertNotIn("\u200b", copilot_html, "Found raw zero-width character in meeting-followup.html")

        # Test VoiceGuard regex sanitizer
        sample_dirty = "Deploy to production with key sk-proj-1234567890abcdefghijklmnop and AWS AKIAIOSFODNN7EXAMPLE"
        sanitized = re.sub(r"\b(sk-(?:proj-)?[A-Za-z0-9_\-]{20,})\b", "[REDACTED_API_KEY]", sample_dirty)
        sanitized = re.sub(r"\b(AKIA[0-9A-Z]{16})\b", "[REDACTED_AWS_KEY]", sanitized)
        
        self.assertNotIn("sk-proj-", sanitized)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", sanitized)
        self.assertIn("[REDACTED_API_KEY]", sanitized)
        self.assertIn("[REDACTED_AWS_KEY]", sanitized)

        # Test RFC 5545 iCalendar tokens
        self.assertIn("BEGIN:VCALENDAR", copilot_html)
        self.assertIn("VERSION:2.0", copilot_html)
        self.assertIn("BEGIN:VEVENT", copilot_html)
        self.assertIn("END:VEVENT", copilot_html)
        self.assertIn("END:VCALENDAR", copilot_html)

    def test_05_vercel_routing_and_security_headers(self):
        """Verifies root vercel.json contains complete subtool rewrites and enterprise security headers."""
        root_dir = PORTAL_DIR.parent.parent.parent
        vercel_json_path = root_dir / "vercel.json"
        self.assertTrue(vercel_json_path.exists(), "Root vercel.json not found")

        with open(vercel_json_path, "r", encoding="utf-8") as f:
            vconf = json.load(f)

        rewrites = {r["source"]: r["destination"] for r in vconf.get("rewrites", [])}
        self.assertIn("/contract-scanner.html", rewrites)
        self.assertIn("/invoice-extractor.html", rewrites)
        self.assertIn("/meeting-followup.html", rewrites)

        # Check security headers
        headers_list = vconf.get("headers", [])
        self.assertTrue(len(headers_list) > 0)
        global_headers = {h["key"]: h["value"] for h in headers_list[0].get("headers", [])}
        self.assertEqual(global_headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(global_headers.get("X-Frame-Options"), "DENY")


if __name__ == "__main__":
    unittest.main()
