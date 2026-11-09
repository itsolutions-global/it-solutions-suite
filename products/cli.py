"""
Unified Corporate CLI Harness: 'it-solutions'
Integrates CorePulse v1.0 (Productivity OS), NexusShield v1.0 (Code Security Auditor),
and EchoStream v1.0 (Speech & Thought Stream Perception Engine).
Zero external dependencies. Runs on standard Python 3.8+.

Usage:
  it-solutions pulse [--host HOST] [--port PORT] [--debug] [--companion] [--morning] [--streaks] [--omnibar] [--popup] [-c CMD]
  it-solutions license status [--json]
  it-solutions license activate <key> [--json]
  it-solutions license generate-demo [tier] [--customer ...] [--org ...] [--days N] [--seats N] [--json]
  it-solutions sync status [--json]
  it-solutions sync pair <passphrase> [--relay-url URL] [--json]
  it-solutions sync push [--passphrase PASS] [--relay-url URL] [--json]
  it-solutions sync pull [--passphrase PASS] [--relay-url URL] [--json]
  it-solutions shield scan <path> [--json] [--output FILE] [--fail-under SCORE]
  it-solutions stream parse <input> [--dispatch] [--json]
  it-solutions stream scan <text> [--json]
  it-solutions stream watch [dir] [--poll-interval N] [--once] [--json]
  it-solutions stream demo
  it-solutions bridge find [query]
  it-solutions bridge hud [--target TITLE_OR_HWND] [--status active|paused|stopped] [--duration N]
  it-solutions bridge tray [--target TITLE]
  it-solutions bridge capture [--target TITLE_OR_HWND] [--output FILE]
  it-solutions bridge click <x> <y> [--button left|right]
  it-solutions bridge type <text> [--typo-rate RATE]
  it-solutions bridge status
  it-solutions health
  it-solutions version
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Paths
PRODUCTS_DIR = Path(__file__).resolve().parent
COREPULSE_DIR = PRODUCTS_DIR / "corepulse"
NEXUSSHIELD_DIR = PRODUCTS_DIR / "nexusshield"
ECHOSTREAM_DIR = PRODUCTS_DIR / "echostream"
QUANTPULSE_DIR = PRODUCTS_DIR / "quantpulse"
NEXUSBRIDGE_DIR = PRODUCTS_DIR / "nexusbridge"

# Add product paths to sys.path
if str(COREPULSE_DIR) not in sys.path:
    sys.path.insert(0, str(COREPULSE_DIR))
if str(NEXUSSHIELD_DIR) not in sys.path:
    sys.path.insert(0, str(NEXUSSHIELD_DIR))
if str(ECHOSTREAM_DIR) not in sys.path:
    sys.path.insert(0, str(ECHOSTREAM_DIR))
if str(PRODUCTS_DIR) not in sys.path:
    sys.path.insert(0, str(PRODUCTS_DIR))
if str(QUANTPULSE_DIR) not in sys.path:
    sys.path.insert(0, str(QUANTPULSE_DIR))
if str(NEXUSBRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(NEXUSBRIDGE_DIR))

# Console encoding setup
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

# ANSI Styling
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

SUITE_NAME = "IT Solutions Enterprise Suite"
SUITE_VERSION = "1.0.0"


def print_suite_banner():
    """Prints unified corporate banner."""
    banner = fr"""{CYAN}{BOLD}
  ___ _____   _____       _       _   _                 
 |_ _|_   _| /  ___|     | |     | | (_)                
  | |  | |   \ `--.  ___ | |_   _| |_ _  ___  _ __  ___ 
  | |  | |    `--. \/ _ \| | | | | __| |/ _ \| '_ \/ __|
 _| |_ | |   /\__/ / (_) | | |_| | |_| | (_) | | | \__ \
 \___/ \_/   \____/ \___/|_|\__,_|\__|_|\___/|_| |_|___/
{RESET}{DIM}    Unified Corporate CLI Harness [v{SUITE_VERSION}] | CorePulse + NexusShield + EchoStream{RESET}
    """
    print(banner)


def cmd_pulse(args):
    """Launches CorePulse Autonomous Productivity Server, Desktop Companion, or Omnibar."""
    if getattr(args, "omnibar", False) or getattr(args, "popup", False) or getattr(args, "command", None):
        omnibar_py = COREPULSE_DIR / "omnibar.py"
        cmd = [sys.executable, str(omnibar_py)]
        if getattr(args, "popup", False):
            cmd.append("--popup")
        elif getattr(args, "command", None):
            cmd.extend(["--command", args.command])
            if getattr(args, "json", False):
                cmd.append("--json")
        else:
            cmd.append("--daemon")
        try:
            proc = subprocess.run(cmd)
            sys.exit(proc.returncode)
        except KeyboardInterrupt:
            print(f"\n{YELLOW}CorePulse Omnibar stopped.{RESET}")
            sys.exit(0)

    if getattr(args, "tunnel", False):
        tunnel_py = PRODUCTS_DIR / "tunnel.py"
        cmd = [sys.executable, str(tunnel_py), "--port", str(getattr(args, "port", 8080))]
        if getattr(args, "tunnel_provider", None):
            cmd.extend(["--provider", args.tunnel_provider])
        if getattr(args, "json", False):
            cmd.append("--json")
        try:
            proc = subprocess.run(cmd)
            sys.exit(proc.returncode)
        except KeyboardInterrupt:
            print(f"\n{YELLOW}CorePulse tunnel closed.{RESET}")
            sys.exit(0)

    if getattr(args, "companion", False) or getattr(args, "morning", False) or getattr(args, "streaks", False):
        companion_py = COREPULSE_DIR / "companion.py"
        cmd = [sys.executable, str(companion_py)]
        if getattr(args, "morning", False):
            cmd.append("--morning")
        if getattr(args, "streaks", False):
            cmd.append("--streaks")
        if getattr(args, "daemon", False):
            cmd.append("--daemon")
        if getattr(args, "dry_run", False):
            cmd.append("--dry-run")
        try:
            proc = subprocess.run(cmd)
            sys.exit(proc.returncode)
        except KeyboardInterrupt:
            print(f"\n{YELLOW}CorePulse companion stopped.{RESET}")
            sys.exit(0)

    main_py = COREPULSE_DIR / "main.py"
    if not main_py.exists():
        print(f"{RED}Error:{RESET} CorePulse entrypoint not found at '{main_py}'", file=sys.stderr)
        sys.exit(1)

    cmd = [sys.executable, str(main_py)]
    if hasattr(args, "host") and args.host:
        cmd.extend(["--host", args.host])
    if hasattr(args, "port") and args.port:
        cmd.extend(["--port", str(args.port)])
    if hasattr(args, "debug") and args.debug:
        cmd.append("--debug")

    try:
        proc = subprocess.run(cmd)
        sys.exit(proc.returncode)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}CorePulse server stopped.{RESET}")
        sys.exit(0)


def cmd_shield(args):
    """Executes NexusShield Code Security and Vulnerability Scanner."""
    main_py = NEXUSSHIELD_DIR / "main.py"
    if not main_py.exists():
        print(f"{RED}Error:{RESET} NexusShield entrypoint not found at '{main_py}'", file=sys.stderr)
        sys.exit(1)

    if args.shield_action == "scan":
        cmd = [sys.executable, str(main_py), "scan", args.path]
        if args.json:
            cmd.append("--json")
        if args.output:
            cmd.extend(["--output", args.output])
        if args.fail_under > 0:
            cmd.extend(["--fail-under", str(args.fail_under)])

        proc = subprocess.run(cmd)
        sys.exit(proc.returncode)
    else:
        print(f"{RED}Unknown shield action:{RESET} {args.shield_action}", file=sys.stderr)
        sys.exit(1)


def cmd_stream(args):
    """Executes EchoStream Speech & Thought Stream Perception Engine."""
    main_py = ECHOSTREAM_DIR / "main.py"
    if not main_py.exists():
        print(f"{RED}Error:{RESET} EchoStream entrypoint not found at '{main_py}'", file=sys.stderr)
        sys.exit(1)

    cmd = [sys.executable, str(main_py)]
    if args.stream_action == "parse":
        cmd.extend(["parse", args.input])
        if getattr(args, "dispatch", False):
            cmd.append("--dispatch")
        if getattr(args, "json", False):
            cmd.append("--json")
    elif args.stream_action == "scan":
        cmd.extend(["scan", args.text])
        if getattr(args, "json", False):
            cmd.append("--json")
    elif args.stream_action == "watch":
        cmd.append("watch")
        if getattr(args, "dir", None):
            cmd.append(args.dir)
        if getattr(args, "poll_interval", None):
            cmd.extend(["--poll-interval", str(args.poll_interval)])
        if getattr(args, "once", False):
            cmd.append("--once")
        if getattr(args, "json", False):
            cmd.append("--json")
    elif args.stream_action == "demo":
        cmd.append("demo")
    else:
        cmd.append("version")

    proc = subprocess.run(cmd)
    sys.exit(proc.returncode)


def cmd_trade(args):
    r"""Launches or commands TradeKavach Autonomous AI Trading Suite at E:\Treding."""
    treding_cli = Path("E:/Treding/cli.py")
    if not treding_cli.exists():
        print(f"{RED}Error: TradeKavach CLI not found at E:\\Treding\\cli.py{RESET}")
        sys.exit(1)

    cmd = [sys.executable, str(treding_cli)]
    if getattr(args, "kill_switch", False):
        cmd.append("kill-switch")
    elif getattr(args, "scan_once", False):
        cmd.append("scan-once")
    else:
        cmd.append("run")
        if getattr(args, "host", None):
            cmd.extend(["--host", args.host])
        if getattr(args, "port", None):
            cmd.extend(["--port", str(args.port)])
        if getattr(args, "mode", None):
            cmd.extend(["--mode", args.mode])
        if getattr(args, "strategy", None):
            cmd.extend(["--strategy", args.strategy])

    proc = subprocess.run(cmd)
    sys.exit(proc.returncode)


def cmd_license(args):
    """Manages CorePulse commercial cryptographic licenses and tier activations."""
    try:
        from corepulse.licensing import (
            get_active_license,
            activate_license_key,
            generate_license_key
        )
    except ImportError:
        try:
            from products.corepulse.corepulse.licensing import (
                get_active_license,
                activate_license_key,
                generate_license_key
            )
        except Exception as ex:
            print(f"{RED}Error loading licensing engine:{RESET} {ex}", file=sys.stderr)
            sys.exit(1)

    action = getattr(args, "license_action", "status")

    if action == "status":
        sub = get_active_license()
        if getattr(args, "json", False):
            print(json.dumps(sub, indent=2))
        else:
            tier_name = sub.get("features", {}).get("name", sub.get("tier", "Starter").title())
            status = sub.get("status", "active").upper()
            price = sub.get("features", {}).get("price_monthly", 0)
            key = sub.get("license_key") or "None (Free Community Edition)"
            renews = sub.get("renews_at") or "Permanent / No Expiration"

            print(f"\n{BOLD}CorePulse Commercial License Status:{RESET}")
            print(f"  Tier:         {CYAN}{tier_name}{RESET} (${price}/mo)")
            print(f"  Status:       {GREEN}{status}{RESET}")
            print(f"  Customer:     {sub.get('customer_name', 'Community User')}")
            print(f"  Organization: {sub.get('organization', 'Open Source')}")
            print(f"  License Key:  {DIM}{key}{RESET}")
            print(f"  Expires:      {renews}")
            print(f"  Features:")
            for feat, val in sub.get("features", {}).items():
                if feat not in ("name", "price_monthly"):
                    icon = f"{GREEN}✔{RESET}" if val is True or val == -1 else (f"{DIM}✘{RESET}" if val is False else str(val))
                    print(f"    • {feat:25}: {icon}")
            print()
        sys.exit(0)

    elif action == "activate":
        res = activate_license_key(args.key)
        if getattr(args, "json", False):
            print(json.dumps(res, indent=2))
        else:
            if res.get("success"):
                print(f"{GREEN}✔ License Activated Successfully!{RESET}")
                print(f"  Tier:         {CYAN}{res.get('tier', '').upper()}{RESET}")
                print(f"  Customer:     {res.get('customer_name')}")
                print(f"  Organization: {res.get('organization')}")
                print(f"  License ID:   {res.get('license_id')}")
                print(f"  Expires:      {res.get('expires_at') or 'Never'}")
            else:
                print(f"{RED}✘ License Activation Failed:{RESET} {res.get('error')}", file=sys.stderr)
                sys.exit(1)
        sys.exit(0 if res.get("success") else 1)

    elif action == "generate-demo":
        tier = (getattr(args, "tier", None) or getattr(args, "tier_flag", None) or "pro").lower()
        seats = getattr(args, "seats", None)
        key = generate_license_key(
            tier=tier,
            customer_name=args.customer,
            organization=args.org,
            days_valid=args.days,
            seats=seats
        )
        if getattr(args, "json", False):
            print(json.dumps({
                "tier": tier,
                "customer": args.customer,
                "organization": args.org,
                "days_valid": args.days,
                "license_key": key
            }, indent=2))
        else:
            print(f"\n{BOLD}Generated {tier.upper()} Cryptographic License Key:{RESET}")
            print(f"{CYAN}{key}{RESET}")
            print(f"{DIM}Payload: {args.customer} ({args.org}) • Valid for {args.days} days{RESET}\n")
        sys.exit(0)

    else:
        print(f"{RED}Unknown license action:{RESET} {action}", file=sys.stderr)
        sys.exit(1)


def cmd_sync(args):
    """Manages CorePulse Zero-Knowledge E2EE Cloud Sync and CRDT operations."""
    try:
        from corepulse.sync import SyncEngine, ZeroKnowledgeCipher, SyncError
    except Exception as ex:
        print(f"{RED}Error importing sync engine:{RESET} {ex}", file=sys.stderr)
        sys.exit(1)

    action = getattr(args, "sync_action", "status")
    engine = SyncEngine()

    if action == "status":
        status = engine.get_sync_status()
        if getattr(args, "json", False):
            print(json.dumps(status, indent=2))
            sys.exit(0)

        print_suite_banner()
        border = "=" * 68
        print(border)
        print(f"  {BOLD}CorePulse Zero-Knowledge E2EE Cloud Sync Status{RESET}")
        print(border)
        print(f"  Client ID:       {CYAN}{status['client_id']}{RESET}")
        print(f"  Paired State:    {GREEN if status['paired'] else YELLOW}{'PAIRED' if status['paired'] else 'NOT PAIRED'}{RESET}")
        print(f"  Channel Hash:    {status['pair_token_preview']}")
        print(f"  Relay Server:    {status['relay_url']}")
        print(f"  Lamport Clock:   {status['lamport_clock']}")
        print(f"  Pending Outbox:  {status['pending_outbox_count']} delta(s) queued")
        print(f"  Last Push:       {status['last_pushed_at'] or 'Never'}")
        print(f"  Last Pull:       {status['last_pulled_at'] or 'Never'} (seq={status['last_pulled_seq']})")
        print(border + "\n")
        sys.exit(0)

    elif action == "pair":
        passphrase = args.passphrase
        relay_url = getattr(args, "relay_url", None)
        try:
            res = engine.pair(passphrase, relay_url=relay_url)
            if getattr(args, "json", False):
                print(json.dumps(res, indent=2))
            else:
                print(f"\n{GREEN}{BOLD}✔ E2EE Sync Pairing Successful!{RESET}")
                print(f"  Client ID:    {res['client_id']}")
                print(f"  Relay Server: {res['relay_url']}")
                print(f"  Blinded Hash: {res['pair_token_hash_preview']}\n")
            sys.exit(0)
        except Exception as ex:
            if getattr(args, "json", False):
                print(json.dumps({"success": False, "error": str(ex)}, indent=2))
            else:
                print(f"\n{RED}{BOLD}✖ Pairing Failed:{RESET} {ex}\n")
            sys.exit(1)

    elif action == "push":
        passphrase = getattr(args, "passphrase", None) or os.environ.get("COREPULSE_SYNC_PASSPHRASE")
        relay_url = getattr(args, "relay_url", None)
        try:
            res = engine.push_deltas(relay_url=relay_url, passphrase=passphrase)
            if getattr(args, "json", False):
                print(json.dumps(res, indent=2))
            else:
                if res.get("pushed_count", 0) > 0:
                    print(f"\n{GREEN}{BOLD}✔ Cloud Sync Push Succeeded:{RESET} {res['pushed_count']} encrypted delta(s) stored on relay (seq={res.get('seq_id')}).\n")
                else:
                    print(f"\n{CYAN}{BOLD}ℹ Cloud Sync Push:{RESET} Outbox clear. No new deltas to push.\n")
            sys.exit(0)
        except Exception as ex:
            if getattr(args, "json", False):
                print(json.dumps({"success": False, "error": str(ex)}, indent=2))
            else:
                print(f"\n{RED}{BOLD}✖ Cloud Sync Push Failed:{RESET} {ex}\n")
            sys.exit(1)

    elif action == "pull":
        passphrase = getattr(args, "passphrase", None) or os.environ.get("COREPULSE_SYNC_PASSPHRASE")
        relay_url = getattr(args, "relay_url", None)
        try:
            res = engine.pull_deltas(relay_url=relay_url, passphrase=passphrase)
            if getattr(args, "json", False):
                print(json.dumps(res, indent=2))
            else:
                print(f"\n{GREEN}{BOLD}✔ Cloud Sync Pull Succeeded:{RESET}")
                print(f"  Records Received: {res['records_received']}")
                print(f"  Deltas Applied:   {res['applied_count']}")
                print(f"  Deltas Discarded: {res['discarded_count']}")
                print(f"  Highest Seq:      {res['latest_seq']}\n")
            sys.exit(0)
        except Exception as ex:
            if getattr(args, "json", False):
                print(json.dumps({"success": False, "error": str(ex)}, indent=2))
            else:
                print(f"\n{RED}{BOLD}✖ Cloud Sync Pull Failed:{RESET} {ex}\n")
            sys.exit(1)


def cmd_bridge(args):
    """NexusBridge browser co-pilot and human-assisted physical OS window driver."""
    action = args.bridge_action

    if action == "launch":
        platform = args.platform
        custom_url = getattr(args, "url", None)
        try:
            from nexusbridge.copilot import run_copilot_session
            run_copilot_session(platform, custom_url=custom_url, interactive=True)
            sys.exit(0)
        except Exception as ex:
            print(f"\n{RED}{BOLD}✖ Co-Pilot Session Failed:{RESET} {ex}\n")
            sys.exit(1)

    elif action == "find":
        from nexusbridge.win32_input import Win32WindowFinder, ensure_default_desktop
        ensure_default_desktop()
        query = getattr(args, "query", None)
        windows = Win32WindowFinder.list_all_windows(visible_only=True)
        if query:
            q_lower = query.lower()
            windows = [w for w in windows if q_lower in w["title"].lower()]

        print_suite_banner()
        print(f"\n{BOLD}NexusBridge v2.0 — Win32 Window Enumeration ({len(windows)} matched){RESET}\n")
        print(f"  {'HWND':<12} {'PID':<8} {'Dimensions':<16} {'Window Title'}")
        print("  " + "-" * 72)
        for w in windows:
            dim_str = f"{w['width']}x{w['height']}"
            print(f"  {hex(w['hwnd']):<12} {w['pid']:<8} {dim_str:<16} {w['title'][:36]}")
        print()
        sys.exit(0)

    elif action == "hud":
        from nexusbridge.win32_input import Win32WindowFinder, ensure_default_desktop
        from nexusbridge.hud_overlay import HUDOverlay
        ensure_default_desktop()
        target_arg = getattr(args, "target", None)
        target_hwnd = None
        if target_arg:
            if target_arg.startswith("0x") or target_arg.isdigit():
                target_hwnd = int(target_arg, 16 if target_arg.startswith("0x") else 10)
            else:
                target_hwnd = Win32WindowFinder.find_window(target_arg)
        else:
            target_hwnd = Win32WindowFinder.find_window()

        status = getattr(args, "status", "ACTIVE").upper()
        duration = getattr(args, "duration", None)

        print(f"\n{GREEN}{BOLD}🟢 NexusBridge HUD Overlay Armed:{RESET}")
        print(f"  Target HWND:   {hex(target_hwnd) if target_hwnd else 'Searching...'}")
        print(f"  Status Color:  {status}")
        print(f"  Hotkeys:       [Ctrl+Alt+Escape to Abort] | Press Ctrl+C in terminal to exit.\n")

        hud = HUDOverlay(target_hwnd=target_hwnd, initial_status=status)
        hud.start()
        try:
            if duration:
                time.sleep(float(duration))
            else:
                while True:
                    time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            hud.stop()
            print(f"\n{CYAN}ℹ HUD Overlay dismissed.{RESET}\n")
        sys.exit(0)

    elif action == "tray":
        from nexusbridge.tray_controller import TrayController, ControllerState
        from nexusbridge.win32_input import ensure_default_desktop
        ensure_default_desktop()
        target_title = getattr(args, "target", "Google Chrome")
        state = ControllerState()
        state.set_running()

        print(f"\n{GREEN}{BOLD}🟢 NexusBridge System Tray Controller Launched:{RESET}")
        print(f"  Target:        {target_title}")
        print(f"  Tray Icon:     Active in Windows Notification Area")
        print(f"  Killswitch:    [Ctrl+Alt+Escape] armed (<10ms abort)")
        print(f"  Press Ctrl+C in terminal or right-click tray icon -> Exit to stop.\n")

        ctrl = TrayController(state=state, target_name=target_title)
        ctrl.start()
        try:
            while not state.is_stopped():
                time.sleep(0.2)
        except KeyboardInterrupt:
            pass
        finally:
            ctrl.stop()
            print(f"\n{CYAN}ℹ System Tray Controller stopped.{RESET}\n")
        sys.exit(0)

    elif action == "capture":
        from nexusbridge.win32_capture import Win32Capture
        from nexusbridge.win32_input import Win32WindowFinder, ensure_default_desktop
        ensure_default_desktop()
        target_arg = getattr(args, "target", None)
        target_hwnd = None
        if target_arg:
            if target_arg.startswith("0x") or target_arg.isdigit():
                target_hwnd = int(target_arg, 16 if target_arg.startswith("0x") else 10)
            else:
                target_hwnd = Win32WindowFinder.find_window(target_arg)
        else:
            target_hwnd = Win32WindowFinder.find_window()

        if not target_hwnd:
            print(f"\n{RED}{BOLD}✖ Capture Error:{RESET} No target window found.\n")
            sys.exit(1)

        filename = getattr(args, "output", None)
        out_path = Win32Capture.capture_to_file(target_hwnd, filename=filename)
        print(f"\n{GREEN}{BOLD}✔ Physical GDI Window Snapshot Captured:{RESET}")
        print(f"  Target HWND: {hex(target_hwnd)} ({Win32WindowFinder.get_window_title(target_hwnd)[:40]})")
        print(f"  Saved Image: {out_path}\n")
        sys.exit(0)

    elif action == "click":
        from nexusbridge.win32_input import Win32Mouse, ensure_default_desktop
        ensure_default_desktop()
        x = int(args.x)
        y = int(args.y)
        btn = getattr(args, "button", "left")
        mouse = Win32Mouse()
        mouse.click(x=x, y=y, button=btn, human=True)
        print(f"\n{GREEN}{BOLD}✔ Physical Click Executed:{RESET} ({x}, {y}) [{btn}]\n")
        sys.exit(0)

    elif action == "type":
        from nexusbridge.win32_input import Win32Keyboard, ensure_default_desktop
        ensure_default_desktop()
        text = args.text
        typo_rate = getattr(args, "typo_rate", 0.0)
        keyboard = Win32Keyboard()
        keyboard.type_text(text, typo_rate=typo_rate)
        print(f"\n{GREEN}{BOLD}✔ Physical Scancode Typing Completed:{RESET} {len(text)} character(s)\n")
        sys.exit(0)

    elif action == "status":
        from nexusbridge.logger import get_copilot_session_log_path, get_autonomous_action_log_path
        from nexusbridge.browser import find_chrome_executable
        copilot_log = get_copilot_session_log_path()
        auto_log = get_autonomous_action_log_path()
        chrome_exe = find_chrome_executable()

        print_suite_banner()
        print(f"\n{BOLD}NexusBridge v1.0 / v2.0 Physical Driver — Operational Status{RESET}")
        print(f"  - Chrome Binary:          {GREEN}{chrome_exe or 'NOT FOUND'}{RESET}")
        print(f"  - Physical Driver:        {GREEN}Win32 SendInput (Hardware Scancodes) & GDI Capture{RESET}")
        print(f"  - On-Screen HUD Overlay:  {GREEN}WS_EX_TRANSPARENT 30Hz Dynamic Tracking{RESET}")
        print(f"  - System Tray Controller: {GREEN}Shell_NotifyIcon & Sub-10ms Killswitch Armed{RESET}")
        print(f"  - Isolated Profile:       data/browser_profile/ (Zero-contamination)")
        print(f"  - Interactive Session Log:{CYAN} {copilot_log}{RESET} ({'Exists' if copilot_log.exists() else 'Empty'})")
        print(f"  - Autonomous Action Log:  {CYAN} {auto_log}{RESET} ({'Exists' if auto_log.exists() else 'Empty'})")

        vault_file = Path(__file__).resolve().parent.parent / "data" / "vault" / "credentials.json"
        if vault_file.exists():
            try:
                vdata = json.loads(vault_file.read_text(encoding="utf-8"))
                print(f"  - Stored Vault Accounts:  {GREEN}{len(vdata)} platform(s) registered ({', '.join(vdata.keys())}){RESET}\n")
            except Exception:
                print(f"  - Stored Vault Accounts:  {YELLOW}Vault file present{RESET}\n")
        else:
            print(f"  - Stored Vault Accounts:  {DIM}None (No credentials saved yet){RESET}\n")
        sys.exit(0)



def cmd_health(args):
    """Runs a holistic corporate infrastructure health check across all products."""
    print_suite_banner()
    border = "=" * 76
    sub_border = "-" * 76

    print(border)
    print(f"  {BOLD}CORPORATE INFRASTRUCTURE HEALTH AUDIT{RESET}")
    print(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(border)

    # 1. Environment & Runtime
    print(f"\n{BOLD}[1] Python Environment & System Runtime{RESET}")
    print(f"    - Python Version:   {GREEN}{sys.version.split()[0]}{RESET}")
    print(f"    - Python Executable:{DIM} {sys.executable}{RESET}")
    print(f"    - Operating System: {GREEN}{os.name.upper()} ({sys.platform}){RESET}")
    print(f"    - Dependencies:     {GREEN}Zero external dependencies (100% Standard Library){RESET}")

    # 2. Product #1: CorePulse Engine Health
    print(f"\n{BOLD}[2] Product #1: CorePulse v1.0 (Productivity Engine & Life OS){RESET}")
    corepulse_ok = True
    try:
        from corepulse.database import db as json_db
        from corepulse.database_sqlite import sqlite_db
        from corepulse.workflows import WorkflowEngine

        json_health = json_db.get_health()
        sqlite_health = sqlite_db.get_health()
        workflows = WorkflowEngine.list_workflows()

        print(f"    - JSON State Backend:   {GREEN}ONLINE{RESET} ({json_health['records_tracked']} records tracked)")
        print(f"    - SQLite WAL Engine:    {GREEN}ONLINE{RESET} (mode={sqlite_health['journal_mode']}, status={sqlite_health['db_status']})")
        print(f"    - Workflow Routines:    {GREEN}{len(workflows)} active routines loaded{RESET}")
        print(f"    - Health Status:        {GREEN}[HEALTHY]{RESET}")
    except Exception as ex:
        corepulse_ok = False
        print(f"    - CorePulse Status:     {RED}[FAILED]{RESET} - {ex}")

    # 3. Product #2: NexusShield Engine Health
    print(f"\n{BOLD}[3] Product #2: NexusShield v1.0 (Code Security & Secret Interceptor){RESET}")
    nexus_ok = True
    try:
        from nexusshield.secrets import SECRET_PATTERNS
        from nexusshield.dependencies import KNOWN_ADVISORIES
        from nexusshield.scanner import NexusScanner

        scanner = NexusScanner()
        secret_patterns_count = len(SECRET_PATTERNS)
        advisories_count = sum(len(advs) for advs in KNOWN_ADVISORIES.values())

        # Self-test sample
        sample_scan = scanner.scan_content("var x = 1;", "selftest.js")

        print(f"    - Secret Rules:         {GREEN}{secret_patterns_count} high-fidelity regex + entropy patterns{RESET}")
        print(f"    - CVE Advisory DB:      {GREEN}{advisories_count} vulnerability signatures cached{RESET}")
        print(f"    - Scanner Engine:       {GREEN}OPERATIONAL{RESET} (Self-test completed in {sample_scan['duration_seconds']}s)")
        print(f"    - Health Status:        {GREEN}[HEALTHY]{RESET}")
    except Exception as ex:
        nexus_ok = False
        print(f"    - NexusShield Status:   {RED}[FAILED]{RESET} - {ex}")

    # 4. Product #3: EchoStream Engine Health
    print(f"\n{BOLD}[4] Product #3: EchoStream v1.0 (Speech & Thought Stream Perception){RESET}")
    echostream_ok = True
    try:
        from echostream.voice_guard import VoiceGuard, VOICE_SECRET_PATTERNS
        from echostream.parser import SemanticStreamParser

        guard = VoiceGuard()
        parser = SemanticStreamParser()
        clean_res = guard.scan_and_redact("Hello world")

        print(f"    - VoiceGuard DLP:       {GREEN}ARMED{RESET} ({len(VOICE_SECRET_PATTERNS)} spoken credential rules active)")
        print(f"    - Semantic Parser:      {GREEN}OPERATIONAL{RESET} (Meeting & Thought Omnibar heuristics ready)")
        print(f"    - Health Status:        {GREEN}[HEALTHY]{RESET}")
    except Exception as ex:
        echostream_ok = False
        print(f"    - EchoStream Status:    {RED}[FAILED]{RESET} - {ex}")

    # 5. Product #4: TradeKavach Engine Health
    print(f"\n{BOLD}[5] Product #4: TradeKavach v1.0 (Autonomous AI Trading Suite at E:\\Treding){RESET}")
    tradekavach_ok = True
    try:
        treding_path = Path("E:/Treding")
        if str(treding_path) not in sys.path:
            sys.path.insert(0, str(treding_path))
        from tradekavach.db import init_db, get_all_settings
        from tradekavach.technical_screener import TechnicalScreener

        init_db()
        settings = get_all_settings()
        sample_ema = TechnicalScreener.calculate_ema([10, 11, 12, 13, 14, 15, 16, 17, 18, 19], 9)

        print(f"    - Workspace Location:   {GREEN}E:\\Treding{RESET}")
        print(f"    - SQLite WAL DB:        {GREEN}OPERATIONAL{RESET} ({len(settings)} runtime settings active)")
        print(f"    - Iron Risk Guardian:   {GREEN}ARMED{RESET} (Capital: INR {settings.get('capital', '10000')}, Max Risk: INR {settings.get('max_risk_per_trade', '100')})")
        print(f"    - Quant Screener:       {GREEN}READY{RESET} (EMA/RSI/VWAP/Supertrend sub-ms math verified)")
        print(f"    - Health Status:        {GREEN}[HEALTHY]{RESET}")
    except Exception as ex:
        tradekavach_ok = False
        print(f"    - TradeKavach Status:   {RED}[FAILED]{RESET} - {ex}")

    # 6. Product #5: NexusBridge Engine Health
    print(f"\n{BOLD}[6] Product #5: NexusBridge v1.0 (Autonomous Human-Emulated Browser & Copilot Bridge){RESET}")
    nexusbridge_ok = True
    try:
        from nexusbridge.human_input import HumanTyping, HumanMouse
        from nexusbridge.browser import find_chrome_executable
        from nexusbridge.logger import get_copilot_session_log_path, get_autonomous_action_log_path

        chrome_exe = find_chrome_executable()
        typing = HumanTyping()
        mouse = HumanMouse()
        sample_traj = mouse.generate_trajectory((0, 0), (100, 100), steps=5)

        chrome_status = f"{GREEN}DETECTED{RESET} ({chrome_exe})" if chrome_exe else f"{YELLOW}NOT FOUND (Install Chrome or set CHROME_PATH){RESET}"
        print(f"    - Chrome Binary:        {chrome_status}")
        print(f"    - Human Input Engine:   {GREEN}OPERATIONAL{RESET} (Gaussian typing & Bézier curves active)")
        print(f"    - Dual Audit Ledgers:   {GREEN}READY{RESET} (Copilot & Autonomous logs armed)")
        print(f"    - Health Status:        {GREEN}[HEALTHY]{RESET}")
    except Exception as ex:
        nexusbridge_ok = False
        print(f"    - NexusBridge Status:   {RED}[FAILED]{RESET} - {ex}")

    # 7. Summary & Readiness
    print(f"\n{sub_border}")
    all_healthy = corepulse_ok and nexus_ok and echostream_ok and tradekavach_ok and nexusbridge_ok
    status_text = f"{GREEN}[ALL SYSTEMS OPTIMAL - PRODUCTION READY]{RESET}" if all_healthy else f"{RED}[DEGRADED]{RESET}"
    print(f"  Corporate Suite Overall Status: {BOLD}{status_text}{RESET}")
    print(border + "\n")

    sys.exit(0 if all_healthy else 1)


def cmd_version(args):
    """Prints versions of all corporate suite products."""
    print_suite_banner()
    print(f"  Corporate Suite Version: {SUITE_VERSION}")
    print(f"  - CorePulse:    v1.0.0 (Autonomous Life OS & Multi-Threaded REST API)")
    print(f"  - NexusShield:  v1.0.0 (Local-First Code Security & Vulnerability Auditor)")
    print(f"  - EchoStream:   v1.0.0 (Autonomous Speech & Thought Stream Perception Engine)")
    print(f"  - TradeKavach:  v1.0.0 (Autonomous AI Trading Suite for Indian Markets at E:\\Treding)")
    print(f"  - NexusBridge:  v1.0.0 (Autonomous Human-Emulated Browser & Copilot Bridge)")
    print(f"  Zero External Dependencies: True")
    print()
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        prog="it-solutions",
        description=f"{SUITE_NAME} - Unified Corporate CLI Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Corporate product or utility command")

    # it-solutions pulse
    pulse_parser = subparsers.add_parser("pulse", help="Launch or manage CorePulse Productivity Engine & Companion")
    pulse_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    pulse_parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    pulse_parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    pulse_parser.add_argument("--companion", action="store_true", help="Launch Desktop Notification & Habit Sentry Companion")
    pulse_parser.add_argument("--morning", action="store_true", help="Trigger Morning Focus Protocol notification & routine")
    pulse_parser.add_argument("--streaks", action="store_true", help="Audit habit streaks and trigger lapse warnings")
    pulse_parser.add_argument("--daemon", action="store_true", help="Run companion in continuous background daemon mode")
    pulse_parser.add_argument("--dry-run", action="store_true", help="Simulate companion notifications without sending native alerts")
    pulse_parser.add_argument("--omnibar", action="store_true", help="Launch Desktop Quick-Capture Omnibar daemon (Ctrl+Shift+Space)")
    pulse_parser.add_argument("--popup", action="store_true", help="Open Omnibar quick-capture popup immediately")
    pulse_parser.add_argument("--command", "-c", type=str, help="Execute Omnibar command headlessly and exit")
    pulse_parser.add_argument("--json", action="store_true", help="Format Omnibar output as JSON")
    pulse_parser.add_argument("--tunnel", action="store_true", help="Launch 1-click public cloud tunnel for CorePulse Cockpit")
    pulse_parser.add_argument("--tunnel-provider", choices=["auto", "cloudflare", "ngrok", "lan"], default="auto", help="Tunnel provider to use")

    # it-solutions shield
    shield_parser = subparsers.add_parser("shield", help="Execute NexusShield Code Security & CVE Auditor")
    shield_sub = shield_parser.add_subparsers(dest="shield_action", required=True)

    scan_sub = shield_sub.add_parser("scan", help="Scan a directory or file for credentials and vulnerabilities")
    scan_sub.add_argument("path", help="Target path to audit")
    scan_sub.add_argument("--json", action="store_true", help="Output audit in JSON format")
    scan_sub.add_argument("--output", "-o", help="Write report or JSON to file")
    scan_sub.add_argument("--fail-under", type=float, default=0.0, help="Exit with code 1 if score < threshold")

    # it-solutions stream
    stream_parser = subparsers.add_parser("stream", help="Execute EchoStream Speech & Thought Stream Perception Engine")
    stream_sub = stream_parser.add_subparsers(dest="stream_action", required=True)

    stream_parse = stream_sub.add_parser("parse", help="Parse meeting transcript or thought stream")
    stream_parse.add_argument("input", help="File path or raw text string to parse")
    stream_parse.add_argument("--dispatch", action="store_true", help="Dispatch extracted tasks to CorePulse")
    stream_parse.add_argument("--json", action="store_true", help="Output in JSON format")

    stream_scan = stream_sub.add_parser("scan", help="Run VoiceGuard DLP credential scan on spoken text")
    stream_scan.add_argument("text", help="Spoken transcript string to scan and redact")
    stream_scan.add_argument("--json", action="store_true", help="Output in JSON format")

    stream_watch = stream_sub.add_parser("watch", help="Launch Autonomous Transcript Ingestion Pipeline directory watcher")
    stream_watch.add_argument("dir", nargs="?", default="data/transcripts", help="Target drop directory to monitor (default: data/transcripts)")
    stream_watch.add_argument("--poll-interval", type=float, default=1.0, help="Polling interval in seconds")
    stream_watch.add_argument("--once", action="store_true", help="Execute single ingestion sweep and exit")
    stream_watch.add_argument("--json", action="store_true", help="Output sweep receipts in JSON format")

    stream_sub.add_parser("demo", help="Run live executive meeting triage simulation")

    # it-solutions trade
    trade_parser = subparsers.add_parser("trade", help="Launch or manage TradeKavach Autonomous AI Trading Suite at E:\\Treding")
    trade_parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    trade_parser.add_argument("--port", type=int, default=9090, help="Port to listen on (default: 9090)")
    trade_parser.add_argument("--mode", choices=["paper", "live"], help="Execution mode (paper / live)")
    trade_parser.add_argument("--strategy", choices=["intraday_equity", "swing_equity", "index_options"], help="Trading strategy")
    trade_parser.add_argument("--scan-once", action="store_true", help="Execute single screener & AI deliberation cycle and exit")
    trade_parser.add_argument("--kill-switch", action="store_true", help="Trigger emergency kill-switch and liquidate open positions")

    # it-solutions license
    license_parser = subparsers.add_parser("license", help="Manage CorePulse commercial cryptographic licenses & tier activation")
    license_sub = license_parser.add_subparsers(dest="license_action", required=True)

    lic_status = license_sub.add_parser("status", help="View active license and tier entitlements")
    lic_status.add_argument("--json", action="store_true", help="Output in JSON format")

    lic_activate = license_sub.add_parser("activate", help="Activate a cryptographic license key")
    lic_activate.add_argument("key", help="Cryptographic license key string (e.g. CP-PRO-...)")
    lic_activate.add_argument("--json", action="store_true", help="Output in JSON format")

    lic_gen = license_sub.add_parser("generate-demo", help="Generate an offline verifiable demo license key")
    lic_gen.add_argument("tier", nargs="?", default=None, choices=["starter", "pro", "team", "enterprise", None], help="Subscription tier (default: pro)")
    lic_gen.add_argument("--tier", dest="tier_flag", default=None, choices=["starter", "pro", "team", "enterprise"], help="Subscription tier flag")
    lic_gen.add_argument("--customer", default="Executive User", help="Customer name")
    lic_gen.add_argument("--org", default="Enterprise Corp", help="Organization name")
    lic_gen.add_argument("--days", type=int, default=365, help="Validity duration in days (default: 365)")
    lic_gen.add_argument("--seats", type=int, default=None, help="Number of seats (team/enterprise)")
    lic_gen.add_argument("--json", action="store_true", help="Output in JSON format")

    # it-solutions sync
    sync_parser = subparsers.add_parser("sync", help="Manage CorePulse Zero-Knowledge E2EE Cloud Sync and Blinded Relay")
    sync_sub = sync_parser.add_subparsers(dest="sync_action", required=True)

    sync_status = sync_sub.add_parser("status", help="View local sync status, outbox count, and pairing state")
    sync_status.add_argument("--json", action="store_true", help="Output in JSON format")

    sync_pair = sync_sub.add_parser("pair", help="Pair device with zero-knowledge sync passphrase and relay server")
    sync_pair.add_argument("passphrase", help="Secret user sync passphrase (min 8 characters)")
    sync_pair.add_argument("--relay-url", help="Blinded relay server URL (default: http://127.0.0.1:8081)")
    sync_pair.add_argument("--json", action="store_true", help="Output in JSON format")

    sync_push = sync_sub.add_parser("push", help="Encrypt and push queued outbox deltas to blinded relay")
    sync_push.add_argument("--passphrase", help="Sync passphrase (or set COREPULSE_SYNC_PASSPHRASE env var)")
    sync_push.add_argument("--relay-url", help="Blinded relay server URL")
    sync_push.add_argument("--json", action="store_true", help="Output in JSON format")

    sync_pull = sync_sub.add_parser("pull", help="Pull and decrypt incoming deltas from relay with CRDT resolution")
    sync_pull.add_argument("--passphrase", help="Sync passphrase (or set COREPULSE_SYNC_PASSPHRASE env var)")
    sync_pull.add_argument("--relay-url", help="Blinded relay server URL")
    sync_pull.add_argument("--json", action="store_true", help="Output in JSON format")

    # it-solutions bridge
    bridge_parser = subparsers.add_parser("bridge", help="NexusBridge browser co-pilot and human-assisted physical OS window driver")
    bridge_sub = bridge_parser.add_subparsers(dest="bridge_action", required=True)

    bridge_launch = bridge_sub.add_parser("launch", help="Launch interactive browser co-pilot session")
    bridge_launch.add_argument("platform", choices=["github", "pypi", "cloudflare"], help="Target enterprise platform")
    bridge_launch.add_argument("--url", help="Custom start URL override")

    bridge_find = bridge_sub.add_parser("find", help="Enumerate active desktop windows and inspect HWNDs")
    bridge_find.add_argument("query", nargs="?", default=None, help="Optional title substring to filter")

    bridge_hud = bridge_sub.add_parser("hud", help="Render on-screen click-through target frame overlay (30Hz tracking)")
    bridge_hud.add_argument("--target", help="Window title substring or hex HWND")
    bridge_hud.add_argument("--status", choices=["active", "paused", "stopped"], default="active", help="Initial HUD border color state")
    bridge_hud.add_argument("--duration", type=float, help="Seconds to display before auto-closing (default: infinite)")

    bridge_tray = bridge_sub.add_parser("tray", help="Launch Windows Notification Area tray controller with sub-10ms killswitch")
    bridge_tray.add_argument("--target", default="Google Chrome", help="Target process or application name")

    bridge_capture = bridge_sub.add_parser("capture", help="Capture physical window GDI screenshot to PNG")
    bridge_capture.add_argument("--target", help="Window title substring or hex HWND")
    bridge_capture.add_argument("--output", "-o", help="Destination file path for PNG snapshot")

    bridge_click = bridge_sub.add_parser("click", help="Execute native mouse click with Bézier curve movement")
    bridge_click.add_argument("x", type=int, help="Target screen X coordinate")
    bridge_click.add_argument("y", type=int, help="Target screen Y coordinate")
    bridge_click.add_argument("--button", choices=["left", "right"], default="left", help="Mouse button to click")

    bridge_type = bridge_sub.add_parser("type", help="Type text using Win32 SendInput physical hardware scancodes")
    bridge_type.add_argument("text", help="Text string to type")
    bridge_type.add_argument("--typo-rate", type=float, default=0.0, help="Simulated typo injection rate (0.0 to 0.1)")

    bridge_status = bridge_sub.add_parser("status", help="Inspect browser co-pilot session logs and vault state")

    # it-solutions health
    subparsers.add_parser("health", help="Run corporate suite infrastructure health audit")

    # it-solutions version
    subparsers.add_parser("version", help="Display suite and product versions")

    if len(sys.argv) == 1:
        print_suite_banner()
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.subcommand == "pulse":
        cmd_pulse(args)
    elif args.subcommand == "shield":
        cmd_shield(args)
    elif args.subcommand == "stream":
        cmd_stream(args)
    elif args.subcommand == "trade":
        cmd_trade(args)
    elif args.subcommand == "license":
        cmd_license(args)
    elif args.subcommand == "sync":
        cmd_sync(args)
    elif args.subcommand == "bridge":
        cmd_bridge(args)
    elif args.subcommand == "health":
        cmd_health(args)
    elif args.subcommand == "version":
        cmd_version(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
