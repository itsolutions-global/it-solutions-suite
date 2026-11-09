"""
CorePulse Security, Concurrency & Edge-Case Audit Test Suite
Developed by Chief Quality Officer & Corporate Auditor
Audits boundary conditions, concurrency safety, input sanitization, and security guardrails.
"""

import json
import os
import sys
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from corepulse.api_handler import CorePulseRequestHandler
from corepulse.database import db

AUDIT_PORT = 9199
AUDIT_HOST = "127.0.0.1"
BASE_URL = f"http://{AUDIT_HOST}:{AUDIT_PORT}"

class AuditServer(ThreadingHTTPServer):
    request_queue_size = 128

class CorePulseSecurityAuditTests(unittest.TestCase):
    """Rigorous audit test cases for security, edge-cases, and resilience."""

    @classmethod
    def setUpClass(cls):
        cls.server = AuditServer((AUDIT_HOST, AUDIT_PORT), CorePulseRequestHandler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _request(self, method: str, endpoint: str, data: dict = None, headers: dict = None) -> tuple[int, dict, dict]:
        url = f"{BASE_URL}{endpoint}"
        req = Request(url, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Connection", "close")
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)

        body_bytes = None
        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")

        for attempt in range(3):
            try:
                with urlopen(req, data=body_bytes, timeout=30) as response:
                    status = response.status
                    resp_headers = dict(response.headers)
                    raw = response.read().decode("utf-8")
                    try:
                        res_json = json.loads(raw)
                    except Exception:
                        res_json = {"raw": raw}
                    return status, res_json, resp_headers
            except HTTPError as e:
                raw = e.read().decode("utf-8")
                try:
                    res_json = json.loads(raw)
                except Exception:
                    res_json = {"raw": raw}
                return e.code, res_json, dict(e.headers)
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                if attempt == 2:
                    raise
                time.sleep(0.05 * (attempt + 1))

    def test_audit_01_path_traversal_escapes(self):
        """Audit traversal vectors that attempt to escape STATIC_DIR."""
        vectors = [
            "/../../../Windows/win.ini",
            "/..\\..\\..\\Windows\\win.ini",
            "/../data/corepulse_store.json",
            "/../../corepulse/config.py",
        ]
        for vector in vectors:
            status, _, _ = self._request("GET", vector)
            self.assertEqual(status, 403, f"Path traversal out of STATIC_DIR was not 403 Forbidden: {vector}")

    def test_audit_02_concurrency_thread_safety(self):
        """Stress test: 20 concurrent threads toggling and creating tasks."""
        errors = []

        created_ids = []

        def worker(thread_id):
            time.sleep(thread_id * 0.01)
            try:
                status, data, _ = self._request("POST", "/api/tasks", {
                    "title": f"Concurrent Task from Worker {thread_id}",
                    "type": "task",
                    "priority": "medium"
                })
                if status != 201:
                    errors.append(f"Worker {thread_id} failed create: {status}")
                    return
                task_id = data["task"]["id"]
                created_ids.append(task_id)

                status_toggle, _, _ = self._request("POST", "/api/tasks/toggle", {"id": task_id})
                if status_toggle != 200:
                    errors.append(f"Worker {thread_id} failed toggle: {status_toggle}")

            except Exception as e:
                errors.append(f"Worker {thread_id} exception: {e}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrency errors encountered: {errors}")

        # Cleanup created tasks to prevent disk bloat
        for tid in created_ids:
            try:
                self._request("DELETE", f"/api/tasks?id={tid}")
            except Exception:
                pass

    def test_audit_03_malformed_json_handling(self):
        """Ensure malformed JSON payload returns structured 400 Bad Request."""
        url = f"{BASE_URL}/api/tasks"
        req = Request(url, data=b"{malformed_json: true,", method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            urlopen(req, timeout=5)
            self.fail("Expected HTTPError 400 for malformed JSON")
        except HTTPError as e:
            self.assertEqual(e.code, 400)
            res = json.loads(e.read().decode("utf-8"))
            self.assertTrue(res.get("error"))

    def test_audit_04_stored_xss_payload_preservation(self):
        """Ensure XSS payloads in title are stored safely and not evaluated."""
        xss_payload = "<script>alert('XSS-TEST')</script>"
        status, data, _ = self._request("POST", "/api/tasks", {
            "title": xss_payload,
            "type": "task",
            "priority": "high"
        })
        self.assertEqual(status, 201)
        self.assertEqual(data["task"]["title"], xss_payload)
        xss_id = data["task"]["id"]

        status2, data2, _ = self._request("GET", "/api/tasks")
        matching = [t for t in data2["tasks"] if t["id"] == xss_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["title"], xss_payload)

        # Cleanup
        self._request("DELETE", f"/api/tasks?id={xss_id}")

    def test_audit_05_unsupported_http_method(self):
        """Test unsupported PUT method behaves predictably without server crash."""
        status, data, _ = self._request("PUT", "/api/tasks", {"title": "Update"})
        self.assertIn(status, (405, 501))

    def test_audit_06_unauthenticated_tier_upgrade_vulnerability(self):
        """
        Audit vulnerability verification:
        Demonstrates that any unauthenticated actor can upgrade to enterprise tier.
        This test documents the absence of cryptographic license checks.
        """
        status, data, _ = self._request("POST", "/api/subscription/upgrade", {"tier": "enterprise"})
        self.assertEqual(status, 200)
        self.assertEqual(data["subscription"]["tier"], "enterprise")

if __name__ == "__main__":
    unittest.main()
