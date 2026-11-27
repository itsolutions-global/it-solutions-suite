"""
Unit tests for NexusShield Advanced Capabilities:
  - GitHistoryScanner ('scan-history')
  - SBOMGenerator ('sbom')
  - SecretRemediator ('remediate')
"""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from nexusshield.scanner import NexusScanner


class TestNexusShieldAdvanced(unittest.TestCase):
    """Tests Git history time-machine scanning, CycloneDX SBOM generation, and 1-click secret remediation."""

    def test_01_cyclonedx_sbom_generation(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            proj = Path(tmpdir)
            (proj / "requirements.txt").write_text("requests==2.30.0\nflask==2.3.0\n", encoding="utf-8")
            (proj / "package.json").write_text('{"dependencies": {"lodash": "^4.17.15", "express": "4.19.2"}}', encoding="utf-8")

            scanner = NexusScanner()
            sbom = scanner.generate_sbom(proj)
            self.assertEqual(sbom["bomFormat"], "CycloneDX")
            self.assertEqual(sbom["specVersion"], "1.5")
            self.assertEqual(sbom["summary"]["total_components"], 4)
            # requests 2.30.0 and lodash 4.17.15 have known advisories
            self.assertGreaterEqual(sbom["summary"]["total_vulnerabilities"], 2)

    def test_02_secret_auto_remediation(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            proj = Path(tmpdir)
            src_file = proj / "config_sample.py"
            fake_aws = "AKIA" + "1234567890ABCDEF"  # nexus-ignore: secret-scan
            src_file.write_text(f'AWS_ACCESS_KEY = "{fake_aws}"\nDEBUG = True\n', encoding="utf-8")

            scanner = NexusScanner()
            res = scanner.remediate_file(src_file)
            self.assertEqual(res["status"], "remediated")
            self.assertEqual(res["remediated_count"], 1)

            rewritten = src_file.read_text(encoding="utf-8")
            self.assertNotIn(fake_aws, rewritten)
            self.assertIn('os.environ.get("AWS_ACCESS_KEY"', rewritten)

            env_content = (proj / ".env").read_text(encoding="utf-8")
            self.assertIn(f'AWS_ACCESS_KEY="{fake_aws}"', env_content)

    def test_03_git_history_time_machine_scanner(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            repo = Path(tmpdir)
            subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, check=False)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(repo), capture_output=True, check=False)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(repo), capture_output=True, check=False)

            app_py = repo / "app.py"
            leaked_key = "AKIA" + "9988776655443322"  # nexus-ignore: secret-scan
            # Commit 1: accidentally commit secret
            app_py.write_text(f'KEY = "{leaked_key}"\n', encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=str(repo), capture_output=True, check=False)
            subprocess.run(["git", "commit", "-m", "Initial commit with key"], cwd=str(repo), capture_output=True, check=False)

            # Commit 2: delete secret in working tree (still in git history!)
            app_py.write_text('KEY = os.getenv("KEY")\n', encoding="utf-8")
            subprocess.run(["git", "add", "app.py"], cwd=str(repo), capture_output=True, check=False)
            subprocess.run(["git", "commit", "-m", "Removed key from file"], cwd=str(repo), capture_output=True, check=False)

            scanner = NexusScanner()
            # Working tree scan should be 100% clean
            worktree_res = scanner.scan_directory(repo)
            self.assertEqual(len(worktree_res["findings"]), 0)

            # Git history time-machine scan should catch the historical leak in Commit 1!
            hist_res = scanner.scan_git_history(repo, max_commits=10)
            self.assertGreaterEqual(hist_res["commits_scanned"], 2)
            self.assertEqual(len(hist_res["findings"]), 1)
            self.assertEqual(hist_res["findings"][0]["id"], "SEC-AWS-KEY")

    def test_04_go_mod_and_cargo_toml_sbom(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            proj = Path(tmpdir)
            (proj / "go.mod").write_text(
                "module github.com/acme/service\n\ngo 1.22\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.9.1\n\tgolang.org/x/crypto v0.21.0 // indirect\n)\n",
                encoding="utf-8",
            )
            (proj / "Cargo.toml").write_text(
                '[package]\nname = "demo"\nversion = "0.1.0"\n\n[dependencies]\nserde = { version = "1.0.197", features = ["derive"] }\ntokio = "1.36.0"\n',
                encoding="utf-8",
            )
            scanner = NexusScanner()
            sbom = scanner.generate_sbom(proj)
            purls = [c["purl"] for c in sbom["components"]]
            self.assertIn("pkg:golang/github.com/gin-gonic/gin@1.9.1", purls)
            self.assertIn("pkg:golang/golang.org/x/crypto@0.21.0", purls)
            self.assertIn("pkg:cargo/serde@1.0.197", purls)
            self.assertIn("pkg:cargo/tokio@1.36.0", purls)


if __name__ == "__main__":
    unittest.main()
