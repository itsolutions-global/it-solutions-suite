"""
CorePulse Companion Test Suite
Validates DesktopNotifier, HabitStreakSentry, MorningPulseTrigger, and CompanionDaemon.
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from companion import (
    CompanionDaemon,
    DesktopNotifier,
    HabitStreakSentry,
    MorningPulseTrigger,
    NotificationResult
)
from corepulse.database import Database


class MockDatabase:
    """Mock database instance for deterministic testing."""

    def __init__(self, tasks=None):
        self.tasks = tasks or []

    def get_tasks(self, item_type=None, completed=None):
        items = list(self.tasks)
        if item_type is not None:
            items = [t for t in items if t.get("type") == item_type]
        if completed is not None:
            items = [t for t in items if t.get("completed") is completed]
        return items


class TestCorePulseCompanion(unittest.TestCase):
    """Automated unit and integration tests for CorePulse companion engine."""

    def setUp(self):
        self.mock_tasks = [
            {
                "id": "habit-001",
                "title": "Morning 45-min Deep Focus Block",
                "type": "habit",
                "completed": True,
                "streak_days": 18,
                "category": "Focus & Flow",
                "estimated_minutes": 45
            },
            {
                "id": "habit-002",
                "title": "Technical Architecture Mastery",
                "type": "habit",
                "completed": False,
                "streak_days": 14,
                "category": "Continuous Mastery",
                "estimated_minutes": 30
            },
            {
                "id": "habit-003",
                "title": "Post-Work Cognitive Shutdown",
                "type": "habit",
                "completed": False,
                "streak_days": 5,
                "category": "Mindfulness",
                "estimated_minutes": 15
            },
            {
                "id": "task-001",
                "title": "Deploy Multi-Agent Telemetry",
                "type": "task",
                "completed": False,
                "streak_days": 0,
                "category": "Engineering",
                "estimated_minutes": 60
            }
        ]
        self.mock_db = MockDatabase(self.mock_tasks)
        self.notifier = DesktopNotifier(dry_run=True)

    def test_01_notification_result_contract(self):
        """Validates NotificationResult serialization and representation."""
        res = NotificationResult(
            success=True,
            channel="test_channel",
            title="Focus Time",
            message="Your streak is active.",
            platform_name="Windows"
        )
        data = res.to_dict()
        self.assertTrue(data["success"])
        self.assertEqual(data["channel"], "test_channel")
        self.assertEqual(data["title"], "Focus Time")
        self.assertEqual(data["message"], "Your streak is active.")
        self.assertEqual(data["platform"], "Windows")
        self.assertIn("timestamp", data)
        self.assertIn("<NotificationResult [SUCCESS]", repr(res))

    def test_02_notifier_dry_run_dispatch(self):
        """Validates DesktopNotifier dry-run mode returns success without OS side-effects."""
        notifier = DesktopNotifier(dry_run=True)
        res = notifier.send("Test Title", "Test Message", urgency="high")
        self.assertTrue(res.success)
        self.assertEqual(res.channel, "dry_run")
        self.assertEqual(res.title, "Test Title")
        self.assertEqual(res.message, "Test Message")

    def test_03_notifier_console_fallback(self):
        """Validates DesktopNotifier console fallback output."""
        notifier = DesktopNotifier(dry_run=False)
        res = notifier._send_fallback("Test Fallback", "Console Output Message", "2026-10-30T00:00:00Z")
        self.assertTrue(res.success)
        self.assertEqual(res.channel, "console_fallback")
        self.assertEqual(res.title, "Test Fallback")

    def test_04_habit_streak_sentry_lapsing_detection(self):
        """Validates HabitStreakSentry identifies uncompleted habits and ranks by streak risk."""
        sentry = HabitStreakSentry(db_instance=self.mock_db, notifier=self.notifier)
        lapsing = sentry.get_lapsing_habits()

        # Should only include uncompleted habits (habit-002 and habit-003)
        self.assertEqual(len(lapsing), 2)
        # habit-002 has streak 14 (critical), habit-003 has streak 5 (normal/at risk)
        self.assertEqual(lapsing[0]["id"], "habit-002")
        self.assertEqual(lapsing[0]["streak_days"], 14)
        self.assertEqual(lapsing[0]["urgency"], "critical")
        self.assertIn("CRITICAL", lapsing[0]["badge"])

        self.assertEqual(lapsing[1]["id"], "habit-003")
        self.assertEqual(lapsing[1]["streak_days"], 5)
        self.assertEqual(lapsing[1]["urgency"], "normal")

    def test_05_habit_streak_sentry_all_completed(self):
        """Validates HabitStreakSentry generates no alerts when all habits are done."""
        completed_tasks = [
            {"id": "h1", "type": "habit", "completed": True, "streak_days": 10, "title": "Done Habit"}
        ]
        db = MockDatabase(completed_tasks)
        sentry = HabitStreakSentry(db_instance=db, notifier=self.notifier)
        lapsing = sentry.get_lapsing_habits()
        self.assertEqual(len(lapsing), 0)

        dispatched = sentry.audit_and_notify()
        self.assertEqual(len(dispatched), 0)

    def test_06_habit_streak_sentry_alert_dispatch(self):
        """Validates HabitStreakSentry dispatches notification for highest streak at risk."""
        sentry = HabitStreakSentry(db_instance=self.mock_db, notifier=self.notifier)
        alerts = sentry.audit_and_notify()

        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert["habit"]["id"], "habit-002")
        self.assertIn("14-day streak", alert["notification"]["message"])
        self.assertEqual(alert["total_pending_habits"], 2)

    def test_07_morning_pulse_trigger_with_workflow(self):
        """Validates MorningPulseTrigger execution with automated workflow."""
        trigger = MorningPulseTrigger(db_instance=self.mock_db, notifier=self.notifier)
        result = trigger.trigger(run_workflow=True)

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["workflow_executed"])
        self.assertIn("notification", result)
        self.assertTrue(result["notification"]["success"])
        if result.get("workflow_result"):
            self.assertEqual(result["workflow_result"]["status"], "success")

    def test_08_morning_pulse_trigger_without_workflow(self):
        """Validates MorningPulseTrigger notification-only mode."""
        trigger = MorningPulseTrigger(db_instance=self.mock_db, notifier=self.notifier)
        result = trigger.trigger(run_workflow=False)

        self.assertEqual(result["status"], "success")
        self.assertFalse(result["workflow_executed"])
        self.assertIsNone(result["workflow_result"])
        self.assertTrue(result["notification"]["success"])

    def test_09_companion_daemon_tick(self):
        """Validates CompanionDaemon scheduled action trigger logic."""
        daemon = CompanionDaemon(
            check_interval=1,
            morning_hour=0,  # Ensure hour condition is met
            evening_hour=0,
            dry_run=True
        )
        daemon.sentry = HabitStreakSentry(db_instance=self.mock_db, notifier=self.notifier)
        daemon.morning_trigger = MorningPulseTrigger(db_instance=self.mock_db, notifier=self.notifier)

        tick_result = daemon.tick_once()
        self.assertIn("timestamp", tick_result)
        self.assertGreaterEqual(len(tick_result["actions_taken"]), 1)

        # Subsequent tick on the same day should not repeat morning or evening action
        second_tick = daemon.tick_once()
        self.assertEqual(len(second_tick["actions_taken"]), 0)

    def test_10_cli_execution_flags(self):
        """Validates CLI invocation with various operational flags."""
        companion_script = BASE_DIR / "companion.py"

        # 1. Test CLI status check (no arguments)
        proc = subprocess.run(
            [sys.executable, str(companion_script), "--dry-run"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Habit Consistency & Streak Status", proc.stdout)

        # 2. Test CLI custom notification
        proc_notify = subprocess.run(
            [sys.executable, str(companion_script), "--notify", "Alert", "Test Message", "--dry-run", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10
        )
        self.assertEqual(proc_notify.returncode, 0)
        notify_data = json.loads(proc_notify.stdout)
        self.assertTrue(notify_data["success"])
        self.assertEqual(notify_data["title"], "Alert")

        # 3. Test CLI streaks check
        proc_streaks = subprocess.run(
            [sys.executable, str(companion_script), "--streaks", "--dry-run", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10
        )
        self.assertEqual(proc_streaks.returncode, 0)
        streaks_data = json.loads(proc_streaks.stdout)
        self.assertIsInstance(streaks_data, list)


if __name__ == "__main__":
    unittest.main()
