"""
Automated Verification Suite for Manifest V3 Chrome Extension
Validates manifest structure, permissions, 5-engine studio tabs, context menus, and Critical Law compliance.
"""

import json
import re
import unittest
from pathlib import Path

EXT_DIR = Path(__file__).resolve().parent


class TestChromeExtension(unittest.TestCase):
    """Test suite verifying Manifest V3 Chrome Extension integrity."""

    def test_01_manifest_v3_structure(self):
        """Validates manifest.json conforms strictly to Chrome Manifest V3."""
        manifest_path = EXT_DIR / "manifest.json"
        self.assertTrue(manifest_path.exists(), "manifest.json not found")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        self.assertEqual(manifest.get("manifest_version"), 3)
        self.assertTrue(manifest.get("name"))
        self.assertTrue(manifest.get("version"))

        # Verify required permissions
        permissions = set(manifest.get("permissions", []))
        required = {"contextMenus", "storage", "activeTab", "sidePanel", "scripting"}
        self.assertTrue(required.issubset(permissions), f"Missing required permissions: {required - permissions}")

        # Verify entry points
        self.assertEqual(manifest.get("background", {}).get("service_worker"), "background.js")
        self.assertEqual(manifest.get("action", {}).get("default_popup"), "popup.html")
        self.assertEqual(manifest.get("side_panel", {}).get("default_path"), "popup.html")

        # Verify icons exist on disk
        for icon_key, icon_file in manifest.get("icons", {}).items():
            icon_path = EXT_DIR / icon_file
            self.assertTrue(icon_path.exists(), f"Icon file {icon_file} not found on disk")

    def test_02_critical_law_zero_pricing_tables(self):
        """CRITICAL LAW: Asserts zero pricing tables, zero 'Pro Tier' badges, and zero hints of payment."""
        prohibited_patterns = [
            r"\bpricing\b",
            r"\$\d+\s*\/\s*mo\b",
            r"\bupgrade\s+to\b",
            r"\bpro\s+tier\b",
            r"\benterprise\s+tier\b",
            r"\bbilling\s+plan\b",
            r"\bpayment\s+gateway\b"
        ]

        files_to_audit = ["popup.html", "popup.js", "styles.css", "background.js"]
        for fname in files_to_audit:
            fpath = EXT_DIR / fname
            self.assertTrue(fpath.exists(), f"{fname} not found")
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().lower()
                for pat in prohibited_patterns:
                    match = re.search(pat, content)
                    self.assertIsNone(
                        match,
                        f"Critical Law Violation: Found '{match.group(0) if match else ''}' in {fname}"
                    )

    def test_03_popup_contains_all_5_engines(self):
        """Verifies popup.html contains active panels for all 5 commercial engines."""
        popup_path = EXT_DIR / "popup.html"
        with open(popup_path, "r", encoding="utf-8") as f:
            html = f.read()

        required_panels = [
            "panel-clauseguard",
            "panel-docupulse",
            "panel-echostream",
            "panel-nexusshield",
            "panel-corepulse"
        ]
        for panel in required_panels:
            self.assertIn(f'id="{panel}"', html, f"Missing engine panel: {panel}")

        # Verify CorePulse quick capture input is present
        self.assertIn('id="cpTaskInput"', html)
        self.assertIn('id="cpSnippetGrid"', html)
        self.assertIn('id="cpTaskList"', html)

    def test_04_background_registers_all_context_menus(self):
        """Verifies background.js registers context menu items for right-click on webpages."""
        bg_path = EXT_DIR / "background.js"
        with open(bg_path, "r", encoding="utf-8") as f:
            bg_code = f.read()

        required_menu_ids = ["its_root", "clg_scan", "doc_extract", "echo_notes", "nxs_scan", "cp_task"]
        for menu_id in required_menu_ids:
            self.assertIn(f'"{menu_id}"', bg_code, f"Missing context menu id: {menu_id}")

        # Verify sidepanel open hook
        self.assertIn("chrome.sidePanel.open", bg_code)

    def test_05_readme_installation_instructions(self):
        """Verifies README.md provides clear Developer Mode installation instructions."""
        readme_path = EXT_DIR / "README.md"
        self.assertTrue(readme_path.exists())
        with open(readme_path, "r", encoding="utf-8") as f:
            readme = f.read()

        self.assertIn("chrome://extensions", readme)
        self.assertIn("Developer mode", readme)
        self.assertIn("Load unpacked", readme)
        self.assertIn("ClauseGuard", readme)
        self.assertIn("DocuPulse", readme)
        self.assertIn("EchoStream", readme)
        self.assertIn("NexusShield", readme)
        self.assertIn("CorePulse", readme)


if __name__ == "__main__":
    unittest.main()
