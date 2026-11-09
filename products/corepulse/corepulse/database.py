"""
CorePulse Database & State Store
Thread-safe persistent JSON state management with pre-seeded enterprise productivity data.
"""

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from corepulse.config import DB_FILE, DATA_DIR, VERSION, BUILD_ID, TIER_FEATURE_GATES

logger = logging.getLogger("corepulse.database")

class Database:
    """Thread-safe state manager for CorePulse with atomic file persistence."""

    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self._lock = threading.RLock()
        self.start_time = time.time()
        self._state: Dict[str, Any] = {}
        self._init_store()

    def _get_default_seed(self) -> Dict[str, Any]:
        """Returns foundational demo seed dataset."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "version": VERSION,
            "build_id": BUILD_ID,
            "created_at": now,
            "subscription": {
                "tier": "pro",
                "status": "active",
                "customer_name": "Executive Director",
                "organization": "OmniCorp Global",
                "license_key": "CP-PRO-" + uuid.uuid4().hex[:12].upper(),
                "renews_at": "2027-10-26T00:00:00Z",
                "features": TIER_FEATURE_GATES["pro"]
            },
            "tasks": [
                {
                    "id": "task-001",
                    "title": "Review Q4 High-Velocity Roadmap & Technical Milestones",
                    "type": "task",
                    "category": "Strategic",
                    "priority": "high",
                    "completed": False,
                    "created_at": now,
                    "due_date": "2026-10-27",
                    "estimated_minutes": 45,
                    "streak_days": 0,
                    "tags": ["strategy", "executive", "q4"]
                },
                {
                    "id": "task-002",
                    "title": "Automate AWS Cloud Cost Anomaly Pipeline",
                    "type": "task",
                    "category": "Engineering",
                    "priority": "critical",
                    "completed": True,
                    "created_at": now,
                    "due_date": "2026-10-26",
                    "estimated_minutes": 60,
                    "streak_days": 0,
                    "tags": ["devops", "cloud", "infra"]
                },
                {
                    "id": "task-003",
                    "title": "Review Multi-Agent Consensus Security Architecture",
                    "type": "task",
                    "category": "Architecture",
                    "priority": "medium",
                    "completed": False,
                    "created_at": now,
                    "due_date": "2026-10-28",
                    "estimated_minutes": 30,
                    "streak_days": 0,
                    "tags": ["ai", "security"]
                },
                {
                    "id": "habit-001",
                    "title": "Morning 45-min Deep Focus Block (Zero Notifications)",
                    "type": "habit",
                    "category": "Focus & Flow",
                    "priority": "high",
                    "completed": True,
                    "created_at": now,
                    "due_date": "Daily",
                    "estimated_minutes": 45,
                    "streak_days": 18,
                    "tags": ["habit", "focus", "flow"]
                },
                {
                    "id": "habit-002",
                    "title": "Technical Reading & Architecture Whitepapers",
                    "type": "habit",
                    "category": "Continuous Mastery",
                    "priority": "medium",
                    "completed": True,
                    "created_at": now,
                    "due_date": "Daily",
                    "estimated_minutes": 30,
                    "streak_days": 24,
                    "tags": ["habit", "reading"]
                },
                {
                    "id": "habit-003",
                    "title": "Post-Work Cognitive Shutdown & Habit Reconciliation",
                    "type": "habit",
                    "category": "Mindfulness",
                    "priority": "medium",
                    "completed": False,
                    "created_at": now,
                    "due_date": "Daily",
                    "estimated_minutes": 15,
                    "streak_days": 12,
                    "tags": ["habit", "recovery"]
                }
            ],
            "metrics": {
                "productivity_score": 94.8,
                "habits_completed_today": 2,
                "total_habits_active": 3,
                "tasks_completed_today": 1,
                "tasks_pending": 2,
                "total_time_saved_hours": 38.5,
                "streak_record_days": 24,
                "focus_hours_logged": 6.2,
                "automations_triggered_today": 5,
                "weekly_velocity": [88, 92, 90, 95, 96, 91, 95]
            },
            "workflow_history": []
        }

    def _init_store(self):
        """Initializes database directory and reads data or creates seed data."""
        with self._lock:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if self.db_path.exists():
                try:
                    with open(self.db_path, "r", encoding="utf-8") as f:
                        self._state = json.load(f)
                        logger.info("CorePulse database loaded successfully from %s", self.db_path)
                        return
                except Exception as ex:
                    logger.warning("Failed to parse existing DB file: %s. Rebuilding seed.", ex)

            self._state = self._get_default_seed()
            self._save_state_unlocked()

    def _save_state_unlocked(self):
        """Persists internal state to disk atomically with retry on Windows file lock."""
        tmp_file = self.db_path.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
            
            # Resilient atomic replace with short backoff for Windows file locks
            replaced = False
            for attempt in range(10):
                try:
                    tmp_file.replace(self.db_path)
                    replaced = True
                    break
                except OSError:
                    time.sleep(0.05 * (attempt + 1))
            
            if not replaced:
                try:
                    tmp_file.replace(self.db_path)
                    replaced = True
                except OSError:
                    # Windows fallback: direct overwrite if atomic rename is held
                    with open(self.db_path, "w", encoding="utf-8") as target_f:
                        json.dump(self._state, target_f, indent=2, ensure_ascii=False)
                    replaced = True
        except Exception as ex:
            logger.error("Error saving state to %s: %s", self.db_path, ex)
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass

    def get_health(self) -> Dict[str, Any]:
        """Returns system operational metrics and health status."""
        uptime = time.time() - self.start_time
        hours, rem = divmod(int(uptime), 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{hours:02d}h {minutes:02d}m {seconds:02d}s"

        with self._lock:
            task_count = len(self._state.get("tasks", []))
            return {
                "status": "healthy",
                "service": "CorePulse Engine",
                "version": VERSION,
                "build_id": BUILD_ID,
                "uptime_seconds": round(uptime, 2),
                "uptime_human": uptime_str,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "db_status": "synced",
                "records_tracked": task_count,
                "thread_count": threading.active_count()
            }

    def get_tasks(self, item_type: Optional[str] = None, completed: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Retrieves tasks and habits with optional filtering."""
        with self._lock:
            items = list(self._state.get("tasks", []))

            if item_type:
                items = [t for t in items if t.get("type", "task") == item_type]

            if completed is not None:
                items = [t for t in items if t.get("completed") is completed]

            # Return deep copy sorted by priority then created_at
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            items.sort(key=lambda x: (
                1 if x.get("completed") else 0,
                priority_order.get(x.get("priority", "medium"), 2),
                x.get("created_at", "")
            ))
            return items

    def create_or_update_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates or updates a task/habit entity."""
        with self._lock:
            tasks = self._state.setdefault("tasks", [])
            task_id = data.get("id")

            # Check if updating existing
            existing_idx = None
            if task_id:
                for idx, t in enumerate(tasks):
                    if t.get("id") == task_id:
                        existing_idx = idx
                        break

            now = datetime.now(timezone.utc).isoformat()
            if existing_idx is not None:
                # Update existing
                existing_item = tasks[existing_idx]
                updated_item = {
                    **existing_item,
                    **data,
                    "updated_at": now
                }
                tasks[existing_idx] = updated_item
                result = updated_item
            else:
                # Enforce subscription tier limits
                tier_key = self._state.get("subscription", {}).get("tier", "starter")
                gates = TIER_FEATURE_GATES.get(tier_key, TIER_FEATURE_GATES["starter"])
                item_type = data.get("type", "task")
                if item_type == "habit":
                    current_habits = sum(1 for t in tasks if t.get("type") == "habit")
                    max_habits = gates.get("max_habits", 5)
                    if max_habits != -1 and current_habits >= max_habits:
                        raise ValueError(f"Limit of {max_habits} habits reached for '{tier_key}' tier. Upgrade required.")
                else:
                    current_tasks = sum(1 for t in tasks if t.get("type") != "habit")
                    max_tasks = gates.get("max_tasks", 20)
                    if max_tasks != -1 and current_tasks >= max_tasks:
                        raise ValueError(f"Limit of {max_tasks} tasks reached for '{tier_key}' tier. Upgrade required.")

                # Create new
                new_id = task_id or (f"task-{uuid.uuid4().hex[:8]}" if data.get("type") != "habit" else f"habit-{uuid.uuid4().hex[:8]}")
                result = {
                    "id": new_id,
                    "title": data.get("title", "Untitled Task").strip(),
                    "type": data.get("type", "task"),
                    "category": data.get("category", "General"),
                    "priority": data.get("priority", "medium"),
                    "completed": bool(data.get("completed", False)),
                    "created_at": now,
                    "due_date": data.get("due_date", "Today"),
                    "estimated_minutes": int(data.get("estimated_minutes", 30)),
                    "streak_days": int(data.get("streak_days", 1 if data.get("type") == "habit" else 0)),
                    "tags": data.get("tags", [])
                }
                tasks.insert(0, result)

            self._recalculate_metrics_unlocked()
            self._save_state_unlocked()
            return result

    def toggle_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Toggles completed status of a task or habit."""
        with self._lock:
            tasks = self._state.setdefault("tasks", [])
            for task in tasks:
                if task.get("id") == task_id:
                    new_state = not task.get("completed", False)
                    task["completed"] = new_state
                    if task.get("type") == "habit":
                        if new_state:
                            task["streak_days"] = task.get("streak_days", 0) + 1
                        else:
                            task["streak_days"] = max(0, task.get("streak_days", 1) - 1)
                    task["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._recalculate_metrics_unlocked()
                    self._save_state_unlocked()
                    return task
            return None

    def delete_task(self, task_id: str) -> bool:
        """Deletes a task by ID."""
        with self._lock:
            tasks = self._state.setdefault("tasks", [])
            before_len = len(tasks)
            self._state["tasks"] = [t for t in tasks if t.get("id") != task_id]
            if len(self._state["tasks"]) != before_len:
                self._recalculate_metrics_unlocked()
                self._save_state_unlocked()
                return True
            return False

    def _recalculate_metrics_unlocked(self):
        """Recomputes internal productivity metrics dynamically."""
        tasks = self._state.get("tasks", [])
        m = self._state.setdefault("metrics", {})

        habits = [t for t in tasks if t.get("type") == "habit"]
        regular_tasks = [t for t in tasks if t.get("type") != "habit"]

        habits_done = sum(1 for h in habits if h.get("completed"))
        tasks_done = sum(1 for t in regular_tasks if t.get("completed"))
        tasks_pending = len(regular_tasks) - tasks_done

        m["habits_completed_today"] = habits_done
        m["total_habits_active"] = len(habits)
        m["tasks_completed_today"] = tasks_done
        m["tasks_pending"] = tasks_pending

        total_tracked = len(tasks)
        if total_tracked > 0:
            total_done = habits_done + tasks_done
            completion_ratio = total_done / total_tracked
            # Score formula weighted by consistency
            streak_bonus = min(15, (m.get("streak_record_days", 10) * 0.4))
            score = min(99.4, round(60 + (completion_ratio * 30) + streak_bonus, 1))
            m["productivity_score"] = score
        else:
            m["productivity_score"] = 75.0

    def get_metrics(self) -> Dict[str, Any]:
        """Returns real-time productivity metrics."""
        with self._lock:
            return dict(self._state.get("metrics", {}))

    def record_workflow_execution(self, workflow_name: str, time_saved_minutes: float, logs: List[str]) -> Dict[str, Any]:
        """Logs workflow execution and increments total time saved."""
        with self._lock:
            m = self._state.setdefault("metrics", {})
            current_saved_hours = m.get("total_time_saved_hours", 38.5)
            hours_saved = round(time_saved_minutes / 60.0, 2)
            m["total_time_saved_hours"] = round(current_saved_hours + hours_saved, 2)
            m["automations_triggered_today"] = m.get("automations_triggered_today", 0) + 1

            record = {
                "id": f"wf-run-{uuid.uuid4().hex[:8]}",
                "workflow_name": workflow_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "time_saved_minutes": time_saved_minutes,
                "status": "success",
                "step_count": len(logs)
            }
            history = self._state.setdefault("workflow_history", [])
            history.insert(0, record)
            if len(history) > 50:
                self._state["workflow_history"] = history[:50]

            self._save_state_unlocked()
            return record

    def get_subscription(self) -> Dict[str, Any]:
        """Returns subscription details and active feature gates."""
        with self._lock:
            sub = self._state.get("subscription", {})
            tier_key = sub.get("tier", "pro").lower()
            features = TIER_FEATURE_GATES.get(tier_key, TIER_FEATURE_GATES["pro"])
            sub["features"] = features
            return dict(sub)

    def upgrade_subscription(
        self,
        tier: str,
        customer_name: Optional[str] = None,
        organization: Optional[str] = None,
        license_key: Optional[str] = None,
        renews_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upgrades or modifies subscription tier and license metadata."""
        tier_key = tier.lower()
        if tier_key not in TIER_FEATURE_GATES:
            raise ValueError(f"Invalid tier: {tier}. Must be one of {list(TIER_FEATURE_GATES.keys())}")

        with self._lock:
            sub = self._state.setdefault("subscription", {})
            sub["tier"] = tier_key
            if customer_name is not None:
                sub["customer_name"] = customer_name
            if organization is not None:
                sub["organization"] = organization
            if license_key is not None:
                sub["license_key"] = license_key
            if renews_at is not None:
                sub["renews_at"] = renews_at
            sub["features"] = TIER_FEATURE_GATES[tier_key]
            sub["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_state_unlocked()
            return dict(sub)

# Singleton DB instance
db = Database()
