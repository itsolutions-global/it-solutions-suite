"""
EchoStream Executive Meeting Co-Pilot (100% Python Standard Library):
  1. ScratchpadMerger: 'Granola-style' merger combining rough personal bullet notes
     with raw meeting transcripts into a unified Executive Brief + Ready-to-Send Follow-Up Email Draft.
  2. CommitmentTracker: Cross-meeting semantic search & accountability ledger tracking promises
     and deliverables by assignee across historical transcripts.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Union

from echostream.parser import SemanticStreamParser, clean_action_title, infer_category_and_tags, infer_due_date, infer_priority
from echostream.voice_guard import VoiceGuard


class ScratchpadMerger:
    """
    Merges a user's rough live meeting scratchpad notes with a raw transcript
    and synthesizes a structured Executive Brief + Ready-to-Send Follow-Up Email Draft.
    """

    def __init__(self):
        self.guard = VoiceGuard()
        self.parser = SemanticStreamParser()

    def merge_and_draft(
        self,
        transcript_text: str,
        scratchpad_notes: str = "",
        meeting_title: str = "Executive Alignment & Next Steps"
    ) -> Dict[str, Any]:
        """
        1. Runs VoiceGuard DLP across both scratchpad notes and transcript.
        2. Extracts structured highlights from scratchpad bullets.
        3. Parses transcript for decisions, action items, and open questions.
        4. Generates a Ready-to-Send Follow-Up Email Draft.
        """
        # 1. DLP Sanitization
        trans_audit = self.guard.scan_and_redact(transcript_text or "")
        notes_audit = self.guard.scan_and_redact(scratchpad_notes or "")

        clean_transcript = trans_audit["redacted_text"]
        clean_notes = notes_audit["redacted_text"]

        # 2. Parse Transcript
        parsed = self.parser.parse_stream(clean_transcript) if clean_transcript.strip() else {
            "session_type": "scratchpad_only",
            "speakers": ["Me"],
            "executive_summary": [],
            "action_items": [],
            "decisions": [],
            "parking_lot": []
        }

        # 3. Parse Scratchpad Bullets & Merge High-Signal Notes
        scratchpad_highlights: List[str] = []
        scratchpad_actions: List[Dict[str, Any]] = []

        for raw_line in clean_notes.splitlines():
            line = re.sub(r"^[\-\*\•\d\.\)\s]+", "", raw_line).strip()
            if not line:
                continue
            scratchpad_highlights.append(line)

            # Check if scratchpad note is itself an action item or todo
            if re.search(r"(?i)\b(?:todo|action|must|need to|will|follow up|send|deploy|review)\b", line):
                cat, tags = infer_category_and_tags(line)
                if "scratchpad" not in tags:
                    tags.append("scratchpad")
                scratchpad_actions.append({
                    "id": f"note-{len(scratchpad_actions) + 1}",
                    "title": clean_action_title(line),
                    "assignee": "Me",
                    "priority": infer_priority(line),
                    "category": cat,
                    "due_date": infer_due_date(line),
                    "estimated_minutes": 30,
                    "tags": tags,
                    "source_quote": f"[Scratchpad] {line}",
                    "type": "task",
                    "completed": False
                })

        # Deduplicate action items by normalized title
        merged_actions: List[Dict[str, Any]] = list(parsed.get("action_items", []))
        existing_titles = {a["title"].lower() for a in merged_actions}
        for sa in scratchpad_actions:
            if sa["title"].lower() not in existing_titles:
                merged_actions.append(sa)
                existing_titles.add(sa["title"].lower())

        decisions = parsed.get("decisions", [])
        parking_lot = parsed.get("parking_lot", [])
        speakers = parsed.get("speakers", ["Team"])

        # 4. Synthesize Follow-Up Email Draft
        email_draft = self._build_followup_email(
            meeting_title=meeting_title,
            speakers=speakers,
            scratchpad_highlights=scratchpad_highlights,
            decisions=decisions,
            action_items=merged_actions,
            parking_lot=parking_lot
        )

        total_incidents = trans_audit["incidents_count"] + notes_audit["incidents_count"]
        return {
            "meeting_title": meeting_title,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "security_audit": {
                "is_clean": total_incidents == 0,
                "incidents_count": total_incidents,
                "incidents": trans_audit["incidents"] + notes_audit["incidents"]
            },
            "scratchpad_highlights": scratchpad_highlights,
            "decisions": decisions,
            "action_items": merged_actions,
            "parking_lot": parking_lot,
            "followup_email": email_draft
        }

    @staticmethod
    def _build_followup_email(
        meeting_title: str,
        speakers: List[str],
        scratchpad_highlights: List[str],
        decisions: List[Dict[str, Any]],
        action_items: List[Dict[str, Any]],
        parking_lot: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Formats a crisp, executive-ready follow-up email draft."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        subject = f"Recap & Next Steps: {meeting_title} ({today_str})"
        greeting_names = ", ".join(speakers) if speakers and speakers != ["Participants"] else "Team"

        lines = [
            f"Hi {greeting_names},",
            "",
            f"Thank you for the productive session today ({today_str}). Below is a concise summary of our key notes, decisions, and action items:",
            ""
        ]

        if scratchpad_highlights:
            lines.append("### Key Executive Notes")
            for h in scratchpad_highlights:
                lines.append(f"- {h}")
            lines.append("")

        if decisions:
            lines.append("### Decisions Approved")
            for d in decisions:
                lines.append(f"- ✔ **{d['decision']}** *(Owner: {d.get('speaker', 'Team')})*")
            lines.append("")

        if action_items:
            lines.append("### Action Items & Commitments")
            for a in action_items:
                lines.append(
                    f"- [ ] **[{a.get('assignee', 'Team')}]** {a['title']} "
                    f"*(Due: {a.get('due_date', 'Today')} | Priority: {a.get('priority', 'medium').upper()})*"
                )
            lines.append("")

        if parking_lot:
            lines.append("### Open Questions / Parking Lot")
            for q in parking_lot:
                lines.append(f"- ? {q['topic']} *(Raised by: {q.get('speaker', 'Team')})*")
            lines.append("")

        lines.extend([
            "Please reply if anything needs adjustment.",
            "",
            "Best regards,"
        ])

        body_md = "\n".join(lines)
        return {
            "subject": subject,
            "recipients_placeholder": greeting_names,
            "body_markdown": body_md
        }


class CommitmentTracker:
    """
    Cross-Meeting Commitment & Accountability Tracker.
    Indexes commitments across meeting transcripts and allows instant querying
    by assignee ('What did Sarah promise?') or topic keyword.
    """

    def __init__(self, ledger_path: Optional[Union[str, Path]] = None):
        if ledger_path:
            self.ledger_path = Path(ledger_path)
        else:
            base_dir = Path(__file__).resolve().parent.parent / "data"
            if os.getenv("COREPULSE_TEST_MODE") == "1" and os.getenv("COREPULSE_DATA_DIR"):
                base_dir = Path(os.environ["COREPULSE_DATA_DIR"])
            self.ledger_path = base_dir / "commitments_ledger.json"

        self.parser = SemanticStreamParser()
        self.guard = VoiceGuard()

    def _read_ledger(self) -> List[Dict[str, Any]]:
        if not self.ledger_path.exists():
            return []
        try:
            data = json.loads(self.ledger_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write_ledger(self, records: List[Dict[str, Any]]):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    def record_commitments(
        self,
        action_items: List[Dict[str, Any]],
        meeting_source: str = "Meeting Session"
    ) -> int:
        """Persists extracted action items into the cross-meeting commitment ledger."""
        if not action_items:
            return 0
        existing = self._read_ledger()
        existing_keys = {(r.get("assignee", "").lower(), r.get("title", "").lower()) for r in existing}
        added = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        for item in action_items:
            key = (str(item.get("assignee", "Me")).lower(), str(item.get("title", "")).lower())
            if key in existing_keys:
                continue
            existing_keys.add(key)
            existing.insert(0, {
                "id": item.get("id", f"commit-{len(existing) + 1}"),
                "assignee": item.get("assignee", "Me"),
                "title": item.get("title", ""),
                "priority": item.get("priority", "medium"),
                "due_date": item.get("due_date", "Today"),
                "category": item.get("category", "General"),
                "source_quote": item.get("source_quote", ""),
                "meeting_source": meeting_source,
                "recorded_at": now_iso,
                "status": "completed" if item.get("completed") else "pending"
            })
            added += 1

        self._write_ledger(existing)
        return added

    def index_transcript_directory(self, directory: Union[str, Path]) -> int:
        """Scans all transcript files (.txt, .md, .vtt, .srt) in a directory and indexes commitments."""
        target = Path(directory)
        if not target.exists() or not target.is_dir():
            return 0

        total_added = 0
        for p in target.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".txt", ".md", ".vtt", ".srt"):
                try:
                    raw = p.read_text(encoding="utf-8", errors="ignore")
                    clean = self.guard.scan_and_redact(raw)["redacted_text"]
                    parsed = self.parser.parse_stream(clean)
                    added = self.record_commitments(parsed.get("action_items", []), meeting_source=p.name)
                    total_added += added
                except Exception:
                    continue
        return total_added

    def query_commitments(
        self,
        assignee: Optional[str] = None,
        query: Optional[str] = None,
        include_dir: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """Queries commitments across meetings with optional assignee or keyword filters."""
        if include_dir:
            self.index_transcript_directory(include_dir)

        records = self._read_ledger()
        if assignee:
            a_low = assignee.strip().lower().lstrip("@")
            records = [r for r in records if a_low in r.get("assignee", "").lower()]
        if query:
            q_low = query.strip().lower()
            records = [
                r for r in records
                if q_low in r.get("title", "").lower()
                or q_low in r.get("category", "").lower()
                or q_low in r.get("source_quote", "").lower()
                or q_low in r.get("meeting_source", "").lower()
            ]

        by_assignee: Dict[str, int] = {}
        for r in records:
            owner = r.get("assignee", "Me")
            by_assignee[owner] = by_assignee.get(owner, 0) + 1

        return {
            "total_commitments": len(records),
            "by_assignee": by_assignee,
            "commitments": records
        }
