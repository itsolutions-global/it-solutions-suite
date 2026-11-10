"""
DocuPulse Financial Ledger & Duplicate Billing Detector
Stores extracted invoices/receipts locally in JSON & CSV formats, flags duplicate
invoice numbers or duplicate vendor+amount charges, and exports accountant-ready CSV ledgers.
"""

import csv
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from docupulse.extractor import InvoiceExtractor


class FinancialLedger:
    """Manages the local invoice ledger, duplicate detection, and CSV exports."""

    def __init__(self, storage_path: Optional[Union[str, Path]] = None):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            base_dir = Path(__file__).resolve().parent.parent / "data"
            if os.getenv("COREPULSE_TEST_MODE") == "1" and os.getenv("COREPULSE_DATA_DIR"):
                base_dir = Path(os.environ["COREPULSE_DATA_DIR"])
            self.storage_path = base_dir / "docupulse_ledger.json"
        self.extractor = InvoiceExtractor()

    def _read_all(self) -> List[Dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write_all(self, records: List[Dict[str, Any]]):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    def ingest_document(self, raw_text: str, source_name: str = "invoice.txt") -> Dict[str, Any]:
        """
        Extracts an invoice/receipt, checks the historical ledger for duplicate billing,
        and appends it to the local ledger.
        """
        extracted = self.extractor.extract(raw_text, source_name=source_name)
        existing = self._read_all()

        # Check for duplicate invoice number or duplicate (vendor, total, issue_date)
        for prev in existing:
            if (
                prev.get("invoice_number") == extracted["invoice_number"]
                and not extracted["invoice_number"].startswith("INV-AUTO-")
            ):
                extracted["anomalies"].append({
                    "code": "FIN-DUPLICATE-INVOICE-NUM",
                    "severity": "CRITICAL",
                    "message": (
                        f"Duplicate Invoice Number '{extracted['invoice_number']}' already recorded "
                        f"for {prev.get('vendor')} on {prev.get('issue_date')}."
                    )
                })
                extracted["is_verified"] = False
                break

            if (
                prev.get("vendor", "").lower() == extracted["vendor"].lower()
                and abs(float(prev.get("total", 0.0)) - float(extracted["total"])) < 0.01
                and prev.get("issue_date") == extracted["issue_date"]
                and extracted["total"] > 0
            ):
                extracted["anomalies"].append({
                    "code": "FIN-DUPLICATE-CHARGE",
                    "severity": "HIGH",
                    "message": (
                        f"Potential duplicate billing: Identical amount ({extracted['currency']} {extracted['total']:.2f}) "
                        f"from '{extracted['vendor']}' on {extracted['issue_date']}."
                    )
                })
                extracted["is_verified"] = False
                break

        existing.insert(0, extracted)
        self._write_all(existing)
        return extracted

    def get_summary(self) -> Dict[str, Any]:
        """Returns aggregate financial ledger telemetry."""
        records = self._read_all()
        total_spend = round(sum(float(r.get("total", 0.0)) for r in records), 2)
        total_tax = round(sum(float(r.get("tax", 0.0)) for r in records), 2)
        flagged = sum(1 for r in records if not r.get("is_verified", True))

        return {
            "total_documents": len(records),
            "total_spend": total_spend,
            "total_tax": total_tax,
            "flagged_anomalies_count": flagged,
            "records": records
        }

    def export_csv(self, output_path: Optional[Union[str, Path]] = None) -> str:
        """Exports the entire financial ledger to CSV format (and optionally writes to disk)."""
        records = self._read_all()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "Invoice ID",
            "Vendor",
            "Invoice Number",
            "Issue Date",
            "Due Date",
            "Currency",
            "Subtotal",
            "Tax",
            "Discount",
            "Total",
            "Verified",
            "Anomalies"
        ])
        for r in records:
            anom_str = "; ".join(a["code"] for a in r.get("anomalies", []))
            writer.writerow([
                r.get("id", ""),
                r.get("vendor", ""),
                r.get("invoice_number", ""),
                r.get("issue_date", ""),
                r.get("due_date", ""),
                r.get("currency", "USD"),
                f"{float(r.get('subtotal', 0.0)):.2f}",
                f"{float(r.get('tax', 0.0)):.2f}",
                f"{float(r.get('discount', 0.0)):.2f}",
                f"{float(r.get('total', 0.0)):.2f}",
                "YES" if r.get("is_verified") else "FLAGGED",
                anom_str
            ])
        csv_content = buf.getvalue()
        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(csv_content, encoding="utf-8")
        return csv_content
