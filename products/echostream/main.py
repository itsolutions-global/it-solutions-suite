"""
EchoStream v1.0 - Autonomous Speech & Thought Stream Perception Engine
Usage:
  python main.py parse <file_or_text> [--dispatch] [--json]
  python main.py scan <text> [--json]
  python main.py demo
  python main.py version
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Add project root and suite root to sys.path
BASE_DIR = Path(__file__).resolve().parent
SUITE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(SUITE_DIR / "corepulse") not in sys.path:
    sys.path.insert(0, str(SUITE_DIR / "corepulse"))

# Safe console reconfigure on Windows
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

from echostream import __product__, __tagline__, __version__
from echostream.dispatcher import CorePulseDispatcher
from echostream.parser import SemanticStreamParser
from echostream.voice_guard import VoiceGuard

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    banner = fr"""{CYAN}{BOLD}
  _____      _             ____   _                               
 | ____|___ | |__    ___  / ___| | |_  _ __  ___   __ _  _ __ ___  
 |  _| / __|| '_ \  / _ \ \___ \ | __|| '__|/ _ \ / _` || '_ ` _ \ 
 | |___| (__ | | | || (_) | ___) || |_ | |  |  __/| (_| || | | | | |
 |_____|\___||_| |_| \___/ |____/  \__||_|   \___| \__,_||_| |_| |_|
{RESET}{DIM}    {__tagline__} [v{__version__}]{RESET}
    """
    print(banner)


def cmd_scan(args):
    """Executes VoiceGuard DLP scan against spoken text."""
    guard = VoiceGuard()
    result = guard.scan_and_redact(args.text)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print_banner()
    border = "=" * 76
    print(border)
    print(f"  {BOLD}ECHOSTREAM VOICEGUARD DLP AUDIT{RESET}")
    print(border)

    if result["is_clean"]:
        print(f"\n  {GREEN}[OK] Voice stream is 100% clean. Zero spoken credentials detected.{RESET}\n")
    else:
        print(f"\n  {RED}[!] SECURITY ALERT: {result['incidents_count']} spoken credential(s) intercepted!{RESET}\n")
        for idx, inc in enumerate(result["incidents"], start=1):
            print(f"    {idx}. {RED}{BOLD}[{inc['severity']}]{RESET} {BOLD}{inc['title']}{RESET}")
            print(f"       Masked Preview: {YELLOW}{inc['redacted_preview']}{RESET} (Entropy: {inc['entropy']})")
            print(f"       Description:    {inc['description']}")
            print(f"       {GREEN}Action:{RESET}         {inc['remediation']}")
            print()

    print(f"{BOLD}[+] Sanitized Transcript:{RESET}")
    print(f"    {result['redacted_text']}\n")
    print(border)


def cmd_parse(args):
    """Parses meeting transcript or thought stream text."""
    input_val = args.input
    text_content = input_val
    if "\n" not in input_val and len(input_val) < 256:
        try:
            p = Path(input_val)
            if p.exists() and p.is_file():
                text_content = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass

    # 1. VoiceGuard DLP Sanitize
    guard = VoiceGuard()
    scan_result = guard.scan_and_redact(text_content)
    clean_text = scan_result["redacted_text"]

    # 2. Semantic Parsing
    parser = SemanticStreamParser()
    if "[" in clean_text and "]" in clean_text:
        parsed = parser.parse_meeting_transcript(clean_text)
    else:
        parsed = parser.parse_thought_stream(clean_text)

    # 3. Optional Dispatch to CorePulse
    dispatch_result = None
    if args.dispatch and parsed.get("action_items"):
        dispatcher = CorePulseDispatcher()
        dispatch_result = dispatcher.dispatch_batch(parsed["action_items"])

    if args.json:
        output_payload = {
            "security_audit": scan_result,
            "parsed_structure": parsed,
            "dispatch": dispatch_result
        }
        print(json.dumps(output_payload, indent=2))
        return

    # Render Terminal Brief
    print_banner()
    border = "=" * 80
    sub_border = "-" * 80

    print(border)
    print(f"  {BOLD}ECHOSTREAM COGNITIVE INTAKE & TRIAGE BRIEF{RESET}")
    print(f"  Mode: {parsed.get('session_type', 'stream').replace('_', ' ').title()}")
    print(border)

    # Security Summary
    if not scan_result["is_clean"]:
        print(f"\n{RED}{BOLD}[!] SECURITY INTERCEPT:{RESET} Redacted {scan_result['incidents_count']} spoken secret(s) from stream.")
        for inc in scan_result["incidents"]:
            print(f"    - {RED}[{inc['severity']}]{RESET} {inc['title']}: {YELLOW}{inc['redacted_preview']}{RESET}")
    else:
        print(f"\n{GREEN}[✓] SECURITY AUDIT:{RESET} Clean voice stream. Zero unredacted credentials.")

    # Executive Summary
    if parsed.get("executive_summary"):
        print(f"\n{BOLD}[+] EXECUTIVE SUMMARY{RESET}")
        for bullet in parsed["executive_summary"]:
            print(f"    • {bullet}")

    # Decisions
    if parsed.get("decisions"):
        print(f"\n{BOLD}[+] KEY DECISIONS APPROVED ({len(parsed['decisions'])}){RESET}")
        for d in parsed["decisions"]:
            print(f"    ✔ {BOLD}{d['decision']}{RESET} (Speaker: {d['speaker']})")

    # Action Items
    actions = parsed.get("action_items", [])
    print(f"\n{BOLD}[+] EXTRACTED ACTION ITEMS & COMMITMENTS ({len(actions)}){RESET}")
    print(sub_border)

    if not actions:
        print(f"    {DIM}No explicit commitments detected.{RESET}")
    else:
        for idx, act in enumerate(actions, start=1):
            p_color = RED if act["priority"] == "critical" else (YELLOW if act["priority"] == "high" else GREEN)
            print(f"    {idx}. [{act['assignee']}] {BOLD}{act['title']}{RESET}")
            print(f"       Priority: {p_color}{act['priority'].upper()}{RESET} | Timeline: {act['due_date']} | Category: {act['category']}")
            print(f"       Quote: {DIM}\"{act['source_quote']}\"{RESET}")
            print()

    # Parking Lot
    if parsed.get("parking_lot"):
        print(f"{BOLD}[+] PARKING LOT / OPEN QUESTIONS ({len(parsed['parking_lot'])}){RESET}")
        for q in parsed["parking_lot"]:
            print(f"    ? {q['topic']} (Raised by: {q['speaker']})")
        print()

    # Dispatch Status
    if dispatch_result:
        print(sub_border)
        print(f"{GREEN}{BOLD}[✓] COREPULSE DISPATCH:{RESET} Successfully injected {dispatch_result['dispatched']} task(s) into CorePulse ({dispatch_result['mode']}).")

    print(border + "\n")


def cmd_demo(args):
    """Executes a live end-to-end demonstration of meeting transcription and triage."""
    sample_meeting = """
[David CTO] Good morning team. Today we must finalize our Q1 security roadmap and client deliverables.
[Sarah] I reviewed the authentication module. Our temporary staging key was sk-proj-98723418726354128937123987123987 and we need to revoke it immediately.  # nexus-ignore: secret-scan
[David CTO] Absolutely agreed on revoking that key. We decided to enforce zero-trust token rotation across all staging clusters.
[David CTO] Sarah, can you make sure to deploy the new auth patch before the client demo on Wednesday?
[Sarah] I will deploy the new auth patch and run regression testing before Wednesday.
[David CTO] Perfect. I will follow up with the enterprise customer regarding SOW approval by Friday afternoon.
[Sarah] Question: can we clarify our timeline for the Kubernetes cluster migration next week?
[David CTO] Let's table this for next Tuesday's infra sync.
"""
    print_banner()
    print(f"{CYAN}{BOLD}Starting Live EchoStream Demonstration...{RESET}\n")
    time.sleep(0.3)

    print(f"{BOLD}[1] Simulating Ingested Audio Transcript:{RESET}")
    print(DIM + sample_meeting.strip() + RESET + "\n")

    time.sleep(0.4)
    # Parse with dispatch enabled
    mock_args = argparse.Namespace(input=sample_meeting, dispatch=True, json=False)
    cmd_parse(mock_args)


def cmd_watch(args):
    """Monitors a drop directory for autonomous transcript ingestion."""
    from echostream.pipeline import AutonomousIngestionPipeline

    drop_path = args.dir if getattr(args, "dir", None) else os.getenv("COREPULSE_TRANSCRIPT_DROP_DIR", "data/transcripts")
    drop_dir = Path(drop_path).resolve()
    poll_interval = getattr(args, "poll_interval", 1.0) or 1.0

    pipeline = AutonomousIngestionPipeline(
        drop_dir=drop_dir,
        poll_interval=poll_interval,
        auto_dispatch=True
    )

    if getattr(args, "once", False):
        receipts = pipeline.scan_once()
        if getattr(args, "json", False):
            print(json.dumps({"processed_count": len(receipts), "receipts": receipts}, indent=2))
        else:
            print_banner()
            print(f"  {BOLD}Autonomous Ingestion Sweep Completed:{RESET} {len(receipts)} file(s) ingested.")
            for r in receipts:
                print(f"    - {GREEN}[{r.get('status', 'success').upper()}]{RESET} {r.get('source_file')} -> {r.get('tasks_extracted', 0)} tasks extracted (DLP: {r.get('secrets_redacted', 0)} redacted)")
        sys.exit(0)

    print_banner()
    border = "=" * 76
    print(border)
    print(f"  {BOLD}ECHOSTREAM AUTONOMOUS INGESTION PIPELINE (DAEMON){RESET}")
    print(f"  Watching Drop Directory: {CYAN}{drop_dir}{RESET}")
    print(f"  Polling Interval:        {poll_interval}s")
    print(f"  Lifecycle Archival:      {drop_dir / 'processed'}")
    print(f"  Quarantine Isolation:    {drop_dir / 'quarantine'}")
    print(f"  CorePulse Auto-Dispatch: {GREEN}ENABLED{RESET}")
    print(border)
    print("  Standby: Drop .txt, .vtt, .srt, .md, or .json transcript files to ingest.")
    print("  Press Ctrl+C to terminate watcher daemon.\n")

    pipeline.run_forever()


def cmd_merge(args):
    """Merges live scratchpad bullet notes with a meeting transcript and drafts a follow-up email."""
    from echostream.copilot import ScratchpadMerger, CommitmentTracker

    raw_transcript = args.transcript
    if "\n" not in raw_transcript and len(raw_transcript) < 256:
        try:
            p = Path(raw_transcript)
            if p.exists() and p.is_file():
                raw_transcript = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass

    raw_notes = args.notes or ""
    if raw_notes and "\n" not in raw_notes and len(raw_notes) < 256:
        try:
            np = Path(raw_notes)
            if np.exists() and np.is_file():
                raw_notes = np.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass

    merger = ScratchpadMerger()
    res = merger.merge_and_draft(
        transcript_text=raw_transcript,
        scratchpad_notes=raw_notes,
        meeting_title=args.title
    )

    tracker = CommitmentTracker()
    tracker.record_commitments(res.get("action_items", []), meeting_source=args.title)

    if args.dispatch and res.get("action_items"):
        dispatcher = CorePulseDispatcher()
        res["dispatch"] = dispatcher.dispatch_batch(res["action_items"])

    if args.json:
        print(json.dumps(res, indent=2))
        return

    print_banner()
    border = "=" * 80
    print(border)
    print(f"  {BOLD}GRANOLA-STYLE SCRATCHPAD + TRANSCRIPT MERGER{RESET}")
    print(f"  Meeting: {res['meeting_title']} | Actions Extracted: {len(res['action_items'])}")
    print(border)
    print(f"\n{BOLD}[+] READY-TO-SEND FOLLOW-UP EMAIL DRAFT{RESET}")
    print(f"  {CYAN}Subject:{RESET} {res['followup_email']['subject']}\n")
    for line in res["followup_email"]["body_markdown"].splitlines():
        print(f"  {line}")
    print("\n" + border)


def cmd_commitments(args):
    """Queries cross-meeting commitments by assignee or keyword."""
    from echostream.copilot import CommitmentTracker

    tracker = CommitmentTracker()
    res = tracker.query_commitments(
        assignee=args.assignee,
        query=args.query,
        include_dir=args.dir
    )

    if args.json:
        print(json.dumps(res, indent=2))
        return

    print_banner()
    border = "=" * 80
    print(border)
    print(f"  {BOLD}CROSS-MEETING COMMITMENT & ACCOUNTABILITY TRACKER{RESET}")
    print(f"  Total Commitments Indexed: {res['total_commitments']}")
    print(border)
    for idx, c in enumerate(res.get("commitments", []), start=1):
        print(f"  {idx}. [{CYAN}{c.get('assignee', 'Me')}{RESET}] {BOLD}{c.get('title')}{RESET}")
        print(f"     Due: {c.get('due_date')} | Priority: {c.get('priority', 'medium').upper()} | Source: {c.get('meeting_source')}")
    if not res.get("commitments"):
        print(f"  {DIM}No matching commitments found.{RESET}")
    print(border)


def main():
    parser = argparse.ArgumentParser(
        prog="echostream",
        description=f"{__product__} v{__version__} - {__tagline__}",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="EchoStream Commands")

    # parse command
    parse_p = subparsers.add_parser("parse", help="Parse meeting transcript or raw voice dump")
    parse_p.add_argument("input", help="File path or raw text string to parse")
    parse_p.add_argument("--dispatch", action="store_true", help="Dispatch extracted tasks to CorePulse")
    parse_p.add_argument("--json", action="store_true", help="Output results in JSON format")

    # scan command
    scan_p = subparsers.add_parser("scan", help="Run real-time VoiceGuard DLP credential scan")
    scan_p.add_argument("text", help="Spoken transcript string to scan and redact")
    scan_p.add_argument("--json", action="store_true", help="Output scan results in JSON format")

    # watch command
    watch_p = subparsers.add_parser("watch", help="Launch Autonomous Transcript Ingestion Pipeline directory watcher")
    watch_p.add_argument("dir", nargs="?", default="data/transcripts", help="Target drop directory to monitor (default: data/transcripts)")
    watch_p.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds")
    watch_p.add_argument("--once", action="store_true", help="Execute single ingestion sweep and exit")
    watch_p.add_argument("--json", action="store_true", help="Output sweep receipts in JSON format")

    # demo command
    subparsers.add_parser("demo", help="Run live executive meeting triage simulation")

    # merge command
    merge_p = subparsers.add_parser("merge", help="Merge live scratchpad notes with transcript & generate follow-up email draft")
    merge_p.add_argument("transcript", help="Meeting transcript string or file path")
    merge_p.add_argument("--notes", "-n", default="", help="Rough live scratchpad bullet notes or file path")
    merge_p.add_argument("--title", "-t", default="Executive Alignment & Next Steps", help="Meeting title")
    merge_p.add_argument("--dispatch", action="store_true", help="Dispatch merged tasks to CorePulse")
    merge_p.add_argument("--json", action="store_true", help="Output JSON payload")

    # commitments command
    comm_p = subparsers.add_parser("commitments", help="Query cross-meeting commitments by assignee or topic")
    comm_p.add_argument("--assignee", "-a", help="Filter commitments by assignee name (e.g. Sarah)")
    comm_p.add_argument("--query", "-q", help="Filter commitments by keyword")
    comm_p.add_argument("--dir", "-d", help="Optional transcript directory to index before querying")
    comm_p.add_argument("--json", action="store_true", help="Output JSON payload")

    # version command
    subparsers.add_parser("version", help="Display EchoStream version")

    if len(sys.argv) == 1:
        print_banner()
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.command == "version":
        print_banner()
        print(f"EchoStream Version: {__version__}")
        print("Zero External Dependencies: True (100% Python Standard Library)")
        sys.exit(0)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "parse":
        cmd_parse(args)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command == "demo":
        cmd_demo(args)
    elif args.command == "merge":
        cmd_merge(args)
    elif args.command == "commitments":
        cmd_commitments(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
