"""
CorePulse v1.0 - Desktop Notification & Habituation Companion Engine
Zero-dependency local companion script for morning pulse triggers and habit streak lapse sentry.
Compatible with Windows, macOS (Darwin), Linux, and headless fallback environments.
"""

import argparse
import base64
import json
import logging
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

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

logger = logging.getLogger("corepulse.companion")

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


class NotificationResult:
    """Encapsulates outcome of a notification dispatch attempt."""

    def __init__(
        self,
        success: bool,
        channel: str,
        title: str,
        message: str,
        platform_name: str,
        timestamp: Optional[str] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.channel = channel
        self.title = title
        self.message = message
        self.platform_name = platform_name
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "channel": self.channel,
            "title": self.title,
            "message": self.message,
            "platform": self.platform_name,
            "timestamp": self.timestamp,
            "error": self.error
        }

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"<NotificationResult [{status}] channel={self.channel} title='{self.title}'>"


class DesktopNotifier:
    """
    Zero-dependency cross-platform desktop notification dispatcher.
    Uses native OS utilities without third-party libraries:
      - Windows: PowerShell WinRT ToastNotification / Windows.Forms NotifyIcon
      - macOS (Darwin): osascript display notification
      - Linux: notify-send
      - Fallback: Formatted CLI & structured logging
    """

    def __init__(self, dry_run: bool = False):
        self.system = platform.system()
        self.dry_run = dry_run or os.getenv("COREPULSE_MOCK_NOTIFICATIONS", "0") in ("1", "true", "yes")

    def send(
        self,
        title: str,
        message: str,
        urgency: str = "normal",
        sound: bool = True
    ) -> NotificationResult:
        """
        Dispatches desktop notification according to host OS.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        if self.dry_run:
            logger.info("[DRY RUN NOTIFICATION] %s: %s", title, message)
            return NotificationResult(
                success=True,
                channel="dry_run",
                title=title,
                message=message,
                platform_name=self.system,
                timestamp=timestamp
            )

        if self.system == "Windows":
            return self._send_windows(title, message, sound, timestamp)
        elif self.system == "Darwin":
            return self._send_darwin(title, message, sound, timestamp)
        elif self.system in ("Linux", "FreeBSD", "OpenBSD"):
            return self._send_linux(title, message, urgency, timestamp)
        else:
            return self._send_fallback(title, message, timestamp)

    def _send_windows(self, title: str, message: str, sound: bool, timestamp: str) -> NotificationResult:
        """Dispatches notification on Windows using PowerShell WinRT or BalloonTip."""
        # Sanitize single quotes and xml chars
        safe_title = title.replace("'", "''").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe_msg = message.replace("'", "''").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        ps_script = f"""
$ErrorActionPreference = 'Stop'
try {{
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
    $xml = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>{safe_title}</text>
            <text>{safe_msg}</text>
        </binding>
    </visual>
</toast>
"@
    $toastXml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $toastXml.LoadXml($xml)
    $toast = [Windows.UI.Notifications.ToastNotification]::new($toastXml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("CorePulse").Show($toast)
}} catch {{
    Add-Type -AssemblyName System.Windows.Forms
    $notify = New-Object System.Windows.Forms.NotifyIcon
    $notify.Icon = [System.Drawing.SystemIcons]::Information
    $notify.Visible = $True
    $notify.ShowBalloonTip(4000, '{safe_title}', '{safe_msg}', [System.Windows.Forms.ToolTipIcon]::Info)
    Start-Sleep -Milliseconds 150
    $notify.Dispose()
}}
"""
        try:
            encoded_cmd = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_cmd],
                capture_output=True,
                text=True,
                timeout=4
            )
            if proc.returncode == 0:
                return NotificationResult(
                    success=True,
                    channel="powershell_toast",
                    title=title,
                    message=message,
                    platform_name="Windows",
                    timestamp=timestamp
                )
            else:
                logger.warning("PowerShell notification returned code %d: %s", proc.returncode, proc.stderr)
                return self._send_fallback(title, message, timestamp, error=proc.stderr.strip())
        except Exception as ex:
            logger.warning("Windows notification error: %s. Reverting to console fallback.", ex)
            return self._send_fallback(title, message, timestamp, error=str(ex))

    def _send_darwin(self, title: str, message: str, sound: bool, timestamp: str) -> NotificationResult:
        """Dispatches notification on macOS using osascript."""
        safe_title = title.replace('"', '\\"')
        safe_msg = message.replace('"', '\\"')
        sound_clause = ' sound name "Subtle"' if sound else ""
        script = f'display notification "{safe_msg}" with title "{safe_title}"{sound_clause}'

        try:
            proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=4)
            if proc.returncode == 0:
                return NotificationResult(
                    success=True,
                    channel="osascript",
                    title=title,
                    message=message,
                    platform_name="Darwin",
                    timestamp=timestamp
                )
            else:
                return self._send_fallback(title, message, timestamp, error=proc.stderr.strip())
        except Exception as ex:
            return self._send_fallback(title, message, timestamp, error=str(ex))

    def _send_linux(self, title: str, message: str, urgency: str, timestamp: str) -> NotificationResult:
        """Dispatches notification on Linux using notify-send."""
        try:
            proc = subprocess.run(
                ["notify-send", "-a", "CorePulse", "-u", urgency, title, message],
                capture_output=True,
                text=True,
                timeout=4
            )
            if proc.returncode == 0:
                return NotificationResult(
                    success=True,
                    channel="notify-send",
                    title=title,
                    message=message,
                    platform_name="Linux",
                    timestamp=timestamp
                )
            else:
                return self._send_fallback(title, message, timestamp, error=proc.stderr.strip())
        except Exception as ex:
            return self._send_fallback(title, message, timestamp, error=str(ex))

    def _send_fallback(
        self,
        title: str,
        message: str,
        timestamp: str,
        error: Optional[str] = None
    ) -> NotificationResult:
        """Fallback: Logs notification formatted clearly to console."""
        print(f"\n{CYAN}{BOLD}🔔 [COREPULSE NOTIFICATION]{RESET} {BOLD}{title}{RESET}")
        print(f"   {message}\n")
        return NotificationResult(
            success=True,
            channel="console_fallback",
            title=title,
            message=message,
            platform_name=self.system,
            timestamp=timestamp,
            error=error
        )


class HabitStreakSentry:
    """
    Monitors daily habit consistency and warns when active streaks are at risk of lapsing.
    """

    def __init__(self, db_instance=None, notifier: Optional[DesktopNotifier] = None):
        if db_instance is None:
            # Prefer active JSON database instance
            from corepulse.database import db
            self.db = db
        else:
            self.db = db_instance

        self.notifier = notifier or DesktopNotifier()

    def get_lapsing_habits(self) -> List[Dict[str, Any]]:
        """
        Retrieves all active daily habits that are uncompleted today.
        Evaluates risk based on streak length.
        """
        all_items = self.db.get_tasks()
        lapsing = []

        for item in all_items:
            if item.get("type") == "habit" and not item.get("completed", False):
                streak = int(item.get("streak_days", 0))
                # Habits with active streaks are at immediate lapse risk
                if streak >= 14:
                    urgency = "critical"
                    badge = "🔥 CRITICAL"
                elif streak >= 7:
                    urgency = "high"
                    badge = "⚡ HIGH"
                elif streak >= 3:
                    urgency = "normal"
                    badge = "⚠️ AT RISK"
                else:
                    urgency = "low"
                    badge = "📌 PENDING"

                lapsing.append({
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "streak_days": streak,
                    "category": item.get("category", "General"),
                    "urgency": urgency,
                    "badge": badge,
                    "estimated_minutes": item.get("estimated_minutes", 15)
                })

        # Sort with highest streak at risk first
        lapsing.sort(key=lambda x: x["streak_days"], reverse=True)
        return lapsing

    def audit_and_notify(self) -> List[Dict[str, Any]]:
        """
        Audits habit streaks and fires notifications for uncompleted habits at risk.
        Returns list of dispatch summaries.
        """
        lapsing = self.get_lapsing_habits()
        dispatched = []

        if not lapsing:
            logger.info("HabitStreakSentry: All active habit routines are completed for today.")
            return []

        # Find top priority habit to notify
        top_habit = lapsing[0]
        streak = top_habit["streak_days"]
        title_text = top_habit["title"]

        if streak >= 1:
            notif_title = f"Habit Streak Alert: {top_habit['badge']}"
            notif_msg = f"Your {streak}-day streak on '{title_text}' will lapse tonight! Complete your {top_habit['estimated_minutes']}m routine now to protect your record."
        else:
            notif_title = "CorePulse Daily Routine Check"
            notif_msg = f"Daily habit pending: '{title_text}' ({top_habit['estimated_minutes']}m). Build your streak today!"

        res = self.notifier.send(
            title=notif_title,
            message=notif_msg,
            urgency=top_habit["urgency"]
        )

        dispatched.append({
            "habit": top_habit,
            "notification": res.to_dict(),
            "total_pending_habits": len(lapsing)
        })

        return dispatched


class MorningPulseTrigger:
    """
    Executes morning focus priming and orchestrates the autonomous Morning Focus Protocol.
    """

    def __init__(self, db_instance=None, notifier: Optional[DesktopNotifier] = None):
        if db_instance is None:
            from corepulse.database import db
            self.db = db
        else:
            self.db = db_instance

        self.notifier = notifier or DesktopNotifier()

    def trigger(self, run_workflow: bool = True) -> Dict[str, Any]:
        """
        Fires morning pulse routine, optionally executes morning focus workflow,
        and broadcasts notification.
        """
        now = datetime.now()
        greeting = "Good morning, Executive" if now.hour < 12 else "Good day, Executive"

        workflow_result = None
        if run_workflow:
            try:
                from corepulse.workflows import WorkflowEngine
                workflow_result = WorkflowEngine.run_workflow("morning_focus_init")
                time_saved = workflow_result.get("time_saved_minutes", 25)
                summary_msg = f"{greeting}! Morning Focus Protocol engaged ({time_saved}m saved). High-priority deliverables primed."
            except Exception as ex:
                logger.warning("Could not run workflow in-process: %s", ex)
                summary_msg = f"{greeting}! Ready to dominate the day? Review your strategic focus in CorePulse."
        else:
            summary_msg = f"{greeting}! Review your strategic roadmap and habit streaks in CorePulse."

        notif_res = self.notifier.send(
            title="⚡ CorePulse Morning Focus Protocol",
            message=summary_msg,
            urgency="high"
        )

        return {
            "status": "success",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "workflow_executed": run_workflow,
            "workflow_result": workflow_result,
            "notification": notif_res.to_dict()
        }


class CompanionDaemon:
    """
    Continuous habituation companion runner.
    Checks schedules for morning pulse and monitors habit streak lapse windows.
    """

    def __init__(
        self,
        check_interval: int = 60,
        morning_hour: int = 8,
        evening_hour: int = 18,
        dry_run: bool = False
    ):
        self.check_interval = check_interval
        self.morning_hour = morning_hour
        self.evening_hour = evening_hour
        self.notifier = DesktopNotifier(dry_run=dry_run)
        self.sentry = HabitStreakSentry(notifier=self.notifier)
        self.morning_trigger = MorningPulseTrigger(notifier=self.notifier)
        self.running = False

        self._last_morning_date: Optional[str] = None
        self._last_evening_date: Optional[str] = None

    def tick_once(self) -> Dict[str, Any]:
        """Performs a single evaluation pass."""
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        actions_taken = []

        # Morning pulse check
        if now.hour >= self.morning_hour and self._last_morning_date != today_str:
            res = self.morning_trigger.trigger(run_workflow=True)
            self._last_morning_date = today_str
            actions_taken.append({"action": "morning_pulse", "data": res})

        # Evening habit streak lapse check
        if now.hour >= self.evening_hour and self._last_evening_date != today_str:
            alerts = self.sentry.audit_and_notify()
            self._last_evening_date = today_str
            actions_taken.append({"action": "habit_streak_audit", "data": alerts})

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actions_taken": actions_taken,
            "lapsing_habits": self.sentry.get_lapsing_habits()
        }

    def run_daemon(self):
        """Runs the continuous companion daemon until interrupted."""
        self.running = True
        print(f"{CYAN}{BOLD}⚡ CorePulse Habituation Companion Daemon started.{RESET}")
        print(f"   Morning Focus: {self.morning_hour}:00 | Evening Sentry: {self.evening_hour}:00")
        print(f"   Check Interval: {self.check_interval}s | Press Ctrl+C to stop.\n")

        try:
            while self.running:
                result = self.tick_once()
                if result["actions_taken"]:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Executed scheduled action: {len(result['actions_taken'])} tasks dispatched.")
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print(f"\n{YELLOW}CorePulse Companion Daemon stopped gracefully.{RESET}")
            self.running = False


def print_banner():
    banner = fr"""{CYAN}{BOLD}
   ____                     ____        _            
  / ___|___  _ __ ___      |  _ \ _   _| |___  ___   
 | |   / _ \| '__/ _ \_____| |_) | | | | / __|/ _ \  
 | |__| (_) | | |  __/_____|  __/| |_| | \__ \  __/  
  \____\___/|_|  \___|     |_|    \__,_|_|___/\___|  
{RESET}{DIM}    Desktop Notification & Habit Streak Sentry Companion v1.0{RESET}
"""
    print(banner)


def main():
    parser = argparse.ArgumentParser(
        description="CorePulse Desktop Notification & Habit Streak Companion",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--morning", action="store_true", help="Trigger Morning Focus Protocol notification & workflow")
    parser.add_argument("--streaks", action="store_true", help="Audit habit streaks and notify if any are at risk of lapsing")
    parser.add_argument("--notify", nargs=2, metavar=("TITLE", "MESSAGE"), help="Dispatch test notification: --notify <title> <message>")
    parser.add_argument("--daemon", action="store_true", help="Run in continuous background daemon mode")
    parser.add_argument("--interval", type=int, default=60, help="Daemon poll interval in seconds (default: 60)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate notifications without sending native OS alerts")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    if not any([args.morning, args.streaks, args.notify, args.daemon]):
        print_banner()
        # Default behavior: run status audit
        sentry = HabitStreakSentry(notifier=DesktopNotifier(dry_run=args.dry_run))
        lapsing = sentry.get_lapsing_habits()
        print(f"{BOLD}[+] Habit Consistency & Streak Status:{RESET}")
        if not lapsing:
            print(f"    {GREEN}✓ All habit routines are completed for today! Streaks secure.{RESET}")
        else:
            for h in lapsing:
                badge_col = RED if "CRITICAL" in h["badge"] else (YELLOW if "HIGH" in h["badge"] else CYAN)
                print(f"    - {badge_col}[{h['badge']}]{RESET} {BOLD}{h['title']}{RESET} ({h['streak_days']}-day streak at risk!)")
        print("\nRun with --morning, --streaks, --daemon, or --notify for active triggers.\n")
        sys.exit(0)

    notifier = DesktopNotifier(dry_run=args.dry_run)

    if args.notify:
        title, msg = args.notify
        res = notifier.send(title, msg)
        if args.json:
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(f"{GREEN}[OK]{RESET} Dispatched via {res.channel}: '{res.title}'")
        sys.exit(0 if res.success else 1)

    if args.morning:
        trigger = MorningPulseTrigger(notifier=notifier)
        res = trigger.trigger(run_workflow=True)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"{GREEN}[OK]{RESET} Morning Focus Protocol Triggered. Time saved: {res.get('workflow_result', {}).get('time_saved_minutes', 25)}m.")
        sys.exit(0)

    if args.streaks:
        sentry = HabitStreakSentry(notifier=notifier)
        alerts = sentry.audit_and_notify()
        if args.json:
            print(json.dumps(alerts, indent=2))
        else:
            if alerts:
                print(f"{GREEN}[OK]{RESET} Dispatched {len(alerts)} habit lapse warnings.")
            else:
                print(f"{GREEN}[OK]{RESET} All habit routines completed today. Zero lapse warnings needed.")
        sys.exit(0)

    if args.daemon:
        daemon = CompanionDaemon(check_interval=args.interval, dry_run=args.dry_run)
        daemon.run_daemon()


if __name__ == "__main__":
    main()
