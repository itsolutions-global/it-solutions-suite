"""
NexusShield Core Security Scanner
Orchestrates secret leak scanning, dependency vulnerability auditing, and compliance scoring.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from nexusshield.dependencies import DependencyScanner
from nexusshield.scorer import compute_security_score
from nexusshield.secrets import SecretScanner

# Directories ignored during recursive scanning
IGNORED_DIRS: Set[str] = {
    ".git", ".hg", ".svn", "node_modules", "venv", ".venv", "env",
    "__pycache__", ".pytest_cache", "dist", "build", ".egg-info",
    ".idea", ".vscode", "coverage", ".next", ".nuxt", "chrome_copilot_profile"
}

# Binary and non-code file extensions ignored during scanning
IGNORED_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".wav",
    ".zip", ".tar", ".gz", ".7z", ".pdf", ".exe", ".dll", ".so",
    ".dylib", ".pyc", ".pyo", ".sqlite3", ".db", ".bin"
}


class NexusScanner:
    """Enterprise-grade local-first code security and vulnerability scanner."""

    def __init__(self, entropy_threshold: float = 4.6):
        self.secret_scanner = SecretScanner(entropy_threshold=entropy_threshold)
        self.dep_scanner = DependencyScanner()

    def scan_file(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """Scans a single file for credentials or manifest vulnerabilities."""
        p = Path(file_path)
        if not p.is_file():
            return []

        filename = p.name.lower()
        if p.suffix.lower() in IGNORED_EXTENSIONS:
            return []

        # Avoid scanning files > 10MB
        try:
            if p.stat().st_size > 10 * 1024 * 1024:
                return []
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        findings = []

        # 1. Dependency manifest scanning
        if filename in ("requirements.txt", "package.json") or filename.endswith(".txt") and "requirements" in filename:
            dep_findings = self.dep_scanner.scan_manifest(str(p), content)
            findings.extend(dep_findings)

        # 2. Secret leak scanning
        secret_findings = self.secret_scanner.scan_content(content, file_path=str(p))
        findings.extend(secret_findings)

        return findings

    def scan_content(self, content: str, filename: str = "inline_snippet.py") -> Dict[str, Any]:
        """Scans in-memory source content or code snippets."""
        start_time = time.time()
        findings = []

        if filename.endswith("requirements.txt") or filename.endswith("package.json"):
            dep_findings = self.dep_scanner.scan_manifest(filename, content)
            findings.extend(dep_findings)

        secret_findings = self.secret_scanner.scan_content(content, file_path=filename)
        findings.extend(secret_findings)

        score_data = compute_security_score(findings)
        elapsed_sec = round(time.time() - start_time, 4)
        loc = len(content.splitlines())

        return {
            "target": filename,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": elapsed_sec,
            "files_scanned": 1,
            "lines_scanned": loc,
            "findings": findings,
            **score_data
        }

    def scan_directory(self, target_path: Union[str, Path], recursive: bool = True) -> Dict[str, Any]:
        """Recursively audits an entire directory or repository."""
        start_time = time.time()
        base = Path(target_path).resolve()

        if not base.exists():
            raise FileNotFoundError(f"Target path '{target_path}' does not exist.")

        all_findings: List[Dict[str, Any]] = []
        files_scanned = 0
        total_loc = 0

        # Load .nexusignore rules if present (check target and parent root)
        ignore_patterns: Set[str] = set()
        for candidate, prefix_to_strip in ((base / ".nexusignore", ""), (base.parent / ".nexusignore", f"{base.name}/")):
            if candidate.exists():
                for line in candidate.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        norm = line.replace("\\", "/").strip("/")
                        ignore_patterns.add(norm)
                        if prefix_to_strip and norm.startswith(prefix_to_strip):
                            ignore_patterns.add(norm[len(prefix_to_strip):])

        if base.is_file():
            files_to_scan = [base]
        else:
            files_to_scan = []
            if recursive:
                for root, dirs, files in os.walk(base):
                    # Filter out ignored directories in-place to prevent traversing them
                    dirs[:] = [
                        d for d in dirs
                        if d not in IGNORED_DIRS
                        and not d.startswith(".")
                        and d not in ignore_patterns
                        and (Path(root).relative_to(base) / d).as_posix() not in ignore_patterns
                    ]
                    for f in files:
                        p = Path(root) / f
                        if p.suffix.lower() not in IGNORED_EXTENSIONS:
                            rel_posix = p.relative_to(base).as_posix()
                            if not any(rel_posix == pat or rel_posix.startswith(pat + "/") or f == pat for pat in ignore_patterns):
                                files_to_scan.append(p)
            else:
                for item in base.iterdir():
                    if item.is_file() and item.suffix.lower() not in IGNORED_EXTENSIONS:
                        if item.name not in ignore_patterns:
                            files_to_scan.append(item)

        for p in files_to_scan:
            try:
                # Basic size guard
                if p.stat().st_size > 10 * 1024 * 1024:
                    continue
                content = p.read_text(encoding="utf-8", errors="ignore")
                total_loc += len(content.splitlines())
                files_scanned += 1

                rel_path = str(p.relative_to(base)) if base.is_dir() else p.name
                filename = p.name.lower()

                # Dependency manifest check
                if filename in ("requirements.txt", "package.json") or (filename.endswith(".txt") and "requirements" in filename):
                    all_findings.extend(self.dep_scanner.scan_manifest(rel_path, content))

                # Secret scanning
                all_findings.extend(self.secret_scanner.scan_content(content, file_path=rel_path))

            except Exception:
                continue

        elapsed_sec = round(time.time() - start_time, 4)
        score_data = compute_security_score(all_findings)

        return {
            "target": str(base),
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": elapsed_sec,
            "files_scanned": files_scanned,
            "lines_scanned": total_loc,
            "findings": all_findings,
            **score_data
        }

    def scan_git_history(self, repo_path: Union[str, Path], max_commits: int = 50) -> Dict[str, Any]:
        """Scans Git commit history ('git log -p') for historical leaked secrets."""
        from nexusshield.advanced import GitHistoryScanner
        hist = GitHistoryScanner(entropy_threshold=self.secret_scanner.entropy_threshold)
        return hist.scan_git_history(repo_path, max_commits=max_commits)

    def generate_sbom(self, target_path: Union[str, Path]) -> Dict[str, Any]:
        """Generates a CycloneDX v1.5 Software Bill of Materials (SBOM) for the target directory."""
        from nexusshield.advanced import SBOMGenerator
        gen = SBOMGenerator()
        return gen.generate_sbom(target_path)

    def remediate_file(self, file_path: Union[str, Path], env_file_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """Automatically extracts hardcoded secrets from a file into .env and rewrites source code."""
        from nexusshield.advanced import SecretRemediator
        rem = SecretRemediator(entropy_threshold=self.secret_scanner.entropy_threshold)
        return rem.remediate_file(file_path, env_file_path=env_file_path)


# Global convenience scanner instance
scanner = NexusScanner()
