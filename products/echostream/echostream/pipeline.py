"""
EchoStream Autonomous Background Ingestion Pipeline v1.0
Fulfills PRD_AUTONOMOUS_PIPELINE_V1.md.
Ambient computing engine that monitors a drop directory, applies in-flight VoiceGuard DLP,
extracts action items from multi-format transcripts (.txt, .md, .json, .vtt, .srt),
dispatches prioritized tasks into CorePulse, and manages atomic archival & quarantine.
Zero external dependencies (Python standard library only).
"""

import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from echostream.dispatcher import CorePulseDispatcher
from echostream.parser import SemanticStreamParser
from echostream.voice_guard import VoiceGuard

logger = logging.getLogger("echostream.pipeline")

# Supported file extensions
SUPPORTED_EXTENSIONS: Set[str] = {".txt", ".md", ".json", ".vtt", ".srt"}


def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 digest of file content."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_binary_file(file_path: Path) -> bool:
    """Detects whether a file contains raw binary data (null bytes)."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except Exception:
        return True


class PipelineRegistry:
    """
    SQLite-backed ingestion ledger tracking processed file hashes,
    tasks created, secrets redacted, and quarantine events.
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path).resolve()
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10.0,
                isolation_level=None
            )
            self._conn.row_factory = sqlite3.Row
            cursor = self._conn.cursor()
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA busy_timeout = 5000;")
            cursor.close()
        return self._conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_ingest_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    file_hash TEXT NOT NULL UNIQUE,
                    format TEXT NOT NULL,
                    tasks_extracted INTEGER NOT NULL DEFAULT 0,
                    secrets_redacted INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL, -- 'success', 'quarantined', 'duplicate'
                    error_message TEXT,
                    ingested_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingest_hash ON pipeline_ingest_registry (file_hash);")
            cursor.close()

    def close(self):
        """Closes SQLite connection."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    def is_hash_processed(self, file_hash: str) -> bool:
        """Returns True if the content hash has already been successfully ingested."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM pipeline_ingest_registry WHERE file_hash = ? AND status = 'success';",
                (file_hash,)
            )
            row = cursor.fetchone()
            cursor.close()
            return row is not None

    def record_ingestion(
        self,
        file_name: str,
        file_hash: str,
        format_type: str,
        tasks_extracted: int = 0,
        secrets_redacted: int = 0,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> int:
        """Inserts or updates an ingestion record in the SQLite ledger."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pipeline_ingest_registry 
                    (file_name, file_hash, format, tasks_extracted, secrets_redacted, status, error_message, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(file_hash) DO UPDATE SET
                    file_name = excluded.file_name,
                    tasks_extracted = excluded.tasks_extracted,
                    secrets_redacted = excluded.secrets_redacted,
                    status = excluded.status,
                    error_message = excluded.error_message,
                    ingested_at = CURRENT_TIMESTAMP;
            """, (file_name, file_hash, format_type, tasks_extracted, secrets_redacted, status, error_message))
            record_id = cursor.lastrowid
            cursor.close()
            return record_id

    def get_stats(self) -> Dict[str, Any]:
        """Calculates aggregate pipeline telemetry."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_files,
                    COALESCE(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END), 0) as success_files,
                    COALESCE(SUM(CASE WHEN status = 'quarantined' THEN 1 ELSE 0 END), 0) as quarantined_files,
                    COALESCE(SUM(CASE WHEN status = 'duplicate' THEN 1 ELSE 0 END), 0) as duplicate_files,
                    COALESCE(SUM(tasks_extracted), 0) as total_tasks,
                    COALESCE(SUM(secrets_redacted), 0) as total_secrets_scrubbed
                FROM pipeline_ingest_registry;
            """)
            row = cursor.fetchone()
            cursor.close()
            if row:
                return dict(row)
            return {
                "total_files": 0,
                "success_files": 0,
                "quarantined_files": 0,
                "duplicate_files": 0,
                "total_tasks": 0,
                "total_secrets_scrubbed": 0
            }

    def get_recent_ingestions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent ingestion audit entries."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, file_name, file_hash, format, tasks_extracted, secrets_redacted, status, error_message, ingested_at
                FROM pipeline_ingest_registry
                ORDER BY id DESC
                LIMIT ?;
            """, (limit,))
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]


class MultiFormatTranscriptNormalizer:
    """
    Standardizes varied speech/audio transcript exports into clean conversational text.
    Handles .txt, .md, .json (Whisper, Otter, EchoStream), .vtt, and .srt.
    """

    @staticmethod
    def normalize_file(file_path: Path) -> Tuple[str, str, Dict[str, Any]]:
        """
        Parses transcript file based on its extension into normalized text.
        Returns: (normalized_text, detected_format, metadata_dict)
        Raises ValueError on corrupt or empty files.
        """
        if not file_path.exists() or not file_path.is_file():
            raise ValueError(f"File '{file_path}' does not exist or is not a file.")

        file_size = file_path.stat().st_size
        if file_size == 0:
            raise ValueError(f"File '{file_path.name}' is empty (0 bytes).")

        if is_binary_file(file_path):
            raise ValueError(f"File '{file_path.name}' contains binary content or corrupted characters.")

        ext = file_path.suffix.lower()
        try:
            raw_content = file_path.read_text(encoding="utf-8", errors="replace").strip()
        except Exception as ex:
            raise ValueError(f"Unable to read file text: {ex}")

        if not raw_content:
            raise ValueError(f"File '{file_path.name}' contains no readable text content.")

        if ext == ".txt":
            return raw_content, "txt", {"size": file_size}

        elif ext == ".md":
            # Strip Markdown headers / bullet markers if desired, or keep as dialogue
            # Keep action item bullets intact for the SemanticStreamParser
            return raw_content, "md", {"size": file_size}

        elif ext == ".vtt":
            # WebVTT subtitle parsing
            lines: List[str] = []
            for line in raw_content.splitlines():
                line = line.strip()
                if not line or line.startswith("WEBVTT") or line.startswith("NOTE"):
                    continue
                # Skip cue timing arrows: 00:00:01.000 --> 00:00:04.000
                if re.search(r"\d{2}:\d{2}.*-->.*\d{2}:\d{2}", line):
                    continue
                # Transform <v SpeakerName>Dialogue</v> to [SpeakerName] Dialogue
                line = re.sub(r"<v\s+([^>]+)>", r"[\1] ", line)
                line = re.sub(r"</v>", "", line)
                lines.append(line.strip())
            normalized = "\n".join(l for l in lines if l)
            return normalized, "vtt", {"cues_count": len(lines)}

        elif ext == ".srt":
            # SubRip subtitle parsing
            lines: List[str] = []
            for line in raw_content.splitlines():
                line = line.strip()
                # Skip integer sequence indexes and timestamp arrows (00:01:20,000 --> 00:01:24,000)
                if not line or re.match(r"^\d+$", line) or re.search(r"\d{2}:\d{2}:\d{2},\d{3}\s*-->", line):
                    continue
                lines.append(line)
            normalized = "\n".join(l for l in lines if l)
            return normalized, "srt", {"lines_count": len(lines)}

        elif ext == ".json":
            # Structured transcript parsing
            try:
                data = json.loads(raw_content)
            except Exception as j_err:
                raise ValueError(f"Invalid JSON transcript structure: {j_err}")

            # 1. EchoStream JSON export
            if isinstance(data, dict):
                if "parsed_structure" in data and "action_items" in data["parsed_structure"]:
                    items = data["parsed_structure"]["action_items"]
                    text_parts = [f"[{item.get('assignee', 'Team')}] {item.get('title')}" for item in items]
                    return "\n".join(text_parts), "json", {"schema": "echostream"}
                # 2. Whisper JSON export
                if "segments" in data and isinstance(data["segments"], list):
                    dialogue = []
                    for seg in data["segments"]:
                        spk = seg.get("speaker") or seg.get("speaker_name") or "Speaker"
                        txt = seg.get("text", "").strip()
                        if txt:
                            dialogue.append(f"[{spk}] {txt}")
                    return "\n".join(dialogue), "json", {"schema": "whisper"}
                # 3. Otter JSON export
                if "transcript" in data and isinstance(data["transcript"], list):
                    dialogue = []
                    for turn in data["transcript"]:
                        spk = turn.get("speaker_name") or turn.get("speaker") or "Speaker"
                        txt = turn.get("transcript", "").strip()
                        if txt:
                            dialogue.append(f"[{spk}] {txt}")
                    return "\n".join(dialogue), "json", {"schema": "otter"}
                # 4. Generic text key
                for text_key in ("transcript", "transcription", "text", "content", "raw_text"):
                    if text_key in data and isinstance(data[text_key], str):
                        return data[text_key], "json", {"schema": "generic"}

            elif isinstance(data, list):
                # Array of turn objects
                dialogue = []
                for turn in data:
                    if isinstance(turn, dict):
                        spk = turn.get("speaker") or turn.get("speaker_name") or "Speaker"
                        txt = turn.get("text") or turn.get("transcript") or ""
                        if txt:
                            dialogue.append(f"[{spk}] {txt.strip()}")
                if dialogue:
                    return "\n".join(dialogue), "json", {"schema": "turn_array"}

            raise ValueError("Unrecognized JSON transcript structure; missing 'text', 'segments', or 'transcript' keys.")

        else:
            raise ValueError(f"Unsupported file format '{ext}'. Must be one of: {sorted(list(SUPPORTED_EXTENSIONS))}")


class AutonomousIngestionPipeline:
    """
    Autonomous background ingestion pipeline monitoring data/transcripts/.
    Provides drop-and-forget processing with VoiceGuard DLP and CorePulse dispatch.
    """

    def __init__(
        self,
        drop_dir: Path,
        processed_dir: Optional[Path] = None,
        quarantine_dir: Optional[Path] = None,
        registry_db_path: Optional[Path] = None,
        poll_interval: float = 1.0,
        settle_time: float = 0.3,
        auto_dispatch: bool = True,
        on_processed: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.drop_dir = Path(drop_dir).resolve()
        self.processed_dir = Path(processed_dir).resolve() if processed_dir else (self.drop_dir / "processed")
        self.quarantine_dir = Path(quarantine_dir).resolve() if quarantine_dir else (self.drop_dir / "quarantine")
        self.poll_interval = poll_interval
        self.settle_time = settle_time
        self.auto_dispatch = auto_dispatch
        self.on_processed = on_processed

        # Initialize folders
        self.drop_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        # Registry SQLite Database
        db_file = registry_db_path or (self.drop_dir / "pipeline_registry.sqlite3")
        self.registry = PipelineRegistry(db_file)

        # Core Engines
        self.guard = VoiceGuard()
        self.parser = SemanticStreamParser()
        self.dispatcher = CorePulseDispatcher()
        self.normalizer = MultiFormatTranscriptNormalizer()

        # Threading state
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    def is_running(self) -> bool:
        return self._is_running and self._thread is not None and self._thread.is_alive()

    def _is_file_settled(self, file_path: Path) -> bool:
        """Verifies that file write is finished (debounce stability check)."""
        try:
            stat1 = file_path.stat()
            time.sleep(self.settle_time)
            stat2 = file_path.stat()
            return stat1.st_size == stat2.st_size and stat1.st_mtime == stat2.st_mtime
        except (FileNotFoundError, PermissionError):
            return False

    def _handle_quarantine(self, file_path: Path, error_message: str):
        """Moves a malformed or corrupted file into the quarantine zone with an error log."""
        try:
            target_quarantine = self.quarantine_dir / file_path.name
            if target_quarantine.exists():
                suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_quarantine = self.quarantine_dir / f"{file_path.stem}_{suffix}{file_path.suffix}"

            shutil.move(str(file_path), str(target_quarantine))

            # Write companion .error.json
            error_file = target_quarantine.with_suffix(target_quarantine.suffix + ".error.json")
            error_file.write_text(json.dumps({
                "source_file": file_path.name,
                "quarantined_at": datetime.now(timezone.utc).isoformat(),
                "error": error_message,
                "file_size": target_quarantine.stat().st_size
            }, indent=2), encoding="utf-8")

            # Record in ledger
            file_hash = compute_sha256(target_quarantine) if target_quarantine.stat().st_size > 0 else "empty_file_hash"
            self.registry.record_ingestion(
                file_name=file_path.name,
                file_hash=file_hash,
                format_type=file_path.suffix.lstrip(".").lower() or "unknown",
                tasks_extracted=0,
                secrets_redacted=0,
                status="quarantined",
                error_message=error_message
            )
            logger.warning("Quarantined file %s: %s", file_path.name, error_message)
        except Exception as q_err:
            logger.error("Failed to quarantine file %s: %s", file_path.name, q_err)

    def _handle_archive(self, file_path: Path, date_str: str) -> Path:
        """Moves successfully ingested file into data/transcripts/processed/YYYY-MM-DD/."""
        archive_day_dir = self.processed_dir / date_str
        archive_day_dir.mkdir(parents=True, exist_ok=True)

        target_file = archive_day_dir / file_path.name
        if target_file.exists():
            suffix = datetime.now().strftime("%H%M%S")
            target_file = archive_day_dir / f"{file_path.stem}_{suffix}{file_path.suffix}"

        shutil.move(str(file_path), str(target_file))
        return target_file

    def ingest_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Executes the 6-stage autonomous ingestion lifecycle for a single transcript file.
        """
        if not file_path.exists() or not file_path.is_file():
            return None

        # Exclude dotfiles, temp files, receipts, error logs, and internal database/lock files
        name = file_path.name
        name_lower = name.lower()
        if (
            name.startswith(".")
            or name_lower.endswith((
                ".receipt.json", ".error.json", ".tmp", 
                ".sqlite3", ".sqlite3-shm", ".sqlite3-wal", 
                ".db", ".db-shm", ".db-wal"
            ))
            or ".sqlite3" in name_lower
        ):
            return None

        # Ensure not inside processed or quarantine directories
        try:
            if self.processed_dir in file_path.resolve().parents or self.quarantine_dir in file_path.resolve().parents:
                return None
        except Exception:
            pass

        # Check extension
        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            self._handle_quarantine(file_path, f"Unsupported file extension '{ext}'")
            return None

        # Stage 1: File Detection & Debounce
        if not self._is_file_settled(file_path):
            logger.debug("File %s still settling, waiting for write completion.", name)
            return None

        # Stage 2: Hash & Deduplication Check
        try:
            file_hash = compute_sha256(file_path)
        except Exception as h_err:
            self._handle_quarantine(file_path, f"Failed to compute SHA-256 hash: {h_err}")
            return None

        today_str = datetime.now().strftime("%Y-%m-%d")

        if self.registry.is_hash_processed(file_hash):
            logger.info("Duplicate transcript file detected (%s, hash=%s). Archiving without duplicate tasks.", name, file_hash[:8])
            archived_path = self._handle_archive(file_path, today_str)
            self.registry.record_ingestion(
                file_name=name,
                file_hash=file_hash,
                format_type=ext.lstrip("."),
                tasks_extracted=0,
                secrets_redacted=0,
                status="duplicate",
                error_message="Duplicate content hash detected"
            )
            return {
                "status": "duplicate",
                "source_file": name,
                "file_hash": file_hash,
                "archived_to": str(archived_path),
                "tasks_extracted": 0
            }

        # Stage 3 & 4: Multi-Format Normalization
        try:
            normalized_text, format_type, meta = self.normalizer.normalize_file(file_path)
        except ValueError as val_err:
            self._handle_quarantine(file_path, str(val_err))
            return None

        # Stage 3: In-Flight VoiceGuard DLP Audit & Redaction
        security_audit = self.guard.scan_and_redact(normalized_text)
        clean_text = security_audit["redacted_text"]

        # Stage 4: Semantic Transcript Parsing
        parsed_structure = self.parser.parse(clean_text)
        action_items = parsed_structure.get("action_items", [])

        # Enrich action items with autonomous pipeline tags & source reference
        for item in action_items:
            tags = item.setdefault("tags", [])
            if "autonomous-pipeline" not in tags:
                tags.append("autonomous-pipeline")
            if "transcript" not in tags:
                tags.append("transcript")
            file_tag = file_path.stem.replace(" ", "-").lower()
            if file_tag not in tags:
                tags.append(file_tag)

        # Stage 5: CorePulse Backlog Ingestion
        dispatch_report = None
        if self.auto_dispatch and action_items:
            dispatch_report = self.dispatcher.dispatch_batch(action_items)
            logger.info(
                "Ingested %d task(s) into CorePulse from '%s' (mode=%s)",
                len(action_items), name, dispatch_report.get("mode") if dispatch_report else "none"
            )

        # Stage 6: File Lifecycle Archival
        archived_path = self._handle_archive(file_path, today_str)

        # Construct Ingestion Receipt
        receipt = {
            "status": "success",
            "source_file": name,
            "format": format_type,
            "file_hash": file_hash,
            "archived_to": str(archived_path),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "tasks_extracted": len(action_items),
            "secrets_redacted": security_audit["incidents_count"],
            "security_audit": {
                "is_clean": security_audit["is_clean"],
                "incidents_count": security_audit["incidents_count"],
                "incidents": security_audit.get("incidents", [])
            },
            "parsed_structure": parsed_structure,
            "dispatch_report": dispatch_report
        }

        # Write receipt next to archived file
        receipt_file = archived_path.with_suffix(archived_path.suffix + ".receipt.json")
        try:
            receipt_file.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        except Exception:
            pass

        # Record in persistent registry
        self.registry.record_ingestion(
            file_name=name,
            file_hash=file_hash,
            format_type=format_type,
            tasks_extracted=len(action_items),
            secrets_redacted=security_audit["incidents_count"],
            status="success"
        )

        if self.on_processed:
            try:
                self.on_processed(receipt)
            except Exception as cb_err:
                logger.error("Error in on_processed callback: %s", cb_err)

        return receipt

    def scan_once(self) -> List[Dict[str, Any]]:
        """
        Scans drop directory once, ingesting all pending transcript files.
        Returns list of processed receipts.
        """
        receipts: List[Dict[str, Any]] = []
        if not self.drop_dir.exists():
            return receipts

        try:
            entries = sorted(self.drop_dir.iterdir(), key=lambda p: p.stat().st_mtime if p.exists() else 0)
        except Exception as ex:
            logger.error("Failed to read drop directory %s: %s", self.drop_dir, ex)
            return receipts

        for entry in entries:
            if entry.is_file():
                res = self.ingest_file(entry)
                if res:
                    receipts.append(res)

        return receipts

    def _poll_loop(self):
        """Continuous background polling loop."""
        logger.info("Autonomous Ingestion Pipeline daemon started on '%s' (poll=%.1fs)", self.drop_dir, self.poll_interval)
        try:
            while not self._stop_event.is_set():
                try:
                    self.scan_once()
                except Exception as ex:
                    logger.error("Unexpected error in pipeline polling loop: %s", ex)

                self._stop_event.wait(self.poll_interval)
        finally:
            self._is_running = False
            logger.info("Autonomous Ingestion Pipeline daemon stopped.")

    def start(self, daemon: bool = True):
        """Starts background watcher thread."""
        if self.is_running():
            logger.warning("Pipeline is already running.")
            return

        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(
            target=self._poll_loop,
            daemon=daemon,
            name="AutonomousIngestionPipelineThread"
        )
        self._thread.start()

    def stop(self, timeout: float = 3.0):
        """Gracefully stops background watcher thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._thread = None
        self._is_running = False

    def close(self):
        """Stops thread and releases database handles."""
        self.stop()
        if hasattr(self, "registry") and self.registry:
            self.registry.close()

    def run_forever(self):
        """Runs blocking watcher process until SIGINT."""
        self.start(daemon=False)
        try:
            while not self._stop_event.is_set():
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\nShutting down Autonomous Ingestion Pipeline...")
            self.stop()

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns comprehensive telemetry for Cockpit and health dashboards."""
        stats = self.registry.get_stats()
        recent = self.registry.get_recent_ingestions(limit=8)
        return {
            "status": "watching" if self.is_running() else "idle",
            "drop_dir": str(self.drop_dir),
            "processed_dir": str(self.processed_dir),
            "quarantine_dir": str(self.quarantine_dir),
            "poll_interval_seconds": self.poll_interval,
            "stats": stats,
            "recent_ingestions": recent
        }
