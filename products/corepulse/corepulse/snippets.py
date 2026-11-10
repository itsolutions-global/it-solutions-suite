"""
CorePulse Local Snippet Vault, Dynamic Text Expander & Markdown Vault Exporter
Provides zero-dependency local snippet management with dynamic variable expansion
({{date}}, {{time}}, {{weekday}}, {{git_branch}}, {{clipboard}}) and 1-click
Obsidian/Logseq-compatible Markdown Vault export.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import threading
import uuid
from typing import Any, Dict, List, Optional

from corepulse.config import DATA_DIR


DEFAULT_SNIPPETS: List[Dict[str, Any]] = [
    {
        "id": "snip-standup",
        "trigger": ";;standup",
        "title": "Daily Engineering Standup Update",
        "category": "Engineering",
        "content": (
            "## Daily Standup — {{date}} ({{weekday}})\n"
            "- **Branch**: `{{git_branch}}`\n"
            "- **Completed Yesterday**: Finalized core module implementation and regression suite.\n"
            "- **Focus Today**: Advancing sprint deliverables and code review.\n"
            "- **Blockers**: None."
        ),
        "tags": ["standup", "daily", "engineering"],
        "usage_count": 4,
        "created_at": "2026-11-01T09:00:00+00:00"
    },
    {
        "id": "snip-pr",
        "trigger": ";;pr",
        "title": "Pull Request Summary Template",
        "category": "Code Review",
        "content": (
            "### Summary of Changes ({{date}})\n"
            "- **Source Branch**: `{{git_branch}}`\n"
            "- **Impact**: Zero breaking changes; 100% stdlib compliant.\n"
            "- **Verification**: All unit and integration tests passing locally.\n"
            "- **Security**: Audited via NexusShield SAST (0 critical/high findings)."
        ),
        "tags": ["git", "pr", "review"],
        "usage_count": 7,
        "created_at": "2026-11-01T09:05:00+00:00"
    },
    {
        "id": "snip-followup",
        "trigger": ";;followup",
        "title": "Executive Meeting Follow-Up Note",
        "category": "Communication",
        "content": (
            "Hi {{recipient}},\n\n"
            "Great speaking with you today ({{date}}). Here is a quick recap of our alignment "
            "and next steps:\n\n"
            "1. **Key Decision**: {{decision}}\n"
            "2. **Next Action Item**: {{action_item}}\n\n"
            "Best regards,"
        ),
        "tags": ["email", "meeting", "followup"],
        "usage_count": 5,
        "created_at": "2026-11-01T09:10:00+00:00"
    },
    {
        "id": "snip-audit",
        "trigger": ";;audit",
        "title": "Pre-Release Security & QA Command",
        "category": "DevOps",
        "content": "python products/nexusshield/main.py scan . --fail-under 90 && pytest",
        "tags": ["security", "cli", "devops"],
        "usage_count": 9,
        "created_at": "2026-11-01T09:15:00+00:00"
    }
]


class SnippetVault:
    """Thread-safe local snippet store and dynamic variable expander."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = Path(storage_path) if storage_path else (DATA_DIR / "snippets.json")
        self._lock = threading.RLock()
        self._ensure_initialized()

    def _ensure_initialized(self):
        with self._lock:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.storage_path.exists():
                self._write_all(list(DEFAULT_SNIPPETS))

    def _read_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not self.storage_path.exists():
                return list(DEFAULT_SNIPPETS)
            try:
                raw = self.storage_path.read_text(encoding="utf-8")
                data = json.loads(raw)
                return data if isinstance(data, list) else list(DEFAULT_SNIPPETS)
            except Exception:
                return list(DEFAULT_SNIPPETS)

    def _write_all(self, snippets: List[Dict[str, Any]]):
        with self._lock:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(
                json.dumps(snippets, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )

    def list_snippets(self, query: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists snippets with optional search query or category filter."""
        items = self._read_all()
        if category:
            cat_lower = category.lower()
            items = [s for s in items if s.get("category", "").lower() == cat_lower]
        if query:
            q_lower = query.lower().strip()
            items = [
                s for s in items
                if q_lower in s.get("trigger", "").lower()
                or q_lower in s.get("title", "").lower()
                or q_lower in s.get("content", "").lower()
                or any(q_lower in t.lower() for t in s.get("tags", []))
            ]
        return items

    def get_snippet(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Finds a snippet by exact ID, trigger (with or without ';;'), or title."""
        ident = identifier.strip().lower()
        ident_with_prefix = ident if ident.startswith(";;") else f";;{ident}"
        for s in self._read_all():
            if (
                s.get("id", "").lower() == ident
                or s.get("trigger", "").lower() in (ident, ident_with_prefix)
                or s.get("title", "").lower() == ident
            ):
                return s
        return None

    def save_snippet(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Creates or updates a snippet in the local vault."""
        title = str(payload.get("title", "")).strip()
        content = str(payload.get("content", "")).strip()
        trigger = str(payload.get("trigger", "")).strip()

        if not title:
            raise ValueError("Snippet 'title' is required.")
        if not content:
            raise ValueError("Snippet 'content' is required.")
        if not trigger:
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:20]
            trigger = f";;{slug}"
        elif not trigger.startswith(";;") and not trigger.startswith("/"):
            trigger = f";;{trigger}"

        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            items = self._read_all()
            snip_id = payload.get("id")
            existing_idx = None
            for idx, item in enumerate(items):
                if (snip_id and item.get("id") == snip_id) or item.get("trigger", "").lower() == trigger.lower():
                    existing_idx = idx
                    break

            tags = payload.get("tags", ["snippet"])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]

            if existing_idx is not None:
                prev = items[existing_idx]
                record = {
                    "id": prev["id"],
                    "trigger": trigger,
                    "title": title,
                    "category": payload.get("category", prev.get("category", "General")),
                    "content": content,
                    "tags": tags,
                    "usage_count": prev.get("usage_count", 0),
                    "created_at": prev.get("created_at", now_iso),
                    "updated_at": now_iso
                }
                items[existing_idx] = record
            else:
                record = {
                    "id": snip_id or f"snip-{uuid.uuid4().hex[:8]}",
                    "trigger": trigger,
                    "title": title,
                    "category": payload.get("category", "General"),
                    "content": content,
                    "tags": tags,
                    "usage_count": 0,
                    "created_at": now_iso,
                    "updated_at": now_iso
                }
                items.insert(0, record)

            self._write_all(items)
            return record

    def delete_snippet(self, snippet_id: str) -> bool:
        """Deletes a snippet by ID or trigger."""
        with self._lock:
            items = self._read_all()
            filtered = [
                s for s in items
                if s.get("id") != snippet_id and s.get("trigger") != snippet_id
            ]
            if len(filtered) == len(items):
                return False
            self._write_all(filtered)
            return True

    @staticmethod
    def _detect_git_branch() -> str:
        """Resolves current git branch name safely."""
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=1.5
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip()
        except Exception:
            pass
        return "main"

    def expand_text(self, template: str, custom_vars: Optional[Dict[str, str]] = None) -> str:
        """Expands dynamic {{variables}} inside any text template."""
        now = datetime.now()
        variables: Dict[str, str] = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": now.strftime("%A"),
            "year": now.strftime("%Y"),
            "git_branch": self._detect_git_branch(),
            "clipboard": "",
            "recipient": "Team",
            "decision": "Proceed with proposed implementation",
            "action_item": "Complete verification and ship release"
        }
        if custom_vars:
            for k, v in custom_vars.items():
                if v is not None:
                    variables[str(k).strip()] = str(v)

        def replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            return variables.get(key, match.group(0))

        return re.sub(r"\{\{\s*([a-zA-Z0-9_\-]+)\s*\}\}", replacer, template)

    def expand_snippet(self, identifier: str, custom_vars: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Finds a snippet, expands its dynamic variables, and increments its usage count."""
        with self._lock:
            items = self._read_all()
            ident = identifier.strip().lower()
            ident_with_prefix = ident if ident.startswith(";;") else f";;{ident}"
            target_idx = None

            for idx, s in enumerate(items):
                if (
                    s.get("id", "").lower() == ident
                    or s.get("trigger", "").lower() in (ident, ident_with_prefix)
                    or s.get("title", "").lower() == ident
                ):
                    target_idx = idx
                    break

            if target_idx is None:
                return None

            snippet = items[target_idx]
            snippet["usage_count"] = int(snippet.get("usage_count", 0)) + 1
            self._write_all(items)

            expanded = self.expand_text(snippet["content"], custom_vars=custom_vars)
            return {
                "snippet": snippet,
                "expanded_text": expanded,
                "variables_resolved": True
            }


def export_markdown_vault(
    tasks: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    vault_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Exports all CorePulse tasks, habits, and snippets into a clean,
    Obsidian/Logseq-compatible Markdown folder structure.
    """
    target_dir = Path(vault_dir) if vault_dir else (DATA_DIR / "markdown_vault")
    target_dir.mkdir(parents=True, exist_ok=True)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    today_date = datetime.now().strftime("%Y-%m-%d")

    standard_tasks = [t for t in tasks if t.get("type") != "habit"]
    habits = [t for t in tasks if t.get("type") == "habit"]

    # 1. Tasks.md
    tasks_lines = [
        f"# CorePulse Tasks Vault",
        f"> Synced locally on {now_str} | Total Tasks: {len(standard_tasks)}\n",
        "## Active Tasks"
    ]
    pending = [t for t in standard_tasks if not t.get("completed")]
    completed = [t for t in standard_tasks if t.get("completed")]

    if not pending:
        tasks_lines.append("- *All active tasks completed!*")
    for t in pending:
        prio = t.get("priority", "medium").upper()
        due = t.get("due_date", "Today")
        tags = " ".join(f"#{tag}" for tag in t.get("tags", []))
        tasks_lines.append(f"- [ ] **[{prio}]** {t.get('title')} *(Due: {due})* {tags}".strip())

    tasks_lines.append("\n## Completed Tasks")
    if not completed:
        tasks_lines.append("- *No completed tasks yet.*")
    for t in completed:
        tasks_lines.append(f"- [x] ~~{t.get('title')}~~")

    tasks_file = target_dir / "Tasks.md"
    tasks_file.write_text("\n".join(tasks_lines) + "\n", encoding="utf-8")

    # 2. Habits.md
    habits_lines = [
        f"# CorePulse Habit Streaks",
        f"> Synced locally on {now_str} | Total Habits: {len(habits)}\n"
    ]
    for h in habits:
        chk = "x" if h.get("completed") else " "
        streak = h.get("streak_days", 0)
        habits_lines.append(f"- [{chk}] **{h.get('title')}** — 🔥 Streak: `{streak} days`")

    habits_file = target_dir / "Habits.md"
    habits_file.write_text("\n".join(habits_lines) + "\n", encoding="utf-8")

    # 3. Snippets.md
    snip_lines = [
        f"# CorePulse Snippet Vault",
        f"> Synced locally on {now_str} | Total Snippets: {len(snippets)}\n"
    ]
    for s in snippets:
        snip_lines.append(f"## `{s.get('trigger')}` — {s.get('title')}")
        snip_lines.append(f"- **Category**: {s.get('category', 'General')} | **Used**: {s.get('usage_count', 0)}x\n")
        snip_lines.append("```markdown")
        snip_lines.append(s.get("content", ""))
        snip_lines.append("```\n")

    snippets_file = target_dir / "Snippets.md"
    snippets_file.write_text("\n".join(snip_lines) + "\n", encoding="utf-8")

    # 4. Daily Brief
    daily_file = target_dir / f"Daily-Brief-{today_date}.md"
    daily_lines = [
        f"# Executive Daily Brief — {today_date}",
        f"- **Pending Tasks**: {len(pending)}",
        f"- **Completed Tasks**: {len(completed)}",
        f"- **Active Habits**: {len(habits)}",
        f"- **Saved Snippets**: {len(snippets)}\n",
        "## Top Priority Focus",
    ]
    for t in pending[:5]:
        daily_lines.append(f"- [ ] **{t.get('title')}** (`{t.get('priority', 'medium').upper()}`)")
    daily_file.write_text("\n".join(daily_lines) + "\n", encoding="utf-8")

    files_written = [
        str(tasks_file),
        str(habits_file),
        str(snippets_file),
        str(daily_file)
    ]
    return {
        "status": "success",
        "vault_dir": str(target_dir),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "files_count": len(files_written),
        "files": files_written,
        "summary": {
            "tasks_exported": len(standard_tasks),
            "habits_exported": len(habits),
            "snippets_exported": len(snippets)
        }
    }


snippet_vault = SnippetVault()
