"""
DocuPulse v1.2 Expense Categorization Engine
Keyword-maps vendors and line items to standard operational expense categories
(Software & SaaS, Cloud Hosting, Travel, Meals, Office Supplies, Professional Services,
Advertising, Utilities, Other).

Honesty Guard: Labeled strictly as 'expense categorization' — do NOT claim IRS/HMRC
compliance, deductibility, or statutory tax returns.
Disclaimer: 'Not tax or legal advice — confirm with your accountant.'
"""

import csv
import io
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Union

DISCLAIMER = "Not tax or legal advice — confirm with your accountant."

CATEGORIES: List[str] = [
    "Software & SaaS",
    "Cloud Hosting",
    "Travel",
    "Meals",
    "Office Supplies",
    "Professional Services",
    "Advertising",
    "Utilities",
    "Other"
]

CATEGORY_PATTERNS: Dict[str, List[str]] = {
    "Cloud Hosting": [
        r"\baws\b", r"\bamazon\s+web\s+services\b", r"\bazure\b", r"\bgcp\b",
        r"\bgoogle\s+cloud\b", r"\bcloudflare\b", r"\bvercel\b", r"\bnetlify\b",
        r"\bheroku\b", r"\bdigitalocean\b", r"\blinode\b", r"\bhetzner\b",
        r"\bovh\b", r"\bsupabase\b", r"\brender\b", r"\bfly\.io\b",
        r"\bcloudscale\b", r"\bcloud\s+hosting\b", r"\bweb\s+hosting\b",
        r"\bserver\b", r"\bvps\b", r"\bcompute\s+engine\b", r"\bkubernetes\b",
        r"\bpostgres\b", r"\bmysql\b", r"\bdatabase\s+hosting\b", r"\bs3\s+storage\b"
    ],
    "Software & SaaS": [
        r"\bsoftware\b", r"\bsaas\b", r"\bsubscription\b", r"\blicense\b",
        r"\bgithub\b", r"\bgitlab\b", r"\bslack\b", r"\bzoom\b", r"\batlassian\b",
        r"\bjira\b", r"\bconfluence\b", r"\bnotion\b", r"\bfigma\b", r"\bmiro\b",
        r"\badobe\b", r"\bcanva\b", r"\bsalesforce\b", r"\bhubspot\b", r"\bzapier\b",
        r"\bairtable\b", r"\bopenai\b", r"\banthropic\b", r"\bcursor\b",
        r"\bjetbrains\b", r"\bdatadog\b", r"\bnew\s+relic\b", r"\bsentry\b",
        r"\b1password\b", r"\bbitwarden\b", r"\bgsuite\b", r"\bgoogle\s+workspace\b",
        r"\bmicrosoft\s*365\b", r"\boffice\s*365\b", r"\bdocu(?:sign|pulse)\b"
    ],
    "Travel": [
        r"\bairline\b", r"\bairways\b", r"\bflight\b", r"\bdelta\b", r"\bunited\b",
        r"\bsouthwest\b", r"\bamerican\s+airlines\b", r"\bbritish\s+airways\b",
        r"\blufthansa\b", r"\bexpedia\b", r"\bbooking\.com\b", r"\bairbnb\b",
        r"\bhotel\b", r"\bmotel\b", r"\bmarriott\b", r"\bhilton\b", r"\bhyatt\b",
        r"\buber\b", r"\blyft\b", r"\btaxi\b", r"\bcab\b", r"\btrain\b",
        r"\bamtrak\b", r"\beurostar\b", r"\bcar\s+rental\b", r"\bhertz\b",
        r"\benterprise\b", r"\btravel\b", r"\bparking\b", r"\btoll\b"
    ],
    "Meals": [
        r"\brestaurant\b", r"\bcafe\b", r"\bcoffee\b", r"\bstarbucks\b",
        r"\bdiner\b", r"\bbistro\b", r"\bgrill\b", r"\bfood\b", r"\bdining\b",
        r"\bcatering\b", r"\blunch\b", r"\bdinner\b", r"\bbreakfast\b",
        r"\bdoordash\b", r"\buber\s*eats\b", r"\bgrubhub\b", r"\bseamless\b",
        r"\bdeliveroo\b", r"\bbakery\b", r"\bpizza\b", r"\bburger\b"
    ],
    "Office Supplies": [
        r"\bstaples\b", r"\boffice\s+depot\b", r"\bofficemax\b", r"\bpaper\b",
        r"\bprinter\b", r"\bink\b", r"\btoner\b", r"\bstationery\b", r"\bpens\b",
        r"\bdesk\b", r"\bchair\b", r"\boffice\s+supplies\b", r"\bamazon\s+basics\b",
        r"\bhardware\s+store\b"
    ],
    "Professional Services": [
        r"\blegal\b", r"\blawyer\b", r"\battorney\b", r"\bcounsel\b",
        r"\baccounting\b", r"\baccountant\b", r"\bcpa\b", r"\bbookkeeping\b",
        r"\btax\s+prep\b", r"\baudit\b", r"\bconsulting\b", r"\bconsultant\b",
        r"\badvisory\b", r"\bcontractor\b", r"\bsubcontractor\b", r"\bfreelance\b",
        r"\bagency\b", r"\brecruiting\b", r"\bdesign\s+studio\b"
    ],
    "Advertising": [
        r"\bgoogle\s+ads\b", r"\badwords\b", r"\bfacebook\s+ads\b", r"\bmeta\s+ads\b",
        r"\blinkedin\s+ads\b", r"\btwitter\s+ads\b", r"\bx\s+ads\b", r"\btiktok\s+ads\b",
        r"\bbing\s+ads\b", r"\badvertising\b", r"\bmarketing\b", r"\bpromotional\b",
        r"\bcampaign\b", r"\bsponsorship\b", r"\bpr\s+firm\b", r"\bpublic\s+relations\b"
    ],
    "Utilities": [
        r"\belectric\b", r"\belectricity\b", r"\bpower\b", r"\benergy\b",
        r"\bwater\b", r"\bgas\s+utility\b", r"\bbroadband\b", r"\binternet\b",
        r"\btelecom\b", r"\bphone\b", r"\bmobile\b", r"\bcellular\b",
        r"\bverizon\b", r"\bat&t\b", r"\bt-mobile\b", r"\bcomcast\b",
        r"\bvodafone\b", r"\butility\b"
    ]
}


class ExpenseCategorizer:
    """Classifies invoice records into operational expense categories."""

    DISCLAIMER = DISCLAIMER
    CATEGORIES = CATEGORIES

    def __init__(self):
        self._compiled_patterns = {
            cat: [re.compile(p, re.IGNORECASE) for p in pats]
            for cat, pats in CATEGORY_PATTERNS.items()
        }

    def categorize_record(self, record: Dict[str, Any]) -> str:
        """
        Determines the most accurate expense category for an invoice record
        by inspecting vendor name and line item descriptions.
        """
        # Collect candidate search texts
        vendor = str(record.get("vendor", "")).strip()
        line_items = record.get("line_items", [])
        line_descs = " ".join(str(i.get("description", "")) for i in line_items if isinstance(i, dict))
        combined_text = f"{vendor} {line_descs}".strip()

        if not combined_text:
            return "Other"

        # Check Cloud Hosting first (often specific vendor names overlap with software)
        for cat in ["Cloud Hosting", "Software & SaaS", "Travel", "Meals", "Office Supplies", "Professional Services", "Advertising", "Utilities"]:
            for pat in self._compiled_patterns[cat]:
                if pat.search(combined_text):
                    return cat

        return "Other"

    def categorize_records(self, records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Categorizes a list of invoice records, returning per-category breakdown and summary metrics.
        """
        if records is None:
            from docupulse.ledger import FinancialLedger
            records = FinancialLedger()._read_all()

        category_groups: Dict[str, Dict[str, Any]] = {
            cat: {"category": cat, "count": 0, "total": 0.0, "records": []}
            for cat in self.CATEGORIES
        }

        annotated_records: List[Dict[str, Any]] = []
        grand_total = 0.0

        for rec in records:
            cat = self.categorize_record(rec)
            annotated = dict(rec)
            annotated["category"] = cat

            amount = float(rec.get("total", 0.0))
            grand_total += amount

            category_groups[cat]["count"] += 1
            category_groups[cat]["total"] = round(category_groups[cat]["total"] + amount, 2)
            category_groups[cat]["records"].append({
                "invoice_number": rec.get("invoice_number", "INV-UNKNOWN"),
                "vendor": rec.get("vendor", "Unknown Vendor"),
                "issue_date": rec.get("issue_date", ""),
                "amount": amount,
                "currency": rec.get("currency", "USD")
            })

            annotated_records.append(annotated)

        # Filter out empty categories for concise summary, while keeping full structure available
        active_breakdown = {
            cat: data for cat, data in category_groups.items() if data["count"] > 0
        }

        return {
            "label": "Expense Categorization",
            "total_documents": len(records),
            "total_spend": round(grand_total, 2),
            "categories": category_groups,
            "active_categories": active_breakdown,
            "records": annotated_records,
            "disclaimer": self.DISCLAIMER
        }

    def export_csv(
        self,
        categorized_data: Dict[str, Any],
        output_path: Optional[Union[str, Path]] = None
    ) -> str:
        """
        Exports categorized expense records to CSV format.
        Headers: Date, Vendor, Invoice Number, Category, Amount, Currency, Description
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Vendor", "Invoice Number", "Category", "Amount", "Currency", "Description"])

        for rec in categorized_data.get("records", []):
            date_val = rec.get("issue_date", "")
            vendor_val = rec.get("vendor", "")
            inv_val = rec.get("invoice_number", "")
            cat_val = rec.get("category", "Other")
            amt_val = f"{float(rec.get('total', 0.0)):.2f}"
            curr_val = rec.get("currency", "USD")
            line_items = rec.get("line_items", [])
            desc_val = "; ".join(i.get("description", "") for i in line_items if isinstance(i, dict))
            if not desc_val:
                desc_val = rec.get("source_file", "invoice")
            writer.writerow([date_val, vendor_val, inv_val, cat_val, amt_val, curr_val, desc_val])

        csv_content = output.getvalue()
        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(csv_content, encoding="utf-8")

        return csv_content
