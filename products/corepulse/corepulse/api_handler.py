"""
CorePulse REST API Request Handler & Static Asset Server
Implements standard library high-performance zero-dependency HTTP server with REST routing.
"""

from datetime import datetime
import json
import logging
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from corepulse.config import STATIC_DIR, BASE_DIR
from corepulse.database import db
from corepulse.workflows import WorkflowEngine

import sys

# Dynamic resolution of adjacent product directories in enterprise suite
PRODUCTS_DIR = BASE_DIR.parent
NEXUSSHIELD_DIR = PRODUCTS_DIR / "nexusshield"
ECHOSTREAM_DIR = PRODUCTS_DIR / "echostream"

if str(NEXUSSHIELD_DIR) not in sys.path and NEXUSSHIELD_DIR.exists():
    sys.path.insert(0, str(NEXUSSHIELD_DIR))
if str(ECHOSTREAM_DIR) not in sys.path and ECHOSTREAM_DIR.exists():
    sys.path.insert(0, str(ECHOSTREAM_DIR))

logger = logging.getLogger("corepulse.api")

class CorePulseRequestHandler(BaseHTTPRequestHandler):
    """Zero-dependency REST API and Static File Server for CorePulse."""

    server_version = "CorePulseEngine/1.0"

    def _send_cors_headers(self):
        """Attaches secure CORS headers for local/same-origin requests."""
        origin = self.headers.get("Origin", "")
        if not origin or "localhost" in origin or "127.0.0.1" in origin:
            self.send_header("Access-Control-Allow-Origin", origin if origin else "*")
        else:
            self.send_header("Access-Control-Allow-Origin", "null")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def _send_json_response(self, data: any, status_code: int = HTTPStatus.OK):
        """Serializes and transmits a JSON response."""
        payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _send_error_response(self, message: str, status_code: int = HTTPStatus.BAD_REQUEST, details: any = None):
        """Transmits structured error response."""
        resp = {
            "error": True,
            "message": message,
            "status_code": status_code,
            "details": details
        }
        self._send_json_response(resp, status_code)

    def do_OPTIONS(self):
        """Handles CORS preflight requests."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Routes GET requests to appropriate API handlers or static files."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        try:
            # API Endpoints
            if path == "/api/health":
                self._send_json_response(db.get_health())
                return

            if path == "/api/tasks":
                item_type = query.get("type", [None])[0]
                completed_param = query.get("completed", [None])[0]
                completed = None
                if completed_param is not None:
                    completed = completed_param.lower() in ("true", "1")
                tasks = db.get_tasks(item_type=item_type, completed=completed)
                self._send_json_response({
                    "count": len(tasks),
                    "tasks": tasks
                })
                return

            if path == "/api/metrics":
                self._send_json_response(db.get_metrics())
                return

            if path == "/api/subscription":
                try:
                    from corepulse.licensing import get_active_license
                    self._send_json_response(get_active_license())
                except Exception:
                    self._send_json_response(db.get_subscription())
                return

            if path in ("/api/sync/status", "/api/sync/status/"):
                try:
                    from corepulse.sync import sync_engine
                    self._send_json_response(sync_engine.get_sync_status())
                except Exception as ex:
                    self._send_error_response(f"Sync status error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            if path == "/api/workflows":
                self._send_json_response({
                    "workflows": WorkflowEngine.list_workflows()
                })
                return

            if path == "/api/founder/report":
                report_dir = BASE_DIR.parent.parent / "company" / "reports"
                report_file = report_dir / f"DAILY_REPORT_{datetime.now().strftime('%Y-%m-%d')}.md"
                report_content = "Daily briefing compiling..."
                if report_file.exists():
                    try:
                        with open(report_file, "r", encoding="utf-8") as rf:
                            report_content = rf.read()
                    except Exception as e:
                        report_content = f"Error reading report: {e}"

                self._send_json_response({
                    "company": "IT Solutions Global Corporation",
                    "status": "OPERATIONAL_24X7",
                    "founder_role": "Founder, Owner & Chairman of the Board",
                    "monetization_phase": "User Infiltration & Habituation First",
                    "payment_gateway_status": "Deferred until mass habituation threshold reached",
                    "obstacles_resolved": 2,
                    "active_blockers": 0,
                    "report_markdown": report_content
                })
                return

            if path in ("/api/tools/shield/scan", "/api/tools/shield/scan/"):
                from nexusshield.scanner import NexusScanner
                scanner = NexusScanner()
                scan_report = scanner.scan_directory(PRODUCTS_DIR)
                self._send_json_response({
                    "status": "success",
                    "target": str(PRODUCTS_DIR),
                    "score": scan_report.get("score"),
                    "grade": scan_report.get("grade"),
                    "compliance": scan_report.get("compliance"),
                    "summary": scan_report.get("summary"),
                    "duration_seconds": scan_report.get("duration_seconds"),
                    "files_scanned": scan_report.get("files_scanned"),
                    "lines_scanned": scan_report.get("lines_scanned"),
                    "findings_count": len(scan_report.get("findings", [])),
                    "findings": scan_report.get("findings", [])
                })
                return

            if path in ("/api/tools/pipeline/status", "/api/tools/pipeline/status/"):
                from echostream.pipeline import AutonomousIngestionPipeline
                drop_dir = PRODUCTS_DIR.parent / "data" / "transcripts"
                pipeline = AutonomousIngestionPipeline(drop_dir=drop_dir)
                try:
                    telemetry = pipeline.get_telemetry()
                finally:
                    pipeline.close()
                self._send_json_response(telemetry)
                return

            # Static File Serving
            self._serve_static(path)

        except Exception as ex:
            logger.exception("Error processing GET %s", path)
            self._send_error_response(f"Internal Server Error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self):
        """Routes POST requests to REST API handlers."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Read JSON body with 2MB bounds
        content_length_header = self.headers.get("Content-Length", "0")
        try:
            content_length = int(content_length_header)
        except (ValueError, TypeError):
            self._send_error_response("Invalid Content-Length header", HTTPStatus.BAD_REQUEST)
            return

        if content_length > 2 * 1024 * 1024:
            self._send_error_response("Payload exceeds 2MB limit", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return

        body = {}
        if content_length > 0:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            try:
                body = json.loads(raw_body)
            except Exception as ex:
                self._send_error_response(f"Malformed JSON body: {str(ex)}", HTTPStatus.BAD_REQUEST)
                return

        try:
            # POST /api/tasks (Create or update task)
            if path == "/api/tasks":
                if not body.get("title"):
                    self._send_error_response("Field 'title' is required", HTTPStatus.UNPROCESSABLE_ENTITY)
                    return
                try:
                    saved_task = db.create_or_update_task(body)
                    try:
                        from corepulse.database_sqlite import sqlite_db
                        sqlite_db.create_or_update_task(saved_task)
                    except Exception:
                        pass
                except ValueError as v_err:
                    self._send_error_response(str(v_err), HTTPStatus.FORBIDDEN)
                    return
                self._send_json_response({
                    "message": "Task saved successfully",
                    "task": saved_task
                }, HTTPStatus.CREATED)
                return

            # POST /api/tasks/toggle or /api/tasks/toggle?id=xyz
            if path in ("/api/tasks/toggle", "/api/tasks/toggle/"):
                task_id = body.get("id") or query.get("id", [None])[0]
                if not task_id:
                    self._send_error_response("Task 'id' is required to toggle", HTTPStatus.BAD_REQUEST)
                    return
                toggled = db.toggle_task(task_id)
                if not toggled:
                    self._send_error_response(f"Task with id '{task_id}' not found", HTTPStatus.NOT_FOUND)
                    return
                try:
                    from corepulse.database_sqlite import sqlite_db
                    sqlite_db.toggle_task(task_id)
                except Exception:
                    pass
                self._send_json_response({
                    "message": "Task completion toggled",
                    "task": toggled
                })
                return

            # POST /api/workflows/run (Execute automated workflow script)
            if path in ("/api/workflows/run", "/api/workflows/run/"):
                workflow_id = body.get("workflow_id")
                if not workflow_id:
                    self._send_error_response("Field 'workflow_id' is required", HTTPStatus.BAD_REQUEST)
                    return
                custom_params = body.get("parameters", {})
                result = WorkflowEngine.run_workflow(workflow_id, custom_params)
                self._send_json_response(result, HTTPStatus.OK)
                return

            # POST /api/subscription/upgrade (Feature gate testing and cryptographic license activation)
            if path in ("/api/subscription/upgrade", "/api/subscription/upgrade/"):
                license_key = body.get("license_key") or body.get("key")
                if license_key:
                    try:
                        from corepulse.licensing import activate_license_key
                        res = activate_license_key(license_key)
                        if not res.get("success"):
                            self._send_error_response(res.get("error", "Invalid license key"), HTTPStatus.BAD_REQUEST)
                            return
                        self._send_json_response({
                            "message": res.get("summary", "License activated successfully"),
                            "tier": res.get("tier"),
                            "subscription": res,
                            "features": res.get("features")
                        })
                        return
                    except Exception as ex:
                        self._send_error_response(f"License activation error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                        return

                tier = body.get("tier")
                if not tier:
                    self._send_error_response("Field 'tier' or 'license_key' is required", HTTPStatus.BAD_REQUEST)
                    return
                sub = db.upgrade_subscription(tier)
                try:
                    from corepulse.database_sqlite import sqlite_db
                    sqlite_db.upgrade_subscription(tier)
                except Exception:
                    pass
                self._send_json_response({
                    "message": f"Successfully upgraded subscription to {tier.upper()}",
                    "subscription": sub
                })
                return

            # POST /api/sync/pair (Pair with zero-knowledge passphrase and relay)
            if path in ("/api/sync/pair", "/api/sync/pair/"):
                passphrase = body.get("passphrase")
                if not passphrase:
                    self._send_error_response("Field 'passphrase' is required (minimum 8 characters)", HTTPStatus.BAD_REQUEST)
                    return
                relay_url = body.get("relay_url")
                try:
                    from corepulse.sync import sync_engine
                    res = sync_engine.pair(passphrase, relay_url=relay_url)
                    self._send_json_response(res, HTTPStatus.OK)
                except ValueError as ve:
                    self._send_error_response(str(ve), HTTPStatus.BAD_REQUEST)
                except Exception as ex:
                    self._send_error_response(f"Sync pairing error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            # POST /api/sync/push (Encrypt and push pending outbox to relay)
            if path in ("/api/sync/push", "/api/sync/push/"):
                passphrase = body.get("passphrase") or os.environ.get("COREPULSE_SYNC_PASSPHRASE")
                relay_url = body.get("relay_url")
                try:
                    from corepulse.sync import sync_engine
                    res = sync_engine.push_deltas(relay_url=relay_url, passphrase=passphrase)
                    self._send_json_response(res, HTTPStatus.OK)
                except ValueError as ve:
                    self._send_error_response(str(ve), HTTPStatus.BAD_REQUEST)
                except Exception as ex:
                    self._send_error_response(f"Sync push error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            # POST /api/sync/pull (Pull and decrypt deltas with CRDT resolution)
            if path in ("/api/sync/pull", "/api/sync/pull/"):
                passphrase = body.get("passphrase") or os.environ.get("COREPULSE_SYNC_PASSPHRASE")
                relay_url = body.get("relay_url")
                try:
                    from corepulse.sync import sync_engine
                    res = sync_engine.pull_deltas(relay_url=relay_url, passphrase=passphrase)
                    self._send_json_response(res, HTTPStatus.OK)
                except ValueError as ve:
                    self._send_error_response(str(ve), HTTPStatus.BAD_REQUEST)
                except Exception as ex:
                    self._send_error_response(f"Sync pull error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            # POST /api/tools/shield/scan (Execute NexusShield security audit)
            if path in ("/api/tools/shield/scan", "/api/tools/shield/scan/"):
                target_path = body.get("path")
                if not target_path:
                    target_path = str(PRODUCTS_DIR)
                target = Path(target_path)
                if not target.exists():
                    self._send_error_response(f"Target path '{target_path}' does not exist", HTTPStatus.BAD_REQUEST)
                    return

                try:
                    from nexusshield.scanner import NexusScanner
                    scanner = NexusScanner()
                    scan_report = scanner.scan_directory(target)
                    self._send_json_response({
                        "status": "success",
                        "target": str(target),
                        "score": scan_report.get("score"),
                        "grade": scan_report.get("grade"),
                        "compliance": scan_report.get("compliance"),
                        "summary": scan_report.get("summary"),
                        "duration_seconds": scan_report.get("duration_seconds"),
                        "files_scanned": scan_report.get("files_scanned"),
                        "lines_scanned": scan_report.get("lines_scanned"),
                        "findings_count": len(scan_report.get("findings", [])),
                        "findings": scan_report.get("findings", [])
                    }, HTTPStatus.OK)
                    return
                except Exception as sc_err:
                    logger.exception("NexusShield scan error")
                    self._send_error_response(f"NexusShield Scan Failed: {str(sc_err)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

            # POST /api/tools/stream/parse (Execute EchoStream VoiceGuard DLP & semantic task extraction)
            if path in ("/api/tools/stream/parse", "/api/tools/stream/parse/"):
                input_text = body.get("text") or body.get("transcript") or body.get("content")
                if not input_text or not isinstance(input_text, str) or not input_text.strip():
                    self._send_error_response("Field 'text' or 'transcript' is required", HTTPStatus.BAD_REQUEST)
                    return

                try:
                    from echostream.voice_guard import VoiceGuard
                    from echostream.parser import SemanticStreamParser

                    # 1. VoiceGuard DLP Sanitize
                    guard = VoiceGuard()
                    audit = guard.scan_and_redact(input_text)
                    clean_text = audit["redacted_text"]

                    # 2. Semantic Stream Extraction
                    parser = SemanticStreamParser()
                    structure = parser.parse_stream(clean_text)

                    # 3. Stage Action Items directly as CorePulse Tasks
                    action_items = structure.get("action_items", [])
                    staged_tasks = []
                    for action in action_items:
                        task_payload = {
                            "title": action.get("title"),
                            "type": "task",
                            "category": action.get("category", "General"),
                            "priority": action.get("priority", "medium"),
                            "due_date": action.get("due_date", "Today"),
                            "estimated_minutes": action.get("estimated_minutes", 30),
                            "tags": action.get("tags", ["echostream", "voice-intake"]),
                            "source_quote": action.get("source_quote", ""),
                            "completed": False
                        }
                        saved = db.create_or_update_task(task_payload)
                        staged_tasks.append(saved)

                        # Dual-store integration: mirror staged task into CorePulse SQLite WAL store
                        try:
                            from corepulse.database_sqlite import sqlite_db
                            sqlite_db.create_or_update_task(saved)
                        except Exception as sq_err:
                            logger.debug("SQLite WAL mirror sync notice: %s", sq_err)

                    self._send_json_response({
                        "status": "success",
                        "message": f"Successfully parsed stream and staged {len(staged_tasks)} task(s) into CorePulse.",
                        "security_audit": audit,
                        "parsed_structure": structure,
                        "staged_tasks": staged_tasks,
                        "tasks_count": len(staged_tasks)
                    }, HTTPStatus.OK)
                    return
                except Exception as ps_err:
                    logger.exception("EchoStream parse error")
                    self._send_error_response(f"EchoStream Parse Failed: {str(ps_err)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

            # POST /api/tools/pipeline/scan (Trigger autonomous ingestion sweep on drop directory)
            if path in ("/api/tools/pipeline/scan", "/api/tools/pipeline/scan/"):
                try:
                    from echostream.pipeline import AutonomousIngestionPipeline
                    target_drop = body.get("drop_dir")
                    drop_dir = Path(target_drop).resolve() if target_drop else (PRODUCTS_DIR.parent / "data" / "transcripts")
                    pipeline = AutonomousIngestionPipeline(drop_dir=drop_dir, auto_dispatch=True)
                    try:
                        receipts = pipeline.scan_once()
                        telemetry = pipeline.get_telemetry()
                    finally:
                        pipeline.close()

                    self._send_json_response({
                        "status": "success",
                        "message": f"Autonomous ingestion sweep completed: {len(receipts)} transcript(s) processed.",
                        "processed_count": len(receipts),
                        "receipts": receipts,
                        "telemetry": telemetry
                    }, HTTPStatus.OK)
                    return
                except Exception as pl_err:
                    logger.exception("Pipeline sweep error")
                    self._send_error_response(f"Pipeline Sweep Failed: {str(pl_err)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

            self._send_error_response(f"Endpoint not found: {path}", HTTPStatus.NOT_FOUND)

        except ValueError as val_err:
            self._send_error_response(str(val_err), HTTPStatus.BAD_REQUEST)
        except Exception as ex:
            logger.exception("Error processing POST %s", path)
            self._send_error_response(f"Internal Server Error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_DELETE(self):
        """Handles DELETE /api/tasks?id=xyz."""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/tasks":
            task_id = query.get("id", [None])[0]
            if not task_id:
                self._send_error_response("Query parameter 'id' is required", HTTPStatus.BAD_REQUEST)
                return
            deleted = db.delete_task(task_id)
            if not deleted:
                self._send_error_response(f"Task '{task_id}' not found", HTTPStatus.NOT_FOUND)
                return
            try:
                from corepulse.database_sqlite import sqlite_db
                sqlite_db.delete_task(task_id)
            except Exception:
                pass
            self._send_json_response({
                "message": f"Task '{task_id}' deleted successfully",
                "id": task_id
            })
            return

        self._send_error_response(f"Cannot DELETE {path}", HTTPStatus.NOT_FOUND)

    def _serve_static(self, path: str):
        """Serves static files safely from the STATIC_DIR directory."""
        if path == "/" or not path:
            relative_path = "index.html"
        else:
            relative_path = path.lstrip("/")

        target_file = (STATIC_DIR / relative_path).resolve()

        # Path traversal guard
        try:
            target_file.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self._send_error_response("Forbidden", HTTPStatus.FORBIDDEN)
            return

        # SPA fallback: if file does not exist, serve index.html
        if not target_file.exists() or target_file.is_dir():
            target_file = STATIC_DIR / "index.html"

        if not target_file.exists():
            self._send_error_response("File Not Found", HTTPStatus.NOT_FOUND)
            return

        if target_file.suffix == ".js":
            content_type = "application/javascript"
        elif target_file.suffix == ".css":
            content_type = "text/css"
        elif target_file.suffix in (".html", ".htm"):
            content_type = "text/html"
        else:
            content_type, _ = mimetypes.guess_type(str(target_file))
            if content_type is None:
                content_type = "application/octet-stream"

        try:
            with open(target_file, "rb") as f:
                content = f.read()

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8" if "text" in content_type or "javascript" in content_type or "json" in content_type else content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache, must-revalidate")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except Exception as ex:
            logger.error("Failed to read static file %s: %s", target_file, ex)
            self._send_error_response("Internal Server Error reading static asset", HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format, *args):
        """Overridden to suppress noise or use clean standard logging format."""
        logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)
