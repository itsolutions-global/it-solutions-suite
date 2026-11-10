#!/usr/bin/env python3
"""
Corporate Health Monitoring Daemon
IT Solutions Global Corporation - Quality Assurance & Operational Auditing

Author: Chief Quality Officer & Corporate Auditor
Mission: Continuously audits live product APIs, database integrity/size,
         and automated test pass rates across all company products.
         Generates structured executive telemetry at company/audits/HEALTH_TELEMETRY.json.
"""

import argparse
import json
import logging
import os
import platform
import re
import signal
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen, build_opener, ProxyHandler

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
COMPANY_DIR = BASE_DIR / "company"
AUDITS_DIR = COMPANY_DIR / "audits"
PRODUCTS_DIR = BASE_DIR / "products"
DEFAULT_TELEMETRY_PATH = AUDITS_DIR / "HEALTH_TELEMETRY.json"
DEFAULT_API_URL = "http://127.0.0.1:8080/api/health"

# Configure Logging
logger = logging.getLogger("health_monitor")


def format_size(size_bytes: int) -> str:
    """Formats byte count to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


class CorporateHealthMonitor:
    """Enterprise Health Monitoring Daemon and Quality Telemetry Engine."""

    def __init__(
        self,
        base_dir: Path = BASE_DIR,
        api_url: str = DEFAULT_API_URL,
        telemetry_path: Path = DEFAULT_TELEMETRY_PATH,
        interval_seconds: int = 60,
        verbose: bool = False
    ):
        self.base_dir = Path(base_dir)
        self.products_dir = self.base_dir / "products"
        self.audits_dir = self.base_dir / "company" / "audits"
        self.api_url = api_url
        self.telemetry_path = Path(telemetry_path)
        self.interval_seconds = interval_seconds
        self.verbose = verbose
        self.audits_dir.mkdir(parents=True, exist_ok=True)

    def ping_api(self) -> Dict[str, Any]:
        """
        Pings the live product API health endpoint.
        Measures round-trip latency in milliseconds and records operational telemetry.
        """
        start_time = time.perf_counter()
        req = Request(self.api_url, headers={"User-Agent": "CorePulse-HealthMonitor/1.0", "Connection": "close"})
        opener = build_opener(ProxyHandler({}))

        try:
            with opener.open(req, timeout=10) as resp:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                status_code = resp.status
                raw_body = resp.read().decode("utf-8")
                try:
                    payload = json.loads(raw_body)
                except Exception:
                    payload = {"raw": raw_body}

                return {
                    "endpoint": self.api_url,
                    "reachable": True,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "api_status": payload.get("status", "unknown"),
                    "service": payload.get("service", "CorePulse Engine"),
                    "version": payload.get("version", "unknown"),
                    "build_id": payload.get("build_id", "unknown"),
                    "uptime_seconds": payload.get("uptime_seconds", 0),
                    "uptime_human": payload.get("uptime_human", "N/A"),
                    "records_tracked": payload.get("records_tracked", 0),
                    "thread_count": payload.get("thread_count", 0),
                    "db_status": payload.get("db_status", "unknown"),
                    "error": None
                }
        except HTTPError as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "endpoint": self.api_url,
                "reachable": True,
                "status_code": e.code,
                "latency_ms": latency_ms,
                "api_status": "degraded",
                "error": f"HTTP {e.code}: {e.reason}"
            }
        except URLError as e:
            return {
                "endpoint": self.api_url,
                "reachable": False,
                "status_code": 0,
                "latency_ms": None,
                "api_status": "unreachable",
                "error": f"Connection refused or timed out: {e.reason}"
            }
        except Exception as e:
            return {
                "endpoint": self.api_url,
                "reachable": False,
                "status_code": 0,
                "latency_ms": None,
                "api_status": "error",
                "error": str(e)
            }

    def check_database_integrity(self) -> Dict[str, Any]:
        """
        Validates the integrity, schema consistency, and file sizing
        for all active product data stores (both SQLite and JSON).
        """
        stores: List[Dict[str, Any]] = []
        overall_integrity = "PASS"

        # 1. Inspect CorePulse JSON Store
        json_path = self.products_dir / "corepulse" / "data" / "corepulse_store.json"
        if json_path.exists():
            try:
                stat = json_path.stat()
                size_bytes = stat.st_size
                mtime_iso = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()

                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Schema validation
                required_keys = {"version", "subscription", "tasks", "metrics"}
                missing_keys = [k for k in required_keys if k not in data]
                tasks = data.get("tasks", [])
                habits = [t for t in tasks if t.get("type") == "habit"]
                completed_tasks = [t for t in tasks if t.get("completed")]

                json_status = "PASS" if not missing_keys else "FAIL"
                if json_status == "FAIL":
                    overall_integrity = "DEGRADED"

                stores.append({
                    "engine": "JSON",
                    "file_path": str(json_path),
                    "exists": True,
                    "size_bytes": size_bytes,
                    "size_human": format_size(size_bytes),
                    "last_modified": mtime_iso,
                    "integrity_check": json_status,
                    "schema_valid": len(missing_keys) == 0,
                    "missing_keys": missing_keys,
                    "records": {
                        "total_tasks": len(tasks),
                        "habits": len(habits),
                        "completed": len(completed_tasks),
                        "pending": len(tasks) - len(completed_tasks)
                    }
                })
            except Exception as e:
                overall_integrity = "FAIL"
                stores.append({
                    "engine": "JSON",
                    "file_path": str(json_path),
                    "exists": True,
                    "integrity_check": "CORRUPTED",
                    "error": str(e)
                })
        else:
            stores.append({
                "engine": "JSON",
                "file_path": str(json_path),
                "exists": False,
                "integrity_check": "MISSING"
            })

        # 2. Inspect CorePulse SQLite Store
        sqlite_path = self.products_dir / "corepulse" / "data" / "corepulse.sqlite3"
        if sqlite_path.exists():
            try:
                stat = sqlite_path.stat()
                size_bytes = stat.st_size
                mtime_iso = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()

                conn = sqlite3.connect(str(sqlite_path), timeout=5)
                cur = conn.cursor()

                # PRAGMA integrity_check
                cur.execute("PRAGMA integrity_check;")
                integrity_rows = cur.fetchall()
                integrity_ok = len(integrity_rows) == 1 and integrity_rows[0][0] == "ok"

                # PRAGMA journal_mode
                cur.execute("PRAGMA journal_mode;")
                journal_mode = cur.fetchone()[0]

                # Table inventory and row counts
                cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [r[0] for r in cur.fetchall()]
                table_counts = {}
                for tbl in tables:
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {tbl};")
                        table_counts[tbl] = cur.fetchone()[0]
                    except Exception:
                        table_counts[tbl] = -1

                conn.close()

                sqlite_status = "PASS" if integrity_ok else "FAIL"
                if sqlite_status == "FAIL":
                    overall_integrity = "FAIL"

                stores.append({
                    "engine": "SQLite3",
                    "file_path": str(sqlite_path),
                    "exists": True,
                    "size_bytes": size_bytes,
                    "size_human": format_size(size_bytes),
                    "last_modified": mtime_iso,
                    "integrity_check": sqlite_status,
                    "journal_mode": journal_mode,
                    "tables": tables,
                    "table_row_counts": table_counts
                })
            except Exception as e:
                overall_integrity = "FAIL"
                stores.append({
                    "engine": "SQLite3",
                    "file_path": str(sqlite_path),
                    "exists": True,
                    "integrity_check": "CORRUPTED",
                    "error": str(e)
                })
        else:
            stores.append({
                "engine": "SQLite3",
                "file_path": str(sqlite_path),
                "exists": False,
                "integrity_check": "MISSING"
            })

        return {
            "overall_integrity": overall_integrity,
            "total_stores_checked": len(stores),
            "stores": stores
        }

    def verify_test_pass_rates(self) -> Dict[str, Any]:
        """
        Dynamically discovers and executes all test suites across all products.
        Computes pass rates, execution durations, and test suite health.
        """
        product_results = []
        global_total = 0
        global_passed = 0
        global_failed = 0
        global_errors = 0

        # Scan products directory
        if self.products_dir.exists():
            for prod_dir in sorted(self.products_dir.iterdir()):
                if not prod_dir.is_dir():
                    continue

                test_dir = prod_dir / "tests"
                if not test_dir.exists() or not test_dir.is_dir():
                    continue

                product_name = prod_dir.name
                cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
                start_test = time.perf_counter()

                try:
                    proc = subprocess.run(
                        cmd,
                        cwd=str(prod_dir),
                        capture_output=True,
                        timeout=240
                    )
                    duration_s = round(time.perf_counter() - start_test, 3)
                    output = (proc.stderr or b"").decode("utf-8", errors="replace") + "\n" + (proc.stdout or b"").decode("utf-8", errors="replace")

                    # Parse standard unittest discovery summary
                    # Example: "Ran 26 tests in 3.101s"
                    ran_match = re.search(r"Ran (\d+) tests? in ([\d\.]+)s", output)
                    total_tests = int(ran_match.group(1)) if ran_match else 0

                    failed_count = 0
                    error_count = 0

                    fail_match = re.search(r"FAILED \((?:failures=(\d+))?(?:, )?(?:errors=(\d+))?\)", output)
                    if fail_match:
                        failed_count = int(fail_match.group(1) or 0)
                        error_count = int(fail_match.group(2) or 0)

                    passed_count = total_tests - failed_count - error_count
                    pass_rate = round((passed_count / total_tests * 100), 2) if total_tests > 0 else 0.0

                    product_results.append({
                        "product": product_name,
                        "test_directory": str(test_dir),
                        "total_tests": total_tests,
                        "passed": passed_count,
                        "failed": failed_count,
                        "errors": error_count,
                        "pass_rate_percent": pass_rate,
                        "duration_seconds": duration_s,
                        "exit_code": proc.returncode,
                        "status": "PASS" if proc.returncode == 0 else "FAIL"
                    })

                    global_total += total_tests
                    global_passed += passed_count
                    global_failed += failed_count
                    global_errors += error_count

                except subprocess.TimeoutExpired:
                    product_results.append({
                        "product": product_name,
                        "test_directory": str(test_dir),
                        "total_tests": 0,
                        "passed": 0,
                        "failed": 0,
                        "errors": 1,
                        "pass_rate_percent": 0.0,
                        "duration_seconds": 240.0,
                        "exit_code": -1,
                        "status": "TIMEOUT",
                        "error": "Test suite exceeded execution timeout"
                    })
                except Exception as e:
                    product_results.append({
                        "product": product_name,
                        "test_directory": str(test_dir),
                        "total_tests": 0,
                        "passed": 0,
                        "failed": 0,
                        "errors": 1,
                        "pass_rate_percent": 0.0,
                        "duration_seconds": 0.0,
                        "exit_code": -1,
                        "status": "ERROR",
                        "error": str(e)
                    })

        global_pass_rate = round((global_passed / global_total * 100), 2) if global_total > 0 else 0.0
        overall_status = "PASS" if (global_failed == 0 and global_errors == 0 and global_total > 0) else "FAIL"

        return {
            "overall_status": overall_status,
            "total_products_scanned": len(product_results),
            "global_total_tests": global_total,
            "global_passed_tests": global_passed,
            "global_failed_tests": global_failed,
            "global_error_tests": global_errors,
            "global_pass_rate_percent": global_pass_rate,
            "products": product_results
        }

    def compute_composite_health_index(
        self,
        api_data: Dict[str, Any],
        db_data: Dict[str, Any],
        test_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Computes a comprehensive weighted Corporate Health Index (0 - 100).
        Weights:
        - Live API Health & Latency: 35%
        - Database Integrity & Schemas: 30%
        - Automated Test Pass Rate: 35%
        """
        score = 0.0

        # 1. API Component (35 pts max)
        if api_data.get("reachable"):
            score += 25.0
            if api_data.get("api_status") == "healthy":
                score += 5.0
            lat = api_data.get("latency_ms")
            if lat is not None and lat < 250.0:
                score += 5.0
            elif lat is not None and lat < 750.0:
                score += 3.0

        # 2. Database Component (30 pts max)
        db_status = db_data.get("overall_integrity")
        if db_status == "PASS":
            score += 30.0
        elif db_status == "DEGRADED":
            score += 15.0

        # 3. Test Suite Component (35 pts max)
        pass_rate = test_data.get("global_pass_rate_percent", 0.0)
        score += round((pass_rate / 100.0) * 35.0, 2)

        final_score = round(min(100.0, score), 1)

        if final_score >= 90.0:
            status = "HEALTHY"
        elif final_score >= 70.0:
            status = "DEGRADED"
        else:
            status = "CRITICAL"

        return {
            "score": final_score,
            "status": status,
            "breakdown": {
                "api_weight_score": min(35.0, round(score * 0.35, 1)),
                "database_weight_score": 30.0 if db_status == "PASS" else (15.0 if db_status == "DEGRADED" else 0.0),
                "test_weight_score": round((pass_rate / 100.0) * 35.0, 1)
            }
        }

    def run_health_sweep(self) -> Dict[str, Any]:
        """
        Executes a single comprehensive health audit sweep,
        generates structured telemetry, and persists it atomically to disk.
        """
        now_utc = datetime.now(timezone.utc).isoformat()

        logger.info("Executing Corporate Health Telemetry Sweep...")

        # 1. Ping API
        api_telemetry = self.ping_api()

        # 2. Check Database Integrity
        db_telemetry = self.check_database_integrity()

        # 3. Verify Test Pass Rates
        test_telemetry = self.verify_test_pass_rates()

        # 4. Compute Health Index
        health_index = self.compute_composite_health_index(
            api_telemetry,
            db_telemetry,
            test_telemetry
        )

        # 5. Assemble Full Structured Telemetry Payload
        telemetry_payload = {
            "metadata": {
                "system": "IT Solutions Global Corporate Health Monitor",
                "version": "1.0.0",
                "auditor": "Chief Quality Officer & Corporate Auditor",
                "generated_at": now_utc,
                "host_os": f"{platform.system()} {platform.release()}",
                "python_version": platform.python_version()
            },
            "corporate_health_index": health_index,
            "api_health": api_telemetry,
            "database_health": db_telemetry,
            "test_suite_health": test_telemetry
        }

        # 6. Atomic Write to Disk
        self._write_telemetry_atomic(telemetry_payload)

        # 7. Print Console Summary
        self._print_console_summary(telemetry_payload)

        return telemetry_payload

    def _write_telemetry_atomic(self, payload: Dict[str, Any]):
        """Safely writes telemetry JSON using atomic file replacement."""
        tmp_file = self.telemetry_path.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            tmp_file.replace(self.telemetry_path)
            logger.info("Telemetry successfully recorded to %s", self.telemetry_path)
        except Exception as e:
            logger.error("Failed to write telemetry to %s: %s", self.telemetry_path, e)
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass

    def _print_console_summary(self, t: Dict[str, Any]):
        """Prints high-visibility executive dashboard to console."""
        hi = t["corporate_health_index"]
        api = t["api_health"]
        db = t["database_health"]
        ts = t["test_suite_health"]

        border = "=" * 68
        print("\n" + border)
        print("  [*] CORPORATE HEALTH & QUALITY TELEMETRY REPORT")
        print(f"     Status: {hi['status']}  |  Health Index: {hi['score']} / 100")
        print(f"     Timestamp: {t['metadata']['generated_at']}")
        print(border)

        # API
        if api["reachable"]:
            print(f"  [+] CorePulse API:        ONLINE [HTTP {api['status_code']}] | Latency: {api['latency_ms']}ms")
            print(f"    Uptime:                 {api['uptime_human']} ({api['uptime_seconds']}s)")
            print(f"    Active Records:         {api['records_tracked']} | Threads: {api['thread_count']}")
        else:
            print(f"  [-] CorePulse API:        OFFLINE | Error: {api.get('error')}")

        # Database
        print(f"  [+] Database Integrity:   {db['overall_integrity']} ({db['total_stores_checked']} stores checked)")
        for st in db["stores"]:
            engine = st["engine"]
            chk = st["integrity_check"]
            sz = st.get("size_human", "N/A")
            print(f"    - {engine:<8} Store:         {chk} (Size: {sz})")

        # Tests
        print(f"  [+] Test Verification:    {ts['overall_status']} | Pass Rate: {ts['global_pass_rate_percent']}%")
        print(f"    Tests Summary:          {ts['global_passed_tests']} Passed / {ts['global_total_tests']} Total "
              f"({ts['global_failed_tests']} Failed, {ts['global_error_tests']} Errors)")
        for p in ts["products"]:
            pass_rate = p.get('pass_rate_percent', 0.0)
            passed = p.get('passed', 0)
            total = p.get('total_tests', 0)
            dur = p.get('duration_seconds', 0.0)
            print(f"    - Product '{p['product']}': {pass_rate}% ({passed}/{total} in {dur}s)")

        print(border)
        print(f"  [OK] Output Synced: {self.telemetry_path}")
        print(border + "\n")

    def run_daemon(self):
        """Runs the monitoring daemon loop until interrupted."""
        logger.info(f"Starting Corporate Health Monitor Daemon (Interval: {self.interval_seconds}s)...")
        print(f"\n[DAEMON INITIALIZED] Monitoring every {self.interval_seconds} seconds. Press Ctrl+C to terminate.")

        def shutdown_handler(signum, frame):
            print("\n[DAEMON STOPPED] Shutdown signal received. Exiting gracefully.")
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        iteration = 0
        while True:
            iteration += 1
            try:
                self.run_health_sweep()
            except Exception as e:
                logger.error(f"Error in telemetry iteration {iteration}: {e}")

            time.sleep(self.interval_seconds)


def main():
    parser = argparse.ArgumentParser(description="Corporate Health Monitoring Daemon")
    parser.add_argument("--once", action="store_true", help="Run a single health check sweep and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as a monitoring daemon")
    parser.add_argument("--interval", type=int, default=60, help="Monitoring interval in seconds (default: 60)")
    parser.add_argument("--url", default=DEFAULT_API_URL, help=f"Health endpoint URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--output", default=str(DEFAULT_TELEMETRY_PATH), help="Path to telemetry output JSON file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging")

    args = parser.parse_args()

    # Logging setup
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    monitor = CorporateHealthMonitor(
        base_dir=BASE_DIR,
        api_url=args.url,
        telemetry_path=Path(args.output),
        interval_seconds=args.interval,
        verbose=args.verbose
    )

    if args.daemon:
        monitor.run_daemon()
    else:
        # Default behavior is single sweep
        result = monitor.run_health_sweep()
        sys.exit(0 if result["corporate_health_index"]["status"] in ("HEALTHY", "DEGRADED") else 1)


if __name__ == "__main__":
    main()
