"""
EchoStream Autonomous Background Ingestion Pipeline Automated Test Suite
Fulfills QA Validation Matrix in PRD_AUTONOMOUS_PIPELINE_V1.md:
QA-PIPE-01 to QA-PIPE-07:
- Raw text (.txt) ingestion
- WebVTT (.vtt) subtitle normalization
- SubRip (.srt) subtitle normalization
- JSON transcript export ingestion (Whisper / Otter / EchoStream)
- In-flight VoiceGuard DLP credential redaction
- SHA-256 deduplication and idempotent archival
- Corrupt and 0-byte file quarantine isolation
- Write-safety debounce stability
- Telemetry reporting and persistent registry stats
"""

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

_TEST_TMP_DIR = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
os.environ.setdefault("COREPULSE_TEST_MODE", "1")
os.environ.setdefault("COREPULSE_DATA_DIR", _TEST_TMP_DIR.name)

# Add project paths to sys.path
TEST_DIR = Path(__file__).resolve().parent
ECHOSTREAM_DIR = TEST_DIR.parent
PRODUCTS_DIR = ECHOSTREAM_DIR.parent
COREPULSE_DIR = PRODUCTS_DIR / "corepulse"

if str(ECHOSTREAM_DIR) not in sys.path:
    sys.path.insert(0, str(ECHOSTREAM_DIR))
if str(COREPULSE_DIR) not in sys.path:
    sys.path.insert(0, str(COREPULSE_DIR))

from echostream.pipeline import (
    AutonomousIngestionPipeline,
    MultiFormatTranscriptNormalizer,
    PipelineRegistry,
    compute_sha256
)


class TestAutonomousIngestionPipeline(unittest.TestCase):
    """Integration test suite for Autonomous Ingestion Pipeline."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="echostream_pipeline_test_")
        self.drop_dir = Path(self.tmp_dir) / "transcripts"
        self.processed_dir = self.drop_dir / "processed"
        self.quarantine_dir = self.drop_dir / "quarantine"
        self.registry_db = Path(self.tmp_dir) / "registry.sqlite3"

        self.pipeline = AutonomousIngestionPipeline(
            drop_dir=self.drop_dir,
            processed_dir=self.processed_dir,
            quarantine_dir=self.quarantine_dir,
            registry_db_path=self.registry_db,
            poll_interval=0.1,
            settle_time=0.02,
            auto_dispatch=True
        )

    def tearDown(self):
        self.pipeline.close()
        time.sleep(0.05)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_qa_pipe_01_raw_text_ingestion(self):
        """QA-PIPE-01: Verifies raw .txt transcript ingestion and task extraction."""
        txt_file = self.drop_dir / "standup_notes.txt"
        txt_file.write_text(
            "[David CTO] Good morning team. We must finalize the security roadmap by Friday !p1.\n"
            "[Sarah] I will deploy the auth update and run regression testing before Wednesday.\n"
            "[David CTO] Perfect. I will review the client SOW by Friday afternoon.",
            encoding="utf-8"
        )

        receipts = self.pipeline.scan_once()
        self.assertEqual(len(receipts), 1)
        receipt = receipts[0]

        self.assertEqual(receipt["status"], "success")
        self.assertEqual(receipt["source_file"], "standup_notes.txt")
        self.assertEqual(receipt["format"], "txt")
        self.assertGreaterEqual(receipt["tasks_extracted"], 2)

        # File must be archived in YYYY-MM-DD folder
        self.assertFalse(txt_file.exists(), "Original file must be removed from drop zone")
        self.assertTrue(Path(receipt["archived_to"]).exists(), "File must exist in processed archive")
        self.assertIn("processed", receipt["archived_to"])

    def test_02_qa_pipe_02_webvtt_subtitle_ingestion(self):
        """QA-PIPE-02: Verifies WebVTT (.vtt) subtitle ingestion, tag stripping, and speaker extraction."""
        vtt_file = self.drop_dir / "q1_planning.vtt"
        vtt_file.write_text(
            "WEBVTT - Zoom Meeting Recording\n\n"
            "00:00:01.000 --> 00:00:04.500\n"
            "<v Alex Lead>We need to migrate our database to SQLite WAL mode before tomorrow !p0.</v>\n\n"
            "00:00:05.000 --> 00:00:09.000\n"
            "<v Elena>I will benchmark the write throughput and verify zero collisions.</v>\n",
            encoding="utf-8"
        )

        receipts = self.pipeline.scan_once()
        self.assertEqual(len(receipts), 1)
        receipt = receipts[0]

        self.assertEqual(receipt["status"], "success")
        self.assertEqual(receipt["format"], "vtt")
        self.assertGreaterEqual(receipt["tasks_extracted"], 1)

        # Parsed action items must have speaker Alex Lead or Elena
        action_items = receipt["parsed_structure"].get("action_items", [])
        assignees = [a.get("assignee") for a in action_items]
        self.assertTrue(any("Alex" in ass or "Elena" in ass for ass in assignees))

    def test_03_qa_pipe_03_inflight_voiceguard_dlp(self):
        """QA-PIPE-03: Verifies in-flight VoiceGuard DLP credential redaction before task injection."""
        leak_file = self.drop_dir / "incident_sync.txt"
        leak_file.write_text(
            "[Sarah] Our temporary staging key was sk-proj-98723418726354128937123987123987 and we need to revoke it immediately.\n"
            "[David CTO] Absolutely agreed on revoking that key. I will rotate all AWS credentials today.",
            encoding="utf-8"
        )

        receipts = self.pipeline.scan_once()
        self.assertEqual(len(receipts), 1)
        receipt = receipts[0]

        self.assertEqual(receipt["status"], "success")
        self.assertFalse(receipt["security_audit"]["is_clean"])
        self.assertGreaterEqual(receipt["secrets_redacted"], 1)

        # Ensure raw secret is NOT anywhere in the parsed tasks
        for task in receipt["parsed_structure"]["action_items"]:
            self.assertNotIn("sk-proj-98723418726354128937123987123987", task.get("title", ""))
            self.assertNotIn("sk-proj-98723418726354128937123987123987", task.get("source_quote", ""))

    def test_04_qa_pipe_04_deduplication_protection(self):
        """QA-PIPE-04: Verifies SHA-256 deduplication archives duplicates without duplicating tasks."""
        content = "[David CTO] Team, let's ship the patch by Friday !p1 #security\n[Sarah] I will test the endpoints."
        file_1 = self.drop_dir / "original_notes.txt"
        file_1.write_text(content, encoding="utf-8")

        # First scan
        receipts_1 = self.pipeline.scan_once()
        self.assertEqual(len(receipts_1), 1)
        self.assertEqual(receipts_1[0]["status"], "success")
        first_tasks = receipts_1[0]["tasks_extracted"]
        self.assertGreaterEqual(first_tasks, 1)

        # Drop second file with identical content under different name
        file_2 = self.drop_dir / "duplicate_notes_copy.txt"
        file_2.write_text(content, encoding="utf-8")

        # Second scan
        receipts_2 = self.pipeline.scan_once()
        self.assertEqual(len(receipts_2), 1)
        self.assertEqual(receipts_2[0]["status"], "duplicate")
        self.assertEqual(receipts_2[0]["tasks_extracted"], 0)
        self.assertFalse(file_2.exists(), "Duplicate file must be moved to processed archive")

    def test_05_qa_pipe_06_corrupt_and_empty_file_quarantine(self):
        """QA-PIPE-06: Verifies 0-byte and binary files are quarantined with .error.json companion logs."""
        # 1. Zero-byte file
        empty_file = self.drop_dir / "empty_memo.txt"
        empty_file.write_text("", encoding="utf-8")

        # 2. Corrupt binary file
        bin_file = self.drop_dir / "corrupted_chunk.txt"
        bin_file.write_bytes(b"\x00\x01\x02\x03\x04\xff\xfe\x00corrupt")

        receipts = self.pipeline.scan_once()
        self.assertEqual(len(receipts), 0)  # No success receipts

        # Both files must now be in quarantine directory
        self.assertFalse(empty_file.exists())
        self.assertFalse(bin_file.exists())

        quarantined_files = [p.name for p in self.quarantine_dir.iterdir()]
        self.assertIn("empty_memo.txt", quarantined_files)
        self.assertIn("empty_memo.txt.error.json", quarantined_files)
        self.assertIn("corrupted_chunk.txt", quarantined_files)
        self.assertIn("corrupted_chunk.txt.error.json", quarantined_files)

        # Verify error file content
        error_json = json.loads((self.quarantine_dir / "empty_memo.txt.error.json").read_text(encoding="utf-8"))
        self.assertIn("empty", error_json["error"].lower())

    def test_06_subrip_srt_and_json_ingestion(self):
        """QA-PIPE-07: Verifies SubRip (.srt) and structured JSON transcript ingestion."""
        # 1. SRT file
        srt_file = self.drop_dir / "client_call.srt"
        srt_file.write_text(
            "1\n00:00:01,000 --> 00:00:04,000\n[David CTO] Finalize the Kubernetes migration before Wednesday !p1 #infra\n\n"
            "2\n00:00:05,000 --> 00:00:08,000\n[Sarah] I will audit failover latency before tomorrow.\n",
            encoding="utf-8"
        )

        # 2. JSON Whisper-style file
        json_file = self.drop_dir / "whisper_export.json"
        json_data = {
            "text": "Team sync",
            "segments": [
                {"speaker": "Marcus", "text": "We need to send the Q4 proposal to the enterprise client by Thursday !urgent #sales"},
                {"speaker": "Elena", "text": "I will prepare the contract agreement today."}
            ]
        }
        json_file.write_text(json.dumps(json_data), encoding="utf-8")

        receipts = self.pipeline.scan_once()
        self.assertEqual(len(receipts), 2)
        formats = [r["format"] for r in receipts]
        self.assertIn("srt", formats)
        self.assertIn("json", formats)

    def test_07_telemetry_and_persistent_registry(self):
        """QA-PIPE-08: Verifies pipeline telemetry stats and SQLite registry recording."""
        txt_file = self.drop_dir / "sample.txt"
        txt_file.write_text("[Marcus] I will review marketing budget by Friday !p1 #finance", encoding="utf-8")
        self.pipeline.scan_once()

        telemetry = self.pipeline.get_telemetry()
        self.assertIn("stats", telemetry)
        self.assertIn("recent_ingestions", telemetry)
        stats = telemetry["stats"]
        self.assertGreaterEqual(stats["total_files"], 1)
        self.assertGreaterEqual(stats["success_files"], 1)
        self.assertGreaterEqual(stats["total_tasks"], 1)

    def test_08_background_daemon_lifecycle(self):
        """QA-PIPE-09: Verifies start, background polling, and clean stop of the pipeline daemon."""
        self.assertFalse(self.pipeline.is_running())
        self.pipeline.start(daemon=True)
        self.assertTrue(self.pipeline.is_running())

        # Drop file while running in background
        bg_file = self.drop_dir / "live_memo.txt"
        bg_file.write_text("[David CTO] Deploy new auth proxy by Friday !p1 #infra", encoding="utf-8")

        # Wait briefly for background loop to ingest
        time.sleep(0.5)

        self.pipeline.stop(timeout=2.0)
        self.assertFalse(self.pipeline.is_running())

        # Verify file was processed
        self.assertFalse(bg_file.exists())
        stats = self.pipeline.registry.get_stats()
        self.assertGreaterEqual(stats["success_files"], 1)


if __name__ == "__main__":
    unittest.main()
