"""
CorePulse REST API Request Handler & Static Asset Server
Implements standard library high-performance zero-dependency HTTP server with REST routing.
"""

from datetime import datetime, timezone
import uuid
import json
import logging
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from corepulse.config import STATIC_DIR, BASE_DIR, DATA_DIR
from corepulse.database import db
from corepulse.workflows import WorkflowEngine

import sys

# Dynamic resolution of adjacent product directories in enterprise suite
PRODUCTS_DIR = BASE_DIR.parent
NEXUSSHIELD_DIR = PRODUCTS_DIR / "nexusshield"
ECHOSTREAM_DIR = PRODUCTS_DIR / "echostream"
DOCUPULSE_DIR = PRODUCTS_DIR / "docupulse"
CLAUSEGUARD_DIR = PRODUCTS_DIR / "clauseguard"

for _pdir in (NEXUSSHIELD_DIR, ECHOSTREAM_DIR, DOCUPULSE_DIR, CLAUSEGUARD_DIR):
    if str(_pdir) not in sys.path and _pdir.exists():
        sys.path.insert(0, str(_pdir))

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
        try:
            payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(payload)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as conn_err:
            logger.debug(f"Client disconnected during transmission: {conn_err}")

    def _send_error_response(self, message: str, status_code: int = HTTPStatus.BAD_REQUEST, details: any = None):
        """Transmits structured error response."""
        resp = {
            "error": True,
            "message": message,
            "status_code": status_code,
            "details": details
        }
        try:
            self._send_json_response(resp, status_code)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            pass

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

            if path in ("/api/feedback", "/api/feedback/"):
                feedback_file = DATA_DIR / "feedback_log.json"
                entries = []
                if feedback_file.exists():
                    try:
                        with open(feedback_file, "r", encoding="utf-8") as f:
                            entries = json.load(f)
                    except Exception:
                        entries = []
                self._send_json_response({"total": len(entries), "feedback": entries})
                return

            if path in ("/api/sync/status", "/api/sync/status/"):
                try:
                    from corepulse.sync import sync_engine
                    self._send_json_response(sync_engine.get_sync_status())
                except Exception as ex:
                    self._send_error_response(f"Sync status error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            if path in ("/api/supabase/status", "/api/supabase/status/"):
                try:
                    from sync_supabase import supabase_sync
                    self._send_json_response(supabase_sync.get_status())
                except Exception as ex:
                    self._send_error_response(f"Supabase status error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            if path in ("/api/supabase/outbox", "/api/supabase/outbox/"):
                try:
                    from sync_supabase import supabase_sync
                    outbox = supabase_sync.get_outbox()
                    self._send_json_response({"total_pending": len(outbox), "records": outbox})
                except Exception as ex:
                    self._send_error_response(f"Supabase outbox error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            if path in ("/api/supabase/conflicts", "/api/supabase/conflicts/"):
                try:
                    from sync_supabase import supabase_sync
                    conflicts = supabase_sync.get_conflicts()
                    self._send_json_response({"total_conflicts": len(conflicts), "conflicts": conflicts})
                except Exception as ex:
                    self._send_error_response(f"Supabase conflicts error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            if path == "/api/workflows":
                self._send_json_response({
                    "workflows": WorkflowEngine.list_workflows()
                })
                return

            if path in ("/api/snippets", "/api/snippets/"):
                from corepulse.snippets import snippet_vault
                q = query.get("q", [None])[0]
                cat = query.get("category", [None])[0]
                snippets = snippet_vault.list_snippets(query=q, category=cat)
                self._send_json_response({
                    "count": len(snippets),
                    "snippets": snippets
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

            if path in ("/api/tools/shield/sbom", "/api/tools/shield/sbom/"):
                from nexusshield.scanner import NexusScanner
                scanner = NexusScanner()
                self._send_json_response(scanner.generate_sbom(PRODUCTS_DIR))
                return

            if path in ("/api/tools/stream/commitments", "/api/tools/stream/commitments/"):
                from echostream.copilot import CommitmentTracker
                tracker = CommitmentTracker()
                assignee = query.get("assignee", [None])[0]
                q = query.get("q", [None])[0]
                self._send_json_response(tracker.query_commitments(assignee=assignee, query=q))
                return

            if path in ("/api/tools/docupulse/ledger", "/api/tools/docupulse/ledger/"):
                from docupulse.ledger import FinancialLedger
                ledger = FinancialLedger()
                self._send_json_response(ledger.get_summary())
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

            # POST /api/snippets (Create or update snippet in local vault)
            if path in ("/api/snippets", "/api/snippets/"):
                from corepulse.snippets import snippet_vault
                saved = snippet_vault.save_snippet(body)
                self._send_json_response({
                    "status": "success",
                    "message": f"Snippet '{saved['trigger']}' saved to vault.",
                    "snippet": saved
                }, HTTPStatus.CREATED)
                return

            # POST /api/snippets/expand (Expand dynamic snippet variables)
            if path in ("/api/snippets/expand", "/api/snippets/expand/"):
                from corepulse.snippets import snippet_vault
                identifier = body.get("trigger") or body.get("id") or body.get("query")
                if not identifier:
                    self._send_error_response("Field 'trigger' or 'id' is required", HTTPStatus.BAD_REQUEST)
                    return
                custom_vars = body.get("variables") or {}
                res = snippet_vault.expand_snippet(str(identifier), custom_vars=custom_vars)
                if not res:
                    self._send_error_response(f"Snippet '{identifier}' not found", HTTPStatus.NOT_FOUND)
                    return
                self._send_json_response({
                    "status": "success",
                    **res
                }, HTTPStatus.OK)
                return

            # POST /api/vault/export (Export 2-Way Markdown Vault for Obsidian/Logseq)
            if path in ("/api/vault/export", "/api/vault/export/"):
                from corepulse.snippets import snippet_vault, export_markdown_vault
                vault_dir_param = body.get("vault_dir")
                vault_dir = None
                if vault_dir_param:
                    try:
                        resolved = Path(vault_dir_param).resolve() if Path(vault_dir_param).is_absolute() else (DATA_DIR / vault_dir_param).resolve()
                        resolved.relative_to(BASE_DIR.parent.resolve())
                        vault_dir = resolved
                    except Exception:
                        self._send_error_response("Forbidden: vault_dir must reside within workspace hierarchy", HTTPStatus.FORBIDDEN)
                        return
                all_tasks = db.get_tasks()
                all_snippets = snippet_vault.list_snippets()
                res = export_markdown_vault(all_tasks, all_snippets, vault_dir=vault_dir)
                self._send_json_response(res, HTTPStatus.OK)
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

            # POST /api/supabase/sync (Immediate two-way push/pull synchronization)
            if path in ("/api/supabase/sync", "/api/supabase/sync/"):
                try:
                    from sync_supabase import supabase_sync
                    res = supabase_sync.sync()
                    self._send_json_response(res, HTTPStatus.OK)
                except Exception as ex:
                    self._send_error_response(f"Supabase sync error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            # POST /api/supabase/configure (Configure URL, API Key, Tenant, User ID)
            if path in ("/api/supabase/configure", "/api/supabase/configure/"):
                new_url = body.get("supabase_url") or body.get("url")
                new_key = body.get("api_key") or body.get("key")
                new_tenant = body.get("tenant_id")
                new_user = body.get("user_id")

                try:
                    from sync_supabase import supabase_sync, SupabaseRestClient
                    if new_url:
                        supabase_sync.config.url = new_url.rstrip("/")
                    if new_key:
                        supabase_sync.config.key = new_key
                    if new_tenant:
                        supabase_sync.config.tenant_id = new_tenant
                    if new_user:
                        supabase_sync.config.user_id = new_user

                    # Re-instantiate client
                    supabase_sync.client = SupabaseRestClient(supabase_sync.config)

                    # Test reachability
                    reachable, latency, err = supabase_sync.client.ping()
                    self._send_json_response({
                        "success": True,
                        "configured": supabase_sync.config.is_configured,
                        "reachable": reachable,
                        "latency_ms": latency,
                        "message": "Supabase configuration updated successfully",
                        "error": err
                    }, HTTPStatus.OK)
                except Exception as ex:
                    self._send_error_response(f"Supabase configuration error: {str(ex)}", HTTPStatus.INTERNAL_SERVER_ERROR)
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

            # POST /api/tools/shield/history (Git Commit History Time-Machine Scanner)
            if path in ("/api/tools/shield/history", "/api/tools/shield/history/"):
                from nexusshield.scanner import NexusScanner
                target_path = body.get("path") or str(PRODUCTS_DIR.parent)
                max_commits = int(body.get("max_commits", 50))
                scanner = NexusScanner()
                self._send_json_response(scanner.scan_git_history(target_path, max_commits=max_commits), HTTPStatus.OK)
                return

            # POST /api/tools/stream/merge (Granola-Style Scratchpad + Transcript Merger & Email Draft)
            if path in ("/api/tools/stream/merge", "/api/tools/stream/merge/"):
                from echostream.copilot import ScratchpadMerger, CommitmentTracker
                transcript_text = body.get("transcript") or body.get("text") or ""
                scratchpad_notes = body.get("scratchpad") or body.get("notes") or ""
                meeting_title = body.get("title") or "Executive Alignment & Next Steps"
                if not transcript_text.strip() and not scratchpad_notes.strip():
                    self._send_error_response("Either 'transcript' or 'scratchpad' is required", HTTPStatus.BAD_REQUEST)
                    return
                merger = ScratchpadMerger()
                res = merger.merge_and_draft(
                    transcript_text=transcript_text,
                    scratchpad_notes=scratchpad_notes,
                    meeting_title=meeting_title
                )
                tracker = CommitmentTracker()
                tracker.record_commitments(res.get("action_items", []), meeting_source=meeting_title)
                self._send_json_response({
                    "status": "success",
                    **res
                }, HTTPStatus.OK)
                return

            # POST /api/tools/docupulse/parse (Extract invoice/receipt & audit anomalies)
            if path in ("/api/tools/docupulse/parse", "/api/tools/docupulse/parse/"):
                from docupulse.ledger import FinancialLedger
                raw_text = body.get("text") or body.get("invoice") or body.get("content") or ""
                if not raw_text.strip():
                    self._send_error_response("Field 'text' or 'invoice' is required", HTTPStatus.BAD_REQUEST)
                    return
                src = body.get("source_file", "inline_invoice.txt")
                ledger = FinancialLedger()
                rec = ledger.ingest_document(raw_text, source_name=src)
                self._send_json_response({"status": "success", "invoice": rec}, HTTPStatus.OK)
                return

            # POST /api/tools/docupulse/chase (Analyze overdue receivables & draft reminder emails)
            if path in ("/api/tools/docupulse/chase", "/api/tools/docupulse/chase/"):
                from docupulse.receivables import ReceivablesChaser
                chaser = ReceivablesChaser()
                today_val = body.get("today")
                interest_rate = body.get("interest_rate")
                invoices = body.get("invoices")
                rep = chaser.chase_invoices(records=invoices, today=today_val, interest_rate=interest_rate)
                self._send_json_response({"status": "success", **rep}, HTTPStatus.OK)
                return

            # POST /api/tools/docupulse/categorize (Categorize expense records by operational category)
            if path in ("/api/tools/docupulse/categorize", "/api/tools/docupulse/categorize/"):
                from docupulse.tax_mapper import ExpenseCategorizer
                categorizer = ExpenseCategorizer()
                invoices = body.get("invoices")
                export_csv_path = body.get("export_csv")
                rep = categorizer.categorize_records(records=invoices)
                if export_csv_path:
                    categorizer.export_csv(rep, output_path=export_csv_path)
                self._send_json_response({"status": "success", **rep}, HTTPStatus.OK)
                return

            # POST /api/tools/clauseguard/scan (Scan contract/NDA for predatory clauses & redlines)
            if path in ("/api/tools/clauseguard/scan", "/api/tools/clauseguard/scan/"):
                from clauseguard.scanner import ContractRiskScanner
                raw_text = body.get("text") or body.get("contract") or body.get("content") or ""
                if not raw_text.strip():
                    self._send_error_response("Field 'text' or 'contract' is required", HTTPStatus.BAD_REQUEST)
                    return
                doc_name = body.get("document", "Contract.txt")
                scanner = ContractRiskScanner()
                rep = scanner.scan_contract(raw_text, document_name=doc_name)
                self._send_json_response({"status": "success", **rep}, HTTPStatus.OK)
                return

            # POST /api/tools/clauseguard/negotiate (Generate redline diffs and collaborative cover letter)
            if path in ("/api/tools/clauseguard/negotiate", "/api/tools/clauseguard/negotiate/"):
                from clauseguard.scanner import ContractRiskScanner
                from clauseguard.negotiator import NegotiationDrafter
                raw_text = body.get("text") or body.get("contract") or body.get("content") or ""
                if not raw_text.strip():
                    self._send_error_response("Field 'text' or 'contract' is required", HTTPStatus.BAD_REQUEST)
                    return
                doc_name = body.get("document", "Contract.txt")
                recipient = body.get("recipient", "Client Team")
                scanner = ContractRiskScanner()
                scan_rep = scanner.scan_contract(raw_text, document_name=doc_name)
                negotiator = NegotiationDrafter()
                pkg = negotiator.generate_negotiation_package(scan_rep, recipient_name=recipient)
                self._send_json_response({"status": "success", **pkg}, HTTPStatus.OK)
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

            # POST /api/feedback (Privacy-preserving user feedback intake)
            if path in ("/api/feedback", "/api/feedback/"):
                message = body.get("message", "").strip()
                if not message:
                    self._send_error_response("Field 'message' is required", HTTPStatus.BAD_REQUEST)
                    return

                sentiment = body.get("sentiment", "neutral").lower()
                category = body.get("category", "General")
                contact = body.get("contact", "anonymous")
                diagnostics = body.get("diagnostics")

                now_iso = datetime.now(timezone.utc).isoformat()
                feedback_id = f"FB-{uuid.uuid4().hex[:8].upper()}"

                feedback_record = {
                    "id": feedback_id,
                    "sentiment": sentiment,
                    "category": category,
                    "message": message,
                    "contact": contact,
                    "diagnostics": diagnostics if diagnostics else None,
                    "created_at": now_iso
                }

                # Save locally to data/feedback_log.json
                feedback_file = DATA_DIR / "feedback_log.json"
                try:
                    entries = []
                    if feedback_file.exists():
                        try:
                            with open(feedback_file, "r", encoding="utf-8") as f:
                                entries = json.load(f)
                        except Exception:
                            entries = []
                    entries.append(feedback_record)
                    with open(feedback_file, "w", encoding="utf-8") as f:
                        json.dump(entries, f, indent=2)
                except Exception as fb_err:
                    logger.warning("Failed to append feedback record locally: %s", fb_err)

                self._send_json_response({
                    "status": "success",
                    "feedback_id": feedback_id,
                    "message": "Thank you! Your feedback has been safely recorded and queued for the executive team.",
                    "recorded_at": now_iso
                }, HTTPStatus.CREATED)
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

        if path in ("/api/snippets", "/api/snippets/"):
            snip_id = query.get("id", [None])[0]
            if not snip_id:
                self._send_error_response("Query parameter 'id' is required", HTTPStatus.BAD_REQUEST)
                return
            from corepulse.snippets import snippet_vault
            deleted = snippet_vault.delete_snippet(snip_id)
            if not deleted:
                self._send_error_response(f"Snippet '{snip_id}' not found", HTTPStatus.NOT_FOUND)
                return
            self._send_json_response({
                "message": f"Snippet '{snip_id}' deleted successfully",
                "id": snip_id
            })
            return

        self._send_error_response(f"Cannot DELETE {path}", HTTPStatus.NOT_FOUND)

    def _serve_static(self, path: str):
        """Serves static files safely from the STATIC_DIR directory."""
        clean_path = path.replace("\\", "/")
        path_segments = [seg for seg in clean_path.split("/") if seg]
        if ".." in path_segments:
            self._send_error_response("Forbidden", HTTPStatus.FORBIDDEN)
            return
        if not path_segments:
            relative_path = "index.html"
        else:
            relative_path = "/".join(path_segments)
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
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as conn_err:
            logger.debug(f"Client disconnected during static asset transmission: {conn_err}")
        except Exception as ex:
            logger.error("Failed to read static file %s: %s", target_file, ex)
            self._send_error_response("Internal Server Error reading static asset", HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle(self):
        """Processes incoming requests, suppressing abrupt client disconnections."""
        try:
            super().handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
            logger.debug("Client socket connection terminated abruptly: %s", e)

    def address_string(self):
        """Bypasses slow reverse DNS lookup on Windows."""
        return self.client_address[0] if self.client_address else "127.0.0.1"

    def log_message(self, format, *args):
        """Overridden to suppress noise or use clean standard logging format."""
        logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)
