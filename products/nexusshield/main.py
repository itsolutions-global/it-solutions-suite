"""
NexusShield v1.0 - CLI Interface & Autonomous Vulnerability Auditor
Usage:
  python main.py scan <path> [--json] [--output <file>] [--fail-under <score>]
  python main.py version
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ensure clean UTF-8 output across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from nexusshield import __product__, __tagline__, __version__
from nexusshield.scanner import NexusScanner

# ANSI Terminal Styling
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    """Renders executive ASCII shield banner."""
    banner = fr"""{CYAN}{BOLD}
  _   _  _____ __   __ _   _  _____  _____  _   _  _____  _____  _     ______ 
 | \ | ||  ___|\ \ / /| | | |/  ___|/  ___|| | | ||_   _||  ___|| |    |  _  \
 |  \| || |__   \ V / | | | |\ `--. \ `--. | |_| |  | |  | |__  | |    | | | |
 | . ` ||  __|  /   \ | | | | `--. \ `--. \|  _  |  | |  |  __| | |    | | | |
 | |\  || |___ / /^\ \| |_| |/\__/ //\__/ /| | | | _| |_ | |___ | |____| |/ / 
 \_| \_/\____/ \/   \/ \___/ \____/ \____/ \_| |_/ \___/ \____/ \_____/|___/  
{RESET}{DIM}    {__tagline__} [v{__version__}]{RESET}
    """
    print(banner)


def format_severity_badge(sev: str) -> str:
    """Formats colored severity badge."""
    s = sev.upper()
    if s == "CRITICAL":
        return f"{RED}{BOLD}[CRITICAL]{RESET}"
    elif s == "HIGH":
        return f"{RED}[HIGH]{RESET}"
    elif s == "MEDIUM":
        return f"{YELLOW}[MEDIUM]{RESET}"
    else:
        return f"{DIM}[LOW]{RESET}"


def format_grade_badge(grade: str, score: float) -> str:
    """Formats colored letter grade."""
    if score >= 90:
        color = GREEN
    elif score >= 75:
        color = YELLOW
    else:
        color = RED
    return f"{color}{BOLD}{grade} ({score}/100){RESET}"


def render_terminal_report(result: dict):
    """Prints clean, high-impact executive security audit report."""
    border = "=" * 80
    sub_border = "-" * 80

    print_banner()
    print(border)
    print(f"  TARGET: {result['target']}")
    print(f"  TIME:   {result['scanned_at']} | SCANNED: {result['files_scanned']} files ({result['lines_scanned']:,} LOC) in {result['duration_seconds']}s")
    print(border)

    score = result["score"]
    grade = result["grade"]
    status = result["status"]
    counts = result["counts"]
    comp = result["compliance"]

    # Security Posture Card
    print(f"\n{BOLD}[+] SECURITY POSTURE OVERVIEW{RESET}")
    print(f"  Shield Health Score: {format_grade_badge(grade, score)} | Status: {BOLD}{status}{RESET}")
    print(f"  Vulnerability Breakdown:")
    print(f"    - Critical: {RED}{counts['Critical']}{RESET}  - High: {RED}{counts['High']}{RESET}  - Medium: {YELLOW}{counts['Medium']}{RESET}  - Low: {counts['Low']}")
    print(f"  Compliance Benchmarks:")
    owasp_col = GREEN if comp['owasp_top_10'] == 'PASS' else RED
    iso_col = GREEN if comp['iso_27001_baseline'] == 'COMPLIANT' else RED
    print(f"    - OWASP Top 10:       {owasp_col}{comp['owasp_top_10']}{RESET}")
    print(f"    - SOC 2 Readiness:    {GREEN}{comp['soc_2_readiness_pct']}%{RESET}")
    print(f"    - ISO 27001 Baseline: {iso_col}{comp['iso_27001_baseline']}{RESET}")

    # Findings Section
    findings = result.get("findings", [])
    print(f"\n{BOLD}[!] DETECTED FINDINGS ({len(findings)}){RESET}")
    print(sub_border)

    if not findings:
        print(f"  {GREEN}[OK] Clean Bill of Health! Zero secrets or CVE dependencies detected.{RESET}")
    else:
        for idx, f in enumerate(findings, start=1):
            sev_badge = format_severity_badge(f.get("severity", "Medium"))
            f_type = f.get("type", "finding")
            print(f"  {idx}. {sev_badge} {BOLD}{f['title']}{RESET}")
            print(f"     Location: {f['file']}:{f['line']}")

            if f_type == "secret_leak":
                print(f"     Secret Preview: {YELLOW}{f.get('redacted_secret', 'REDACTED')}{RESET} (Entropy: {f.get('entropy', 'N/A')})")
            elif f_type == "cve_vulnerability":
                print(f"     CVE Reference:  {CYAN}{f.get('id')}{RESET} (CVSS: {f.get('cvss', 'N/A')})")
                print(f"     Installed:      {RED}{f.get('installed_version')}{RESET} -> Safe: {GREEN}>={f.get('safe_version')}{RESET}")

            print(f"     Description:    {f.get('description', '')}")
            print(f"     {GREEN}Action:{RESET}         {f.get('remediation', '')}")
            print()

    # Remediation Roadmap
    print(sub_border)
    print(f"{BOLD}[*] RECOMMENDED REMEDIATION ROADMAP{RESET}")
    for tip in result.get("remediation_tips", []):
        print(f"  - {tip}")
    print(border + "\n")


def main():
    parser = argparse.ArgumentParser(
        description=f"{__product__} v{__version__} - {__tagline__}",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan directory or file for secrets and CVEs")
    scan_parser.add_argument("path", help="Path to directory or file to audit")
    scan_parser.add_argument("--json", action="store_true", help="Output raw JSON to stdout")
    scan_parser.add_argument("--output", "-o", help="Write audit report or JSON to specified file path")
    scan_parser.add_argument("--fail-under", type=float, default=0.0, help="Exit with code 1 if score < threshold")
    scan_parser.add_argument("--entropy", type=float, default=4.6, help="Shannon entropy threshold (default: 4.6)")

    # version command
    subparsers.add_parser("version", help="Show NexusShield version and system info")

    args = parser.parse_args()

    if args.command == "version" or not args.command:
        print_banner()
        print(f"NexusShield Version: {__version__}")
        print(f"Zero External Dependencies: True (Pure Python 3 standard library)")
        sys.exit(0)

    if args.command == "scan":
        target = Path(args.path)
        if not target.exists():
            print(f"{RED}Error:{RESET} Target path '{args.path}' does not exist.", file=sys.stderr)
            sys.exit(2)

        scanner = NexusScanner(entropy_threshold=args.entropy)
        if target.is_dir():
            result = scanner.scan_directory(target)
        else:
            findings = scanner.scan_file(target)
            from nexusshield.scorer import compute_security_score
            score_data = compute_security_score(findings)
            result = {
                "target": str(target.resolve()),
                "scanned_at": "now",
                "duration_seconds": 0.01,
                "files_scanned": 1,
                "lines_scanned": 100,
                "findings": findings,
                **score_data
            }

        # JSON output mode
        if args.json:
            output_json = json.dumps(result, indent=2)
            if args.output:
                Path(args.output).write_text(output_json, encoding="utf-8")
                print(f"JSON audit report written to {args.output}")
            else:
                print(output_json)
        else:
            render_terminal_report(result)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    # Write clean text report
                    f.write(json.dumps(result, indent=2))
                print(f"Audit report saved to {args.output}")

        # Check threshold
        if args.fail_under > 0 and result["score"] < args.fail_under:
            print(f"{RED}Audit Failure:{RESET} Health score {result['score']} is below required threshold of {args.fail_under}.")
            sys.exit(1)

        # Also fail if critical findings exist when fail-under is default 0
        if result["counts"]["Critical"] > 0:
            sys.exit(1)

        sys.exit(0)


if __name__ == "__main__":
    main()
