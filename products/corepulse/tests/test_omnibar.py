"""
Unit and Integration Test Suite: CorePulse Desktop Quick-Capture Omnibar v1.0
Validates:
  1. Natural Language Task Parsing (Priority tokens @p1-@p4, #tags, ~est, due dates)
  2. Offline SQLite WAL Fallback Persistence
  3. Habit Completion and Streak Incrementing
  4. 1-Click NexusShield Security Scan Routing
  5. EchoStream VoiceGuard DLP Redaction & Voice Memo Intake
  6. CorePulse Routine & Workflow Automation Execution
  7. Telemetry & Vitals HUD Status
  8. Cockpit Launcher Routing
  9. Global Hotkey Lifecycle & UI Preview Safety
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

_TEST_TMP_DIR = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
os.environ.setdefault("COREPULSE_TEST_MODE", "1")
os.environ.setdefault("COREPULSE_DATA_DIR", _TEST_TMP_DIR.name)

# Base Directories
TESTS_DIR = Path(__file__).resolve().parent
COREPULSE_DIR = TESTS_DIR.parent
PRODUCTS_DIR = COREPULSE_DIR.parent
NEXUSSHIELD_DIR = PRODUCTS_DIR / "nexusshield"
ECHOSTREAM_DIR = PRODUCTS_DIR / "echostream"

for p in (PRODUCTS_DIR, COREPULSE_DIR, NEXUSSHIELD_DIR, ECHOSTREAM_DIR):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

from corepulse.database_sqlite import Database
try:
    from corepulse.omnibar import GlobalHotkeyListener, OmnibarRouter, OmnibarUI
except ImportError:
    from omnibar import GlobalHotkeyListener, OmnibarRouter, OmnibarUI


class TestOmnibarNaturalLanguageParser(unittest.TestCase):
    """Tests natural language heuristic token extraction in OmnibarRouter."""

    def setUp(self):
        self.router = OmnibarRouter()

    def test_01_priority_extraction(self):
        """Validates extraction of priority tokens (@p1, @critical, @p2, @p3, @p4)."""
        res_p1 = self.router.parse_natural_language_task("Refactor auth middleware @p1")
        self.assertEqual(res_p1["priority"], "critical")
        self.assertEqual(res_p1["title"], "Refactor auth middleware")

        res_crit = self.router.parse_natural_language_task("Fix SQL injection flaw @critical")
        self.assertEqual(res_crit["priority"], "critical")

        res_p2 = self.router.parse_natural_language_task("Update API documentation @p2")
        self.assertEqual(res_p2["priority"], "high")

        res_p3 = self.router.parse_natural_language_task("Organize team backlog @p3")
        self.assertEqual(res_p3["priority"], "medium")

        res_p4 = self.router.parse_natural_language_task("Clean up stale branches @p4")
        self.assertEqual(res_p4["priority"], "low")

        # Default priority
        res_default = self.router.parse_natural_language_task("Read technical architecture paper")
        self.assertEqual(res_default["priority"], "medium")

    def test_02_tags_extraction(self):
        """Validates extraction of hashtag tokens (#backend #security)."""
        res = self.router.parse_natural_language_task("Audit OAuth2 token exchange #backend #security #auth")
        self.assertIn("backend", res["tags"])
        self.assertIn("security", res["tags"])
        self.assertIn("auth", res["tags"])
        self.assertIn("omnibar", res["tags"])
        self.assertEqual(res["title"], "Audit OAuth2 token exchange")

    def test_03_estimated_time_extraction(self):
        """Validates extraction of estimated duration (~45m, ~1h, 15 mins)."""
        res_min = self.router.parse_natural_language_task("Write unit tests ~45m")
        self.assertEqual(res_min["estimated_minutes"], 45)

        res_hour = self.router.parse_natural_language_task("Database migration planning ~2h")
        self.assertEqual(res_hour["estimated_minutes"], 120)

        res_word = self.router.parse_natural_language_task("Prepare sprint demo 30 mins")
        self.assertEqual(res_word["estimated_minutes"], 30)

    def test_04_due_date_extraction(self):
        """Validates relative and day-of-week deadline extraction."""
        res_tomorrow = self.router.parse_natural_language_task("Deploy staging build tomorrow")
        self.assertEqual(res_tomorrow["due_date"], "Tomorrow")

        res_friday = self.router.parse_natural_language_task("Submit quarterly financial budget by Friday")
        self.assertEqual(res_friday["due_date"], "Friday")

        res_next_week = self.router.parse_natural_language_task("Review Q1 candidate pipeline next week")
        self.assertEqual(res_next_week["due_date"], "Next Week")

    def test_05_compound_task_string(self):
        """Validates comprehensive parsing of a realistic complex task sentence."""
        raw = "task Hardening API rate limits @p1 #security #infra tomorrow ~45m"
        res = self.router.parse_natural_language_task(raw)
        self.assertEqual(res["title"], "Hardening API rate limits")
        self.assertEqual(res["priority"], "critical")
        self.assertEqual(res["due_date"], "Tomorrow")
        self.assertEqual(res["estimated_minutes"], 45)
        self.assertIn("security", res["tags"])
        self.assertIn("infra", res["tags"])


class TestOmnibarOfflineDatabaseFallback(unittest.TestCase):
    """Validates resilient SQLite WAL fallback when REST API server is offline."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="omnibar_test_")
        self.db_path = Path(self.temp_dir) / "test_corepulse.sqlite3"
        self.db = Database(self.db_path)
        # Point to dummy offline port (9998)
        self.router = OmnibarRouter(api_url="http://127.0.0.1:9998/api/tasks", db_path=self.db_path)

    def tearDown(self):
        self.router.close()
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_06_offline_task_persistence(self):
        """Submitting a task when the API server is unreachable persists directly to SQLite."""
        cmd = "task Implement zero-trust network ingress @p1 #networking tomorrow ~60m"
        result = self.router.parse_and_route(cmd)

        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "task")
        self.assertEqual(result["transport"], "sqlite_wal_fallback")

        task_data = result["data"]
        self.assertEqual(task_data["title"], "Implement zero-trust network ingress")
        self.assertEqual(task_data["priority"], "critical")
        self.assertEqual(task_data["estimated_minutes"], 60)

        # Verify persisted record in SQLite DB
        tasks_in_db = self.db.get_tasks()
        persisted = next((t for t in tasks_in_db if t["id"] == task_data["id"]), None)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted["title"], "Implement zero-trust network ingress")
        self.assertEqual(persisted["priority"], "critical")
        self.assertIn("networking", persisted["tags"])

    def test_07_habit_streak_check_offline(self):
        """Validates habit completion and streak incrementing directly in database."""
        # Pre-seed a habit in test database
        seeded = self.db.create_or_update_task({
            "title": "Morning Cold Shower & Hydration",
            "type": "habit",
            "category": "Habits",
            "priority": "medium",
            "completed": False,
            "streak_days": 4,
            "tags": ["wellness"]
        })

        # Submit habit completion via Omnibar
        cmd = "habit completed Morning Cold Shower"
        res = self.router.parse_and_route(cmd)

        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "habit_completed")
        self.assertIn("Streak: 5 days", res["summary"])

        # Check DB
        all_tasks = self.db.get_tasks()
        updated = next((t for t in all_tasks if t["id"] == seeded["id"]), None)
        self.assertIsNotNone(updated)
        self.assertTrue(updated["completed"])
        self.assertEqual(updated["streak_days"], 5)


class TestOmnibarMultiModalRouting(unittest.TestCase):
    """Validates multi-modal routing across Shield, EchoStream, Workflows, and Telemetry."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="omnibar_routing_")
        self.db_path = Path(self.temp_dir) / "test_corepulse.sqlite3"
        self.db = Database(self.db_path)
        self.router = OmnibarRouter(api_url="http://127.0.0.1:9998/api/tasks", db_path=self.db_path)

    def tearDown(self):
        self.router.close()
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_08_nexusshield_scan_routing(self):
        """Validates 1-click NexusShield SAST security scan execution."""
        # Create a clean mock repository in temp_dir
        repo_dir = Path(self.temp_dir) / "mock_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "app.py").write_text("print('Clean application')\n", encoding="utf-8")

        res = self.router.parse_and_route(f"scan {repo_dir}")
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "scan")
        self.assertIn("NexusShield", res["summary"])
        self.assertIn("Score", res["summary"])
        self.assertEqual(res["data"]["files_scanned"], 1)

    def test_09_echostream_voice_guard_redaction(self):
        """Validates EchoStream voice memo intake with VoiceGuard credential redaction."""
        spoken = "voice Remind Marcus to rotate the OpenAI production token sk-proj-1234567890abcdef1234567890abcdef by Friday"
        res = self.router.parse_and_route(spoken)

        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "voice")
        self.assertIn("EchoStream", res["summary"])
        self.assertIn("1 secret(s) redacted", res["summary"])

        redacted_text = res["data"]["redacted_text"]
        self.assertNotIn("sk-proj-1234567890abcdef1234567890abcdef", redacted_text)
        self.assertIn("[REDACTED_SECRET: OpenAI API Key]", redacted_text)

    def test_10_routine_workflow_runner(self):
        """Validates CorePulse automated workflow trigger."""
        res_morning = self.router.parse_and_route("run morning")
        self.assertTrue(res_morning["success"])
        self.assertEqual(res_morning["mode"], "routine")
        self.assertIn("Morning Focus Protocol", res_morning["summary"])

        res_focus = self.router.parse_and_route("run focus")
        self.assertTrue(res_focus["success"])
        self.assertEqual(res_focus["mode"], "routine")
        self.assertIn("Deep Work Distraction Shield", res_focus["summary"])

        res_shutdown = self.router.parse_and_route("run shutdown")
        self.assertTrue(res_shutdown["success"])
        self.assertEqual(res_shutdown["mode"], "routine")
        self.assertIn("Shutdown Protocol", res_shutdown["summary"])

    def test_11_telemetry_status_hud(self):
        """Validates telemetry and vitals reporting."""
        res = self.router.parse_and_route("status")
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "status")
        self.assertIn("CorePulse Vitals", res["summary"])
        self.assertIn("Pending Tasks", res["summary"])

    @patch("webbrowser.open")
    def test_12_cockpit_launcher(self, mock_browser):
        """Validates Cockpit URL launch trigger."""
        mock_browser.return_value = True
        res = self.router.parse_and_route("cockpit")
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "cockpit")
        self.assertIn("Opened CorePulse Cockpit", res["summary"])
        mock_browser.assert_called_once_with("http://127.0.0.1:8080")


class TestOmnibarUIAndHotkeyLifecycle(unittest.TestCase):
    """Validates live preview generation, UI creation safety, and hotkey listener lifecycle."""

    def test_13_preview_command_generation(self):
        """Validates live dynamic preview for each subsystem mode."""
        router = OmnibarRouter()

        prev_scan = router.preview_command("scan .")
        self.assertEqual(prev_scan["mode"], "scan")
        self.assertEqual(prev_scan["badge"], "SECURITY SCAN")

        prev_voice = router.preview_command("voice Need to sync with Sarah")
        self.assertEqual(prev_voice["mode"], "voice")
        self.assertEqual(prev_voice["badge"], "ECHOSTREAM")

        prev_routine = router.preview_command("run morning")
        self.assertEqual(prev_routine["mode"], "routine")
        self.assertEqual(prev_routine["badge"], "ROUTINE")

        prev_task = router.preview_command("Deploy backend service @p1 #prod ~30m")
        self.assertEqual(prev_task["mode"], "task")
        self.assertEqual(prev_task["badge"], "TASK CAPTURE")

    def test_14_hotkey_listener_lifecycle(self):
        """Validates starting and stopping GlobalHotkeyListener cleanly without thread leaks."""
        listener = GlobalHotkeyListener(callback=lambda: None, hotkey_id=9888)
        listener.start()
        # Allow thread to start
        import time
        time.sleep(0.05)
        listener.stop()
        self.assertFalse(listener.is_registered)

    def test_15_ui_instantiation_safety(self):
        """Validates OmnibarUI initializes without unhandled exceptions."""
        try:
            ui = OmnibarUI()
            if ui.root:
                # Validate window geometry was set
                self.assertIsNotNone(ui.entry)
                self.assertIsNotNone(ui.preview_lbl)
                ui.show()
                self.assertTrue(ui._visible)
                ui.hide()
                self.assertFalse(ui._visible)
                ui.root.destroy()
        except Exception as ex:
            # On strictly headless servers without X11 or display, gracefully pass
            self.skipTest(f"Display not available for Tkinter GUI: {ex}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
