"""
CorePulse Blinded Sync Relay Server
Lightweight, Zero-Dependency Blinded HTTP Relay for E2EE Cloud Sync.
Sprint 12 Implementation.

Security Architecture:
  - The relay server has ZERO access to encryption keys, passphrases, or plaintext data.
  - Blinded payloads are partitioned purely by `pair_token_hash` (derived client-side via SHA256).
  - High-throughput persistence via SQLite WAL mode (data/relay_store.sqlite3).
  - 100% Python Standard Library. Zero external pip dependencies.

Endpoints:
  - POST /v1/relay/push: Store an encrypted delta blob for a paired channel.
  - GET  /v1/relay/pull: Retrieve new encrypted deltas since sequence cursor.
  - GET  /v1/relay/health: System vitals, uptime, and storage telemetry.
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import parse_qs, urlparse

# Base Directory & Logging
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "corepulse" / "data"
DEFAULT_DB_PATH = DATA_DIR / "relay_store.sqlite3"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sync.relay")


class RelayStore:
    """Thread-safe SQLite storage backend for blinded encrypted payloads."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS blinded_records (
                        seq_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pair_token_hash TEXT NOT NULL,
                        client_id TEXT NOT NULL,
                        encrypted_blob TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_blinded_token_seq
                    ON blinded_records(pair_token_hash, seq_id);
                """)
                conn.commit()
            finally:
                conn.close()

    def push_record(self, pair_token_hash: str, client_id: str, encrypted_blob: str) -> int:
        """Stores a blinded encrypted delta record and returns sequential ID."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO blinded_records (pair_token_hash, client_id, encrypted_blob, created_at)
                    VALUES (?, ?, ?, ?);
                """, (pair_token_hash, client_id, encrypted_blob, now))
                seq_id = cursor.lastrowid
                conn.commit()
                return seq_id
            finally:
                conn.close()

    def pull_records(self, pair_token_hash: str, since_seq: int = 0, limit: int = 100) -> list:
        """Retrieves blinded records for given pair token since sequence ID."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT seq_id, client_id, encrypted_blob, created_at
                    FROM blinded_records
                    WHERE pair_token_hash = ? AND seq_id > ?
                    ORDER BY seq_id ASC
                    LIMIT ?;
                """, (pair_token_hash, since_seq, limit))
                rows = cursor.fetchall()
                return [
                    {
                        "seq_id": r["seq_id"],
                        "client_id": r["client_id"],
                        "encrypted_blob": r["encrypted_blob"],
                        "created_at": r["created_at"]
                    }
                    for r in rows
                ]
            finally:
                conn.close()

    def get_stats(self) -> dict:
        """Returns storage metrics."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), COUNT(DISTINCT pair_token_hash), MAX(seq_id) FROM blinded_records;")
                total, unique_tokens, max_seq = cursor.fetchone()
                return {
                    "total_records": total or 0,
                    "unique_paired_channels": unique_tokens or 0,
                    "latest_seq_id": max_seq or 0
                }
            finally:
                conn.close()


# Global store instance
relay_store = RelayStore()


class RelayRequestHandler(BaseHTTPRequestHandler):
    """HTTP request dispatcher for CorePulse Blinded Relay API."""

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json_response(self, data: dict, status: int = HTTPStatus.OK):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_error_response(self, message: str, status: int = HTTPStatus.BAD_REQUEST):
        self._send_json_response({"error": message, "status": status}, status=status)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = parse_qs(parsed.query)

        # 1. Health check
        if path in ("/v1/relay/health", "/health", ""):
            stats = relay_store.get_stats()
            uptime = time.time() - getattr(self.server, "start_time", time.time())
            self._send_json_response({
                "service": "CorePulse Blinded Relay",
                "version": "1.0.0",
                "status": "healthy",
                "uptime_seconds": round(uptime, 2),
                "telemetry": stats
            })
            return

        # 2. Pull deltas
        if path == "/v1/relay/pull":
            token = query.get("token", [None])[0]
            if not token:
                self._send_error_response("Query parameter 'token' (pair_token_hash) is required.", HTTPStatus.BAD_REQUEST)
                return
            try:
                since = int(query.get("since", [0])[0])
            except ValueError:
                since = 0

            try:
                limit = min(int(query.get("limit", [100])[0]), 500)
            except ValueError:
                limit = 100

            records = relay_store.pull_records(token, since_seq=since, limit=limit)
            latest_seq = max([r["seq_id"] for r in records], default=since)

            self._send_json_response({
                "token": token,
                "count": len(records),
                "since_seq": since,
                "latest_seq": latest_seq,
                "records": records
            })
            return

        self._send_error_response(f"Cannot GET {path}", HTTPStatus.NOT_FOUND)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 10 * 1024 * 1024:  # 10MB limit
            self._send_error_response("Payload exceeds maximum 10MB threshold", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return

        try:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            body = json.loads(raw_body)
        except Exception as ex:
            self._send_error_response(f"Malformed JSON body: {ex}", HTTPStatus.BAD_REQUEST)
            return

        # 1. Push blinded deltas
        if path == "/v1/relay/push":
            token = body.get("pair_token_hash")
            client_id = body.get("client_id")
            blob = body.get("encrypted_blob")

            if not token or not client_id or not blob:
                self._send_error_response("Fields 'pair_token_hash', 'client_id', and 'encrypted_blob' are required.", HTTPStatus.UNPROCESSABLE_ENTITY)
                return

            seq_id = relay_store.push_record(token, client_id, blob)
            logger.info("Stored blinded record #%d for channel %s... (client=%s)", seq_id, token[:12], client_id)

            self._send_json_response({
                "success": True,
                "seq_id": seq_id,
                "stored_at": datetime.now(timezone.utc).isoformat(),
                "message": "Blinded delta stored successfully."
            }, HTTPStatus.CREATED)
            return

        self._send_error_response(f"Cannot POST {path}", HTTPStatus.NOT_FOUND)

    def log_message(self, format, *args):
        logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)


class BlindedRelayServer:
    """Wrapper to run the blinded relay server programmatically or in daemon thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8081, db_path: Optional[Path] = None):
        global relay_store
        if db_path:
            relay_store = RelayStore(db_path)
        self.host = host
        self.port = port
        self.server = ThreadingHTTPServer((host, port), RelayRequestHandler)
        self.server.daemon_threads = True
        self.server.start_time = time.time()
        self.thread: Optional[threading.Thread] = None

    def start_background(self):
        """Starts server in a background daemon thread."""
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.2)  # Allow socket to bind
        logger.info("Blinded Relay daemon started at http://%s:%d", self.host, self.port)

    def stop(self):
        """Cleanly shuts down server."""
        self.server.shutdown()
        self.server.server_close()
        logger.info("Blinded Relay server stopped.")

    def serve_forever(self):
        """Runs synchronous blocking server loop."""
        logger.info("=" * 60)
        logger.info("  CorePulse Zero-Knowledge Blinded Sync Relay Server")
        logger.info("  Listening on: http://%s:%d", self.host, self.port)
        logger.info("  Zero plaintext data access. Zero external dependencies.")
        logger.info("=" * 60)
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.stop()


def main():
    parser = argparse.ArgumentParser(description="CorePulse Zero-Knowledge Blinded Sync Relay Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8081, help="Port to listen on (default: 8081)")
    parser.add_argument("--db", type=str, default=None, help="Custom SQLite database path for relay store")

    args = parser.parse_args()
    db_p = Path(args.db) if args.db else DEFAULT_DB_PATH
    srv = BlindedRelayServer(host=args.host, port=args.port, db_path=db_p)
    srv.serve_forever()


if __name__ == "__main__":
    main()
