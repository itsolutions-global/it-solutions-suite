"""
NexusShield Advanced Enterprise Capabilities (100% Python Standard Library):
  1. GitHistoryScanner ('scan-history'): Time-Machine git log commit diff scanner for historical secret leaks.
  2. SBOMGenerator ('sbom'): CycloneDX v1.5 Software Bill of Materials (SBOM) generator with CVE enrichment.
  3. SecretRemediator ('remediate'): 1-Click automatic secret extraction to .env and source code rewriting.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from nexusshield.dependencies import DependencyScanner, is_version_vulnerable
from nexusshield.scanner import IGNORED_DIRS, IGNORED_EXTENSIONS
from nexusshield.scorer import compute_security_score
from nexusshield.secrets import SecretScanner


class GitHistoryScanner:
    """Scans Git commit history ('git log -p') to detect historical secret leaks."""

    def __init__(self, entropy_threshold: float = 4.6):
        self.secret_scanner = SecretScanner(entropy_threshold=entropy_threshold)

    def scan_git_history(
        self,
        repo_path: Union[str, Path],
        max_commits: int = 50
    ) -> Dict[str, Any]:
        """
        Inspects added lines ('+') across the last `max_commits` git commits in `repo_path`.
        Detects secrets that were committed in the past even if deleted in subsequent commits.
        """
        start_time = time.time()
        base = Path(repo_path).resolve()
        if not base.exists():
            raise FileNotFoundError(f"Repository path '{repo_path}' does not exist.")

        target_dir = base if base.is_dir() else base.parent

        # Load .nexusignore patterns
        ignore_patterns: Set[str] = set()
        for candidate in (target_dir / ".nexusignore", target_dir.parent / ".nexusignore"):
            if candidate.exists():
                for line in candidate.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        ignore_patterns.add(line.replace("\\", "/").strip("/"))

        cmd = [
            "git",
            "log",
            "-p",
            f"-n{int(max_commits)}",
            "--no-color",
            "--pretty=format:__COMMIT__%H|%an|%ad|%s",
            "--date=short"
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(target_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30
            )
        except Exception as ex:
            return {
                "target": str(target_dir),
                "scanned_at": datetime.now(timezone.utc).isoformat(),
                "commits_scanned": 0,
                "findings": [],
                "error": f"Git history execution failed: {ex}",
                **compute_security_score([])
            }

        if proc.returncode != 0:
            return {
                "target": str(target_dir),
                "scanned_at": datetime.now(timezone.utc).isoformat(),
                "commits_scanned": 0,
                "findings": [],
                "error": proc.stderr.strip() or "Not a git repository or git log failed",
                **compute_security_score([])
            }

        findings: List[Dict[str, Any]] = []
        seen_keys: Set[Tuple[str, str, str]] = set()
        commits_scanned = 0
        current_commit = "HEAD"
        current_author = "Unknown"
        current_date = ""
        current_subject = ""
        current_file = ""
        current_line_num = 0
        ignore_next_added_line = False

        for raw_line in proc.stdout.splitlines():
            if raw_line.startswith("__COMMIT__"):
                parts = raw_line[len("__COMMIT__"):].split("|", 3)
                current_commit = parts[0][:12] if len(parts) > 0 else "HEAD"
                current_author = parts[1] if len(parts) > 1 else "Unknown"
                current_date = parts[2] if len(parts) > 2 else ""
                current_subject = parts[3] if len(parts) > 3 else ""
                commits_scanned += 1
                ignore_next_added_line = False
                continue

            if raw_line.startswith("+++ b/"):
                current_file = raw_line[6:].strip()
                current_line_num = 0
                ignore_next_added_line = False
                continue

            if raw_line.startswith("@@ "):
                # Parse hunk header: @@ -old,count +new,count @@
                m = re.search(r"\+(\d+)", raw_line)
                current_line_num = int(m.group(1)) - 1 if m else 0
                ignore_next_added_line = False
                continue

            if raw_line.startswith("+") and not raw_line.startswith("+++"):
                current_line_num += 1
                added_content = raw_line[1:]

                # Skip ignored files or test files in .nexusignore
                if current_file:
                    norm_file = current_file.replace("\\", "/")
                    if any(
                        norm_file == pat
                        or norm_file.startswith(pat + "/")
                        or Path(norm_file).name == pat
                        for pat in ignore_patterns
                    ):
                        continue

                stripped = added_content.strip()
                if stripped.startswith(("#", "//", "/*")) and ("nexus-ignore" in stripped or "nexusshield-ignore" in stripped):
                    ignore_next_added_line = True
                    continue

                if ignore_next_added_line:
                    ignore_next_added_line = False
                    continue

                line_findings = self.secret_scanner.scan_line(
                    added_content,
                    line_number=current_line_num,
                    file_path=current_file or "git-history"
                )
                for f in line_findings:
                    dedup_key = (f["id"], f["redacted_secret"], current_file)
                    if dedup_key in seen_keys:
                        continue
                    seen_keys.add(dedup_key)
                    f["commit"] = current_commit
                    f["author"] = current_author
                    f["commit_date"] = current_date
                    f["commit_subject"] = current_subject
                    f["title"] = f"[Git History {current_commit}] {f['title']}"
                    findings.append(f)

        elapsed_sec = round(time.time() - start_time, 4)
        score_data = compute_security_score(findings)
        return {
            "target": str(target_dir),
            "mode": "git_history",
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": elapsed_sec,
            "commits_scanned": commits_scanned,
            "findings": findings,
            **score_data
        }


class SBOMGenerator:
    """Generates CycloneDX v1.5 JSON Software Bill of Materials (SBOM) from project manifests."""

    def __init__(self):
        self.dep_scanner = DependencyScanner()

    def parse_pyproject_toml(self, content: str) -> List[Tuple[str, str]]:
        """Extracts dependencies from pyproject.toml using stdlib regex parsing."""
        pkgs: List[Tuple[str, str]] = []
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("dependencies") and "[" in stripped:
                in_deps = True
                if "]" in stripped:
                    in_deps = False
            elif in_deps:
                if "]" in stripped:
                    in_deps = False
                m = re.search(r"['\"]([a-zA-Z0-9_\-\.]+)\s*(?:>=|==|~=|>|<)?\s*([0-9a-zA-Z\.\-]*)['\"]", stripped)
                if m:
                    pkg_name = m.group(1).lower().replace("_", "-")
                    ver = m.group(2) or "latest"
                    pkgs.append((pkg_name, ver))
        return pkgs

    def generate_sbom(self, target_path: Union[str, Path]) -> Dict[str, Any]:
        """Scans directory for dependency manifests and builds CycloneDX 1.5 JSON SBOM."""
        base = Path(target_path).resolve()
        if not base.exists():
            raise FileNotFoundError(f"Target path '{target_path}' does not exist.")

        components: List[Dict[str, Any]] = []
        vulnerabilities: List[Dict[str, Any]] = []
        seen_purls: Set[str] = set()

        files_to_check: List[Path] = []
        if base.is_file():
            files_to_check.append(base)
        else:
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
                for f in files:
                    fl = f.lower()
                    if fl in ("requirements.txt", "package.json", "pyproject.toml") or (fl.endswith(".txt") and "requirements" in fl):
                        files_to_check.append(Path(root) / f)

        for manifest in files_to_check:
            try:
                content = manifest.read_text(encoding="utf-8", errors="ignore")
                rel_manifest = str(manifest.relative_to(base)) if base.is_dir() else manifest.name
            except Exception:
                continue

            fname = manifest.name.lower()
            extracted: List[Tuple[str, str, str]] = []  # (name, version, ecosystem)
            if "package.json" in fname:
                for pkg, ver, _ in self.dep_scanner.parse_package_json(content):
                    extracted.append((pkg, ver, "npm"))
            elif "pyproject.toml" in fname:
                for pkg, ver in self.parse_pyproject_toml(content):
                    extracted.append((pkg, ver, "pypi"))
            else:
                for pkg, ver, _ in self.dep_scanner.parse_requirements_txt(content):
                    extracted.append((pkg, ver, "pypi"))

            for pkg_name, ver, ecosystem in extracted:
                purl = f"pkg:{ecosystem}/{pkg_name}@{ver}"
                if purl in seen_purls:
                    continue
                seen_purls.add(purl)

                components.append({
                    "type": "library",
                    "bom-ref": purl,
                    "name": pkg_name,
                    "version": ver,
                    "purl": purl,
                    "properties": [
                        {"name": "nexusshield:ecosystem", "value": ecosystem},
                        {"name": "nexusshield:manifest", "value": rel_manifest}
                    ]
                })

                # Check CVE advisories
                if pkg_name in self.dep_scanner.advisories:
                    for adv in self.dep_scanner.advisories[pkg_name]:
                        if is_version_vulnerable(ver, adv["vulnerable_below"]):
                            vulnerabilities.append({
                                "id": adv["cve"],
                                "source": {"name": "NexusShield Advisory DB"},
                                "ratings": [
                                    {
                                        "score": adv["cvss"],
                                        "severity": adv["severity"].lower(),
                                        "method": "CVSSv3"
                                    }
                                ],
                                "description": adv["description"],
                                "recommendation": f"Upgrade {pkg_name} to >= {adv['safe_version']}",
                                "affects": [{"ref": purl}]
                            })

        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "serialNumber": f"urn:uuid:{uuid.uuid4()}",
            "version": 1,
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tools": [
                    {
                        "vendor": "IT Solutions Global",
                        "name": "NexusShield",
                        "version": "1.0.0"
                    }
                ],
                "component": {
                    "type": "application",
                    "name": base.name,
                    "path": str(base)
                },
                "properties": [
                    {
                        "name": "nexusshield:zero_external_dependencies",
                        "value": "true" if len(components) == 0 else "false"
                    }
                ]
            },
            "components": components,
            "vulnerabilities": vulnerabilities,
            "summary": {
                "total_components": len(components),
                "total_vulnerabilities": len(vulnerabilities),
                "manifests_scanned": len(files_to_check)
            }
        }


class SecretRemediator:
    """
    1-Click Automatic Secret Remediation:
    Extracts hardcoded credentials from source files into a .env file,
    ensures .env is git-ignored, and rewrites the source code to use os.environ.get().
    """

    def __init__(self, entropy_threshold: float = 4.6):
        self.secret_scanner = SecretScanner(entropy_threshold=entropy_threshold)

    def remediate_file(
        self,
        file_path: Union[str, Path],
        env_file_path: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """
        Scans `file_path` for hardcoded secrets, moves them to `.env`, and rewrites
        the file to read from environment variables.
        """
        target = Path(file_path).resolve()
        if not target.is_file():
            raise FileNotFoundError(f"File '{file_path}' does not exist.")

        content = target.read_text(encoding="utf-8")
        lines = content.splitlines()
        env_path = Path(env_file_path).resolve() if env_file_path else (target.parent / ".env")

        extracted_vars: List[Dict[str, Any]] = []
        new_lines: List[str] = []
        needs_os_import = False
        is_python = target.suffix.lower() == ".py"
        is_js = target.suffix.lower() in (".js", ".ts", ".jsx", ".tsx")

        # Assignment matcher: VAR_NAME = "secret_value" or var_name: "secret_value"
        assign_re = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*([:=])\s*['\"]([^'\"]+)['\"](.*)$")

        for idx, line in enumerate(lines, start=1):
            findings = self.secret_scanner.scan_line(line, idx, str(target))
            if not findings:
                new_lines.append(line)
                continue

            m = assign_re.match(line)
            if not m:
                new_lines.append(line)
                continue

            indent, var_name, sep, secret_val, trailing = m.groups()
            env_key = re.sub(r"[^A-Z0-9_]", "_", var_name.upper()).strip("_")
            if not env_key:
                env_key = f"NEXUS_SECRET_{idx}"

            if is_js and sep == "=":
                replacement_expr = f"process.env.{env_key}"
                new_line = f"{indent}{var_name} = {replacement_expr}{trailing}"
            else:
                needs_os_import = True
                new_line = f'{indent}{var_name} {sep} os.environ.get("{env_key}", ""){trailing}'

            new_lines.append(new_line)
            extracted_vars.append({
                "line": idx,
                "variable": var_name,
                "env_key": env_key,
                "secret_value": secret_val,
                "rule_id": findings[0]["id"],
                "title": findings[0]["title"]
            })

        if not extracted_vars:
            return {
                "status": "clean",
                "file": str(target),
                "remediated_count": 0,
                "extracted_variables": [],
                "message": "No hardcoded secret assignments required remediation."
            }

        if is_python and needs_os_import:
            has_os = any(re.match(r"^\s*import\s+os\b", l) for l in new_lines)
            if not has_os:
                new_lines.insert(0, "import os")

        # Write updated source file
        target.write_text("\n".join(new_lines) + ("\n" if content.endswith("\n") else ""), encoding="utf-8")

        # Append extracted secrets to .env
        existing_env = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        env_additions = []
        for item in extracted_vars:
            key = item["env_key"]
            val = item["secret_value"]
            if f"{key}=" not in existing_env:
                env_additions.append(f'{key}="{val}"')

        if env_additions:
            prefix = "\n" if existing_env and not existing_env.endswith("\n") else ""
            env_path.write_text(existing_env + prefix + "\n".join(env_additions) + "\n", encoding="utf-8")

        # Ensure .gitignore contains .env
        gitignore_path = target.parent / ".gitignore"
        if gitignore_path.exists():
            gi_content = gitignore_path.read_text(encoding="utf-8")
            if ".env" not in gi_content.splitlines():
                gitignore_path.write_text(gi_content.rstrip("\n") + "\n.env\n", encoding="utf-8")

        return {
            "status": "remediated",
            "file": str(target),
            "env_file": str(env_path),
            "remediated_count": len(extracted_vars),
            "extracted_variables": [
                {
                    "line": v["line"],
                    "variable": v["variable"],
                    "env_key": v["env_key"],
                    "rule_id": v["rule_id"],
                    "title": v["title"]
                }
                for v in extracted_vars
            ],
            "message": f"Extracted {len(extracted_vars)} secret(s) to {env_path.name} and updated {target.name}."
        }
