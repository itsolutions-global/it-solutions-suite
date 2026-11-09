"""
NexusShield Dependency Vulnerability Scanner
Cross-references manifest packages (requirements.txt, package.json) against known CVE advisories.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

# Local Offline Vulnerability Advisory Database
KNOWN_ADVISORIES: Dict[str, List[Dict[str, Any]]] = {
    # --- Python Ecosystem ---
    "requests": [
        {
            "cve": "CVE-2023-32681",
            "title": "Proxy-Authorization Header Leak",
            "vulnerable_below": "2.31.0",
            "safe_version": "2.31.0",
            "severity": "High",
            "cvss": 7.5,
            "description": "Requests leaks Proxy-Authorization headers to destination servers when following redirects."
        }
    ],
    "urllib3": [
        {
            "cve": "CVE-2023-45803",
            "title": "HTTP Request Smuggling & Header Stripping",
            "vulnerable_below": "1.26.18",
            "safe_version": "1.26.18",
            "severity": "High",
            "cvss": 7.8,
            "description": "urllib3 fails to strip Cookie headers when redirected across origins."
        }
    ],
    "cryptography": [
        {
            "cve": "CVE-2023-49083",
            "title": "NULL Pointer Dereference in PKCS12 Certificate Loading",
            "vulnerable_below": "41.0.6",
            "safe_version": "41.0.6",
            "severity": "Medium",
            "cvss": 5.3,
            "description": "Calling load_pkcs12 with certificates without a private key causes a segmentation fault."
        }
    ],
    "flask": [
        {
            "cve": "CVE-2023-30861",
            "title": "Session Cookie Secret Key Disclosure",
            "vulnerable_below": "2.2.5",
            "safe_version": "2.2.5",
            "severity": "High",
            "cvss": 7.5,
            "description": "Flask session cookies exposed to unintended caching layers."
        }
    ],
    "django": [
        {
            "cve": "CVE-2024-27351",
            "title": "Regular Expression Denial of Service in URL Validator",
            "vulnerable_below": "4.2.11",
            "safe_version": "4.2.11",
            "severity": "High",
            "cvss": 7.5,
            "description": "Django regular expression denial of service in django.core.validators.URLValidator."
        }
    ],
    "jinja2": [
        {
            "cve": "CVE-2024-22195",
            "title": "Cross-Site Scripting via xmlattr Filter",
            "vulnerable_below": "3.1.3",
            "safe_version": "3.1.3",
            "severity": "Medium",
            "cvss": 6.1,
            "description": "Jinja xmlattr filter allows injection of arbitrary HTML/JS attributes."
        }
    ],
    "pillow": [
        {
            "cve": "CVE-2024-28219",
            "title": "Buffer Overflow in ImageColor Parsing",
            "vulnerable_below": "10.2.0",
            "safe_version": "10.2.0",
            "severity": "Critical",
            "cvss": 9.8,
            "description": "Heap buffer overflow in Pillow ImageColor.getrgb allowing arbitrary code execution."
        }
    ],
    "aiohttp": [
        {
            "cve": "CVE-2024-23334",
            "title": "Static File Path Traversal",
            "vulnerable_below": "3.9.2",
            "safe_version": "3.9.2",
            "severity": "High",
            "cvss": 7.5,
            "description": "aiohttp directory traversal via static route handlers with follow_symlinks=True."
        }
    ],
    "pyyaml": [
        {
            "cve": "CVE-2020-14343",
            "title": "Arbitrary Code Execution via Default YAML Loader",
            "vulnerable_below": "5.4.0",
            "safe_version": "5.4.0",
            "severity": "Critical",
            "cvss": 9.8,
            "description": "PyYAML untrusted YAML loading allows arbitrary code execution via FullLoader."
        }
    ],
    "werkzeug": [
        {
            "cve": "CVE-2024-34069",
            "title": "Debugger Console Remote Code Execution",
            "vulnerable_below": "3.0.3",
            "safe_version": "3.0.3",
            "severity": "High",
            "cvss": 7.5,
            "description": "Interactive developer debugger pin bypass leading to unauthorized command execution."
        }
    ],

    # --- JavaScript / Node Ecosystem ---
    "lodash": [
        {
            "cve": "CVE-2020-8203",
            "title": "Prototype Pollution via zipObjectDeep",
            "vulnerable_below": "4.17.21",
            "safe_version": "4.17.21",
            "severity": "High",
            "cvss": 7.4,
            "description": "Prototype pollution in lodash via zipObjectDeep allows property injection."
        }
    ],
    "jsonwebtoken": [
        {
            "cve": "CVE-2022-23529",
            "title": "Insecure Key Object Verification RCE",
            "vulnerable_below": "9.0.0",
            "safe_version": "9.0.0",
            "severity": "High",
            "cvss": 7.6,
            "description": "jsonwebtoken library allows arbitrary file write or RCE through malicious key object."
        }
    ],
    "axios": [
        {
            "cve": "CVE-2021-3749",
            "title": "Regular Expression Denial of Service in trim",
            "vulnerable_below": "0.21.4",
            "safe_version": "0.21.4",
            "severity": "High",
            "cvss": 7.5,
            "description": "Axios ReDoS via data trimming on specific unauthenticated HTTP inputs."
        }
    ],
    "minimatch": [
        {
            "cve": "CVE-2022-3517",
            "title": "ReDoS via Regular Expression Glob Parsing",
            "vulnerable_below": "3.0.5",
            "safe_version": "3.0.5",
            "severity": "Medium",
            "cvss": 6.2,
            "description": "Denial of Service via complex regular expression wildcard matches."
        }
    ],
    "express": [
        {
            "cve": "CVE-2024-29041",
            "title": "Open Redirect via Malformed Request URL",
            "vulnerable_below": "4.19.2",
            "safe_version": "4.19.2",
            "severity": "Medium",
            "cvss": 6.1,
            "description": "Express open redirect vulnerability handling malformed relative path headers."
        }
    ],
    "semver": [
        {
            "cve": "CVE-2022-25883",
            "title": "ReDoS in SemVer Range Validator",
            "vulnerable_below": "7.5.2",
            "safe_version": "7.5.2",
            "severity": "High",
            "cvss": 7.5,
            "description": "semver ReDoS when comparing very long untrusted range inputs."
        }
    ]
}


def parse_version_tuple(version_str: str) -> Tuple[int, ...]:
    """Converts a semantic version string (e.g., '2.31.0') into an integer comparison tuple."""
    # Strip any prefix like ^, ~, >=, ==, v
    cleaned = re.sub(r"^[^\d]*", "", version_str).strip()
    parts = []
    for piece in cleaned.split("."):
        # Match only digits from leading piece
        m = re.match(r"^\d+", piece)
        if m:
            parts.append(int(m.group(0)))
        else:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_version_vulnerable(current_version: str, vulnerable_below: str) -> bool:
    """Returns True if current_version < vulnerable_below."""
    try:
        curr_tuple = parse_version_tuple(current_version)
        vuln_tuple = parse_version_tuple(vulnerable_below)
        return curr_tuple < vuln_tuple
    except Exception:
        return False


class DependencyScanner:
    """Zero-dependency manifest vulnerability scanner."""

    def __init__(self, advisories: Optional[Dict[str, List[Dict[str, Any]]]] = None):
        self.advisories = advisories or KNOWN_ADVISORIES

    def parse_requirements_txt(self, content: str) -> List[Tuple[str, str, int]]:
        """Parses requirements.txt content into (package_name, version, line_number)."""
        packages = []
        for line_idx, line in enumerate(content.splitlines(), start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Handle pkg==1.2.3, pkg>=1.2.3, pkg<=1.2.3
            match = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*(?:==|>=|<=|~=)\s*([0-9a-zA-Z\.\-]+)", line)
            if match:
                pkg_name = match.group(1).lower().replace("_", "-")
                version = match.group(2)
                packages.append((pkg_name, version, line_idx))
            else:
                # Handle bare package name without version (warn or skip)
                bare = re.match(r"^([a-zA-Z0-9_\-\.]+)", line)
                if bare:
                    pkg_name = bare.group(1).lower().replace("_", "-")
                    packages.append((pkg_name, "0.0.0", line_idx))
        return packages

    def parse_package_json(self, content: str) -> List[Tuple[str, str, int]]:
        """Parses package.json dependencies and devDependencies."""
        packages = []
        try:
            data = json.loads(content)
        except Exception:
            return packages

        deps = {}
        if isinstance(data.get("dependencies"), dict):
            deps.update(data["dependencies"])
        if isinstance(data.get("devDependencies"), dict):
            deps.update(data["devDependencies"])

        for pkg, raw_ver in deps.items():
            clean_ver = re.sub(r"[\^~>=<v]", "", str(raw_ver)).strip()
            packages.append((pkg.lower(), clean_ver, 1))

        return packages

    def scan_manifest(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Scans a manifest file for packages matching CVE advisories."""
        findings = []
        filename = file_path.lower().replace("\\", "/").split("/")[-1]

        if "requirements" in filename or filename.endswith(".txt"):
            parsed_pkgs = self.parse_requirements_txt(content)
            ecosystem = "pypi"
        elif "package.json" in filename:
            parsed_pkgs = self.parse_package_json(content)
            ecosystem = "npm"
        else:
            return []

        for pkg_name, version, line_num in parsed_pkgs:
            # Check if package is in advisory database
            if pkg_name in self.advisories:
                for adv in self.advisories[pkg_name]:
                    if is_version_vulnerable(version, adv["vulnerable_below"]):
                        findings.append({
                            "id": adv["cve"],
                            "title": f"Vulnerable Dependency: {pkg_name} {version} ({adv['cve']})",
                            "package": pkg_name,
                            "installed_version": version,
                            "safe_version": adv["safe_version"],
                            "severity": adv["severity"],
                            "cvss": adv["cvss"],
                            "category": "Known Dependency CVE",
                            "type": "cve_vulnerability",
                            "ecosystem": ecosystem,
                            "file": file_path,
                            "line": line_num,
                            "description": adv["description"],
                            "remediation": f"Upgrade {pkg_name} to >={adv['safe_version']} in {filename}."
                        })

        return findings
