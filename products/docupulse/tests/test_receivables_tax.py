"""
Unit tests for DocuPulse v1.2 ReceivablesChaser & ExpenseCategorizer
Validates stage boundary classifications (14, 15, 44, 45 days), date formats,
interest mention behavior, expense category keyword mapping, CSV exports,
and honesty disclaimers.
"""

from datetime import date, timedelta
from pathlib import Path
import sys
import tempfile
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from docupulse.receivables import ReceivablesChaser, parse_date_flexible
from docupulse.tax_mapper import ExpenseCategorizer


class TestDocuPulseExpansion(unittest.TestCase):
    """Test suite for ReceivablesChaser and ExpenseCategorizer."""

    def setUp(self):
        self.chaser = ReceivablesChaser()
        self.categorizer = ExpenseCategorizer()
        self.today = date(2026, 11, 15)

    def test_01_stage_boundaries_exact(self):
        """Verify strict stage boundaries: <=0 (Stage 0), 1-14 (Stage 1), 15-44 (Stage 2), 45+ (Stage 3)."""
        self.assertEqual(self.chaser.classify_stage(-5), 0)
        self.assertEqual(self.chaser.classify_stage(0), 0)
        self.assertEqual(self.chaser.classify_stage(1), 1)
        self.assertEqual(self.chaser.classify_stage(14), 1)  # Boundary 14
        self.assertEqual(self.chaser.classify_stage(15), 2)  # Boundary 15
        self.assertEqual(self.chaser.classify_stage(44), 2)  # Boundary 44
        self.assertEqual(self.chaser.classify_stage(45), 3)  # Boundary 45
        self.assertEqual(self.chaser.classify_stage(90), 3)

    def test_02_flexible_date_parsing(self):
        """Verify parsing of YYYY-MM-DD, MM/DD/YYYY, Net 30, and Net 15 relative to issue_date."""
        base_issue = date(2026, 10, 1)

        # ISO
        self.assertEqual(parse_date_flexible("2026-10-15"), date(2026, 10, 15))
        # US format MM/DD/YYYY
        self.assertEqual(parse_date_flexible("10/15/2026"), date(2026, 10, 15))
        # Net 30 relative to base_issue
        self.assertEqual(parse_date_flexible("Net 30", base_issue_date=base_issue), date(2026, 10, 31))
        # Net 15 relative to base_issue
        self.assertEqual(parse_date_flexible("Net 15", base_issue_date=base_issue), date(2026, 10, 16))
        # Upon Receipt
        self.assertEqual(parse_date_flexible("Upon Receipt", base_issue_date=base_issue), base_issue)

    def test_03_chaser_evaluation_and_interest_mention(self):
        """Verify overdue evaluation and that interest is ONLY mentioned when supplied and never asserts statutory rights."""
        invoice_stage3 = {
            "invoice_number": "INV-ST3-001",
            "vendor": "Delinquent Client LLC",
            "issue_date": "2026-09-01",
            "due_date": "2026-09-15",
            "total": 5000.00,
            "currency": "USD"
        }
        # As of 2026-11-15, days_overdue = 61 -> Stage 3
        res_no_interest = self.chaser.evaluate_invoice(invoice_stage3, today=self.today, interest_rate=None)
        self.assertEqual(res_no_interest["stage"], 3)
        self.assertEqual(res_no_interest["days_overdue"], 61)
        self.assertNotIn("late payment interest fee", res_no_interest["email_draft"]["body"])
        self.assertNotIn("statutory", res_no_interest["email_draft"]["body"].lower())

        # With interest_rate supplied (1.5%)
        res_with_interest = self.chaser.evaluate_invoice(invoice_stage3, today=self.today, interest_rate=1.5)
        self.assertIn("1.5%", res_with_interest["email_draft"]["body"])
        self.assertIn("75.00", res_with_interest["email_draft"]["body"])
        self.assertNotIn("statutory", res_with_interest["email_draft"]["body"].lower())

        # Verify Honesty Disclaimer
        self.assertIn("Not tax or legal advice", res_with_interest["disclaimer"])
        self.assertIn("confirm with your accountant", res_with_interest["disclaimer"])

    def test_04_expense_categorization_mapping(self):
        """Verify keyword mapping for all 9 required operational expense categories."""
        cases = [
            ({"vendor": "Amazon Web Services (AWS)", "line_items": [{"description": "EC2 and RDS compute"}]}, "Cloud Hosting"),
            ({"vendor": "Cloudflare Inc.", "line_items": [{"description": "Edge CDN and DDoS protection"}]}, "Cloud Hosting"),
            ({"vendor": "GitHub Inc.", "line_items": [{"description": "Team Copilot SaaS license"}]}, "Software & SaaS"),
            ({"vendor": "Slack Technologies", "line_items": [{"description": "Business Pro subscription"}]}, "Software & SaaS"),
            ({"vendor": "Delta Airlines", "line_items": [{"description": "Flight from SFO to JFK"}]}, "Travel"),
            ({"vendor": "Uber Technologies", "line_items": [{"description": "Ride to conference"}]}, "Travel"),
            ({"vendor": "Starbucks Coffee", "line_items": [{"description": "Team breakfast and coffee"}]}, "Meals"),
            ({"vendor": "DoorDash", "line_items": [{"description": "Late night team dinner"}]}, "Meals"),
            ({"vendor": "Staples Office Supply", "line_items": [{"description": "Printer ink and paper reams"}]}, "Office Supplies"),
            ({"vendor": "Baker McKenzie Legal LLP", "line_items": [{"description": "Corporate legal advisory"}]}, "Professional Services"),
            ({"vendor": "KPMG LLP", "line_items": [{"description": "Annual financial accounting audit"}]}, "Professional Services"),
            ({"vendor": "Google Ads", "line_items": [{"description": "Search campaign advertising"}]}, "Advertising"),
            ({"vendor": "Pacific Gas and Electric", "line_items": [{"description": "Commercial electricity bill"}]}, "Utilities"),
            ({"vendor": "Random Gizmo Shop", "line_items": [{"description": "Custom antique gadget"}]}, "Other"),
        ]

        for record, expected_cat in cases:
            cat = self.categorizer.categorize_record(record)
            self.assertEqual(cat, expected_cat, f"Expected {expected_cat} for {record['vendor']}, got {cat}")

    def test_05_categorizer_summary_and_csv_export(self):
        """Verify categorized records summary, CSV generation, and honesty disclaimer."""
        records = [
            {"vendor": "AWS", "invoice_number": "INV-1", "issue_date": "2026-11-01", "total": 1200.0, "currency": "USD"},
            {"vendor": "GitHub", "invoice_number": "INV-2", "issue_date": "2026-11-02", "total": 42.0, "currency": "USD"},
            {"vendor": "Starbucks", "invoice_number": "INV-3", "issue_date": "2026-11-03", "total": 18.5, "currency": "USD"},
        ]
        res = self.categorizer.categorize_records(records)
        self.assertEqual(res["total_documents"], 3)
        self.assertEqual(res["total_spend"], 1260.5)
        self.assertEqual(res["categories"]["Cloud Hosting"]["count"], 1)
        self.assertEqual(res["categories"]["Software & SaaS"]["count"], 1)
        self.assertEqual(res["categories"]["Meals"]["count"], 1)
        self.assertIn("Not tax or legal advice", res["disclaimer"])

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            csv_path = Path(tmpdir) / "categories.csv"
            csv_str = self.categorizer.export_csv(res, output_path=csv_path)
            self.assertTrue(csv_path.exists())
            self.assertIn("Date,Vendor,Invoice Number,Category,Amount,Currency,Description", csv_str)
            self.assertIn("Cloud Hosting", csv_str)
            self.assertIn("Software & SaaS", csv_str)
            self.assertIn("Meals", csv_str)


if __name__ == "__main__":
    unittest.main()
