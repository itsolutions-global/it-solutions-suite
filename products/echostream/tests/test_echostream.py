"""
EchoStream Automated Unit & Integration Test Suite
Validates VoiceGuard DLP, SemanticStreamParser, CorePulseDispatcher, and CLI commands.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
SUITE_DIR = BASE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(SUITE_DIR / "corepulse") not in sys.path:
    sys.path.insert(0, str(SUITE_DIR / "corepulse"))

from echostream.dispatcher import CorePulseDispatcher
from echostream.parser import (
    SemanticStreamParser,
    clean_action_title,
    infer_due_date,
    infer_priority,
)
from echostream.voice_guard import (
    VoiceGuard,
    calculate_shannon_entropy,
    is_placeholder,
    mask_secret,
)


class TestEchoStream(unittest.TestCase):
    """Test suite for EchoStream core perception engine."""

    def setUp(self):
        self.guard = VoiceGuard()
        self.parser = SemanticStreamParser()
        self.dispatcher = CorePulseDispatcher()

    def test_01_voice_guard_credential_redaction(self):
        """Verifies VoiceGuard intercepts and redacts multiple credential formats."""
        raw_speech = (
            "Our staging OpenAI key is sk-proj-1234567890abcdef1234567890abcdef and "
            "the AWS key is AKIAIOSFODNN7EXAMPLE. Also the db password is SuperSecurePass2026!"
        )
        result = self.guard.scan_and_redact(raw_speech)

        self.assertFalse(result["is_clean"])
        self.assertGreaterEqual(result["incidents_count"], 2)

        # Raw secrets must not be in the redacted text
        self.assertNotIn("sk-proj-1234567890abcdef1234567890abcdef", result["redacted_text"])
        self.assertNotIn("SuperSecurePass2026!", result["redacted_text"])
        self.assertIn("[REDACTED_SECRET:", result["redacted_text"])

    def test_02_voice_guard_clean_speech(self):
        """Verifies clean conversations pass VoiceGuard without false alerts."""
        clean_speech = "Good morning everyone. Let's discuss the product release roadmap for Q1."
        result = self.guard.scan_and_redact(clean_speech)

        self.assertTrue(result["is_clean"])
        self.assertEqual(result["incidents_count"], 0)
        self.assertEqual(result["redacted_text"], clean_speech)

    def test_03_voice_guard_placeholder_bypassing(self):
        """Verifies template placeholders are ignored by VoiceGuard."""
        speech = "Set the environment variable OPENAI_KEY to YOUR_API_KEY_HERE."
        result = self.guard.scan_and_redact(speech)
        self.assertTrue(result["is_clean"])
        self.assertEqual(result["incidents_count"], 0)

    def test_04_semantic_meeting_parser(self):
        """Verifies multi-speaker meeting transcript parsing into structured pillars."""
        transcript = """
        [David CTO] We decided to migrate our caching layer to Redis cluster.
        [David CTO] Sarah, can you make sure to benchmark the Redis throughput by Thursday afternoon?
        [Sarah] I will benchmark the Redis cluster throughput by Thursday afternoon.
        [David CTO] Open question: what about the memory sizing on our staging nodes?
        [David CTO] Let's table this for next Tuesday's meeting.
        """
        parsed = self.parser.parse_meeting_transcript(transcript)

        self.assertEqual(parsed["session_type"], "meeting_transcript")
        self.assertIn("David CTO", parsed["speakers"])
        self.assertIn("Sarah", parsed["speakers"])

        # Check action items
        self.assertGreaterEqual(len(parsed["action_items"]), 1)
        sarah_action = next((a for a in parsed["action_items"] if a["assignee"] == "Sarah"), None)
        self.assertIsNotNone(sarah_action)
        self.assertIn("Benchmark the Redis cluster throughput", sarah_action["title"])
        self.assertIn("Thursday", sarah_action["due_date"])

        # Check decisions
        self.assertGreaterEqual(len(parsed["decisions"]), 1)
        self.assertIn("Migrate our caching layer to Redis cluster", parsed["decisions"][0]["decision"])

        # Check parking lot
        self.assertGreaterEqual(len(parsed["parking_lot"]), 1)

        # Check executive summary
        self.assertGreaterEqual(len(parsed["executive_summary"]), 1)

    def test_05_semantic_thought_stream_parser(self):
        """Verifies parsing and splitting of compound stream-of-consciousness thoughts."""
        thought = (
            "Reminder to follow up with Alex tomorrow morning at 10 AM regarding the Docker setup, "
            "and also write a quick bug ticket about the memory leak in auth middleware"
        )
        parsed = self.parser.parse_thought_stream(thought)

        self.assertEqual(parsed["session_type"], "thought_stream")
        self.assertEqual(parsed["tasks_extracted"], 2)

        task1 = parsed["action_items"][0]
        self.assertIn("Follow up with Alex", task1["title"])
        self.assertEqual(task1["assignee"], "Me")
        self.assertIn("tomorrow", task1["due_date"].lower())
        self.assertIn("thought-omnibar", task1["tags"])

        task2 = parsed["action_items"][1]
        self.assertIn("Bug ticket about the memory leak", task2["title"])
        self.assertEqual(task2["assignee"], "Me")

    def test_06_priority_and_timeline_inference(self):
        """Verifies priority sentiment and timeline extraction logic."""
        self.assertEqual(infer_priority("This is urgent and must ship tonight!"), "critical")
        self.assertEqual(infer_priority("High priority item before client demo"), "high")
        self.assertEqual(infer_priority("Nice to have when you get time"), "low")
        self.assertEqual(infer_priority("We should review the PR"), "medium")

        self.assertIn("Friday", infer_due_date("Finish report by Friday afternoon"))
        self.assertIn("Tomorrow", infer_due_date("Call client tomorrow morning"))
        self.assertEqual(infer_due_date("General background discussion"), "Today")

    def test_07_dispatcher_batch_handling(self):
        """Verifies dispatcher transmits tasks and returns structured reports."""
        tasks = [
            {
                "title": "Verify WASAPI Audio Capture Loopback",
                "type": "task",
                "category": "Engineering",
                "priority": "high",
                "due_date": "Today",
                "tags": ["audio", "loopback"]
            }
        ]
        result = self.dispatcher.dispatch_batch(tasks)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["dispatched"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertIn(result["mode"], ("rest_api", "direct_db"))

    def test_08_cli_scan_subcommand(self):
        """Verifies CLI scan subcommand via subprocess."""
        cli_main = BASE_DIR / "main.py"
        speech = "My key is sk-proj-1234567890abcdef1234567890abcdef"

        proc = subprocess.run(
            [sys.executable, str(cli_main), "scan", speech, "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10
        )
        self.assertEqual(proc.returncode, 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertFalse(data["is_clean"])
        self.assertGreaterEqual(data["incidents_count"], 1)

    def test_09_cli_parse_subcommand(self):
        """Verifies CLI parse subcommand via subprocess."""
        cli_main = BASE_DIR / "main.py"
        thought = "Reminder to update documentation tomorrow morning"

        proc = subprocess.run(
            [sys.executable, str(cli_main), "parse", thought, "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10
        )
        self.assertEqual(proc.returncode, 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertIn("parsed_structure", data)
        self.assertGreaterEqual(len(data["parsed_structure"]["action_items"]), 1)

    def test_10_cli_demo_subcommand(self):
        """Verifies CLI demo subcommand runs without errors."""
        cli_main = BASE_DIR / "main.py"
        proc = subprocess.run(
            [sys.executable, str(cli_main), "demo"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15
        )
        self.assertEqual(proc.returncode, 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")
        self.assertIn("ECHOSTREAM COGNITIVE INTAKE & TRIAGE BRIEF", proc.stdout)
        self.assertIn("SECURITY INTERCEPT", proc.stdout)

    def test_11_transcript_watcher_pipeline(self):
        """Verifies autonomous TranscriptWatcher directory polling and ingestion pipeline."""
        import tempfile
        from echostream.watcher import TranscriptWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            watch_dir = Path(tmpdir) / "inbox"
            archive_dir = Path(tmpdir) / "archive"
            watcher = TranscriptWatcher(watch_dir=watch_dir, archive_dir=archive_dir, settle_time=0.01)

            # Drop a raw meeting notes file into inbox
            notes_file = watch_dir / "strategy_sync.txt"
            notes_file.write_text(
                "[David CTO] Please ship the Postgres replication patch by Friday !p1 #infra\n"
                "[Sarah] I will monitor failover latency before Wednesday.",
                encoding="utf-8"
            )

            receipts = watcher.scan_once()
            self.assertEqual(len(receipts), 1)
            receipt = receipts[0]
            self.assertEqual(receipt["source_file"], "strategy_sync.txt")
            self.assertGreaterEqual(receipt["tasks_extracted"], 1)
            self.assertTrue(Path(receipt["archived_to"]).exists())

            # Verify idempotence on next scan cycle
            receipts_repeat = watcher.scan_once()
            self.assertEqual(len(receipts_repeat), 0)


if __name__ == "__main__":
    unittest.main()
