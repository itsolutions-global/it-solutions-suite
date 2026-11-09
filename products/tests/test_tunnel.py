"""
Unit Test Suite: Public Cloud Tunneling Engine
Validates PublicTunnelManager, binary detection, LAN demo sharing, and CLI integration.
"""

import json
import socket
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PRODUCTS_DIR = Path(__file__).resolve().parent.parent
if str(PRODUCTS_DIR) not in sys.path:
    sys.path.insert(0, str(PRODUCTS_DIR))

from tunnel import PublicTunnelManager


class TestPublicTunnelManager(unittest.TestCase):
    """Test suite for CorePulse public cloud tunneling engine."""

    def setUp(self):
        self.manager = PublicTunnelManager(target_port=8080, target_host="127.0.0.1")

    def tearDown(self):
        self.manager.stop()

    def test_01_get_lan_ip(self):
        """Validates that a valid IPv4 address is detected for local network sharing."""
        lan_ip = self.manager.get_lan_ip()
        self.assertIsInstance(lan_ip, str)
        # Verify valid IP format
        octets = lan_ip.split(".")
        self.assertEqual(len(octets), 4)
        for octet in octets:
            self.assertTrue(0 <= int(octet) <= 255)

    def test_02_lan_demo_mode(self):
        """Validates zero-dependency LAN demo sharing fallback."""
        info = self.manager.start_lan_demo_mode()
        self.assertEqual(info["provider"], "lan_sharing")
        self.assertEqual(info["port"], 8080)
        self.assertTrue(info["lan_url"].startswith("http://"))
        self.assertIn(":8080", info["lan_url"])
        self.assertEqual(info["local_url"], "http://127.0.0.1:8080")

    def test_03_run_auto_fallback(self):
        """Validates that run() automatically falls back to LAN mode when no binaries exist."""
        result = self.manager.run(provider="lan")
        self.assertTrue(result["success"])
        self.assertEqual(result["provider"], "lan_sharing")
        self.assertIsNotNone(result["public_url"])
        self.assertIn(":8080", result["public_url"])

    @patch("subprocess.Popen")
    def test_04_mock_cloudflare_tunnel(self, mock_popen):
        """Validates parsing of Cloudflare trycloudflare.com URL from subprocess output."""
        mock_process = MagicMock()
        mock_process.stderr.readline.side_effect = [
            "2026-11-04 INF Starting tunnel\n",
            "2026-11-04 INF +-------------------------------------------------------+\n",
            "2026-11-04 INF |  Your quick Tunnel has been created! Visit it at:   |\n",
            "2026-11-04 INF |  https://executive-pulse-demo.trycloudflare.com       |\n",
            "2026-11-04 INF +-------------------------------------------------------+\n",
        ]
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        fake_bin = Path("mock/cloudflared.exe")
        url = self.manager.start_cloudflare_tunnel(binary_path=fake_bin)
        self.assertEqual(url, "https://executive-pulse-demo.trycloudflare.com")
        self.assertEqual(self.manager.provider_active, "cloudflare")

    def test_05_cli_tunnel_integration(self):
        """Validates it-solutions pulse --tunnel --tunnel-provider lan --json output."""
        cli_py = PRODUCTS_DIR / "cli.py"
        cmd = [sys.executable, str(cli_py), "pulse", "--tunnel", "--tunnel-provider", "lan", "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("provider"), "lan_sharing")
        self.assertIn(":8080", data.get("public_url", ""))


if __name__ == "__main__":
    unittest.main()
