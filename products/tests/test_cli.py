"""
Unified Corporate CLI Harness Automated Tests
Validates it-solutions CLI commands, multi-product orchestration, and installer scripts.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_TEST_TMP_DIR = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
os.environ.setdefault("COREPULSE_TEST_MODE", "1")
os.environ.setdefault("COREPULSE_DATA_DIR", _TEST_TMP_DIR.name)

BASE_DIR = Path(__file__).resolve().parent.parent
CLI_PATH = BASE_DIR / "cli.py"


class CorporateCLITests(unittest.TestCase):
    """Test suite for unified corporate CLI harness."""

    def test_01_version_command(self):
        """Validates it-solutions version command output."""
        cmd = [sys.executable, str(CLI_PATH), "version"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Corporate Suite Version", proc.stdout)
        self.assertIn("CorePulse", proc.stdout)
        self.assertIn("NexusShield", proc.stdout)
        self.assertIn("EchoStream", proc.stdout)

    def test_02_health_command(self):
        """Validates it-solutions health audit across all corporate products."""
        cmd = [sys.executable, str(CLI_PATH), "health"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("CORPORATE INFRASTRUCTURE HEALTH AUDIT", proc.stdout)
        self.assertIn("CorePulse v1.0", proc.stdout)
        self.assertIn("NexusShield v1.0", proc.stdout)
        self.assertIn("EchoStream v1.0", proc.stdout)
        self.assertIn("ALL SYSTEMS OPTIMAL", proc.stdout)

    def test_03_shield_scan_integration(self):
        """Validates it-solutions shield scan command delegating to NexusShield."""
        target_dir = BASE_DIR / "nexusshield" / "nexusshield"
        cmd = [sys.executable, str(CLI_PATH), "shield", "scan", str(target_dir), "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0)

        # Parse JSON output
        result = json.loads(proc.stdout)
        self.assertIn("score", result)
        self.assertIn("grade", result)
        self.assertIn("compliance", result)

    def test_04_installer_artifacts_presence(self):
        """Validates that installer scripts and distribution wrappers exist."""
        self.assertTrue((BASE_DIR / "install.ps1").exists(), "install.ps1 must exist")
        self.assertTrue((BASE_DIR / "install.sh").exists(), "install.sh must exist")
        self.assertTrue((BASE_DIR / "it-solutions.bat").exists(), "it-solutions.bat must exist")
        self.assertTrue((BASE_DIR / "it-solutions").exists(), "it-solutions bash wrapper must exist")

    def test_05_pulse_companion_integration(self):
        """Validates it-solutions pulse --companion integration."""
        cmd = [sys.executable, str(CLI_PATH), "pulse", "--companion", "--dry-run"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Habit Consistency & Streak Status", proc.stdout)

    def test_06_stream_scan_integration(self):
        """Validates it-solutions stream scan voice DLP redaction."""
        spoken = "Our staging API key was sk-proj-98723418726354128937123987123987 for authentication."
        cmd = [sys.executable, str(CLI_PATH), "stream", "scan", spoken, "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertFalse(data.get("is_clean"))
        self.assertEqual(data.get("incidents_count"), 1)
        self.assertIn("[REDACTED_SECRET: OpenAI API Key]", data.get("redacted_text", ""))

    def test_07_stream_parse_integration(self):
        """Validates it-solutions stream parse meeting and thought stream extraction."""
        stream_text = "Need to review PR-104 by Thursday !p1 #security"
        cmd = [sys.executable, str(CLI_PATH), "stream", "parse", stream_text, "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIn("parsed_structure", data)
        action_items = data["parsed_structure"].get("action_items", [])
        self.assertTrue(len(action_items) >= 1)
        self.assertEqual(action_items[0]["priority"], "high")

    def test_08_stream_demo_integration(self):
        """Validates it-solutions stream demo execution."""
        cmd = [sys.executable, str(CLI_PATH), "stream", "demo"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Starting Live EchoStream Demonstration", proc.stdout)
        self.assertIn("ECHOSTREAM COGNITIVE INTAKE & TRIAGE BRIEF", proc.stdout)
        self.assertIn("COREPULSE DISPATCH", proc.stdout)

    def test_09_stream_watch_integration(self):
        """Validates it-solutions stream watch --once autonomous ingestion sweep."""
        import tempfile
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            watch_dir = Path(tmpdir) / "transcripts"
            watch_dir.mkdir(parents=True, exist_ok=True)
            memo_file = watch_dir / "quick_memo.txt"
            memo_file.write_text("[Marcus] We must ship the client contract by Friday !p1 #sales", encoding="utf-8")

            cmd = [sys.executable, str(CLI_PATH), "stream", "watch", str(watch_dir), "--once", "--json"]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            self.assertEqual(data.get("processed_count"), 1)
            self.assertGreaterEqual(data["receipts"][0].get("tasks_extracted", 0), 1)

    def test_10_pulse_omnibar_command(self):
        """Validates it-solutions pulse -c <command> --json Omnibar command dispatch."""
        cmd = [sys.executable, str(CLI_PATH), "pulse", "-c", "status", "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("mode"), "status")
        self.assertIn("CorePulse Vitals", data.get("summary", ""))


    def test_11_license_cli_integration(self):
        """Validates it-solutions license generate-demo, activate, and status subcommands."""
        # 1. Generate demo license key
        cmd_gen = [sys.executable, str(CLI_PATH), "license", "generate-demo", "team", "--customer", "CLI Tester", "--org", "QA Corp", "--json"]
        proc_gen = subprocess.run(cmd_gen, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc_gen.returncode, 0)
        data_gen = json.loads(proc_gen.stdout)
        self.assertEqual(data_gen["tier"], "team")
        key = data_gen["license_key"]
        self.assertTrue(key.startswith("CP-TEAM-"))

        # 2. Activate generated key
        cmd_act = [sys.executable, str(CLI_PATH), "license", "activate", key, "--json"]
        proc_act = subprocess.run(cmd_act, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc_act.returncode, 0)
        data_act = json.loads(proc_act.stdout)
        self.assertTrue(data_act["success"])
        self.assertEqual(data_act["tier"], "team")

        # 3. Check status
        cmd_stat = [sys.executable, str(CLI_PATH), "license", "status", "--json"]
        proc_stat = subprocess.run(cmd_stat, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc_stat.returncode, 0)
        data_stat = json.loads(proc_stat.stdout)
        self.assertEqual(data_stat["tier"], "team")
        self.assertEqual(data_stat["customer_name"], "CLI Tester")

    def test_12_sync_cli_integration(self):
        """Validates it-solutions sync status and pair subcommands."""
        # 1. it-solutions sync status --json
        cmd_stat = [sys.executable, str(CLI_PATH), "sync", "status", "--json"]
        proc_stat = subprocess.run(cmd_stat, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc_stat.returncode, 0)
        data_stat = json.loads(proc_stat.stdout)
        self.assertIn("client_id", data_stat)

        # 2. it-solutions sync pair <passphrase> --json
        cmd_pair = [sys.executable, str(CLI_PATH), "sync", "pair", "cli-test-passphrase-2026", "--relay-url", "http://127.0.0.1:8081", "--json"]
        proc_pair = subprocess.run(cmd_pair, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc_pair.returncode, 0)
        data_pair = json.loads(proc_pair.stdout)
        self.assertTrue(data_pair["success"])
        self.assertTrue(data_pair["paired"])

    def test_13_bridge_cli_integration(self):
        """Validates it-solutions bridge status CLI command."""
        cmd = [sys.executable, str(CLI_PATH), "bridge", "status"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("NexusBridge v1.0", proc.stdout)
        self.assertIn("Chrome Binary", proc.stdout)
        self.assertIn("data/browser_profile", proc.stdout)

    def test_14_bridge_v2_cli_integration(self):
        """Validates it-solutions bridge find and bridge capture commands."""
        # 1. bridge find
        cmd_find = [sys.executable, str(CLI_PATH), "bridge", "find"]
        proc_find = subprocess.run(cmd_find, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc_find.returncode, 0)
        self.assertIn("NexusBridge v2.0", proc_find.stdout)
        self.assertIn("HWND", proc_find.stdout)

        # 2. bridge capture
        cmd_cap = [sys.executable, str(CLI_PATH), "bridge", "capture"]
        proc_cap = subprocess.run(cmd_cap, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc_cap.returncode, 0)
        self.assertIn("Physical GDI Window Snapshot Captured", proc_cap.stdout)


if __name__ == "__main__":
    unittest.main()



