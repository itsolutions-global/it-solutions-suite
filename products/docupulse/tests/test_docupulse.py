"""
Unit tests for DocuPulse v1.0 - Autonomous Invoice, Receipt & Financial Ledger Extraction Engine.
"""

from pathlib import Path
import sys
import tempfile
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from docupulse.extractor import InvoiceExtractor
from docupulse.ledger import FinancialLedger


class TestDocuPulse(unittest.TestCase):
    """Validates invoice field extraction, math anomaly detection, duplicate billing alerts, and CSV export."""

    def test_01_invoice_extraction_and_math_verification(self):
        extractor = InvoiceExtractor()
        sample = (
            "Vendor: Acme Design Studio LLC\n"
            "Invoice Number: INV-9001\n"
            "Date: 2026-11-01\n"
            "Due Date: 2026-11-15\n"
            "- UI/UX System Architecture $1,500.00\n"
            "- Brand Asset Package $500.00\n"
            "Subtotal: $2,000.00\n"
            "Tax: $160.00\n"
            "Total Due: $2,160.00\n"
        )
        res = extractor.extract(sample)
        self.assertEqual(res["vendor"], "Acme Design Studio LLC")
        self.assertEqual(res["invoice_number"], "INV-9001")
        self.assertEqual(res["subtotal"], 2000.00)
        self.assertEqual(res["tax"], 160.00)
        self.assertEqual(res["total"], 2160.00)
        self.assertEqual(len(res["line_items"]), 2)
        self.assertTrue(res["is_verified"])

    def test_02_math_mismatch_anomaly_detection(self):
        extractor = InvoiceExtractor()
        bad_invoice = (
            "Vendor: Overcharge Vendor Corp\n"
            "Invoice #: INV-BAD-01\n"
            "Subtotal: $1,000.00\n"
            "Tax: $50.00\n"
            "Total Due: $1,250.00\n"
        )
        res = extractor.extract(bad_invoice)
        self.assertFalse(res["is_verified"])
        codes = [a["code"] for a in res["anomalies"]]
        self.assertIn("FIN-MATH-MISMATCH", codes)

    def test_03_duplicate_invoice_and_csv_export(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            ledger_file = Path(tmpdir) / "ledger.json"
            csv_file = Path(tmpdir) / "export.csv"
            ledger = FinancialLedger(storage_path=ledger_file)

            inv_text = (
                "Vendor: Stripe Cloud Services\n"
                "Invoice #: INV-777\n"
                "Date: 2026-11-10\n"
                "Subtotal: $500.00\n"
                "Tax: $0.00\n"
                "Total: $500.00\n"
            )
            first = ledger.ingest_document(inv_text)
            self.assertTrue(first["is_verified"])

            # Ingest exact same invoice again -> must flag duplicate!
            second = ledger.ingest_document(inv_text)
            self.assertFalse(second["is_verified"])
            self.assertIn("FIN-DUPLICATE-INVOICE-NUM", [a["code"] for a in second["anomalies"]])

            csv_out = ledger.export_csv(output_path=csv_file)
            self.assertTrue(csv_file.exists())
            self.assertIn("INV-777", csv_out)


if __name__ == "__main__":
    unittest.main()
