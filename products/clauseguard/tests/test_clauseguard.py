"""
Unit tests for ClauseGuard v1.0 - Local-First Contract, NDA & Legal Redline Risk Scanner.
"""

from pathlib import Path
import sys
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from clauseguard.scanner import ContractRiskScanner


class TestClauseGuard(unittest.TestCase):
    """Validates predatory clause detection, safety score calculation, and redline generation."""

    def test_01_predatory_contract_detection_and_redlines(self):
        scanner = ContractRiskScanner()
        bad_contract = (
            "1. Contractor agrees to unlimited liability for all claims.\n"
            "2. Including pre-existing intellectual property shall become the sole property of Client.\n"
            "3. This contract shall automatically renew unless written notice is provided 90 days prior.\n"
            "4. Invoices are payable Net 90 days.\n"
        )
        res = scanner.scan_contract(bad_contract, document_name="Vendor_MSA.txt")
        self.assertEqual(res["findings_count"], 4)
        self.assertLess(res["safety_score"], 50.0)
        self.assertEqual(res["grade"], "F")
        rule_ids = [f["id"] for f in res["findings"]]
        self.assertIn("CLG-UNCAPPED-LIABILITY", rule_ids)
        self.assertIn("CLG-BROAD-IP-GRAB", rule_ids)
        self.assertIn("CLG-AUTO-RENEWAL-TRAP", rule_ids)
        self.assertIn("CLG-DELAYED-PAYMENT-TERMS", rule_ids)
        self.assertTrue(all("PROPOSED REDLINE:" in f["redline_counter_clause"] for f in res["findings"]))

    def test_02_clean_mutual_nda_passes_with_a_plus(self):
        scanner = ContractRiskScanner()
        clean_nda = (
            "MUTUAL NON-DISCLOSURE AGREEMENT\n"
            "1. Both parties agree to hold Confidential Information in strict confidence for 2 years.\n"
            "2. Either party may terminate this Agreement upon 30 days written notice.\n"
            "3. Aggregate liability under this Agreement is capped at $10,000.\n"
        )
        res = scanner.scan_contract(clean_nda, document_name="Mutual_NDA.txt")
        self.assertEqual(res["findings_count"], 0)
        self.assertEqual(res["safety_score"], 100.0)
        self.assertEqual(res["grade"], "A+")
        self.assertEqual(res["verdict"], "SAFE TO SIGN")


if __name__ == "__main__":
    unittest.main()
