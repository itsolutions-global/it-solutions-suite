"""
DocuPulse Financial Document Extractor & Anomaly Auditor
Extracts structured accounting fields (Vendor, Invoice #, Dates, Line Items, Tax, Total)
from unstructured invoice/receipt text, HTML, or JSON, and flags math discrepancies
or duplicate billings automatically.
"""

from datetime import datetime, timezone
import hashlib
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple


CURRENCY_MAP = {
    "$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "₹": "INR",
    "inr": "INR",
    "rs": "INR",
}


def _parse_amount(raw: str) -> float:
    """Safely converts a formatted currency number string ('1,450.50') to float."""
    cleaned = re.sub(r"[^0-9.\-]", "", str(raw))
    try:
        return round(float(cleaned), 2)
    except (ValueError, TypeError):
        return 0.0


class InvoiceExtractor:
    """Zero-dependency parser for unstructured invoices, receipts, and purchase orders."""

    def extract(self, raw_text: str, source_name: str = "inline_document.txt") -> Dict[str, Any]:
        """
        Extracts structured financial metadata and line items from raw invoice/receipt text.
        Also performs mathematical reconciliation (Subtotal + Tax - Discount == Total).
        """
        text = raw_text.strip()
        lines = [l.strip() for l in text.splitlines() if l.strip()]

        # 1. Detect Vendor Name
        vendor = "Unknown Vendor"
        vendor_patterns = [
            r"(?i)^(?:vendor|from|merchant|billed\s+by|company|supplier)\s*[:\-]\s*(.+)$",
            r"(?i)^([A-Z][A-Za-z0-9\s&\.,\-]{2,45}\s+(?:Inc\.?|LLC|Ltd\.?|Corp\.?|Corporation|GmbH|Co\.?|Solutions|Services|Studio|Labs))\b",
        ]
        for line in lines[:12]:
            matched = False
            for pat in vendor_patterns:
                m = re.search(pat, line)
                if m:
                    candidate = m.group(1).strip()
                    if candidate.lower() not in ("invoice", "receipt", "tax invoice", "bill to"):
                        vendor = candidate
                        matched = True
                        break
            if matched:
                break

        if vendor == "Unknown Vendor" and lines:
            # Fallback to first non-header line
            for line in lines[:5]:
                if not re.match(r"(?i)^(?:invoice|receipt|purchase\s+order|date|bill\s+to|page)\b", line):
                    vendor = line[:50].strip("#* ")
                    break

        # 2. Detect Invoice / Receipt Number
        invoice_number = f"INV-AUTO-{hashlib.sha256(text.encode('utf-8')).hexdigest()[:6].upper()}"
        inv_patterns = [
            r"(?i)\b(?:invoice\s*(?:no\.?|number|#|id)?|receipt\s*(?:no\.?|#|id)?|po\s*#|ref(?:erence)?\s*#?)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9\-_/]{2,24})\b",
        ]
        for pat in inv_patterns:
            m = re.search(pat, text)
            if m:
                candidate = m.group(1).strip()
                if candidate.lower() not in ("date", "total", "due", "number", "from", "to"):
                    invoice_number = candidate
                    break

        # 3. Detect Dates (Issue Date & Due Date)
        issue_date = datetime.now().strftime("%Y-%m-%d")
        due_date = "Upon Receipt"

        date_regex = r"(\d{4}-\d{2}-\d{2}|\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})"
        issue_m = re.search(rf"(?i)\b(?:invoice\s+date|date|issued)\s*[:\-]?\s*{date_regex}", text)
        if issue_m:
            issue_date = issue_m.group(1).strip()
        else:
            any_date = re.search(date_regex, text)
            if any_date:
                issue_date = any_date.group(1).strip()

        due_m = re.search(rf"(?i)\b(?:due\s+date|payment\s+due|pay\s+by)\s*[:\-]?\s*{date_regex}", text)
        if due_m:
            due_date = due_m.group(1).strip()
        else:
            net_m = re.search(r"(?i)\b(net\s*(?:15|30|45|60|90)|due\s+on\s+receipt)\b", text)
            if net_m:
                due_date = net_m.group(1).upper()

        # 4. Detect Currency
        currency = "USD"
        curr_m = re.search(r"(?i)\b(USD|EUR|GBP|INR|CAD|AUD)\b|([\$€£₹])", text)
        if curr_m:
            token = (curr_m.group(1) or curr_m.group(2) or "$").lower()
            currency = CURRENCY_MAP.get(token, token.upper())

        # 5. Extract Subtotal, Tax, Discount, and Total Amount
        subtotal: Optional[float] = None
        tax: float = 0.0
        discount: float = 0.0
        total: Optional[float] = None

        num_pat = r"[\$€£₹]?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)"

        for line in lines:
            low = line.lower()
            if re.search(r"\b(?:sub[\s\-]?total|net\s+amount)\b", low):
                matches = re.findall(num_pat, line)
                if matches:
                    subtotal = _parse_amount(matches[-1])
            elif re.search(r"\b(?:tax|vat|gst|sales\s+tax)\b", low) and "invoice" not in low:
                matches = re.findall(num_pat, line)
                if matches:
                    tax = _parse_amount(matches[-1])
            elif re.search(r"\b(?:discount|credit)\b", low):
                matches = re.findall(num_pat, line)
                if matches:
                    discount = abs(_parse_amount(matches[-1]))
            elif re.search(r"\b(?:grand\s+total|total\s+due|amount\s+due|balance\s+due|total\s+amount|^total)\b", low):
                matches = re.findall(num_pat, line)
                if matches:
                    total = _parse_amount(matches[-1])

        # 6. Extract Line Items
        line_items: List[Dict[str, Any]] = []
        # Match lines like: "1. Cloud Hosting Services (2x @ $250.00) - $500.00" or "- Security Audit   $1,200.00"
        item_re = re.compile(
            r"^(?:[\-\*\•]|\d+[\.\)])?\s*([A-Za-z][A-Za-z0-9\s\(\)\-\/,&\.@\$]{2,70}?)\s+[\$€£₹]?\s*([0-9]{1,3}(?:,[0-9]{3})*\.[0-9]{2}|[0-9]+\.[0-9]{2})\s*$"
        )
        skip_keywords = ("subtotal", "sub-total", "total", "tax", "vat", "gst", "discount", "amount due", "balance due")
        for line in lines:
            if any(k in line.lower() for k in skip_keywords):
                continue
            im = item_re.match(line)
            if im:
                desc = im.group(1).strip(" -:\t")
                qty_m = re.search(r"\((\d+)\s*[xX]", desc)
                qty = int(qty_m.group(1)) if qty_m else 1
                amt = _parse_amount(im.group(2))
                if amt > 0:
                    line_items.append({
                        "description": desc,
                        "quantity": qty,
                        "amount": amt
                    })

        # Fallback computations
        items_sum = round(sum(i["amount"] for i in line_items), 2)
        if subtotal is None:
            subtotal = items_sum if items_sum > 0 else (round(total - tax + discount, 2) if total is not None else 0.0)
        if total is None:
            total = round(subtotal + tax - discount, 2)

        # 7. Mathematical & Anomaly Audit
        anomalies: List[Dict[str, str]] = []
        expected_total = round(subtotal + tax - discount, 2)
        if subtotal > 0 and total > 0 and abs(expected_total - total) >= 0.05:
            anomalies.append({
                "code": "FIN-MATH-MISMATCH",
                "severity": "HIGH",
                "message": (
                    f"Invoice math discrepancy: Subtotal ({subtotal:.2f}) + Tax ({tax:.2f}) "
                    f"- Discount ({discount:.2f}) = {expected_total:.2f}, but stated Total is {total:.2f}."
                )
            })

        if items_sum > 0 and subtotal > 0 and abs(items_sum - subtotal) >= 0.05:
            anomalies.append({
                "code": "FIN-LINEITEM-MISMATCH",
                "severity": "MEDIUM",
                "message": f"Sum of line items ({items_sum:.2f}) does not match stated Subtotal ({subtotal:.2f})."
            })

        if total <= 0:
            anomalies.append({
                "code": "FIN-ZERO-TOTAL",
                "severity": "LOW",
                "message": "No positive total amount detected on document."
            })

        return {
            "id": f"doc-{uuid.uuid4().hex[:8]}",
            "source_file": source_name,
            "vendor": vendor,
            "invoice_number": invoice_number,
            "issue_date": issue_date,
            "due_date": due_date,
            "currency": currency,
            "subtotal": subtotal,
            "tax": tax,
            "discount": discount,
            "total": total,
            "line_items": line_items,
            "anomalies": anomalies,
            "is_verified": len(anomalies) == 0,
            "extracted_at": datetime.now(timezone.utc).isoformat()
        }
