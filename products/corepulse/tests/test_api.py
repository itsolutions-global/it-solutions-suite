"""
CorePulse Automated Integration & Unit Test Suite
Validates all REST API endpoints, workflow executions, state mutations, and static assets.
"""

import json
import os
import sys
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS_DIR = os.path.dirname(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if PRODUCTS_DIR not in sys.path:
    sys.path.insert(0, PRODUCTS_DIR)

from corepulse.api_handler import CorePulseRequestHandler
from corepulse.database import db

TEST_PORT = 9188
TEST_HOST = "127.0.0.1"
BASE_URL = f"http://{TEST_HOST}:{TEST_PORT}"

class CorePulseIntegrationTests(unittest.TestCase):
    """Full-stack integration tests for CorePulse REST API."""

    @classmethod
    def setUpClass(cls):
        """Starts test server in a daemon thread."""
        cls.server = ThreadingHTTPServer((TEST_HOST, TEST_PORT), CorePulseRequestHandler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)  # Allow socket to bind

    @classmethod
    def tearDownClass(cls):
        """Stops test server cleanly."""
        cls.server.shutdown()
        cls.server.server_close()

    def _request(self, method: str, endpoint: str, data: dict = None, timeout: int = 15) -> tuple[int, dict, dict]:
        """Helper to dispatch HTTP requests."""
        url = f"{BASE_URL}{endpoint}"
        req = Request(url, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Connection", "close")

        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")

        for attempt in range(3):
            try:
                with urlopen(req, data=body_bytes, timeout=timeout) as response:
                    status = response.status
                    headers = dict(response.headers)
                    raw = response.read().decode("utf-8")
                    try:
                        res_json = json.loads(raw)
                    except Exception:
                        res_json = {"raw": raw}
                    return status, res_json, headers
            except ConnectionResetError:
                if attempt == 2:
                    raise
                time.sleep(0.1)
            except HTTPError as e:
                raw = e.read().decode("utf-8")
                try:
                    res_json = json.loads(raw)
                except Exception:
                    res_json = {"raw": raw}
                return e.code, res_json, dict(e.headers)

    def test_01_health_check(self):
        """Verifies GET /api/health returns healthy status."""
        status, data, _ = self._request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("service"), "CorePulse Engine")
        self.assertEqual(data.get("version"), "1.0.0")
        self.assertIn("uptime_human", data)

    def test_02_get_tasks_and_habits(self):
        """Verifies GET /api/tasks returns initial seed items."""
        status, data, _ = self._request("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertIn("tasks", data)
        self.assertGreaterEqual(data["count"], 3)

    def test_03_create_new_task(self):
        """Verifies POST /api/tasks creates a task and recalculates metrics."""
        new_task = {
            "title": "Architect Zero-Trust Telemetry Mesh",
            "type": "task",
            "category": "Security",
            "priority": "critical",
            "estimated_minutes": 90
        }
        status, data, _ = self._request("POST", "/api/tasks", new_task)
        self.assertEqual(status, 201)
        self.assertEqual(data["task"]["title"], new_task["title"])
        self.assertEqual(data["task"]["priority"], "critical")
        self.assertFalse(data["task"]["completed"])
        self.created_task_id = data["task"]["id"]

        # Verify task is returned in task list
        status2, data2, _ = self._request("GET", "/api/tasks")
        matching = [t for t in data2["tasks"] if t["id"] == self.created_task_id]
        self.assertEqual(len(matching), 1)
        # Clean up created task
        self._request("DELETE", f"/api/tasks?id={self.created_task_id}")

    def test_04_toggle_task(self):
        """Verifies POST /api/tasks/toggle flips completion status."""
        # Find first task
        _, tasks_data, _ = self._request("GET", "/api/tasks")
        target_task = tasks_data["tasks"][0]
        original_status = target_task["completed"]

        status, data, _ = self._request("POST", "/api/tasks/toggle", {"id": target_task["id"]})
        self.assertEqual(status, 200)
        self.assertEqual(data["task"]["completed"], not original_status)

    def test_05_run_workflow(self):
        """Verifies POST /api/workflows/run executes script and updates metrics."""
        _, initial_metrics, _ = self._request("GET", "/api/metrics")
        initial_saved = initial_metrics["total_time_saved_hours"]

        payload = {"workflow_id": "deep_work_shield"}
        status, data, _ = self._request("POST", "/api/workflows/run", payload)
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["workflow_id"], "deep_work_shield")
        self.assertGreaterEqual(len(data["logs"]), 3)
        self.assertEqual(data["time_saved_minutes"], 35)

        # Check metrics updated
        _, updated_metrics, _ = self._request("GET", "/api/metrics")
        self.assertGreater(updated_metrics["total_time_saved_hours"], initial_saved)

    def test_06_get_metrics(self):
        """Verifies GET /api/metrics structure."""
        status, data, _ = self._request("GET", "/api/metrics")
        self.assertEqual(status, 200)
        self.assertIn("productivity_score", data)
        self.assertIn("total_time_saved_hours", data)
        self.assertIn("habits_completed_today", data)

    def test_07_subscription_and_upgrade(self):
        """Verifies GET /api/subscription and POST /api/subscription/upgrade."""
        status, data, _ = self._request("GET", "/api/subscription")
        self.assertEqual(status, 200)
        self.assertIn("tier", data)
        self.assertIn("features", data)

        # Upgrade to Enterprise via tier string
        status2, data2, _ = self._request("POST", "/api/subscription/upgrade", {"tier": "enterprise"})
        self.assertEqual(status2, 200)
        self.assertEqual(data2["subscription"]["tier"], "enterprise")
        self.assertTrue(data2["subscription"]["features"]["dedicated_sla"])

        # Upgrade via Cryptographic License Key
        from corepulse.licensing import generate_license_key
        pro_key = generate_license_key(tier="pro", customer_name="API User", organization="REST Corp")
        status3, data3, _ = self._request("POST", "/api/subscription/upgrade", {"license_key": pro_key})
        self.assertEqual(status3, 200)
        self.assertEqual(data3["tier"], "pro")
        self.assertEqual(data3["subscription"]["customer_name"], "API User")

        # Rejection of invalid license key
        status4, data4, _ = self._request("POST", "/api/subscription/upgrade", {"license_key": "CP-PRO-corrupted-invalid"})
        self.assertEqual(status4, 400)

    def test_08_static_file_serving(self):
        """Verifies static dashboard, CSS, and JS are served properly."""
        # Index.html
        status, data, headers = self._request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn("COREPULSE", data.get("raw", ""))

        # CSS
        status_css, _, headers_css = self._request("GET", "/css/dashboard.css")
        self.assertEqual(status_css, 200)
        self.assertIn("text/css", headers_css.get("Content-Type", ""))

        # JS
        status_js, _, headers_js = self._request("GET", "/js/dashboard.js")
        self.assertEqual(status_js, 200)
        self.assertIn("application/javascript", headers_js.get("Content-Type", ""))

    def test_09_delete_task(self):
        """Verifies DELETE /api/tasks?id=... removes item."""
        # Create temp task to delete
        _, create_data, _ = self._request("POST", "/api/tasks", {"title": "Temp Task to Delete"})
        task_id = create_data["task"]["id"]

        status, data, _ = self._request("DELETE", f"/api/tasks?id={task_id}")
        self.assertEqual(status, 200)
        self.assertEqual(data["id"], task_id)

        # Ensure gone
        _, tasks_data, _ = self._request("GET", "/api/tasks")
        self.assertNotIn(task_id, [t["id"] for t in tasks_data["tasks"]])

    def test_10_validation_and_security_guardrails(self):
        """Verifies input validation and directory traversal defenses."""
        # Missing title on task creation
        status, data, _ = self._request("POST", "/api/tasks", {"category": "Ops"})
        self.assertEqual(status, 422)
        self.assertTrue(data.get("error"))

        # Non-existent workflow
        status_wf, data_wf, _ = self._request("POST", "/api/workflows/run", {"workflow_id": "non_existent_routine"})
        self.assertEqual(status_wf, 400)
        self.assertTrue(data_wf.get("error"))

        # Path traversal prevention
        status_traversal, _, _ = self._request("GET", "/../../../Windows/win.ini")
        # Should be forbidden (403) or not found (404)
        self.assertIn(status_traversal, (403, 404))

    def test_11_tools_shield_scan(self):
        """Verifies POST /api/tools/shield/scan triggers NexusShield audit."""
        target_dir = str(Path(__file__).resolve().parent.parent)
        status, data, _ = self._request("POST", "/api/tools/shield/scan", {"path": target_dir}, timeout=20)
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "success")
        self.assertIn("score", data)
        self.assertIn("grade", data)
        self.assertIn("findings", data)
        self.assertIsInstance(data["findings"], list)

    def test_12_tools_stream_parse(self):
        """Verifies POST /api/tools/stream/parse scrubs secrets and auto-stages tasks."""
        transcript = (
            "[David CTO] Please deploy the auth service update by Friday !p1 #security. "
            "Our temporary key was sk-proj-98723418726354128937123987123987 and must be rotated.\n"  # nexus-ignore: secret-scan
            "[Sarah] I will complete API testing before Wednesday."
        )
        status, data, _ = self._request("POST", "/api/tools/stream/parse", {"text": transcript})
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["tasks_count"], 1)

        # VoiceGuard must have intercepted the secret
        self.assertFalse(data["security_audit"]["is_clean"])
        self.assertIn("[REDACTED_SECRET: OpenAI API Key]", data["security_audit"]["redacted_text"])

        # Staged tasks must exist in database
        status_t, tasks_data, _ = self._request("GET", "/api/tasks")
        self.assertEqual(status_t, 200)
        titles = [t["title"] for t in tasks_data["tasks"]]
        staged_titles = [st["title"] for st in data["staged_tasks"]]
        for st_title in staged_titles:
            self.assertIn(st_title, titles)

        # Verify SQLite WAL store contains staged tasks
        from corepulse.database_sqlite import sqlite_db
        sqlite_tasks = sqlite_db.get_tasks()
        sqlite_titles = [t["title"] for t in sqlite_tasks]
        for st_title in staged_titles:
            self.assertIn(st_title, sqlite_titles)

        # Clean up staged tasks to maintain pristine test store state
        for st in data["staged_tasks"]:
            try:
                self._request("DELETE", f"/api/tasks?id={st['id']}")
            except Exception:
                pass

    def test_13_pipeline_status_and_scan(self):
        """Verifies GET /api/tools/pipeline/status and POST /api/tools/pipeline/scan."""
        import tempfile
        # 1. Test Status
        status_s, data_s, _ = self._request("GET", "/api/tools/pipeline/status")
        self.assertEqual(status_s, 200)
        self.assertIn("status", data_s)
        self.assertIn("stats", data_s)
        self.assertIn("drop_dir", data_s)

        # 2. Test Scan
        with tempfile.TemporaryDirectory() as tmp_drop:
            drop_path = Path(tmp_drop)
            sample_file = drop_path / "sync.txt"
            sample_file.write_text("[Alex Lead] We need to review the Q1 sprint plan by Friday !p1 #planning", encoding="utf-8")

            status_p, data_p, _ = self._request("POST", "/api/tools/pipeline/scan", {"drop_dir": str(drop_path)})
            self.assertEqual(status_p, 200)
            self.assertEqual(data_p["status"], "success")
            self.assertEqual(data_p["processed_count"], 1)
            self.assertGreaterEqual(data_p["receipts"][0]["tasks_extracted"], 1)
            time.sleep(0.05)

    def test_14_e2ee_sync_rest_endpoints(self):
        """Verifies GET /api/sync/status, POST /api/sync/pair, /api/sync/push, /api/sync/pull."""
        import tempfile
        from sync_relay import BlindedRelayServer
        from corepulse.sync import sync_engine

        # 1. GET /api/sync/status
        status1, data1, _ = self._request("GET", "/api/sync/status")
        self.assertEqual(status1, 200)
        self.assertIn("client_id", data1)
        self.assertIn("paired", data1)
        self.assertIn("pending_outbox_count", data1)

        # 2. POST /api/sync/pair validation (missing passphrase -> 400)
        status_bad, data_bad, _ = self._request("POST", "/api/sync/pair", {})
        self.assertEqual(status_bad, 400)

        # 3. Start ephemeral test relay
        with tempfile.TemporaryDirectory() as tmp_r:
            relay_db = Path(tmp_r) / "test_relay.sqlite3"
            test_relay_port = 9189
            relay_srv = BlindedRelayServer(host="127.0.0.1", port=test_relay_port, db_path=relay_db)
            relay_srv.start_background()

            try:
                passphrase = "api-test-passphrase-2026"
                relay_url = f"http://127.0.0.1:{test_relay_port}"

                # 4. POST /api/sync/pair (Valid pairing)
                status2, data2, _ = self._request("POST", "/api/sync/pair", {
                    "passphrase": passphrase,
                    "relay_url": relay_url
                })
                self.assertEqual(status2, 200)
                self.assertTrue(data2.get("success"))
                self.assertTrue(data2.get("paired"))

                # 5. Record change & POST /api/sync/push
                sync_engine.record_change("task", "api-sync-task-99", "create", {
                    "id": "api-sync-task-99",
                    "title": "REST API Synchronized Task",
                    "completed": False
                })

                status3, data3, _ = self._request("POST", "/api/sync/push", {
                    "passphrase": passphrase
                })
                self.assertEqual(status3, 200)
                self.assertTrue(data3.get("success"))
                self.assertGreaterEqual(data3.get("pushed_count", 0), 1)

                # 6. POST /api/sync/pull
                status4, data4, _ = self._request("POST", "/api/sync/pull", {
                    "passphrase": passphrase
                })
                self.assertEqual(status4, 200)
                self.assertTrue(data4.get("success"))
                self.assertIn("records_received", data4)

            finally:
                relay_srv.stop()


    def test_feedback_intake_api(self):
        """Verifies POST /api/feedback records sentiment and GET /api/feedback lists entries."""
        # 1. Validation error on empty message
        status_err, data_err, _ = self._request("POST", "/api/feedback", {"message": ""})
        self.assertEqual(status_err, 400)
        self.assertIn("error", data_err)

        # 2. Successful feedback submission
        status, data, _ = self._request("POST", "/api/feedback", {
            "sentiment": "great",
            "category": "Performance",
            "message": "Sub-15ms response time on local SQLite WAL is fantastic!",
            "contact": "founder@example.com"
        })
        self.assertEqual(status, 201)
        self.assertEqual(data.get("status"), "success")
        self.assertTrue(data.get("feedback_id", "").startswith("FB-"))

        # 3. GET /api/feedback retrieves saved entries
        status_get, data_get, _ = self._request("GET", "/api/feedback")
        self.assertEqual(status_get, 200)
        self.assertGreaterEqual(data_get.get("total", 0), 1)
        found = any(f.get("message") == "Sub-15ms response time on local SQLite WAL is fantastic!" for f in data_get.get("feedback", []))
        self.assertTrue(found, "Submitted feedback entry must be present in local log")


if __name__ == "__main__":
    unittest.main()

