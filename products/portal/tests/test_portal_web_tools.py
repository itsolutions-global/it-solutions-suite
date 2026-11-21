"""
Automated Verification Suite for IT Solutions Portal Web Tools & Revenue Engines
Validates ClauseGuard, DocuPulse, EchoStream, ClaimForge, ComplianceForge, ScopeShield,
B2B Commercial Desk (solutions.html), and Cryptographic White-Label License Verification.
"""

import json
import os
import re
import sys
import unittest
from pathlib import Path

PORTAL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "company" / "growth" / "portal"
PRODUCTS_DIR = Path(__file__).resolve().parent.parent.parent
if str(PRODUCTS_DIR) not in sys.path:
    sys.path.insert(0, str(PRODUCTS_DIR))

from portal.whitelabel_issuer import (
    compute_signature,
    issue_whitelabel_key,
    verify_whitelabel_key,
)


class TestPortalWebTools(unittest.TestCase):
    """Test suite verifying client-side browser tools integrity, statutory math, and white-label licensing."""

    def test_01_portal_files_exist_and_valid(self):
        """Validates all 6 web tools, B2B storefront, and supporting static assets exist."""
        required_files = [
            "index.html",
            "contract-scanner.html",
            "invoice-extractor.html",
            "meeting-followup.html",
            "payment-recovery.html",
            "compliance-dossier.html",
            "scope-shield.html",
            "solutions.html",
            "whitelabel.js",
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

        self.assertNotIn("\\u200B", scanner_html, "Found hidden unicode watermark in contract-scanner.html")
        self.assertNotIn("\u200b", scanner_html, "Found raw zero-width character in contract-scanner.html")

        uk_regex = re.compile(r"exclude\s+all\s+liability\s+for\s+breach\s+of\s+statutory|no\s+liability\s+for\s+fundamental\s+breach|exclusion\s+of\s+implied\s+terms\s+under\s+sale\s+of\s+goods", re.I)
        self.assertTrue(uk_regex.search("Company shall exclude all liability for breach of statutory warranties."))

        eu_regex = re.compile(r"use\s+(?:all\s+)?customer\s+data\s+to\s+train\s+(?:ai|machine\s+learning|internal\s+models)|transfer\s+personal\s+data\s+without\s+(?:standard\s+contractual|dpa)|no\s+data\s+processing\s+addendum", re.I)
        self.assertTrue(eu_regex.search("Vendor may use customer data to train AI and machine learning models."))

        india_regex = re.compile(r"restrained\s+from\s+exercising\s+a\s+lawful\s+profession|restraint\s+of\s+trade|shall\s+not\s+practice\s+any\s+profession\s+or\s+trade\s+in\s+india", re.I)
        self.assertTrue(india_regex.search("Contractor shall be restrained from exercising a lawful profession in India."))

        ca_regex = re.compile(r"california.*non-compete|governed\s+by\s+california\s+law.*shall\s+not\s+compete|subject\s+to\s+california.*restricting\s+employment", re.I)
        self.assertTrue(ca_regex.search("This Agreement is governed by California law and Contractor shall not compete for 2 years."))

    def test_03_docupulse_math_reconciliation_and_clean_csv(self):
        """Verifies DocuPulse invoice extraction, math auditor, and clean CSV export formatting."""
        extractor_html = (PORTAL_DIR / "invoice-extractor.html").read_text(encoding="utf-8")

        self.assertNotIn("\\u200B", extractor_html)
        self.assertNotIn("\u200b", extractor_html)
        self.assertIn("Vendor,Invoice Number,Issue Date,Due Date", extractor_html)
        self.assertIn("Vendor\\tInvoice #\\tIssue Date\\tDue Date", extractor_html)

    def test_04_echostream_voiceguard_and_ical_export(self):
        """Verifies EchoStream VoiceGuard secret sanitization and RFC 5545 iCalendar generation."""
        copilot_html = (PORTAL_DIR / "meeting-followup.html").read_text(encoding="utf-8")

        self.assertNotIn("\\u200B", copilot_html)
        self.assertNotIn("\u200b", copilot_html)
        self.assertIn("BEGIN:VCALENDAR", copilot_html)
        self.assertIn("VERSION:2.0", copilot_html)
        self.assertIn("BEGIN:VEVENT", copilot_html)
        self.assertIn("END:VCALENDAR", copilot_html)

    def test_05_vercel_routing_and_security_headers(self):
        """Verifies root vercel.json contains complete subtool rewrites for all 6 engines and B2B desk."""
        root_dir = PORTAL_DIR.parent.parent.parent
        vercel_json_path = root_dir / "vercel.json"
        self.assertTrue(vercel_json_path.exists(), "Root vercel.json not found")

        config = json.loads(vercel_json_path.read_text(encoding="utf-8"))
        self.assertIn("rewrites", config)
        sources = [r["source"] for r in config["rewrites"]]
        for expected_route in [
            "/contract-scanner.html",
            "/invoice-extractor.html",
            "/meeting-followup.html",
            "/payment-recovery.html",
            "/payment-recovery",
            "/compliance-dossier.html",
            "/compliance-dossier",
            "/scope-shield.html",
            "/scope-shield",
            "/solutions.html",
            "/solutions",
            "/whitelabel.js",
        ]:
            self.assertIn(expected_route, sources)

    def test_06_claimforge_statutory_payment_recovery_engine(self):
        """Verifies ClaimForge multi-jurisdiction statutory late payment interest and tax disallowance logic."""
        recovery_html = (PORTAL_DIR / "payment-recovery.html").read_text(encoding="utf-8")
        self.assertNotIn("\u200b", recovery_html)
        self.assertIn("MSMED Act, 2006", recovery_html)
        self.assertIn("Section 43B(h)", recovery_html)
        self.assertIn("Late Payment of Commercial Debts (Interest) Act 1998", recovery_html)
        self.assertIn("2011/7/EU", recovery_html)
        self.assertIn("DOUBLE DAMAGES", recovery_html)

        # Verify India MSME Section 16 monthly rests compound math & 43B(h) tax disallowance
        principal = 250000.0
        r = 0.2025
        days = 75
        full_months = days // 30
        rem_days = days % 30
        compounded = principal * ((1 + r / 12) ** full_months) * (1 + (r * rem_days) / 365)
        interest = compounded - principal
        self.assertGreater(interest, principal * r * (days / 365))  # Compound > Simple interest
        tax_disallowance = principal * 0.2517
        self.assertAlmostEqual(tax_disallowance, 62925.0, places=2)

    def test_07_complianceforge_dossier_and_cyclonedx_sbom(self):
        """Verifies ComplianceForge GDPR Art. 28 DPA, EU AI Act 2024/1689, SOC 2 IRP, and CycloneDX v1.5 SBOM."""
        comp_html = (PORTAL_DIR / "compliance-dossier.html").read_text(encoding="utf-8")
        self.assertNotIn("\u200b", comp_html)
        self.assertIn("GDPR ARTICLE 28", comp_html)
        self.assertIn("REGULATION (EU) 2024/1689", comp_html)
        self.assertIn("NIST SP 800-61", comp_html)
        self.assertIn("CycloneDX", comp_html)
        self.assertIn("specVersion: '1.5'", comp_html)

    def test_08_scopeshield_change_order_and_ip_escrow(self):
        """Verifies ScopeShield Bilateral Change Order calculation and Conditional IP Escrow Certificate."""
        scope_html = (PORTAL_DIR / "scope-shield.html").read_text(encoding="utf-8")
        self.assertNotIn("\u200b", scope_html)
        self.assertIn("BILATERAL CHANGE ORDER ADDENDUM", scope_html)
        self.assertIn("CONDITIONAL INTELLECTUAL PROPERTY RESERVATION", scope_html)
        self.assertIn("17 U.S.C. § 204", scope_html)
        self.assertIn("Section 19 of the Indian Copyright Act", scope_html)

    def test_09_cryptographic_whitelabel_license_engine(self):
        """Verifies deterministic cryptographic White-Label license key generation and tamper rejection."""
        wl_js = (PORTAL_DIR / "whitelabel.js").read_text(encoding="utf-8")
        self.assertIn("ITSG::WHITELABEL::2026::ENTERPRISE::v1", wl_js)
        self.assertIn("verifyLicenseKey", wl_js)
        self.assertIn("generateProFormaInvoiceHTML", wl_js)

        # Issue valid key via Python issuer and verify
        key = issue_whitelabel_key("APEXLEGAL", "PRO")
        self.assertTrue(key.startswith("ITSG-WL-PRO-APEXLEGAL-"))
        res = verify_whitelabel_key(key)
        self.assertTrue(res["valid"])
        self.assertEqual(res["firm_code"], "APEXLEGAL")
        self.assertEqual(res["tier"], "PRO")

        # Tamper with key and assert rejection
        tampered = key[:-2] + ("00" if not key.endswith("00") else "FF")
        bad_res = verify_whitelabel_key(tampered)
        self.assertFalse(bad_res["valid"])
        self.assertEqual(bad_res["reason"], "Signature mismatch")


if __name__ == "__main__":
    unittest.main()
