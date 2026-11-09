"""
CorePulse Zero-Knowledge E2EE Cloud Sync & Blinded Relay Test Suite
Sprint 12 Automated Verification Suite.
Validates:
  1. PBKDF2-HMAC-SHA256 & HMAC-CTR stream cipher round-trip.
  2. Cryptographic tamper resistance and Encrypt-then-MAC authentication.
  3. Lamport logical clock monotonicity and LWW CRDT convergence.
  4. Multi-node offline outbox queuing, push, and pull lifecycle.
  5. Blinded relay server storage and Zero-Knowledge partition isolation.
  6. Corporate CLI sync subcommands.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Paths
TEST_DIR = Path(__file__).resolve().parent
COREPULSE_DIR = TEST_DIR.parent
PRODUCTS_DIR = COREPULSE_DIR.parent

if str(COREPULSE_DIR) not in sys.path:
    sys.path.insert(0, str(COREPULSE_DIR))
if str(PRODUCTS_DIR) not in sys.path:
    sys.path.insert(0, str(PRODUCTS_DIR))


from corepulse.sync import (
    ZeroKnowledgeCipher,
    CRDTResolver,
    SyncEngine,
    AuthenticationError,
    SyncError
)
from sync_relay import BlindedRelayServer, RelayStore


class TestCorePulseSync(unittest.TestCase):
    """Exhaustive test suite for CorePulse Zero-Knowledge E2EE Cloud Sync."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.db_path = self.temp_path / "test_sync.sqlite3"
        self.passphrase = "master-e2ee-sync-passphrase-2026"

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_key_derivation_deterministic(self):
        """Validates that key derivation produces identical keys for identical salt and passphrase."""
        salt = b"0123456789abcdef"
        enc1, mac1 = ZeroKnowledgeCipher.derive_keys(self.passphrase, salt)
        enc2, mac2 = ZeroKnowledgeCipher.derive_keys(self.passphrase, salt)

        self.assertEqual(enc1, enc2)
        self.assertEqual(mac1, mac2)
        self.assertEqual(len(enc1), 32)
        self.assertEqual(len(mac1), 32)

        # Different passphrase produces distinct keys
        enc3, mac3 = ZeroKnowledgeCipher.derive_keys("different-passphrase-2026", salt)
        self.assertNotEqual(enc1, enc3)
        self.assertNotEqual(mac1, mac3)

    def test_02_zero_knowledge_encryption_decryption_roundtrip(self):
        """Validates end-to-end zero-knowledge encryption and decryption round-trip."""
        data = {
            "entity": "task",
            "id": "task-zk-01",
            "title": "Zero-Knowledge Architecture Audit",
            "tags": ["security", "e2ee", "crdt"],
            "metadata": {"priority": "critical", "effort_minutes": 120}
        }
        encrypted_blob = ZeroKnowledgeCipher.encrypt(data, self.passphrase)
        self.assertIsInstance(encrypted_blob, str)
        self.assertNotIn("Zero-Knowledge", encrypted_blob)

        decrypted = ZeroKnowledgeCipher.decrypt(encrypted_blob, self.passphrase)
        self.assertEqual(decrypted, data)

    def test_03_tamper_detection_auth_tag_mismatch(self):
        """Validates that tampering with ciphertext raises AuthenticationError."""
        data = {"id": "task-01", "action": "delete"}
        encrypted_blob = ZeroKnowledgeCipher.encrypt(data, self.passphrase)

        # Decode, corrupt ciphertext, re-encode
        import base64
        envelope_json = json.loads(base64.urlsafe_b64decode(encrypted_blob.encode("ascii")).decode("utf-8"))
        # Flip a character in base64 ciphertext
        c = envelope_json["c"]
        corrupted_c = ("A" if c[0] != "A" else "B") + c[1:]
        envelope_json["c"] = corrupted_c
        tampered_blob = base64.urlsafe_b64encode(json.dumps(envelope_json).encode("utf-8")).decode("ascii")

        with self.assertRaises(AuthenticationError):
            ZeroKnowledgeCipher.decrypt(tampered_blob, self.passphrase)

    def test_04_wrong_passphrase_fails(self):
        """Validates that decrypting with an incorrect passphrase fails authentication."""
        data = {"secret_plan": "Executive roadmap details"}
        encrypted_blob = ZeroKnowledgeCipher.encrypt(data, self.passphrase)

        with self.assertRaises(AuthenticationError):
            ZeroKnowledgeCipher.decrypt(encrypted_blob, "wrong-passphrase-attacker")

    def test_05_crdt_lamport_clock_monotonicity(self):
        """Validates that local Lamport logical clock advances monotonically."""
        engine = SyncEngine(db_path=self.db_path)
        c0 = engine.get_lamport_clock()
        self.assertEqual(c0, 0)

        engine.record_change("task", "t-1", "create", {"title": "Task 1"})
        c1 = engine.get_lamport_clock()
        self.assertEqual(c1, 1)

        engine.record_change("task", "t-2", "create", {"title": "Task 2"})
        c2 = engine.get_lamport_clock()
        self.assertEqual(c2, 2)

    def test_06_crdt_last_write_wins_resolution(self):
        """Validates Last-Write-Wins CRDT conflict resolution rules."""
        # Rule 1: Higher clock wins
        self.assertTrue(CRDTResolver.is_incoming_winner(
            incoming_clock=5, incoming_ts="2026-11-05T10:00:00Z", incoming_client_id="client-b",
            current_clock=4, current_ts="2026-11-05T12:00:00Z", current_client_id="client-a"
        ))
        self.assertFalse(CRDTResolver.is_incoming_winner(
            incoming_clock=3, incoming_ts="2026-11-05T12:00:00Z", incoming_client_id="client-b",
            current_clock=4, current_ts="2026-11-05T10:00:00Z", current_client_id="client-a"
        ))

        # Rule 2: Tied clocks, later timestamp wins
        self.assertTrue(CRDTResolver.is_incoming_winner(
            incoming_clock=4, incoming_ts="2026-11-05T12:00:00Z", incoming_client_id="client-a",
            current_clock=4, current_ts="2026-11-05T10:00:00Z", current_client_id="client-b"
        ))
        self.assertFalse(CRDTResolver.is_incoming_winner(
            incoming_clock=4, incoming_ts="2026-11-05T09:00:00Z", incoming_client_id="client-a",
            current_clock=4, current_ts="2026-11-05T10:00:00Z", current_client_id="client-b"
        ))

        # Rule 3: Tied clocks & timestamps, deterministic client_id tie-breaker
        self.assertTrue(CRDTResolver.is_incoming_winner(
            incoming_clock=4, incoming_ts="2026-11-05T10:00:00Z", incoming_client_id="client-z",
            current_clock=4, current_ts="2026-11-05T10:00:00Z", current_client_id="client-a"
        ))
        self.assertFalse(CRDTResolver.is_incoming_winner(
            incoming_clock=4, incoming_ts="2026-11-05T10:00:00Z", incoming_client_id="client-a",
            current_clock=4, current_ts="2026-11-05T10:00:00Z", current_client_id="client-z"
        ))

    def test_07_offline_outbox_queuing(self):
        """Validates that local mutations are queued in SQLite outbox."""
        engine = SyncEngine(db_path=self.db_path)
        d1 = engine.record_change("task", "task-out-01", "create", {"title": "Offline Task"})
        self.assertTrue(d1.startswith("delta-"))

        pending = engine.get_pending_outbox()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["entity_id"], "task-out-01")
        self.assertEqual(pending[0]["payload"]["title"], "Offline Task")

    def test_08_blinded_relay_push_pull_lifecycle(self):
        """Validates end-to-end distributed sync lifecycle between Node A, Relay, and Node B."""
        relay_db = self.temp_path / "relay.sqlite3"
        node_a_db = self.temp_path / "node_a.sqlite3"
        node_b_db = self.temp_path / "node_b.sqlite3"

        test_port = 9187
        server = BlindedRelayServer(host="127.0.0.1", port=test_port, db_path=relay_db)
        server.start_background()

        try:
            relay_url = f"http://127.0.0.1:{test_port}"
            engine_a = SyncEngine(db_path=node_a_db)
            engine_a.pair(self.passphrase, relay_url=relay_url)

            engine_b = SyncEngine(db_path=node_b_db)
            engine_b.pair(self.passphrase, relay_url=relay_url)

            # Node A records two changes
            engine_a.record_change("task", "task-sync-100", "create", {
                "id": "task-sync-100",
                "title": "Master Cloud Sync",
                "priority": "critical",
                "completed": False
            })
            engine_a.record_change("task", "task-sync-101", "create", {
                "id": "task-sync-101",
                "title": "Blinded Relay Mesh",
                "priority": "high",
                "completed": True
            })

            # Node A pushes
            res_push = engine_a.push_deltas(passphrase=self.passphrase)
            self.assertTrue(res_push["success"])
            self.assertEqual(res_push["pushed_count"], 2)

            # Node A outbox should now be clear
            self.assertEqual(len(engine_a.get_pending_outbox()), 0)

            # Node B pulls
            res_pull = engine_b.pull_deltas(passphrase=self.passphrase)
            self.assertTrue(res_pull["success"])
            self.assertEqual(res_pull["applied_count"], 2)

            # Verify Node B database has both tasks
            conn = engine_b._get_connection()
            rows = conn.execute("SELECT id, title, completed FROM tasks ORDER BY id ASC;").fetchall()
            conn.close()

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["id"], "task-sync-100")
            self.assertEqual(rows[0]["title"], "Master Cloud Sync")
            self.assertEqual(rows[1]["id"], "task-sync-101")
            self.assertEqual(rows[1]["completed"], 1)

        finally:
            server.stop()

    def test_09_blinded_relay_does_not_reapply_own_pushes(self):
        """Validates that an instance pulling from relay skips its own pushed deltas."""
        relay_db = self.temp_path / "relay2.sqlite3"
        node_a_db = self.temp_path / "node_a2.sqlite3"

        test_port = 9186
        server = BlindedRelayServer(host="127.0.0.1", port=test_port, db_path=relay_db)
        server.start_background()

        try:
            relay_url = f"http://127.0.0.1:{test_port}"
            engine_a = SyncEngine(db_path=node_a_db)
            engine_a.pair(self.passphrase, relay_url=relay_url)

            engine_a.record_change("task", "task-self-01", "create", {"id": "task-self-01", "title": "Self Task"})
            engine_a.push_deltas(passphrase=self.passphrase)

            # Self pull
            res_pull = engine_a.pull_deltas(passphrase=self.passphrase)
            self.assertTrue(res_pull["success"])
            self.assertEqual(res_pull["applied_count"], 0)  # Skipped because client_id matches
        finally:
            server.stop()

    def test_10_cli_sync_subcommands(self):
        """Validates it-solutions sync status and pair via CLI."""
        cli_py = PRODUCTS_DIR / "cli.py"

        # 1. it-solutions sync status --json
        proc_stat = subprocess.run(
            [sys.executable, str(cli_py), "sync", "status", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        self.assertEqual(proc_stat.returncode, 0)
        data_stat = json.loads(proc_stat.stdout)
        self.assertIn("client_id", data_stat)
        self.assertIn("paired", data_stat)

        # 2. it-solutions sync pair <passphrase> --json
        proc_pair = subprocess.run(
            [sys.executable, str(cli_py), "sync", "pair", "cli-test-passphrase-2026", "--relay-url", "http://127.0.0.1:8081", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        self.assertEqual(proc_pair.returncode, 0)
        data_pair = json.loads(proc_pair.stdout)
        self.assertTrue(data_pair["success"])
        self.assertTrue(data_pair["paired"])

    def test_11_confidentiality_zero_plaintext_leakage_audit(self):
        """
        Audit envelope binary structure: verify ZERO plaintext strings leak into
        ciphertext, envelope JSON, or base64 headers.
        """
        import base64
        sensitive_string_1 = "TOP_SECRET_ACQUISITION_DISCLOSURE_2026"
        sensitive_string_2 = "CONFIDENTIAL_FINANCIAL_PROJECTION_9999"
        payload = {
            "entity": "task",
            "title": sensitive_string_1,
            "notes": sensitive_string_2,
            "amount": 95000000
        }
        encrypted_blob = ZeroKnowledgeCipher.encrypt(payload, self.passphrase)

        # 1. Inspect base64 string
        self.assertNotIn(sensitive_string_1, encrypted_blob)
        self.assertNotIn(sensitive_string_2, encrypted_blob)

        # 2. Inspect decoded envelope json
        raw_json_bytes = base64.urlsafe_b64decode(encrypted_blob.encode("ascii"))
        envelope_data = json.loads(raw_json_bytes.decode("utf-8"))

        self.assertIn("v", envelope_data)
        self.assertIn("s", envelope_data)
        self.assertIn("iv", envelope_data)
        self.assertIn("t", envelope_data)
        self.assertIn("c", envelope_data)

        # 3. Inspect individual fields
        for field in ("s", "iv", "t", "c"):
            self.assertNotIn(sensitive_string_1, envelope_data[field])
            self.assertNotIn(sensitive_string_2, envelope_data[field])

        # 4. Inspect raw ciphertext bytes
        raw_ciphertext = base64.b64decode(envelope_data["c"])
        self.assertNotIn(sensitive_string_1.encode("utf-8"), raw_ciphertext)
        self.assertNotIn(sensitive_string_2.encode("utf-8"), raw_ciphertext)

    def test_12_two_client_concurrent_offline_conflict_convergence(self):
        """
        Simulate 2 isolated offline clients mutating the same entity concurrently.
        Verify that applying each other's deltas deterministically converges to
        the exact same state without data loss.
        """
        import sqlite3
        node_a_db = self.temp_path / "conv_node_a.sqlite3"
        node_b_db = self.temp_path / "conv_node_b.sqlite3"

        engine_a = SyncEngine(db_path=node_a_db)
        engine_b = SyncEngine(db_path=node_b_db)

        engine_a.pair(self.passphrase)
        engine_b.pair(self.passphrase)

        entity_id = "task-conv-001"

        # Client A creates Task locally while offline
        conn_a_init = engine_a._get_connection()
        conn_a_init.execute(
            "INSERT INTO tasks (id, title, priority, completed, created_at) VALUES (?, ?, ?, ?, ?);",
            (entity_id, "Initial Draft by Client A", "low", 0, "2026-11-05T12:00:00Z")
        )
        conn_a_init.commit()
        conn_a_init.close()

        engine_a.record_change("task", entity_id, "create", {
            "id": entity_id,
            "title": "Initial Draft by Client A",
            "priority": "low",
            "completed": False
        })

        # Client B concurrently creates/modifies the same Task offline with higher priority
        conn_b_init = engine_b._get_connection()
        conn_b_init.execute(
            "INSERT INTO tasks (id, title, priority, completed, created_at) VALUES (?, ?, ?, ?, ?);",
            (entity_id, "Urgent Revision by Client B", "urgent", 1, "2026-11-05T12:05:00Z")
        )
        conn_b_init.commit()
        conn_b_init.close()

        engine_b._increment_lamport_clock()
        engine_b.record_change("task", entity_id, "update", {
            "id": entity_id,
            "title": "Urgent Revision by Client B",
            "priority": "urgent",
            "completed": True
        })

        # Exchange outboxes
        outbox_a = engine_a.get_pending_outbox()
        outbox_b = engine_b.get_pending_outbox()
        self.assertEqual(len(outbox_a), 1)
        self.assertEqual(len(outbox_b), 1)

        # Encrypt and exchange
        blob_a = ZeroKnowledgeCipher.encrypt({"deltas": [outbox_a[0]]}, self.passphrase)
        blob_b = ZeroKnowledgeCipher.encrypt({"deltas": [outbox_b[0]]}, self.passphrase)

        # A receives B's delta
        batch_for_a = ZeroKnowledgeCipher.decrypt(blob_b, self.passphrase)
        for delta in batch_for_a["deltas"]:
            engine_a._apply_delta_crdt(delta)

        # B receives A's delta
        batch_for_b = ZeroKnowledgeCipher.decrypt(blob_a, self.passphrase)
        for delta in batch_for_b["deltas"]:
            engine_b._apply_delta_crdt(delta)

        # Verify convergence in SQLite databases
        conn_a = sqlite3.connect(node_a_db)
        conn_a.row_factory = sqlite3.Row
        row_a = conn_a.execute("SELECT title, priority, completed FROM tasks WHERE id = ?;", (entity_id,)).fetchone()
        conn_a.close()

        conn_b = sqlite3.connect(node_b_db)
        conn_b.row_factory = sqlite3.Row
        row_b = conn_b.execute("SELECT title, priority, completed FROM tasks WHERE id = ?;", (entity_id,)).fetchone()
        conn_b.close()

        self.assertIsNotNone(row_a)
        self.assertIsNotNone(row_b)
        # Both must converge to Client B's winning state (higher Lamport clock)
        self.assertEqual(row_a["title"], row_b["title"])
        self.assertEqual(row_a["title"], "Urgent Revision by Client B")
        self.assertEqual(row_a["priority"], "urgent")
        self.assertEqual(row_a["completed"], 1)

    def test_13_tampered_iv_and_corrupted_ciphertext_rejection(self):
        """
        Verify that bit flips directly inside IV or corrupted JSON envelope
        raise AuthenticationError.
        """
        import base64
        data = {"test": "data"}
        encrypted_blob = ZeroKnowledgeCipher.encrypt(data, self.passphrase)
        envelope_json = json.loads(base64.urlsafe_b64decode(encrypted_blob.encode("ascii")).decode("utf-8"))

        # 1. Corrupt IV
        iv = envelope_json["iv"]
        corrupted_iv = ("A" if iv[0] != "A" else "B") + iv[1:]
        env_iv_tampered = dict(envelope_json, iv=corrupted_iv)
        blob_iv_tampered = base64.urlsafe_b64encode(json.dumps(env_iv_tampered).encode("utf-8")).decode("ascii")

        with self.assertRaises(AuthenticationError):
            ZeroKnowledgeCipher.decrypt(blob_iv_tampered, self.passphrase)

        # 2. Corrupt Auth Tag
        tag = envelope_json["t"]
        corrupted_tag = ("A" if tag[0] != "A" else "B") + tag[1:]
        env_tag_tampered = dict(envelope_json, t=corrupted_tag)
        blob_tag_tampered = base64.urlsafe_b64encode(json.dumps(env_tag_tampered).encode("utf-8")).decode("ascii")

        with self.assertRaises(AuthenticationError):
            ZeroKnowledgeCipher.decrypt(blob_tag_tampered, self.passphrase)

    def test_14_windows_autostart_script_safety_audit(self):
        """
        Audit products/setup_autostart.ps1 and setup_autostart.bat for:
        1. Strict path quoting (defense against unquoted path / space-in-path injection).
        2. Non-elevated HKCU user registry isolation (zero privilege escalation).
        3. Safe non-mutating execution of -Status switch.
        """
        repo_root = PRODUCTS_DIR
        ps1_path = repo_root / "setup_autostart.ps1"
        bat_path = repo_root / "setup_autostart.bat"

        self.assertTrue(ps1_path.exists(), f"Autostart PS1 not found at {ps1_path}")
        self.assertTrue(bat_path.exists(), f"Autostart BAT not found at {bat_path}")

        ps1_content = ps1_path.read_text(encoding="utf-8")
        # Registry target: HKCU, NOT HKLM
        self.assertIn("HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run", ps1_content)
        self.assertNotIn("HKLM:", ps1_content, "Must NOT target HKLM (privilege escalation risk)")

        # Path quoting
        self.assertIn('`"$Pythonw`"', ps1_content)
        self.assertIn('`"$OmnibarScript`"', ps1_content)

        bat_content = bat_path.read_text(encoding="utf-8")
        self.assertIn('"%~dp0setup_autostart.ps1"', bat_content)
        self.assertIn('"%~dp0corepulse\\omnibar.py"', bat_content)

        # Safe execution of -Status
        if sys.platform != "win32":
            return
        proc = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-File", str(ps1_path), "-Status"],
            capture_output=True,
            text=True
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Autostart Registration Status:", proc.stdout)


if __name__ == "__main__":
    unittest.main()
