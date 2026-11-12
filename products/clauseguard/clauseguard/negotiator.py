"""
ClauseGuard v1.2 Negotiation Drafter & Redline Engine
Generates word-level redline diffs ([-deleted-] / {+proposed+}) comparing
predatory clauses with balanced commercial alternatives, and drafts diplomatic,
collaborative cover letters for seamless contract alignment.

Honesty Guard: Automated heuristic review — not legal advice.
Have a qualified lawyer review important agreements.
"""

from datetime import datetime, timezone
import difflib
import re
from typing import Any, Dict, List, Optional

DISCLAIMER = "Automated heuristic review — not legal advice. Have a qualified lawyer review important agreements."


def compute_word_diff(original_text: str, proposed_text: str) -> str:
    """
    Computes a word-by-word redline diff using difflib.
    Deleted text is marked with [-deleted-]
    Proposed additions are marked with {+proposed+}
    """
    orig_words = [w for w in original_text.strip().split() if w]
    prop_words = [w for w in proposed_text.strip().split() if w]

    if not orig_words and not prop_words:
        return ""
    if not orig_words:
        return " ".join(f"{{+{w}+}}" for w in prop_words)
    if not prop_words:
        return " ".join(f"[-{w}-]" for w in orig_words)

    matcher = difflib.SequenceMatcher(None, orig_words, prop_words)
    diff_tokens: List[str] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            diff_tokens.append(" ".join(orig_words[i1:i2]))
        elif tag == "delete":
            diff_tokens.append(" ".join(f"[-{w}-]" for w in orig_words[i1:i2]))
        elif tag == "insert":
            diff_tokens.append(" ".join(f"{{+{w}+}}" for w in prop_words[j1:j2]))
        elif tag == "replace":
            deleted = " ".join(f"[-{w}-]" for w in orig_words[i1:i2])
            inserted = " ".join(f"{{+{w}+}}" for w in prop_words[j1:j2])
            diff_tokens.append(f"{deleted} {inserted}")

    return " ".join(diff_tokens)


class NegotiationDrafter:
    """Drafts word-level redlines and collaborative negotiation cover letters."""

    DISCLAIMER = DISCLAIMER

    def __init__(self):
        pass

    def diff_clause(self, original_clause: str, suggested_clause: str) -> str:
        """Helper to compute word-level diff for a single clause."""
        return compute_word_diff(original_clause, suggested_clause)

    def draft_cover_email(
        self,
        document_name: str,
        findings: List[Dict[str, Any]],
        recipient_name: str = "Client Team"
    ) -> Dict[str, str]:
        """
        Drafts a diplomatic, collaborative cover email proposing contract redlines
        as standard mutual operational alignment rather than legal hostility.
        """
        subject = f"Proposed Agreement Alignment & Redlines — {document_name}"

        if not findings:
            body = (
                f"Hi {recipient_name},\n\n"
                f"Thank you for sharing the draft agreement for {document_name}. "
                f"Our review did not identify any substantive issues, and the terms look balanced and agreeable.\n\n"
                f"We are ready to proceed with execution whenever convenient.\n\n"
                f"Best regards,\nCollaborative Delivery Team\n\n---\n{self.DISCLAIMER}"
            )
            return {"subject": subject, "body": body}

        bullet_points = []
        for idx, f in enumerate(findings, start=1):
            category = f.get("category", "General")
            title = f.get("title", "Term adjustment")
            risk_summary = f.get("plain_english_risk", "")
            bullet_points.append(
                f"  {idx}. {title} ({category}):\n"
                f"     Alignment: {risk_summary}"
            )
        bullets_text = "\n".join(bullet_points)

        body = (
            f"Hi {recipient_name},\n\n"
            f"Thank you for sharing the draft agreement for {document_name}. We are truly excited "
            f"about the opportunity to partner together and deliver high-impact results.\n\n"
            f"In our standard operational review, we noted a few minor adjustments to ensure our mutual "
            f"expectations regarding scope, milestones, and operational protections are clearly balanced:\n\n"
            f"{bullets_text}\n\n"
            f"We have compiled the specific suggested wording adjustments in the attached redline "
            f"for your team's quick review. These reflect standard industry practices and allow us to "
            f"kick off work smoothly.\n\n"
            f"Please let us know if these look good or if you would like to have a brief alignment chat.\n\n"
            f"Warm regards,\nProject Team\n\n---\n{self.DISCLAIMER}"
        )

        return {"subject": subject, "body": body}

    def generate_negotiation_package(
        self,
        scan_report: Dict[str, Any],
        recipient_name: str = "Client Team"
    ) -> Dict[str, Any]:
        """
        Generates full negotiation package containing word-level redline diffs,
        individual clause comparisons, and a ready-to-send cover letter.
        """
        doc_name = scan_report.get("document", "Agreement.txt")
        findings = scan_report.get("findings", [])

        redlines: List[Dict[str, Any]] = []
        for f in findings:
            original = f.get("matched_excerpt", "")
            proposed = f.get("suggested_alternative", "")
            if not proposed:
                # Strip out 'PROPOSED REDLINE:' prefix if using legacy key
                clean = re.sub(r"^PROPOSED REDLINE:\s*['\"]?", "", f.get("redline_counter_clause", "")).rstrip("'\"")
                proposed = clean

            diff_text = compute_word_diff(original, proposed)
            redlines.append({
                "id": f.get("id"),
                "title": f.get("title"),
                "line": f.get("line"),
                "severity": f.get("severity"),
                "category": f.get("category"),
                "original_clause": original,
                "suggested_alternative": proposed,
                "redline_diff": diff_text,
                "rationale": f.get("plain_english_risk", "")
            })

        cover_email = self.draft_cover_email(doc_name, findings, recipient_name=recipient_name)

        return {
            "document": doc_name,
            "findings_count": len(findings),
            "safety_score": scan_report.get("safety_score", 100.0),
            "grade": scan_report.get("grade", "A+"),
            "verdict": scan_report.get("verdict", "SAFE TO SIGN"),
            "redlines": redlines,
            "cover_email": cover_email,
            "disclaimer": self.DISCLAIMER
        }
