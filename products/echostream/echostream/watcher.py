"""
EchoStream Autonomous Transcript Ingestion Pipeline (Watcher Engine)
Zero-dependency directory watcher for audio transcripts and thought dumps.
Monitors an inbox folder, intercepts credentials via VoiceGuard DLP,
extracts action items via SemanticStreamParser, and auto-dispatches into CorePulse.
"""

import hashlib
import json
import logging
import os
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from echostream.dispatcher import CorePulseDispatcher
from echostream.parser import SemanticStreamParser
from echostream.voice_guard import VoiceGuard

logger = logging.getLogger("echostream.watcher")

# Supported transcript document extensions
SUPPORTED_EXTENSIONS: Set[str] = {".txt", ".md", ".vtt", ".srt", ".json", ".log"}


def compute_file_hash(path: Path) -> str:
    """Computes SHA256 checksum of file for deduplication."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class TranscriptWatcher:
    """
    Zero-dependency polling file watcher and automated cognitive triage pipeline.
    Runs on standard library Python 3.8+.
    """

    def __init__(
        self,
        watch_dir: Path,
        archive_dir: Optional[Path] = None,
        poll_interval: float = 2.0,
        settle_time: float = 1.0,
        auto_dispatch: bool = True,
        on_processed: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.watch_dir = Path(watch_dir).resolve()
        self.archive_dir = Path(archive_dir).resolve() if archive_dir else (self.watch_dir / "archive")
        self.poll_interval = poll_interval
        self.settle_time = settle_time
        self.auto_dispatch = auto_dispatch
        self.on_processed = on_processed

        # Components
        self.guard = VoiceGuard()
        self.parser = SemanticStreamParser()
        self.dispatcher = CorePulseDispatcher()

        # State tracking: {filepath: (mtime, size, hash)}
        self._processed_files: Set[str] = set()
        self._file_snapshots: Dict[str, Tuple[float, int]] = {}

        # Threading controls
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Ensure directories exist
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        if self.archive_dir:
            self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _is_file_settled(self, file_path: Path) -> bool:
        """
        Verifies that file writes are completely finished by checking
        that file size has remained stable across the settle window.
        """
        try:
            stat1 = file_path.stat()
            time.sleep(self.settle_time)
            stat2 = file_path.stat()
            return stat1.st_size == stat2.st_size and stat1.st_mtime == stat2.st_mtime
        except (FileNotFoundError, PermissionError):
            return False

    def process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Ingests a single transcript file through VoiceGuard DLP, Semantic Parser,
        and CorePulse Task Dispatcher.
        """
        if not file_path.exists() or not file_path.is_file():
            return None

        file_key = str(file_path.resolve())
        if file_key in self._processed_files:
            return None

        # Verify extension
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return None

        # Ignore dotfiles, temp files, receipts, and archive contents
        if file_path.name.startswith(".") or file_path.name.endswith(".receipt.json") or file_path.name.endswith(".tmp"):
            return None
        if self.archive_dir and self.archive_dir in file_path.parents:
            return None

        # Debounce settle check
        if not self._is_file_settled(file_path):
            logger.debug("File %s still settling, skipping this cycle.", file_path.name)
            return None

        try:
            raw_text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as ex:
            logger.error("Failed to read file %s: %s", file_path, ex)
            return None

        if not raw_text.strip():
            logger.debug("File %s is empty, skipping.", file_path.name)
            return None

        file_hash = compute_file_hash(file_path)
        logger.info("Processing transcript file: %s (hash=%s)", file_path.name, file_hash[:8])

        # Step 1: VoiceGuard DLP Scan & Redact
        security_audit = self.guard.scan_and_redact(raw_text)
        clean_text = security_audit["redacted_text"]

        # Step 2: Semantic Thought & Meeting Parser
        parsed_structure = self.parser.parse(clean_text)

        # Step 3: Dispatch extracted action items to CorePulse
        action_items = parsed_structure.get("action_items", [])
        dispatch_report = None
        if self.auto_dispatch and action_items:
            dispatch_report = self.dispatcher.dispatch_batch(action_items)
            logger.info(
                "Dispatched %d task(s) into CorePulse (mode=%s)",
                len(action_items),
                dispatch_report.get("mode", "unknown") if dispatch_report else "none"
            )

        # Construct Pipeline Execution Receipt
        receipt = {
            "source_file": file_path.name,
            "source_path": str(file_path.resolve()),
            "sha256": file_hash,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "file_size_bytes": file_path.stat().st_size,
            "session_type": parsed_structure.get("session_type", "stream"),
            "security_audit": {
                "is_clean": security_audit["is_clean"],
                "incidents_count": security_audit["incidents_count"],
                "incidents": security_audit.get("incidents", [])
            },
            "tasks_extracted": len(action_items),
            "parsed_structure": parsed_structure,
            "dispatch_report": dispatch_report
        }

        # Step 4: Archive or Write Receipt
        if self.archive_dir:
            try:
                dest_file = self.archive_dir / file_path.name
                # Avoid collision in archive
                if dest_file.exists():
                    timestamp_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
                    dest_file = self.archive_dir / f"{file_path.stem}_{timestamp_suffix}{file_path.suffix}"

                shutil.move(str(file_path), str(dest_file))
                receipt["archived_to"] = str(dest_file)

                # Write alongside archive
                receipt_path = dest_file.with_suffix(dest_file.suffix + ".receipt.json")
                receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            except Exception as mv_err:
                logger.warning("Failed to move %s to archive: %s", file_path.name, mv_err)
                receipt_path = file_path.with_suffix(file_path.suffix + ".receipt.json")
                receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        else:
            receipt_path = file_path.with_suffix(file_path.suffix + ".receipt.json")
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

        self._processed_files.add(file_key)

        if self.on_processed:
            try:
                self.on_processed(receipt)
            except Exception as cb_err:
                logger.error("Callback error on_processed: %s", cb_err)

        return receipt

    def scan_once(self) -> List[Dict[str, Any]]:
        """
        Executes a single sweep across the watch directory.
        Returns list of processed file receipts.
        """
        receipts: List[Dict[str, Any]] = []
        if not self.watch_dir.exists():
            return receipts

        try:
            entries = sorted(self.watch_dir.iterdir(), key=lambda p: p.stat().st_mtime if p.exists() else 0)
        except Exception as ex:
            logger.error("Failed to list watch directory %s: %s", self.watch_dir, ex)
            return receipts

        for entry in entries:
            if entry.is_file():
                res = self.process_file(entry)
                if res:
                    receipts.append(res)

        return receipts

    def _poll_loop(self):
        """Internal background polling loop."""
        logger.info("Autonomous Transcript Watcher started on '%s' (interval=%.1fs)", self.watch_dir, self.poll_interval)
        while not self._stop_event.is_set():
            try:
                self.scan_once()
            except Exception as loop_ex:
                logger.error("Watcher polling loop error: %s", loop_ex)

            # Responsive wait with stop event
            self._stop_event.wait(self.poll_interval)
        logger.info("Autonomous Transcript Watcher stopped gracefully.")

    def start(self, daemon: bool = True):
        """Starts background watcher thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Watcher thread is already active.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=daemon, name="EchoStreamWatcherThread")
        self._thread.start()

    def stop(self, timeout: float = 3.0):
        """Stops background watcher thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._thread = None

    def run_forever(self):
        """Runs the watcher blocking the main thread until SIGINT / Ctrl+C."""
        self.start(daemon=False)
        try:
            while not self._stop_event.is_set():
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\nShutting down EchoStream transcript watcher...")
            self.stop()
