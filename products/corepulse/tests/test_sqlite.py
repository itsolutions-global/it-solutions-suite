"""
CorePulse SQLite Enterprise Backend Test Suite
Automated unit and concurrency test suite for database_sqlite.py.
Verifies 100% compliance with the database contract and WAL mode high-throughput concurrency.
"""

import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from corepulse.config import TIER_FEATURE_GATES
from corepulse.database_sqlite import Database

class CorePulseSQLiteTestSuite(unittest.TestCase):
    """Unit and concurrency test suite for SQLite WAL storage backend."""

    def setUp(self):
        """Creates an isolated temporary database for each test."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_corepulse.sqlite3"
        self.db = Database(self.db_path)

    def tearDown(self):
        """Closes connection and cleans up temporary database files."""
        self.db.close()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_wal_mode_enabled(self):
        """Validates that PRAGMA journal_mode is WAL."""
        journal_mode = self.db.get_journal_mode()
        self.assertEqual(journal_mode, "wal", f"Expected journal_mode='wal', got '{journal_mode}'")

        health = self.db.get_health()
        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["journal_mode"], "wal")
        self.assertEqual(health["db_status"], "sqlite-wal-active")
        self.assertGreaterEqual(health["records_tracked"], 6)

    def test_02_seed_data_initialization(self):
        """Validates that initial seed data is loaded correctly on fresh database."""
        tasks = self.db.get_tasks()
        self.assertEqual(len(tasks), 6)

        habits = self.db.get_tasks(item_type="habit")
        regular_tasks = self.db.get_tasks(item_type="task")
        self.assertEqual(len(habits), 3)
        self.assertEqual(len(regular_tasks), 3)

        sub = self.db.get_subscription()
        self.assertEqual(sub["tier"], "pro")
        self.assertIn("features", sub)
        self.assertTrue(sub["features"]["workflow_automation"])

        metrics = self.db.get_metrics()
        self.assertIn("productivity_score", metrics)
        self.assertIn("total_time_saved_hours", metrics)

    def test_03_tasks_filtering_and_sorting(self):
        """Validates filtering by item_type and completion status with priority sorting."""
        # Uncompleted tasks
        pending = self.db.get_tasks(completed=False)
        self.assertTrue(all(not t["completed"] for t in pending))

        # Completed tasks
        completed = self.db.get_tasks(completed=True)
        self.assertTrue(all(t["completed"] for t in completed))

        # Verify sorted ordering: completed at bottom, critical before high/medium
        all_tasks = self.db.get_tasks()
        priority_map = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        # In uncompleted subset, priority should be non-decreasing
        uncompleted = [t for t in all_tasks if not t["completed"]]
        for i in range(len(uncompleted) - 1):
            p1 = priority_map.get(uncompleted[i]["priority"], 2)
            p2 = priority_map.get(uncompleted[i+1]["priority"], 2)
            self.assertLessEqual(p1, p2)

    def test_04_create_and_update_task(self):
        """Validates task creation and subsequent in-place updates."""
        new_data = {
            "title": "Deploy Multi-Region Disaster Recovery",
            "type": "task",
            "category": "Infrastructure",
            "priority": "critical",
            "estimated_minutes": 75,
            "tags": ["dr", "infra", "resilience"]
        }
        created = self.db.create_or_update_task(new_data)
        self.assertIsNotNone(created.get("id"))
        self.assertEqual(created["title"], new_data["title"])
        self.assertEqual(created["priority"], "critical")
        self.assertFalse(created["completed"])
        self.assertEqual(created["tags"], ["dr", "infra", "resilience"])

        # Update existing task
        task_id = created["id"]
        update_data = {
            "id": task_id,
            "title": "Deploy Multi-Region Disaster Recovery (Validated)",
            "priority": "high",
            "tags": ["dr", "infra", "verified"]
        }
        updated = self.db.create_or_update_task(update_data)
        self.assertEqual(updated["id"], task_id)
        self.assertEqual(updated["title"], update_data["title"])
        self.assertEqual(updated["priority"], "high")
        self.assertEqual(updated["tags"], ["dr", "infra", "verified"])

    def test_05_toggle_task_and_habit_streaks(self):
        """Validates toggle completion and habit streak calculations."""
        # Standard task toggle
        tasks = self.db.get_tasks(item_type="task")
        target_task = tasks[0]
        initial_state = target_task["completed"]

        toggled = self.db.toggle_task(target_task["id"])
        self.assertIsNotNone(toggled)
        self.assertEqual(toggled["completed"], not initial_state)

        # Habit streak toggle
        habits = self.db.get_tasks(item_type="habit", completed=False)
        target_habit = habits[0]
        initial_streak = target_habit["streak_days"]

        # Mark done -> streak + 1
        toggled_habit = self.db.toggle_task(target_habit["id"])
        self.assertTrue(toggled_habit["completed"])
        self.assertEqual(toggled_habit["streak_days"], initial_streak + 1)

        # Unmark -> streak reverts
        untoggled_habit = self.db.toggle_task(target_habit["id"])
        self.assertFalse(untoggled_habit["completed"])
        self.assertEqual(untoggled_habit["streak_days"], initial_streak)

        # Non-existent ID returns None
        self.assertIsNone(self.db.toggle_task("non-existent-task-id"))

    def test_06_delete_task(self):
        """Validates task deletion and metrics recalculation."""
        tasks = self.db.get_tasks()
        initial_count = len(tasks)
        target_id = tasks[0]["id"]

        self.assertTrue(self.db.delete_task(target_id))
        self.assertEqual(len(self.db.get_tasks()), initial_count - 1)

        # Deleting again returns False
        self.assertFalse(self.db.delete_task(target_id))
        self.assertFalse(self.db.delete_task("invalid-random-id"))

    def test_07_workflow_execution_and_metrics_increment(self):
        """Validates recording workflow executions and updating metrics."""
        initial_metrics = self.db.get_metrics()
        initial_saved = initial_metrics["total_time_saved_hours"]
        initial_automations = initial_metrics["automations_triggered_today"]

        logs = [
            "Scanning network endpoints...",
            "Encrypting telemetry pipes...",
            "Autonomous shield activated."
        ]
        result = self.db.record_workflow_execution("Deep Work Defense", 45.0, logs)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["workflow_name"], "Deep Work Defense")
        self.assertEqual(result["time_saved_minutes"], 45.0)

        updated_metrics = self.db.get_metrics()
        expected_saved = round(initial_saved + (45.0 / 60.0), 2)
        self.assertEqual(updated_metrics["total_time_saved_hours"], expected_saved)
        self.assertEqual(updated_metrics["automations_triggered_today"], initial_automations + 1)

    def test_08_subscription_management_and_feature_gates(self):
        """Validates subscription queries and upgrade transitions."""
        # Initial pro tier
        sub = self.db.get_subscription()
        self.assertEqual(sub["tier"], "pro")
        self.assertEqual(sub["features"]["price_monthly"], 9.99)

        # Upgrade to Enterprise
        upgraded = self.db.upgrade_subscription("enterprise")
        self.assertEqual(upgraded["tier"], "enterprise")
        self.assertEqual(upgraded["features"]["price_monthly"], 199)
        self.assertTrue(upgraded["features"]["dedicated_sla"])
        self.assertEqual(upgraded["features"]["max_tasks"], -1)

        # Downgrade to Starter
        starter = self.db.upgrade_subscription("starter")
        self.assertEqual(starter["tier"], "starter")
        self.assertEqual(starter["features"]["max_tasks"], -1)
        self.assertFalse(starter["features"]["cloud_sync"])

        # Invalid tier raises ValueError
        with self.assertRaises(ValueError):
            self.db.upgrade_subscription("infinite_tier_xyz")

    def test_09_tier_feature_gate_enforcement(self):
        """Validates that starter tier provides unmetered local tasks and habits under Open-Core model."""
        self.db.upgrade_subscription("starter")

        # Starter allows unmetered local habits (max_habits: -1)
        # Adding habits beyond previous 5-habit cap succeeds cleanly
        h4 = self.db.create_or_update_task({"title": "Habit 4", "type": "habit"})
        h5 = self.db.create_or_update_task({"title": "Habit 5", "type": "habit"})
        h6 = self.db.create_or_update_task({"title": "Habit 6", "type": "habit"})
        self.assertEqual(h6["title"], "Habit 6")

        sub = self.db.get_subscription()
        self.assertFalse(sub["features"]["cloud_sync"])
        self.assertFalse(sub["features"]["team_workspaces"])
        self.assertFalse(sub["features"]["central_audit_fleet"])

    def test_10_high_concurrency_wal_throughput(self):
        """
        Validates high-throughput concurrency with WAL mode.
        Fires 20 concurrent worker threads performing mixed reads and writes.
        """
        thread_count = 20
        ops_per_thread = 15
        errors = []

        def worker(thread_idx: int):
            try:
                for i in range(ops_per_thread):
                    # Write task
                    task = self.db.create_or_update_task({
                        "title": f"Concurrent Item T{thread_idx}-Op{i}",
                        "type": "task",
                        "priority": "medium",
                        "estimated_minutes": 15
                    })
                    # Read tasks
                    _ = self.db.get_tasks(completed=False)
                    # Toggle completion
                    self.db.toggle_task(task["id"])
                    # Read metrics
                    _ = self.db.get_metrics()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Encountered concurrency errors: {errors}")

        # Ensure database is intact and consistent
        tasks = self.db.get_tasks()
        expected_added = thread_count * ops_per_thread
        # 6 initial tasks + newly created
        self.assertEqual(len(tasks), 6 + expected_added)
        metrics = self.db.get_metrics()
        self.assertGreater(metrics["productivity_score"], 0)

if __name__ == "__main__":
    unittest.main()
