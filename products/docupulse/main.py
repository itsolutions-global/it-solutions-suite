"""
DocuPulse v1.2 CLI - Autonomous Invoice, Receipt, AR Chaser & Financial Ledger Engine
Usage:
  python main.py parse <file_or_text> [--json]
  python main.py ledger [--export-csv <path>] [--json]
  python main.py chase [--today YYYY-MM-DD] [--interest-rate RATE] [--json]
  python main.py categorize [--export-csv <path>] [--json]
  python main.py demo
  python main.py version
"""

import argparse
import json
from pathlib import Path
import sys

# Ensure clean UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from docupulse import __product__, __tagline__, __version__
from docupulse.ledger import FinancialLedger
from docupulse.receivables import ReceivablesChaser
from docupulse.tax_mapper import ExpenseCategorizer

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    print(f"{CYAN}{BOLD}======================================================================{RESET}")
    print(f"  {BOLD}{__product__} v{__version__}{RESET} — {__tagline__}")
    print(f"{CYAN}{BOLD}======================================================================{RESET}")


def render_invoice_report(record: dict):
    print_banner()
    status_badge = f"{GREEN}{BOLD}[✓ VERIFIED]{RESET}" if record["is_verified"] else f"{RED}{BOLD}[! ANOMALY FLAGGED]{RESET}"
    print(f"  Vendor:         {BOLD}{record['vendor']}{RESET}")
    print(f"  Invoice #:      {CYAN}{record['invoice_number']}{RESET} | Status: {status_badge}")
    print(f"  Issue Date:     {record['issue_date']} | Due Date: {YELLOW}{record['due_date']}{RESET}")
    print("-" * 70)
    if record.get("line_items"):
        print(f"  {BOLD}Extracted Line Items:{RESET}")
        for idx, item in enumerate(record["line_items"], start=1):
            print(f"    {idx}. {item['description']} (x{item['quantity']}) — {record['currency']} {item['amount']:,.2f}")
        print("-" * 70)
    print(f"  Subtotal:       {record['currency']} {record['subtotal']:,.2f}")
    print(f"  Tax / VAT:      {record['currency']} {record['tax']:,.2f}")
    if record.get("discount", 0) > 0:
        print(f"  Discount:      -{record['currency']} {record['discount']:,.2f}")
    print(f"  {BOLD}TOTAL AMOUNT:   {GREEN}{record['currency']} {record['total']:,.2f}{RESET}")

    if record.get("anomalies"):
        print("-" * 70)
        print(f"  {RED}{BOLD}[!] FINANCIAL AUDIT ALERTS ({len(record['anomalies'])}):{RESET}")
        for a in record["anomalies"]:
            print(f"    - [{a['severity']}] {a['code']}: {a['message']}")
    print("=" * 70 + "\n")


def render_chase_report(chase_res: dict):
    print_banner()
    print(f"  As-Of Date:     {BOLD}{chase_res['as_of_date']}{RESET}")
    print(f"  Total Invoices: {chase_res['total_invoices']} | {RED}{BOLD}Overdue: {chase_res['overdue_count']} (${chase_res['overdue_total']:,.2f}){RESET}")
    print("-" * 70)

    for st_key, st_name in [
        ("stage_3_final", f"{RED}{BOLD}Stage 3 (Final Notice / 45+ Days Overdue){RESET}"),
        ("stage_2_formal", f"{YELLOW}{BOLD}Stage 2 (Formal Notice / 15-44 Days Overdue){RESET}"),
        ("stage_1_gentle", f"{CYAN}{BOLD}Stage 1 (Gentle Reminder / 1-14 Days Overdue){RESET}"),
        ("stage_0_not_due", f"{GREEN}Stage 0 (Current / Not Due){RESET}")
    ]:
        items = chase_res["stages"].get(st_key, [])
        if items:
            print(f"\n  {st_name} — {len(items)} item(s):")
            for it in items:
                print(f"    • {BOLD}{it['invoice_number']}{RESET} ({it['vendor']}): {it['currency']} {it['total']:,.2f} | Due: {it['due_date']} ({it['days_overdue']} days overdue)")
                email = it.get("email_draft", {})
                if email and it["is_overdue"]:
                    print(f"      {DIM}Subject: {email.get('subject')}{RESET}")

    print("\n" + "-" * 70)
    print(f"  {DIM}Honesty Guard: {chase_res.get('disclaimer')}{RESET}")
    print("=" * 70 + "\n")


def render_categorize_report(cat_res: dict):
    print_banner()
    print(f"  Expense Categorization Summary — {cat_res['total_documents']} documents | Total Spend: ${cat_res['total_spend']:,.2f}")
    print("-" * 70)

    for cat_name, data in cat_res.get("categories", {}).items():
        if data["count"] > 0:
            print(f"  • {BOLD}{cat_name:<24}{RESET}: {data['count']:>3} doc(s) — ${data['total']:>10,.2f}")

    print("-" * 70)
    print(f"  {DIM}Honesty Guard: {cat_res.get('disclaimer')}{RESET}")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description=f"{__product__} v{__version__} - {__tagline__}")
    sub = parser.add_subparsers(dest="command")

    p_parse = sub.add_parser("parse", help="Extract & audit an invoice or receipt from file or text")
    p_parse.add_argument("input", help="File path or raw invoice text")
    p_parse.add_argument("--json", action="store_true", help="Output raw JSON")

    p_ledger = sub.add_parser("ledger", help="View financial ledger summary or export to CSV")
    p_ledger.add_argument("--export-csv", help="Export ledger to specified CSV file path")
    p_ledger.add_argument("--json", action="store_true", help="Output raw JSON")

    p_chase = sub.add_parser("chase", help="Analyze overdue accounts receivable & generate progressive email drafts")
    p_chase.add_argument("--today", help="Evaluate as-of date (YYYY-MM-DD), default: current date")
    p_chase.add_argument("--interest-rate", type=float, help="Optional late-fee interest rate for Stage 3 (e.g. 1.5)")
    p_chase.add_argument("--json", action="store_true", help="Output raw JSON")

    p_cat = sub.add_parser("categorize", help="Categorize ledger expenses by operational category")
    p_cat.add_argument("--export-csv", help="Export categorized expenses to CSV file path")
    p_cat.add_argument("--json", action="store_true", help="Output raw JSON")

    sub.add_parser("demo", help="Run live invoice extraction & anomaly detection demo")
    sub.add_parser("version", help="Show version")

    args = parser.parse_args()
    ledger = FinancialLedger()

    if args.command == "version" or not args.command:
        print_banner()
        print(f"DocuPulse Version: {__version__} (100% Python Standard Library)")
        sys.exit(0)

    if args.command == "parse":
        raw = args.input
        src_name = "inline_invoice.txt"
        if "\n" not in raw and len(raw) < 256:
            p = Path(raw)
            if p.exists() and p.is_file():
                raw = p.read_text(encoding="utf-8", errors="replace")
                src_name = p.name
        rec = ledger.ingest_document(raw, source_name=src_name)
        if args.json:
            print(json.dumps(rec, indent=2))
        else:
            render_invoice_report(rec)
        sys.exit(0)

    if args.command == "ledger":
        if args.export_csv:
            ledger.export_csv(args.export_csv)
            print(f"{GREEN}[+] Exported financial ledger to {args.export_csv}{RESET}")
        summary = ledger.get_summary()
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print_banner()
            print(f"  Documents Tracked: {summary['total_documents']} | Total Spend: ${summary['total_spend']:,.2f} | Flagged: {summary['flagged_anomalies_count']}")
            print("=" * 70)
        sys.exit(0)

    if args.command == "chase":
        chaser = ReceivablesChaser(ledger_storage=ledger)
        records = ledger._read_all()
        # If ledger is empty, provide sample record for demonstration
        if not records:
            sample_records = [
                {
                    "vendor": "Acme Corp",
                    "invoice_number": "INV-2026-001",
                    "issue_date": "2026-10-01",
                    "due_date": "2026-10-15",
                    "total": 3500.00,
                    "currency": "USD"
                }
            ]
            res = chaser.chase_invoices(records=sample_records, today=args.today, interest_rate=args.interest_rate)
        else:
            res = chaser.chase_invoices(records=records, today=args.today, interest_rate=args.interest_rate)

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            render_chase_report(res)
        sys.exit(0)

    if args.command == "categorize":
        categorizer = ExpenseCategorizer()
        records = ledger._read_all()
        if not records:
            sample_records = [
                {
                    "vendor": "CloudScale Infrastructure Inc.",
                    "invoice_number": "INV-2026-8841",
                    "issue_date": "2026-11-10",
                    "total": 1242.00,
                    "currency": "USD",
                    "line_items": [{"description": "Dedicated Kubernetes Cluster", "amount": 800.0}]
                },
                {
                    "vendor": "GitHub Inc.",
                    "invoice_number": "INV-GH-102",
                    "issue_date": "2026-11-01",
                    "total": 42.00,
                    "currency": "USD",
                    "line_items": [{"description": "GitHub Enterprise SaaS Subscription", "amount": 42.0}]
                }
            ]
            res = categorizer.categorize_records(records=sample_records)
        else:
            res = categorizer.categorize_records(records=records)

        if args.export_csv:
            categorizer.export_csv(res, output_path=args.export_csv)
            if not args.json:
                print(f"{GREEN}[+] Exported categorized expenses to {args.export_csv}{RESET}")

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            render_categorize_report(res)
        sys.exit(0)

    if args.command == "demo":
        sample_invoice = (
            "Vendor: CloudScale Infrastructure Inc.\n"
            "Invoice #: INV-2026-8841\n"
            "Date: 2026-11-10\n"
            "Due Date: 2026-12-10\n\n"
            "1. Dedicated Kubernetes Cluster Node (2x @ $400.00) $800.00\n"
            "2. Managed Postgres High-Availability Storage $350.00\n\n"
            "Subtotal: $1,150.00\n"
            "Tax (8%): $92.00\n"
            "Total Due: $1,242.00\n"
        )
        rec = ledger.ingest_document(sample_invoice, source_name="demo_cloudscale_invoice.txt")
        render_invoice_report(rec)
        sys.exit(0)


if __name__ == "__main__":
    main()
