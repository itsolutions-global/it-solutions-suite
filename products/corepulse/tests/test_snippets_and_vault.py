"""
Unit tests for CorePulse Snippet Vault, Dynamic Variable Expander, and Markdown Vault Exporter.
"""

import os
from pathlib import Path
import sys
import tempfile
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from corepulse.snippets import SnippetVault, export_markdown_vault
from omnibar import OmnibarRouter


class TestCorePulseSnippetsAndVault(unittest.TestCase):
    """Validates SnippetVault CRUD, dynamic variable expansion, Omnibar routing, and Markdown export."""

    def test_01_snippet_vault_crud_and_expansion(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            vault_file = Path(tmpdir) / "snippets.json"
            vault = SnippetVault(storage_path=vault_file)

            # Verify default snippets are seeded
            initial = vault.list_snippets()
            self.assertGreaterEqual(len(initial), 4)

            # Create custom snippet with dynamic variables
            created = vault.save_snippet({
                "trigger": ";;deploy-note",
                "title": "Deployment Release Note",
                "category": "DevOps",
                "content": "Release on {{date}} from branch {{git_branch}} for {{env}}.",
                "tags": ["release", "devops"]
            })
            self.assertEqual(created["trigger"], ";;deploy-note")

            # Expand with custom variable
            res = vault.expand_snippet(";;deploy-note", custom_vars={"env": "production"})
            self.assertIsNotNone(res)
            self.assertIn("production", res["expanded_text"])
            self.assertNotIn("{{date}}", res["expanded_text"])
            self.assertEqual(res["snippet"]["usage_count"], 1)

            # Delete snippet
            self.assertTrue(vault.delete_snippet(created["id"]))
            self.assertIsNone(vault.get_snippet(";;deploy-note"))

    def test_02_markdown_vault_export(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            vault_dir = Path(tmpdir) / "md_vault"
            sample_tasks = [
                {"title": "Ship Snippet Expander", "type": "task", "priority": "high", "completed": False, "due_date": "Today", "tags": ["corepulse"]},
                {"title": "Zero-Trust Code Audit", "type": "habit", "completed": True, "streak_days": 12}
            ]
            sample_snippets = [
                {"trigger": ";;standup", "title": "Daily Standup", "category": "Engineering", "content": "Standup {{date}}", "usage_count": 3}
            ]
            res = export_markdown_vault(sample_tasks, sample_snippets, vault_dir=vault_dir)
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["files_count"], 4)
            self.assertTrue((vault_dir / "Tasks.md").exists())
            self.assertTrue((vault_dir / "Habits.md").exists())
            self.assertTrue((vault_dir / "Snippets.md").exists())

    def test_03_omnibar_snippet_routing(self):
        os.environ["COREPULSE_TEST_MODE"] = "1"
        router = OmnibarRouter()
        mode, payload = router.detect_mode(";;standup")
        self.assertEqual(mode, "snippet")
        self.assertEqual(payload, ";;standup")

        res = router.parse_and_route(";;standup")
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "snippet")
        self.assertIn("Daily Standup", res["data"]["expanded_text"])


if __name__ == "__main__":
    unittest.main()
