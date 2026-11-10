"""
Unit tests for EchoStream Executive Co-Pilot:
  - ScratchpadMerger ('merge' / Granola-style notes + transcript merger & follow-up email draft)
  - CommitmentTracker ('commitments' / cross-meeting accountability ledger)
"""

from pathlib import Path
import sys
import tempfile
import unittest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from echostream.copilot import CommitmentTracker, ScratchpadMerger


class TestEchoStreamCopilot(unittest.TestCase):
    """Validates Granola-style scratchpad merging, email draft generation, and cross-meeting commitment tracking."""

    def test_01_scratchpad_merger_and_followup_email(self):
        merger = ScratchpadMerger()
        transcript = (
            "[David CTO] We agreed to migrate the staging cluster to zero-trust mTLS.\n"
            "[Sarah] I will deploy the mTLS certificates before Wednesday afternoon.\n"
            "[David CTO] Can we clarify the multi-region failover SLA?"
        )
        scratchpad = (
            "- Client emphasized SOC2 audit deadline in November\n"
            "- Todo: Send updated architecture diagram to Sarah by tomorrow"
        )
        res = merger.merge_and_draft(
            transcript_text=transcript,
            scratchpad_notes=scratchpad,
            meeting_title="Q4 Security Architecture Sync"
        )
        self.assertTrue(res["security_audit"]["is_clean"])
        self.assertEqual(len(res["scratchpad_highlights"]), 2)
        self.assertGreaterEqual(len(res["decisions"]), 1)
        self.assertGreaterEqual(len(res["action_items"]), 2)
        self.assertIn("Recap & Next Steps: Q4 Security Architecture Sync", res["followup_email"]["subject"])
        self.assertIn("Action Items & Commitments", res["followup_email"]["body_markdown"])
        self.assertIn("Sarah", res["followup_email"]["body_markdown"])

    def test_02_cross_meeting_commitment_tracker(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            ledger_file = Path(tmpdir) / "commitments.json"
            tracker = CommitmentTracker(ledger_path=ledger_file)

            sample_actions = [
                {"assignee": "Sarah", "title": "Deploy mTLS certificates", "priority": "high", "due_date": "Wednesday", "category": "Security"},
                {"assignee": "David", "title": "Finalize enterprise SOW", "priority": "critical", "due_date": "Friday", "category": "Strategic & Product"}
            ]
            added = tracker.record_commitments(sample_actions, meeting_source="Security Sync")
            self.assertEqual(added, 2)

            # Query by assignee
            sarah_res = tracker.query_commitments(assignee="Sarah")
            self.assertEqual(sarah_res["total_commitments"], 1)
            self.assertEqual(sarah_res["commitments"][0]["title"], "Deploy mTLS certificates")

            # Query by keyword
            sow_res = tracker.query_commitments(query="SOW")
            self.assertEqual(sow_res["total_commitments"], 1)
            self.assertEqual(sow_res["commitments"][0]["assignee"], "David")


if __name__ == "__main__":
    unittest.main()
