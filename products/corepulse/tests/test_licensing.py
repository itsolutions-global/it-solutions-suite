"""
CorePulse Cryptographic Licensing Engine & Tier Entitlements Test Suite
Automated unit, security, persistence, and CLI integration tests for Sprint 11.
Zero external dependencies. Runs on standard Python 3.8+.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

# Setup sys.path
TEST_DIR = Path(__file__).resolve().parent
COREPULSE_DIR = TEST_DIR.parent
PRODUCTS_DIR = COREPULSE_DIR.parent

if str(COREPULSE_DIR) not in sys.path:
    sys.path.insert(0, str(COREPULSE_DIR))
if str(PRODUCTS_DIR) not in sys.path:
    sys.path.insert(0, str(PRODUCTS_DIR))

from corepulse.config import TIER_FEATURE_GATES
from corepulse.licensing import (
    LicenseEngine,
    generate_license_key,
    verify_license_key,
    activate_license_key,
    get_active_license,
    default_engine
)
from corepulse.database_sqlite import Database as SQLiteDatabase
from corepulse.database import Database as JSONDatabase


class TestCorePulseLicensing(unittest.TestCase):
    """Exhaustive test suite for CorePulse Cryptographic Licensing Engine."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sqlite_path = Path(self.temp_dir.name) / "test_licensing.sqlite3"
        self.json_path = Path(self.temp_dir.name) / "test_store.json"
        self.engine = LicenseEngine()

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_01_tier_feature_gates_structure(self):
        """Validates open-core tier structure and unmetered starter tier."""
        starter = TIER_FEATURE_GATES["starter"]
        self.assertEqual(starter["price_monthly"], 0)
        self.assertEqual(starter["max_tasks"], -1)
        self.assertEqual(starter["max_habits"], -1)
        self.assertEqual(starter["max_workflows_per_day"], -1)
        self.assertFalse(starter["cloud_sync"])
        self.assertFalse(starter["team_workspaces"])
        self.assertFalse(starter["central_audit_fleet"])

        pro = TIER_FEATURE_GATES["pro"]
        self.assertEqual(pro["price_monthly"], 9.99)
        self.assertTrue(pro["cloud_sync"])
        self.assertFalse(pro["team_workspaces"])

        team = TIER_FEATURE_GATES["team"]
        self.assertEqual(team["price_monthly"], 19)
        self.assertEqual(team["seats"], 5)
        self.assertTrue(team["team_workspaces"])
        self.assertFalse(team["central_audit_fleet"])

        enterprise = TIER_FEATURE_GATES["enterprise"]
        self.assertEqual(enterprise["price_monthly"], 199)
        self.assertEqual(enterprise["seats"], -1)
        self.assertTrue(enterprise["cloud_sync"])
        self.assertTrue(enterprise["team_workspaces"])
        self.assertTrue(enterprise["central_audit_fleet"])
        self.assertTrue(enterprise["dedicated_sla"])

    def test_02_generate_license_keys_all_tiers(self):
        """Validates key generation format for all four tiers."""
        for tier in ["starter", "pro", "team", "enterprise"]:
            key = self.engine.generate_license_key(
                tier=tier,
                customer_name=f"User {tier}",
                organization="Test Corp",
                days_valid=30,
                seats=5 if tier == "team" else None
            )
            self.assertTrue(key.startswith(f"CP-{tier.upper()}-"))
            parts = key.split("-")
            self.assertEqual(len(parts), 4)  # CP, TIER, PAYLOAD, SIG
            self.assertEqual(parts[0], "CP")
            self.assertEqual(parts[1], tier.upper())
            self.assertEqual(len(parts[3]), 32)  # 32-char hex HMAC

    def test_03_verify_valid_license(self):
        """Verifies signature authenticity and payload integrity of valid keys."""
        key = self.engine.generate_license_key(
            tier="enterprise",
            customer_name="Alice Smith",
            organization="Apex Financial",
            days_valid=90,
            seats=-1
        )
        res = self.engine.verify_license_key(key)
        self.assertTrue(res["valid"])
        self.assertIsNone(res["error"])
        self.assertEqual(res["tier"], "enterprise")
        self.assertEqual(res["payload"]["sub"], "Alice Smith")
        self.assertEqual(res["payload"]["org"], "Apex Financial")
        self.assertEqual(res["payload"]["seats"], -1)

    def test_04_tampering_payload_detection(self):
        """Detects tampering when payload base64 is modified."""
        key = self.engine.generate_license_key(tier="pro")
        parts = key.split("-")
        # Flip a character in base64 payload
        bad_payload = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
        tampered_key = f"{parts[0]}-{parts[1]}-{bad_payload}-{parts[3]}"

        res = self.engine.verify_license_key(tampered_key)
        self.assertFalse(res["valid"])
        self.assertIn("tampered", res["error"].lower())

    def test_05_tampering_tier_prefix_detection(self):
        """Detects tampering when tier prefix is escalated without updating signature."""
        key = self.engine.generate_license_key(tier="pro")
        parts = key.split("-")
        tampered_key = f"CP-ENTERPRISE-{parts[2]}-{parts[3]}"

        res = self.engine.verify_license_key(tampered_key)
        self.assertFalse(res["valid"])
        self.assertIn("tampered", res["error"].lower())

    def test_06_tampering_signature_detection(self):
        """Detects tampering when HMAC signature characters are corrupted."""
        key = self.engine.generate_license_key(tier="team")
        parts = key.split("-")
        bad_sig = ("0" if parts[3][-1] != "0" else "1") + parts[3][:-1]
        tampered_key = f"{parts[0]}-{parts[1]}-{parts[2]}-{bad_sig}"

        res = self.engine.verify_license_key(tampered_key)
        self.assertFalse(res["valid"])
        self.assertIn("signature mismatch", res["error"].lower())

    def test_07_expired_license_rejection(self):
        """Rejects license keys whose expiration date is in the past."""
        expired_key = self.engine.generate_license_key(
            tier="pro",
            days_valid=-10  # Expired 10 days ago
        )
        res = self.engine.verify_license_key(expired_key)
        self.assertFalse(res["valid"])
        self.assertIn("expired", res["error"].lower())

    def test_08_invalid_format_keys(self):
        """Rejects malformed keys gracefully without unhandled exceptions."""
        malformed_keys = [
            "",
            "NOT-A-KEY",
            "CP-PRO",
            "CP-PRO-onlytwoparts",
            "XX-PRO-payload-signature",
            "CP-INVALIDTIER-payload-signature"
        ]
        for key in malformed_keys:
            res = self.engine.verify_license_key(key)
            self.assertFalse(res["valid"])
            self.assertIsNotNone(res["error"])

    def test_09_custom_salt_secret(self):
        """Rejects keys generated with a different secret salt."""
        key = self.engine.generate_license_key(tier="pro", secret="secret-A")
        res_fail = self.engine.verify_license_key(key, secret="secret-B")
        self.assertFalse(res_fail["valid"])

        res_ok = self.engine.verify_license_key(key, secret="secret-A")
        self.assertTrue(res_ok["valid"])

    def test_10_activate_license_updates_dual_persistence(self):
        """Validates that activation synchronizes SQLite and JSON persistence."""
        test_sqlite = SQLiteDatabase(self.sqlite_path)
        test_json = JSONDatabase(self.json_path)

        key = self.engine.generate_license_key(
            tier="enterprise",
            customer_name="Global Enterprise Inc",
            organization="Fortune 500",
            days_valid=365
        )

        with patch("corepulse.database_sqlite.sqlite_db", test_sqlite), \
             patch("corepulse.database.db", test_json):
            res = activate_license_key(key)
            self.assertTrue(res["success"])
            self.assertEqual(res["tier"], "enterprise")
            self.assertEqual(res["customer_name"], "Global Enterprise Inc")

            # Validate SQLite
            sub_sql = test_sqlite.get_subscription()
            self.assertEqual(sub_sql["tier"], "enterprise")
            self.assertEqual(sub_sql["license_key"], key)
            self.assertEqual(sub_sql["organization"], "Fortune 500")

            # Validate JSON
            sub_json = test_json.get_subscription()
            self.assertEqual(sub_json["tier"], "enterprise")
            self.assertEqual(sub_json["license_key"], key)
            self.assertEqual(sub_json["customer_name"], "Global Enterprise Inc")

        test_sqlite.close()

    def test_11_cli_license_subcommands(self):
        """Validates CLI license subcommands (generate-demo, activate, status)."""
        cli_py = PRODUCTS_DIR / "cli.py"

        # 1. Generate demo key
        proc_gen = subprocess.run(
            [sys.executable, str(cli_py), "license", "generate-demo", "pro", "--customer", "Test Corp", "--json"],
            capture_output=True,
            text=True
        )
        self.assertEqual(proc_gen.returncode, 0)
        data_gen = json.loads(proc_gen.stdout)
        self.assertEqual(data_gen["tier"], "pro")
        demo_key = data_gen["license_key"]
        self.assertTrue(demo_key.startswith("CP-PRO-"))

        # 2. Activate generated key
        proc_act = subprocess.run(
            [sys.executable, str(cli_py), "license", "activate", demo_key, "--json"],
            capture_output=True,
            text=True
        )
        self.assertEqual(proc_act.returncode, 0)
        data_act = json.loads(proc_act.stdout)
        self.assertTrue(data_act["success"])
        self.assertEqual(data_act["tier"], "pro")

        # 3. Check status
        proc_stat = subprocess.run(
            [sys.executable, str(cli_py), "license", "status", "--json"],
            capture_output=True,
            text=True
        )
        self.assertEqual(proc_stat.returncode, 0)
        data_stat = json.loads(proc_stat.stdout)
        self.assertEqual(data_stat["tier"], "pro")
        self.assertEqual(data_stat["license_key"], demo_key)

        # 4. Activate invalid key
        proc_bad = subprocess.run(
            [sys.executable, str(cli_py), "license", "activate", "CP-PRO-corrupted-sig", "--json"],
            capture_output=True,
            text=True
        )
        self.assertNotEqual(proc_bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()
