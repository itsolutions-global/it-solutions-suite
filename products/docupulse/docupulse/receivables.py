"""
DocuPulse v1.2 Accounts Receivable (AR) Chaser
Computes overdue invoice aging from due date or terms (Net 30, Net 15, etc.),
classifies invoices into progressive collection stages (0: Not Due, 1: Gentle,
2: Formal, 3: Final Notice), and drafts professional, non-confrontational reminder emails.

Honesty Guard: Labeled as operational reminder automation — not tax or legal advice.
Never asserts statutory rights.
"""

from datetime import date, datetime, timedelta, timezone
import re
from typing import Any, Dict, List, Optional, Union

DISCLAIMER = "Not tax or legal advice — confirm with your accountant."


def parse_date_flexible(val: Any, base_issue_date: Optional[date] = None) -> Optional[date]:
    """
    Parses flexible date inputs:
    - datetime.date or datetime.datetime
    - ISO strings: YYYY-MM-DD
    - US strings: MM/DD/YYYY or M/D/YYYY
    - Terms relative to issue_date: 'Net 30', 'Net 15', 'Net 60', 'Net 45', 'Net 90'
    - 'Upon Receipt' / 'Due Upon Receipt'
    """
    if val is None:
        return None

    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val

    s = str(val).strip()
    if not s:
        return None

    # Handle Net X terms relative to base_issue_date
    net_match = re.match(r"(?i)^net\s*[-]?\s*(\d+)", s)
    if net_match:
        days = int(net_match.group(1))
        ref_date = base_issue_date or datetime.now(timezone.utc).date()
        return ref_date + timedelta(days=days)

    if re.match(r"(?i)^(?:due\s+)?(?:upon|on)\s+receipt$", s):
        return base_issue_date or datetime.now(timezone.utc).date()

    # Try ISO YYYY-MM-DD
    iso_m = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})", s)
    if iso_m:
        try:
            return date(int(iso_m.group(1)), int(iso_m.group(2)), int(iso_m.group(3)))
        except ValueError:
            pass

    # Try US MM/DD/YYYY
    us_m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s)
    if us_m:
        try:
            return date(int(us_m.group(3)), int(us_m.group(1)), int(us_m.group(2)))
        except ValueError:
            pass

    # Try strptime with standard formats
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    return None


class ReceivablesChaser:
    """Evaluates overdue receivables and drafts progressive reminder emails."""

    DISCLAIMER = DISCLAIMER

    def __init__(self, ledger_storage: Optional[Any] = None):
        self.ledger_storage = ledger_storage

    def classify_stage(self, days_overdue: int) -> int:
        """
        Classifies overdue duration into collection stages:
        Stage 0: days_overdue <= 0 (Not Due)
        Stage 1: 1 <= days_overdue <= 14 (Gentle Reminder)
        Stage 2: 15 <= days_overdue <= 44 (Formal Notice)
        Stage 3: days_overdue >= 45 (Final Notice)
        """
        if days_overdue <= 0:
            return 0
        if 1 <= days_overdue <= 14:
            return 1
        if 15 <= days_overdue <= 44:
            return 2
        return 3

    def draft_reminder_email(
        self,
        stage: int,
        invoice: Dict[str, Any],
        days_overdue: int,
        due_date_str: str,
        interest_rate: Optional[float] = None
    ) -> Dict[str, str]:
        """
        Synthesizes stage-appropriate reminder email copy (subject + body).
        Stage 3 may mention late-fee interest ONLY as an optional user-supplied rate (default none).
        Never asserts statutory rights.
        """
        vendor = invoice.get("vendor", "Client")
        inv_num = invoice.get("invoice_number", "INV-UNKNOWN")
        currency = invoice.get("currency", "USD")
        total = float(invoice.get("total", 0.0))
        total_formatted = f"{currency} {total:,.2f}"

        if stage == 0:
            subject = f"Upcoming Invoice Reminder: #{inv_num} - {vendor}"
            body = (
                f"Hi {vendor},\n\n"
                f"This is a courtesy reminder that Invoice #{inv_num} for {total_formatted} "
                f"is scheduled for payment on {due_date_str}.\n\n"
                f"Please let us know if you need any additional documentation or banking details.\n\n"
                f"Best regards,\nAccounts Receivable\n\n---\n{self.DISCLAIMER}"
            )
            return {"subject": subject, "body": body}

        if stage == 1:
            subject = f"Friendly Follow-up: Invoice #{inv_num} ({vendor})"
            body = (
                f"Hi {vendor},\n\n"
                f"I hope you are having a productive week.\n\n"
                f"This is a quick friendly follow-up regarding Invoice #{inv_num} for {total_formatted}, "
                f"which was due on {due_date_str} and is currently {days_overdue} day(s) overdue.\n\n"
                f"Could you please confirm if this invoice is in your payment queue or let us know if "
                f"you need an updated copy or banking information?\n\n"
                f"Thank you for your prompt attention.\n\n"
                f"Best regards,\nAccounts Receivable\n\n---\n{self.DISCLAIMER}"
            )
            return {"subject": subject, "body": body}

        if stage == 2:
            subject = f"Overdue Notice: Invoice #{inv_num} ({days_overdue} Days Past Due) - {vendor}"
            body = (
                f"Dear {vendor},\n\n"
                f"Our records indicate that Invoice #{inv_num} in the amount of {total_formatted} "
                f"remains unpaid and is now {days_overdue} days past due (originally due {due_date_str}).\n\n"
                f"We kindly request that you check on the remittance status and advise us on the scheduled "
                f"date of payment at your earliest convenience.\n\n"
                f"If there is any question or discrepancy regarding this billing, please let us know immediately "
                f"so we can assist.\n\n"
                f"Thank you for your cooperation.\n\n"
                f"Sincerely,\nFinance & Accounts Receivable\n\n---\n{self.DISCLAIMER}"
            )
            return {"subject": subject, "body": body}

        # Stage 3: Final Notice (45+ days)
        # Interest notice only if interest_rate is explicitly provided (> 0), never assert statutory rights.
        interest_clause = ""
        if interest_rate is not None and float(interest_rate) > 0:
            rate_val = float(interest_rate)
            # If user entered 0.015 instead of 1.5, scale to percentage display
            rate_pct = rate_val * 100.0 if rate_val < 0.20 else rate_val
            fee_amount = round(total * (rate_pct / 100.0), 2)
            interest_clause = (
                f"\nPlease note: Under our agreed terms, a late payment interest fee of {rate_pct:.1f}% "
                f"({currency} {fee_amount:,.2f}) may be applied to overdue balances outstanding.\n"
            )

        subject = f"FINAL NOTICE: Urgent Settlement Required for Invoice #{inv_num} ({days_overdue} Days Overdue)"
        body = (
            f"Dear {vendor},\n\n"
            f"Despite previous reminders, Invoice #{inv_num} in the amount of {total_formatted} "
            f"remains outstanding and is now {days_overdue} days overdue from the original due date of {due_date_str}.\n\n"
            f"We urgently request that you remit payment or provide verified wire transfer details within "
            f"five (5) business days.{interest_clause}\n"
            f"If payment has already been sent, please reply with the payment reference so we can update "
            f"your account immediately.\n\n"
            f"Sincerely,\nExecutive Accounts Management\n\n---\n{self.DISCLAIMER}"
        )
        return {"subject": subject, "body": body}

    def evaluate_invoice(
        self,
        invoice: Dict[str, Any],
        today: Optional[Union[str, date]] = None,
        interest_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """Evaluates a single invoice record and produces overdue analysis + draft reminder."""
        today_date = parse_date_flexible(today) if today else datetime.now(timezone.utc).date()
        if today_date is None:
            today_date = datetime.now(timezone.utc).date()

        issue_date_raw = invoice.get("issue_date")
        issue_date = parse_date_flexible(issue_date_raw)

        due_date_raw = invoice.get("due_date")
        due_date = parse_date_flexible(due_date_raw, base_issue_date=issue_date)

        if due_date is None:
            if issue_date:
                due_date = issue_date
            else:
                due_date = today_date

        days_overdue = (today_date - due_date).days
        stage = self.classify_stage(days_overdue)

        stage_labels = {
            0: "Stage 0 (Not Due)",
            1: "Stage 1 (Gentle Reminder)",
            2: "Stage 2 (Formal Notice)",
            3: "Stage 3 (Final Notice)"
        }

        due_date_display = due_date.isoformat()
        email_draft = self.draft_reminder_email(
            stage=stage,
            invoice=invoice,
            days_overdue=days_overdue,
            due_date_str=due_date_display,
            interest_rate=interest_rate
        )

        return {
            "invoice_number": invoice.get("invoice_number", "INV-UNKNOWN"),
            "vendor": invoice.get("vendor", "Unknown Vendor"),
            "issue_date": issue_date.isoformat() if issue_date else str(issue_date_raw),
            "due_date": due_date_display,
            "days_overdue": days_overdue,
            "is_overdue": days_overdue > 0,
            "stage": stage,
            "stage_label": stage_labels[stage],
            "total": float(invoice.get("total", 0.0)),
            "currency": invoice.get("currency", "USD"),
            "email_draft": email_draft,
            "disclaimer": self.DISCLAIMER
        }

    def chase_invoices(
        self,
        records: Optional[List[Dict[str, Any]]] = None,
        today: Optional[Union[str, date]] = None,
        interest_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """Analyzes a list of invoice records (or loads from ledger) and groups by stage."""
        if records is None:
            if self.ledger_storage:
                records = self.ledger_storage._read_all()
            else:
                from docupulse.ledger import FinancialLedger
                records = FinancialLedger()._read_all()

        today_date = parse_date_flexible(today) if today else datetime.now(timezone.utc).date()
        today_iso = today_date.isoformat() if today_date else datetime.now(timezone.utc).date().isoformat()

        evaluated: List[Dict[str, Any]] = []
        stages: Dict[str, List[Dict[str, Any]]] = {
            "stage_0": [],
            "stage_1": [],
            "stage_2": [],
            "stage_3": []
        }

        for rec in records:
            item = self.evaluate_invoice(rec, today=today_date, interest_rate=interest_rate)
            evaluated.append(item)
            key = f"stage_{item['stage']}"
            stages[key].append(item)

        overdue_items = [i for i in evaluated if i["is_overdue"]]
        overdue_total = round(sum(i["total"] for i in overdue_items), 2)

        return {
            "as_of_date": today_iso,
            "total_invoices": len(evaluated),
            "overdue_count": len(overdue_items),
            "overdue_total": overdue_total,
            "stages": {
                "stage_0_not_due": stages["stage_0"],
                "stage_1_gentle": stages["stage_1"],
                "stage_2_formal": stages["stage_2"],
                "stage_3_final": stages["stage_3"]
            },
            "invoices": evaluated,
            "disclaimer": self.DISCLAIMER
        }
