"""
ClauseGuard v1.2 CLI - Local-First Contract, NDA & Legal Redline Risk Scanner
Usage:
  python main.py scan <file_or_text> [--json]
  python main.py negotiate <file_or_text> [--json]
  python main.py demo
  python main.py version
"""

import argparse
import json
from pathlib import Path
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from clauseguard import __product__, __tagline__, __version__
from clauseguard.negotiator import NegotiationDrafter
from clauseguard.scanner import ContractRiskScanner

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    print(f"{CYAN}{BOLD}=============================================================================={RESET}")
    print(f"  {BOLD}{__product__} v{__version__}{RESET} — {__tagline__}")
    print(f"{CYAN}{BOLD}=============================================================================={RESET}")


def colorize_diff(diff_text: str) -> str:
    """Highlights [-deleted-] words in red and {+proposed+} words in green."""
    # Replace [-...-] with RED
    res = re.sub(r"(\[-\S+?-\])", rf"{RED}\1{RESET}", diff_text)
    # Replace {+...+ } with GREEN
    res = re.sub(r"(\{\+\S+?\+\})", rf"{GREEN}\1{RESET}", res)
    return res


def render_contract_report(report: dict):
    print_banner()
    score = report["safety_score"]
    col = GREEN if score >= 90 else (YELLOW if score >= 70 else RED)
    print(f"  Document:     {BOLD}{report['document']}{RESET}")
    print(f"  Safety Score: {col}{BOLD}{report['grade']} ({score}/100){RESET} | Verdict: {col}{BOLD}{report['verdict']}{RESET}")
    print("-" * 78)

    findings = report.get("findings", [])
    if not findings:
        print(f"\n  {GREEN}[✓] Clean Contract! Zero predatory or high-risk clauses detected.{RESET}\n")
    else:
        print(f"\n  {RED}{BOLD}[!] DETECTED {len(findings)} RISKY CLAUSE(S) & SUGGESTED ALTERNATIVE WORDING:{RESET}\n")
        for idx, f in enumerate(findings, start=1):
            sev_col = RED if f["severity"] in ("CRITICAL", "HIGH") else YELLOW
            print(f"  {idx}. {sev_col}{BOLD}[{f['severity']}]{RESET} {BOLD}{f['title']}{RESET} (Line {f['line']})")
            print(f"     {DIM}Clause Excerpt: \"{f['matched_excerpt']}\"{RESET}")
            print(f"     {YELLOW}Why It Hurts:{RESET}   {f['plain_english_risk']}")
            print(f"     {GREEN}{f['redline_counter_clause']}{RESET}\n")
    print("-" * 78)
    print(f"  {DIM}Honesty Guard: {report.get('disclaimer')}{RESET}")
    print("=" * 78 + "\n")


def render_negotiation_package(pkg: dict):
    print_banner()
    score = pkg["safety_score"]
    col = GREEN if score >= 90 else (YELLOW if score >= 70 else RED)
    print(f"  Document:     {BOLD}{pkg['document']}{RESET}")
    print(f"  Safety Score: {col}{BOLD}{pkg['grade']} ({score}/100){RESET} | Verdict: {col}{BOLD}{pkg['verdict']}{RESET}")
    print("-" * 78)

    redlines = pkg.get("redlines", [])
    if not redlines:
        print(f"\n  {GREEN}[✓] Agreement is completely clean! No redlines necessary.{RESET}\n")
    else:
        print(f"\n  {BOLD}WORD-LEVEL REDLINES & COUNTER-PROPOSALS ({len(redlines)}):{RESET}\n")
        for idx, r in enumerate(redlines, start=1):
            sev_col = RED if r["severity"] in ("CRITICAL", "HIGH") else YELLOW
            print(f"  {idx}. {sev_col}{BOLD}[{r['severity']}]{RESET} {BOLD}{r['title']}{RESET} (Line {r['line']})")
            print(f"     {YELLOW}Alignment Rationale:{RESET} {r['rationale']}")
            print(f"     {BOLD}Redline Diff:{RESET} {colorize_diff(r['redline_diff'])}\n")

    print("-" * 78)
    email = pkg.get("cover_email", {})
    if email:
        print(f"  {BOLD}COLLABORATIVE NEGOTIATION COVER LETTER:{RESET}")
        print(f"  {CYAN}Subject: {email.get('subject')}{RESET}")
        print("-" * 78)
        for line in email.get("body", "").splitlines():
            print(f"  {line}")

    print("-" * 78)
    print(f"  {DIM}Honesty Guard: {pkg.get('disclaimer')}{RESET}")
    print("=" * 78 + "\n")


def main():
    parser = argparse.ArgumentParser(description=f"{__product__} v{__version__} - {__tagline__}")
    sub = parser.add_subparsers(dest="command")

    p_scan = sub.add_parser("scan", help="Scan a contract, NDA, or SOW for predatory clauses")
    p_scan.add_argument("input", help="File path or raw contract text")
    p_scan.add_argument("--json", action="store_true", help="Output raw JSON")

    p_neg = sub.add_parser("negotiate", help="Generate word-level redline diffs and collaborative cover letter")
    p_neg.add_argument("input", help="File path or raw contract text")
    p_neg.add_argument("--recipient", default="Client Team", help="Counterparty recipient name")
    p_neg.add_argument("--json", action="store_true", help="Output raw JSON")

    sub.add_parser("demo", help="Run live predatory contract redlining demonstration")
    sub.add_parser("version", help="Show version")

    args = parser.parse_args()
    scanner = ContractRiskScanner()
    negotiator = NegotiationDrafter()

    if args.command == "version" or not args.command:
        print_banner()
        print(f"ClauseGuard Version: {__version__} (100% Offline Python Standard Library)")
        sys.exit(0)

    if args.command == "scan":
        raw = args.input
        doc_name = "Inline_Contract.txt"
        if "\n" not in raw and len(raw) < 256:
            p = Path(raw)
            if p.exists() and p.is_file():
                raw = p.read_text(encoding="utf-8", errors="replace")
                doc_name = p.name
        res = scanner.scan_contract(raw, document_name=doc_name)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            render_contract_report(res)
        sys.exit(0)

    if args.command == "negotiate":
        raw = args.input
        doc_name = "Inline_Contract.txt"
        if "\n" not in raw and len(raw) < 256:
            p = Path(raw)
            if p.exists() and p.is_file():
                raw = p.read_text(encoding="utf-8", errors="replace")
                doc_name = p.name
        scan_res = scanner.scan_contract(raw, document_name=doc_name)
        pkg = negotiator.generate_negotiation_package(scan_res, recipient_name=getattr(args, "recipient", "Client Team"))
        if args.json:
            print(json.dumps(pkg, indent=2))
        else:
            render_negotiation_package(pkg)
        sys.exit(0)

    if args.command == "demo":
        sample_contract = (
            "MASTER SERVICES AGREEMENT & STATEMENT OF WORK\n"
            "1. Liability: Consultant shall have unlimited liability for any and all damages arising out of this project.\n"
            "2. Intellectual Property: Consultant assigns all intellectual property upon creation regardless of payment.\n"
            "3. Term: This Agreement shall automatically renew for successive 24-month terms unless written notice is given 90 days prior.\n"
            "4. Payment: All invoices are payable Net 90 days after Client receipt.\n"
            "5. Scope: Consultant shall provide unlimited revisions until client is satisfied.\n"
            "6. Acceptance: Deliverables shall be deemed rejected if not expressly approved within 90 days.\n"
            "7. Warranty: Consultant provides perpetual warranty and free bug fixes in perpetuity.\n"
        )
        res = scanner.scan_contract(sample_contract, document_name="Demo_Predatory_SOW.txt")
        render_contract_report(res)
        sys.exit(0)


if __name__ == "__main__":
    main()
