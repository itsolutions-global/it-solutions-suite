"""
Unit tests for ClauseGuard v1.2 SOW Rules & NegotiationDrafter
Validates detection of unlimited revisions, deemed rejection, perpetual warranty,
premature IP transfer, clean SOW passing, word-level redline diff markers ([-deleted-] / {+proposed+}),
collaborative cover email drafting, and honesty disclaimers.
"""

from pathlib import Path
import sys
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from clauseguard.negotiator import NegotiationDrafter, compute_word_diff
from clauseguard.scanner import ContractRiskScanner


class TestClauseGuardExpansion(unittest.TestCase):
    """Test suite for SOW rules and NegotiationDrafter."""

    def setUp(self):
        self.scanner = ContractRiskScanner()
        self.negotiator = NegotiationDrafter()

    def test_01_all_sow_rules_fire_individually(self):
        """Verify each of the 4 new SOW rules fires on predatory language."""
        rule_test_cases = [
            (
                "CLG-SOW-UNLIMITED-REVISIONS",
                "Contractor shall perform unlimited revisions until client is satisfied."
            ),
            (
                "CLG-SOW-DEEMED-REJECTION",
                "All deliverables shall be deemed rejected if not expressly approved within 30 days."
            ),
            (
                "CLG-SOW-OPEN-WARRANTY",
                "Developer provides a perpetual warranty and will fix all bugs at no cost in perpetuity."
            ),
            (
                "CLG-SOW-IP-BEFORE-PAYMENT",
                "Contractor assigns all intellectual property upon creation regardless of payment."
            )
        ]

        for expected_id, clause_text in rule_test_cases:
            res = self.scanner.scan_contract(clause_text, document_name="Test_SOW.txt")
            rule_ids = [f["id"] for f in res["findings"]]
            self.assertIn(expected_id, rule_ids, f"Expected {expected_id} to fire for: {clause_text}")
            self.assertIn("disclaimer", res)

    def test_02_clean_sow_does_not_fire_any_rules(self):
        """Verify a balanced, fair SOW produces 100 Safety Score, A+ grade, and 0 findings."""
        clean_sow = (
            "STATEMENT OF WORK\n"
            "1. Deliverables shall include up to two (2) rounds of minor revisions per milestone.\n"
            "2. Client shall review deliverables within ten (10) business days of receipt.\n"
            "3. Provider warrants deliverables for thirty (30) days following acceptance.\n"
            "4. Intellectual property in custom deliverables transfers upon full payment of fees.\n"
            "5. Payment terms are Net 30 from invoice date.\n"
        )
        res = self.scanner.scan_contract(clean_sow, document_name="Clean_SOW.txt")
        self.assertEqual(res["findings_count"], 0)
        self.assertEqual(res["safety_score"], 100.0)
        self.assertEqual(res["grade"], "A+")
        self.assertEqual(res["verdict"], "SAFE TO SIGN")

    def test_03_word_diff_markers_present(self):
        """Verify diff outputs include [-deleted-] and {+proposed+} markers."""
        orig = "Consultant shall provide unlimited revisions until satisfied."
        prop = "Services shall include up to two rounds of revisions."
        diff = compute_word_diff(orig, prop)

        self.assertIn("[-Consultant-]", diff)
        self.assertIn("[-unlimited-]", diff)
        self.assertIn("{+Services+}", diff)
        self.assertIn("{+two+}", diff)

    def test_04_negotiation_package_generation(self):
        """Verify complete negotiation package generation with diffs, cover email, and honesty disclaimer."""
        predatory_sow = (
            "1. Scope: Contractor must provide unlimited revisions.\n"
            "2. Payment: Deliverables deemed rejected unless written acceptance is issued.\n"
        )
        scan_res = self.scanner.scan_contract(predatory_sow, document_name="Predatory_SOW.txt")
        self.assertEqual(scan_res["findings_count"], 2)

        pkg = self.negotiator.generate_negotiation_package(scan_res, recipient_name="Acme Procurement")
        self.assertEqual(pkg["document"], "Predatory_SOW.txt")
        self.assertEqual(len(pkg["redlines"]), 2)

        for redline in pkg["redlines"]:
            self.assertIn("[-", redline["redline_diff"])
            self.assertIn("{+", redline["redline_diff"])
            self.assertTrue(len(redline["rationale"]) > 0)

        # Check Cover Email
        cover_email = pkg["cover_email"]
        self.assertIn("Proposed Agreement Alignment & Redlines", cover_email["subject"])
        self.assertIn("Acme Procurement", cover_email["body"])
        self.assertIn("Scope & Deliverables", cover_email["body"])
        self.assertIn("Acceptance & Milestones", cover_email["body"])

        # Check Honesty Disclaimer
        self.assertIn("Automated heuristic review — not legal advice", pkg["disclaimer"])
        self.assertIn("Have a qualified lawyer review important agreements", pkg["disclaimer"])


if __name__ == "__main__":
    unittest.main()
