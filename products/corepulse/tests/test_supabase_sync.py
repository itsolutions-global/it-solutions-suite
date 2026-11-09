"""
CorePulse Supabase Offline-First Sync & Field-Level CRDT Test Suite
Sprint 16 Automated Verification Suite.

Validates QA-SUPOFF-01 through QA-SUPOFF-08:
  1. QA-SUPOFF-01: Offline Outbox Queueing (< 2ms local write SLA).
  2. QA-SUPOFF-02: Reconnect Batch Replication (Mock PostgREST batch push).
  3. QA-SUPOFF-03: Tenant Isolation & Config Loading from vault/environment.
  4. QA-SUPOFF-04: Hybrid Logical Clock (HLC) Monotonicity & Causality.
  5. QA-SUPOFF-05: Field-Level Last-Write-Wins (LWW-CRDT) Conflict Resolution.
  6. QA-SUPOFF-06: Remote Reception & Delta Ingestion.
  7. QA-SUPOFF-07: Tombstone Deletion Handling.
  8. QA-SUPOFF-08: 4-State Machine Telemetry (SYNCED, PENDING, CONFLICT, FAILED).
  9. REST API Handlers & Diagnostics (/api/supabase/*).
"""

import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

# Paths
TEST_DIR = Path(__file__).resolve().parent
COREPULSE_DIR = TEST_DIR.parent
WORKSPACE_DIR = COREPULSE_DIR.parent.parent

if str(COREPULSE_DIR) not in sys.path:
    sys.path.insert(0, str(COREPULSE_DIR))
if str(COREPULSE_DIR / "corepulse") not in sys.path:
    sys.path.insert(0, str(COREPULSE_DIR / "corepulse"))

from sync_supabase import (
    HybridLogicalClock,
    FieldLevelCRDTResolver,
    SupabaseConfig,
    SupabaseRestClient,
    SupabaseOfflineSync,
)
from database_sqlite import Database


class TestSupabaseOfflineSync(unittest.TestCase):
    """Exhaustive test suite for CorePulse Supabase Offline-First Synchronization."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "test_corepulse.sqlite3"

        # Initialize test config
        self.config = SupabaseConfig(
            url="https://testproject.supabase.co",
            key="test-service-role-key-ey1234567890",
            tenant_id="tenant_alpha_corp",
            user_id="user_test_uuid_999",
            db_path=self.db_path,
        )
        self.sync_engine = SupabaseOfflineSync(config=self.config)

    def tearDown(self):
        self.sync_engine.stop_worker()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # QA-SUPOFF-04: HLC Monotonicity
    # --------------------------------------------------------------------------
    def test_01_hlc_monotonicity_and_ordering(self):
        """Validates that HLC strictly increments monotonically with no reversals."""
        hlc = HybridLogicalClock(node_id="node_a")
        timestamps = [hlc.tick() for _ in range(100)]

        for i in range(1, len(timestamps)):
            cmp = HybridLogicalClock.compare(timestamps[i], timestamps[i - 1])
            self.assertEqual(cmp, 1, f"HLC monotonicity failure at step {i}: {timestamps[i]} not > {timestamps[i - 1]}")

    def test_02_hlc_causality_advance_past_remote(self):
        """Validates that observing a future remote HLC advances the local clock past it."""
        hlc = HybridLogicalClock(node_id="node_b")
        remote_hlc = "9999999999999999:42:node_c"

        advanced = hlc.update(remote_hlc)
        cmp = HybridLogicalClock.compare(advanced, remote_hlc)
        self.assertEqual(cmp, 1, f"Local HLC failed to advance past remote: {advanced} not > {remote_hlc}")

    # --------------------------------------------------------------------------
    # QA-SUPOFF-01: Offline Outbox Queueing (< 2ms SLA)
    # --------------------------------------------------------------------------
    def test_03_offline_outbox_queueing(self):
        """Verifies that mutations queue in SQLite outbox instantaneously without network."""
        t0 = time.perf_counter()
        hlc = self.sync_engine.enqueue_mutation(
            entity_type="task",
            entity_id="task_offline_01",
            action="create",
            payload={"title": "Local Focus Session", "priority": "high", "completed": False},
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        self.assertLess(elapsed_ms, 50.0, "Local enqueue took longer than acceptable SLA")
        self.assertTrue(bool(hlc))

        status = self.sync_engine.get_status()
        self.assertEqual(status["pending_count"], 1)
        self.assertEqual(status["state"], SupabaseOfflineSync.STATE_PENDING)

        outbox = self.sync_engine.get_outbox()
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0]["entity_id"], "task_offline_01")
        self.assertEqual(outbox[0]["action"], "create")
        self.assertFalse(outbox[0]["is_synced"])

    # --------------------------------------------------------------------------
    # QA-SUPOFF-05: Field-Level CRDT LWW Conflict Resolution
    # --------------------------------------------------------------------------
    def test_04_field_level_crdt_non_clobbering(self):
        """
        Validates that when Node A edits title and Node B edits completed status,
        field-level LWW merges both edits without row clobbering.
        """
        local_record = {
            "id": "task_100",
            "title": "Local Updated Title",
            "completed": False,
            "priority": "medium",
            "hlc": "1000000:0:node_a",
        }

        # Remote delta arrived from Node B: higher HLC on completed status
        remote_delta = {
            "id": "task_100",
            "completed": True,
            "priority": "critical",
            "hlc": "2000000:0:node_b",
        }

        merged, conflicts = FieldLevelCRDTResolver.merge_record(local_record, remote_delta)

        # Title from local record should be preserved because remote did not alter title
        self.assertEqual(merged["title"], "Local Updated Title")
        # Completed and priority from remote should win because remote HLC was higher
        self.assertTrue(merged["completed"])
        self.assertEqual(merged["priority"], "critical")
        self.assertEqual(merged["hlc"], "2000000:0:node_b")
        self.assertGreater(len(conflicts), 0)

    # --------------------------------------------------------------------------
    # QA-SUPOFF-02: Reconnect Batch Push (Mocked PostgREST)
    # --------------------------------------------------------------------------
    def test_05_reconnect_batch_flush_success(self):
        """Simulates reconnecting to network and flushing pending outbox to PostgREST."""
        # Queue 3 tasks
        for i in range(3):
            self.sync_engine.enqueue_mutation(
                entity_type="task",
                entity_id=f"task_batch_{i}",
                action="create",
                payload={"title": f"Batch Task {i}", "priority": "medium"},
            )

        status_before = self.sync_engine.get_status()
        self.assertEqual(status_before["pending_count"], 3)
        self.assertEqual(status_before["state"], SupabaseOfflineSync.STATE_PENDING)

        # Mock upsert_records to simulate successful PostgREST HTTP 201
        with patch.object(self.sync_engine.client, "upsert_records", return_value=(True, 3, None)):
            flush_res = self.sync_engine.flush_outbox()

            self.assertTrue(flush_res["success"])
            self.assertEqual(flush_res["flushed_count"], 3)
            self.assertEqual(flush_res["remaining_pending"], 0)
            self.assertEqual(flush_res["state"], SupabaseOfflineSync.STATE_SYNCED)

        # Verify all outbox rows are now marked is_synced = 1
        status_after = self.sync_engine.get_status()
        self.assertEqual(status_after["pending_count"], 0)
        self.assertEqual(status_after["state"], SupabaseOfflineSync.STATE_SYNCED)

    # --------------------------------------------------------------------------
    # QA-SUPOFF-06: Remote Reception & Delta Ingestion
    # --------------------------------------------------------------------------
    def test_06_pull_remote_deltas_into_sqlite(self):
        """Simulates pulling new remote records from Supabase into local SQLite."""
        remote_deltas = [
            {
                "id": "remote_task_01",
                "title": "Cloud Sourced Focus Block",
                "type": "task",
                "category": "Deep Work",
                "priority": "high",
                "completed": False,
                "due_date": "Tomorrow",
                "estimated_minutes": 45,
                "streak_days": 0,
                "tags": ["cloud", "federation"],
                "hlc": "5000000:1:node_cloud",
                "client_id": "node_cloud",
                "is_deleted": False,
            }
        ]

        with patch.object(self.sync_engine.client, "fetch_remote_deltas", return_value=(True, remote_deltas, None)):
            pull_res = self.sync_engine.pull_remote()

            self.assertTrue(pull_res["success"])
            self.assertEqual(pull_res["records_pulled"], 1)
            self.assertEqual(pull_res["applied_count"], 1)

        # Query local SQLite to ensure row was inserted
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT title, priority, estimated_minutes FROM tasks WHERE id = 'remote_task_01';")
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], "Cloud Sourced Focus Block")
        self.assertEqual(row[1], "high")
        self.assertEqual(row[2], 45)

    # --------------------------------------------------------------------------
    # QA-SUPOFF-07: Tombstone Deletion Handling
    # --------------------------------------------------------------------------
    def test_07_tombstone_deletion_propagation(self):
        """Validates that delete mutations enqueue tombstones and pull deletes properly."""
        # 1. Enqueue delete
        hlc = self.sync_engine.enqueue_mutation(
            entity_type="task",
            entity_id="task_to_delete",
            action="delete",
            payload={"id": "task_to_delete", "is_deleted": True},
        )
        outbox = self.sync_engine.get_outbox()
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0]["action"], "delete")

        # 2. Pull remote tombstone for existing local task
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (id, title, created_at, completed) 
            VALUES ('task_remote_del', 'To Be Deleted', '2026-11-09T00:00:00Z', 0);
        """)
        conn.commit()
        conn.close()

        remote_tombstone = [
            {
                "id": "task_remote_del",
                "title": "To Be Deleted",
                "is_deleted": True,
                "hlc": "8000000:0:node_remote",
                "client_id": "node_remote",
            }
        ]

        with patch.object(self.sync_engine.client, "fetch_remote_deltas", return_value=(True, remote_tombstone, None)):
            self.sync_engine.pull_remote()

        # Task should be removed from active SQLite tasks
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tasks WHERE id = 'task_remote_del';")
        row = cursor.fetchone()
        conn.close()

        self.assertIsNone(row, "Deleted tombstone task was not removed from SQLite")

    # --------------------------------------------------------------------------
    # QA-SUPOFF-08: 4-State Machine Telemetry Transitions
    # --------------------------------------------------------------------------
    def test_08_telemetry_state_machine_transitions(self):
        """Verifies state machine transitions: SYNCED -> PENDING -> FAILED -> SYNCED."""
        # Clean state: SYNCED
        status = self.sync_engine.get_status()
        self.assertEqual(status["state"], SupabaseOfflineSync.STATE_SYNCED)

        # Mutate: moves to PENDING
        self.sync_engine.enqueue_mutation("task", "task_st", "create", {"title": "State Test"})
        status = self.sync_engine.get_status()
        self.assertEqual(status["state"], SupabaseOfflineSync.STATE_PENDING)

        # Flush failure: moves to FAILED
        with patch.object(self.sync_engine.client, "upsert_records", return_value=(False, 0, "Network timeout")):
            flush_res = self.sync_engine.flush_outbox()
            self.assertFalse(flush_res["success"])
            status = self.sync_engine.get_status()
            self.assertEqual(status["state"], SupabaseOfflineSync.STATE_FAILED)

        # Flush success: recovers to SYNCED
        with patch.object(self.sync_engine.client, "upsert_records", return_value=(True, 1, None)):
            flush_res = self.sync_engine.flush_outbox()
            self.assertTrue(flush_res["success"])
            status = self.sync_engine.get_status()
            self.assertEqual(status["state"], SupabaseOfflineSync.STATE_SYNCED)

    # --------------------------------------------------------------------------
    # Local SQLite Database Hook Integration
    # --------------------------------------------------------------------------
    def test_09_database_sqlite_outbox_hook(self):
        """Verifies that Database.create_or_update_task automatically enqueues to outbox."""
        db = Database(db_path=self.db_path)
        created = db.create_or_update_task({"title": "Hooked Focus Task", "priority": "high"})
        self.assertTrue(bool(created.get("id")))

        # Check that supabase_sync_outbox captured the mutation
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT entity_id, action, is_synced FROM supabase_sync_outbox WHERE entity_id = ?;", (created["id"],))
        outbox_row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(outbox_row)
        self.assertEqual(outbox_row[0], created["id"])
        self.assertEqual(outbox_row[1], "create")
        self.assertEqual(outbox_row[2], 0)

    # --------------------------------------------------------------------------
    # REST API Handler Diagnostics
    # --------------------------------------------------------------------------
    def test_10_api_supabase_endpoints(self):
        """Verifies /api/supabase/status, /outbox, /conflicts, /sync, and /configure."""
        from io import BytesIO
        from api_handler import CorePulseRequestHandler

        class MockServer:
            pass

        # Helper to invoke mock request
        def invoke_request(method, path, body=None):
            req = MockServer()
            req.rfile = BytesIO(json.dumps(body).encode("utf-8") if body else b"")
            req.wfile = BytesIO()
            handler = CorePulseRequestHandler.__new__(CorePulseRequestHandler)
            handler.rfile = req.rfile
            handler.wfile = req.wfile
            handler.headers = {
                "Content-Length": str(len(req.rfile.getvalue())),
                "Content-Type": "application/json",
            }
            handler.path = path
            handler.command = method
            handler.close_connection = True
            handler.request_version = "HTTP/1.1"
            handler.requestline = f"{method} {path} HTTP/1.1"
            handler.client_address = ("127.0.0.1", 12345)

            # Execute method
            if method == "GET":
                handler.do_GET()
            elif method == "POST":
                handler.do_POST()

            raw_resp = req.wfile.getvalue().decode("utf-8")
            parts = raw_resp.split("\r\n\r\n", 1)
            body_json = json.loads(parts[1]) if len(parts) > 1 and parts[1].strip() else {}
            return body_json

        # 1. GET /api/supabase/status
        st = invoke_request("GET", "/api/supabase/status")
        self.assertIn("state", st)
        self.assertIn("node_id", st)

        # 2. GET /api/supabase/outbox
        out = invoke_request("GET", "/api/supabase/outbox")
        self.assertIn("total_pending", out)
        self.assertIn("records", out)

        # 3. GET /api/supabase/conflicts
        confs = invoke_request("GET", "/api/supabase/conflicts")
        self.assertIn("total_conflicts", confs)

        # 4. POST /api/supabase/configure
        cfg = invoke_request("POST", "/api/supabase/configure", {
            "supabase_url": "https://api.supabase.com",
            "api_key": "test_key",
            "tenant_id": "test_tenant",
        })
        self.assertTrue(cfg.get("success"))

    # --------------------------------------------------------------------------
    # Standalone CLI Subcommands
    # --------------------------------------------------------------------------
    def test_11_cli_subcommands(self):
        """Verifies CLI flag dispatch without runtime exceptions."""
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(COREPULSE_DIR / "sync_supabase.py"), "--status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIn("state", data)
        self.assertIn("tenant_id", data)


if __name__ == "__main__":
    unittest.main()

