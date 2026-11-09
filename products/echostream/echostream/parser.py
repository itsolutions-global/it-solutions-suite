"""
EchoStream Semantic Speech & Thought Stream Parser
Extracts action items, decisions, commitments, parking lot topics, and tags
from meeting transcripts or spontaneous stream-of-consciousness brain dumps.
"""

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple


# Regex patterns for commitment and action detection
ACTION_PATTERNS = [
    re.compile(r"(?i)\b(?:i will|i'll|i can|i am going to|i'm going to)\s+([^.?!;\n]+)", re.IGNORECASE),
    re.compile(r"(?i)\b(?:we need to|we must|we should|let's make sure to|let's)\s+([^.?!;\n]+)", re.IGNORECASE),
    re.compile(r"(?i)\b(?:action item|action items?|todo|task):\s*([^.?!;\n]+)", re.IGNORECASE),
    re.compile(r"(?i)\b(?:reminder to|remind me to|follow up with|follow-up with)\s+([^.?!;\n]+)", re.IGNORECASE),
    re.compile(r"(?i)\b([a-zA-Z]+)\s+(?:will|is going to|needs to|must)\s+([^.?!;\n]+)", re.IGNORECASE),
]

# Regex patterns for decision extraction
DECISION_PATTERNS = [
    re.compile(r"(?i)\b(?:we decided to|decision was to|the decision is to|agreed that|agreed on|approved|we agreed to)\s+([^.?!;\n]+)", re.IGNORECASE),
    re.compile(r"(?i)\b(?:consensus is|we are going with|we're going with)\s+([^.?!;\n]+)", re.IGNORECASE),
]

# Regex patterns for open questions and parked topics
QUESTION_PATTERNS = [
    re.compile(r"(?i)\b(?:table this for|park this topic|parking lot|to be determined|tbd|open question|need to clarify)\s+([^.?!;\n]+)", re.IGNORECASE),
    re.compile(r"([^.?!;\n]+\?)", re.IGNORECASE),
]

# Timeline and due date keyword matchers
TIMELINE_PATTERNS = [
    re.compile(r"(?i)\b(by\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+(?:morning|afternoon|evening|eod))?)\b"),
    re.compile(r"(?i)\b(before\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|the release|the demo|demo))\b"),
    re.compile(r"(?i)\b(tomorrow(?:\s+(?:at\s+[0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?|morning|afternoon|evening))?)\b"),
    re.compile(r"(?i)\b(tonight|today|by\s+eod|end of day)\b"),
    re.compile(r"(?i)\b(next\s+week|by\s+next\s+(?:monday|friday))\b"),
]

# Category and tag inference keywords
CATEGORY_KEYWORDS = {
    "Architecture": ["architecture", "rfc", "design", "system", "scaling", "microservice", "mesh"],
    "Security": ["security", "auth", "token", "jwt", "cve", "secret", "permission", "firewall", "audit"],
    "DevOps & Infra": ["docker", "k8s", "kubernetes", "aws", "cloud", "deploy", "pipeline", "ci/cd", "infra", "staging"],
    "Engineering": ["bug", "fix", "code", "database", "sql", "migration", "test", "testing", "refactor", "api"],
    "Strategic & Product": ["roadmap", "investor", "q1", "q4", "milestone", "prd", "feature", "client", "contract"]
}


def infer_priority(text: str) -> str:
    """Infers priority level (critical, high, medium, low) from sentence sentiment."""
    lower = text.lower()
    if any(k in lower for k in ["urgent", "critical", "blocker", "emergency", "asap", "must ship", "tonight", "p0"]):
        return "critical"
    elif any(k in lower for k in ["high priority", "important", "before release", "before demo", "tomorrow", "p1"]):
        return "high"
    elif any(k in lower for k in ["low priority", "nice to have", "when you can", "someday", "p3"]):
        return "low"
    return "medium"


def infer_due_date(text: str) -> str:
    """Extracts spoken timeline or default due date."""
    for pat in TIMELINE_PATTERNS:
        match = pat.search(text)
        if match:
            # Capitalize cleanly as title
            return match.group(1).strip().title()
    return "Today"


def infer_category_and_tags(text: str) -> Tuple[str, List[str]]:
    """Infers primary category and contextual tags based on semantic content."""
    lower = text.lower()
    detected_category = "General"
    tags = ["echostream", "voice-intake"]

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                detected_category = category
                if kw not in tags:
                    tags.append(kw)

    return detected_category, tags


def clean_action_title(action_str: str) -> str:
    """Strips conversational fillers and formats clean, crisp task title."""
    cleaned = action_str.strip()
    # Strip common leading verbs and particles
    strip_prefixes = [
        "that we ", "to ", "about ", "on ", "like ", "take ownership of ",
        "make sure to ", "make sure ", "ensure that ", "ensure "
    ]
    for p in strip_prefixes:
        if cleaned.lower().startswith(p):
            cleaned = cleaned[len(p):].strip()

    # Capitalize first letter
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


class SemanticStreamParser:
    """
    Semantic parser for unstructured spoken dialogue and spontaneous brain dumps.
    Transforms raw transcripts into CorePulse-ready actionable objects.
    """

    def parse_meeting_transcript(self, transcript_text: str) -> Dict[str, Any]:
        """
        Parses full multi-speaker meeting transcript into structured pillars:
          - Executive Summary
          - Action Items & Commitments
          - Key Decisions Made
          - Questions & Parking Lot
        """
        lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]
        action_items: List[Dict[str, Any]] = []
        decisions: List[Dict[str, Any]] = []
        parking_lot: List[Dict[str, Any]] = []
        speakers_detected: List[str] = []

        for line in lines:
            # Check speaker attribution [Speaker Name]
            speaker_match = re.match(r"^\[([^\]]+)\]\s*(.*)$", line)
            if speaker_match:
                speaker = speaker_match.group(1).strip()
                utterance = speaker_match.group(2).strip()
                if speaker not in speakers_detected:
                    speakers_detected.append(speaker)
            else:
                speaker = "Team"
                utterance = line

            if not utterance:
                continue

            # 1. Action Items Detection
            extracted_action = None
            assignee = speaker

            for pattern in ACTION_PATTERNS:
                match = pattern.search(utterance)
                if match:
                    if pattern.groups == 2:
                        # e.g., "Sarah will deploy..."
                        possible_assignee = match.group(1)
                        if possible_assignee.lower() not in ("we", "it", "that", "this"):
                            assignee = possible_assignee.capitalize()
                        raw_action = match.group(2)
                    else:
                        raw_action = match.group(1)

                    if len(raw_action.split()) >= 2:
                        extracted_action = raw_action
                        break

            if extracted_action:
                clean_title = clean_action_title(extracted_action)
                category, tags = infer_category_and_tags(utterance)
                priority = infer_priority(utterance)
                due_date = infer_due_date(utterance)

                action_items.append({
                    "id": f"action-{uuid.uuid4().hex[:8]}",
                    "title": clean_title,
                    "assignee": "Me" if assignee.lower() in ("me", "i") else assignee,
                    "priority": priority,
                    "category": category,
                    "due_date": due_date,
                    "estimated_minutes": 30,
                    "tags": tags,
                    "source_quote": line,
                    "type": "task",
                    "completed": False
                })

            # 2. Decisions Detection
            for dec_pat in DECISION_PATTERNS:
                d_match = dec_pat.search(utterance)
                if d_match:
                    decisions.append({
                        "id": f"dec-{uuid.uuid4().hex[:8]}",
                        "decision": clean_action_title(d_match.group(1)),
                        "speaker": speaker,
                        "source_quote": line
                    })
                    break

            # 3. Parking Lot & Open Questions
            for q_pat in QUESTION_PATTERNS:
                q_match = q_pat.search(utterance)
                if q_match:
                    topic = q_match.group(1).strip()
                    if len(topic.split()) >= 2:
                        parking_lot.append({
                            "id": f"q-{uuid.uuid4().hex[:8]}",
                            "topic": topic,
                            "speaker": speaker,
                            "source_quote": line
                        })
                    break

        # Synthesize Executive Summary
        summary_bullets = []
        if decisions:
            summary_bullets.append(f"Approved {len(decisions)} key agreement(s): {decisions[0]['decision']}.")
        if action_items:
            summary_bullets.append(f"Established {len(action_items)} executable deliverable(s) across {len(set(a['assignee'] for a in action_items))} owner(s).")
        if parking_lot:
            summary_bullets.append(f"Identified {len(parking_lot)} open question(s) tabled for future alignment.")
        if not summary_bullets:
            summary_bullets.append(f"Meeting session completed across {len(lines)} conversational turns with {len(speakers_detected)} participant(s).")

        return {
            "session_type": "meeting_transcript",
            "speakers": speakers_detected if speakers_detected else ["Participants"],
            "total_turns": len(lines),
            "executive_summary": summary_bullets,
            "action_items": action_items,
            "decisions": decisions,
            "parking_lot": parking_lot
        }

    def parse_thought_stream(self, raw_thought_text: str) -> Dict[str, Any]:
        """
        Parses spontaneous voice memos and stream-of-consciousness brain dumps.
        Segments compounded thoughts ('and also', 'plus', 'then') into discrete tasks.
        """
        text = raw_thought_text.strip()
        # Split compound thoughts on speech connectors
        split_pattern = re.compile(r"(?i)\s*(?:,\s*and\s+also\s+|\s+and\s+also\s+|\s+plus\s+also\s+|\s+then\s+also\s+|\s+additionally,\s*|\s*;\s*|\s*,\s*and\s+(?:then\s+)?remind me to\s+)\s*")
        clauses = split_pattern.split(text)

        tasks: List[Dict[str, Any]] = []

        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue

            # Strip leading memo filler phrases
            cleaned = re.sub(r"(?i)^(?:hey,?\s*|okay,?\s*|so,?\s*|reminder to\s*|remind me to\s*|note to self\s*|write a quick\s*)", "", clause).strip()
            if not cleaned:
                continue

            title = clean_action_title(cleaned)
            category, tags = infer_category_and_tags(clause)
            tags.append("thought-omnibar")
            priority = infer_priority(clause)
            due_date = infer_due_date(clause)

            tasks.append({
                "id": f"thought-{uuid.uuid4().hex[:8]}",
                "title": title,
                "assignee": "Me",
                "priority": priority,
                "category": category,
                "due_date": due_date,
                "estimated_minutes": 25,
                "tags": tags,
                "source_quote": clause,
                "type": "task",
                "completed": False
            })

        return {
            "session_type": "thought_stream",
            "raw_text": raw_thought_text,
            "tasks_extracted": len(tasks),
            "action_items": tasks
        }

    def parse_stream(self, text: str) -> Dict[str, Any]:
        """
        Unified entrypoint: auto-detects session type (meeting transcript vs. thought stream)
        and parses into structured action items.
        """
        stripped = text.strip()
        if ("[" in stripped and "]" in stripped) or ("\n" in stripped and ":" in stripped):
            return self.parse_meeting_transcript(stripped)
        return self.parse_thought_stream(stripped)

    def parse(self, text: str) -> Dict[str, Any]:
        """Alias for parse_stream."""
        return self.parse_stream(text)
