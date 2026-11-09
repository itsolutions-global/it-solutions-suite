"""
CorePulse SQLite Enterprise Persistence Engine
High-throughput enterprise storage backend using Python's built-in sqlite3 with WAL (Write-Ahead Logging) mode.
Fulfills the exact database contract as database.py.
"""

import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from corepulse.config import DATA_DIR, SQLITE_DB_FILE, VERSION, BUILD_ID, TIER_FEATURE_GATES

logger = logging.getLogger("corepulse.database_sqlite")

class Database:
    """Enterprise SQLite storage engine configured with WAL-mode for high concurrency."""

    def __init__(self, db_path: Union[str, Path] = SQLITE_DB_FILE):
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path
        self._lock = threading.RLock()
        self.start_time = time.time()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_engine()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns or creates the thread-safe SQLite connection with WAL mode enabled."""
        if self._conn is None:
            if not str(self.db_path).startswith(":memory:"):
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10.0,
                isolation_level=None  # autocommit mode; manage transactions explicitly when needed
            )
            self._conn.row_factory = sqlite3.Row
            # Enable high-concurrency enterprise PRAGMAs
            cursor = self._conn.cursor()
            cursor.execute("PRAGMA journal_mode = WAL;")
            wal_mode = cursor.fetchone()[0]
            cursor.execute("PRAGMA synchronous = NORMAL;")
            cursor.execute("PRAGMA busy_timeout = 5000;")
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.close()
            logger.info("Initialized CorePulse SQLite database (%s) in journal_mode=%s", self.db_path, wal_mode)
        return self._conn

    def _init_engine(self):
        """Initializes tables and populates default seed data if database is fresh."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscription (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    tier TEXT NOT NULL DEFAULT 'pro',
                    status TEXT NOT NULL DEFAULT 'active',
                    customer_name TEXT DEFAULT 'Executive Director',
                    organization TEXT DEFAULT 'OmniCorp Global',
                    license_key TEXT,
                    renews_at TEXT,
                    updated_at TEXT
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'task',
                    category TEXT NOT NULL DEFAULT 'General',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    completed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    due_date TEXT DEFAULT 'Today',
                    estimated_minutes INTEGER DEFAULT 30,
                    streak_days INTEGER DEFAULT 0,
                    tags TEXT DEFAULT '[]'
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    productivity_score REAL DEFAULT 94.8,
                    habits_completed_today INTEGER DEFAULT 2,
                    total_habits_active INTEGER DEFAULT 3,
                    tasks_completed_today INTEGER DEFAULT 1,
                    tasks_pending INTEGER DEFAULT 2,
                    total_time_saved_hours REAL DEFAULT 38.5,
                    streak_record_days INTEGER DEFAULT 24,
                    focus_hours_logged REAL DEFAULT 6.2,
                    automations_triggered_today INTEGER DEFAULT 5,
                    weekly_velocity TEXT DEFAULT '[88, 92, 90, 95, 96, 91, 95]'
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_history (
                    id TEXT PRIMARY KEY,
                    workflow_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    time_saved_minutes REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'success',
                    step_count INTEGER DEFAULT 0,
                    logs TEXT DEFAULT '[]'
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_outbox (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    lamport_clock INTEGER NOT NULL,
                    client_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    is_synced INTEGER NOT NULL DEFAULT 0
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crdt_metadata (
                    entity_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    lamport_clock INTEGER NOT NULL DEFAULT 0,
                    client_id TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS supabase_sync_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload JSON NOT NULL,
                    hlc TEXT NOT NULL,
                    lamport_clock INTEGER NOT NULL DEFAULT 1,
                    client_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_synced INTEGER DEFAULT 0
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_supabase_outbox_pending 
                ON supabase_sync_outbox (is_synced, id);
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS supabase_sync_inbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload JSON NOT NULL,
                    hlc TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    received_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed INTEGER DEFAULT 0
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS supabase_sync_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS supabase_conflict_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    winner TEXT NOT NULL,
                    winning_val TEXT,
                    winning_hlc TEXT NOT NULL,
                    losing_val TEXT,
                    losing_hlc TEXT NOT NULL,
                    resolved_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Check if seed required
            cursor.execute("SELECT COUNT(*) FROM tasks;")
            task_count = cursor.fetchone()[0]

            if task_count == 0:
                self._populate_seed_data(cursor)

            cursor.close()

    def _populate_seed_data(self, cursor: sqlite3.Cursor):
        """Populates seed data matching the reference system."""
        now = datetime.now(timezone.utc).isoformat()
        license_key = "CP-PRO-" + uuid.uuid4().hex[:12].upper()

        # Seed subscription
        cursor.execute("""
            INSERT OR REPLACE INTO subscription (id, tier, status, customer_name, organization, license_key, renews_at, updated_at)
            VALUES (1, 'pro', 'active', 'Executive Director', 'OmniCorp Global', ?, '2027-10-26T00:00:00Z', ?);
        """, (license_key, now))

        # Seed metrics
        cursor.execute("""
            INSERT OR REPLACE INTO metrics (
                id, productivity_score, habits_completed_today, total_habits_active,
                tasks_completed_today, tasks_pending, total_time_saved_hours,
                streak_record_days, focus_hours_logged, automations_triggered_today, weekly_velocity
            ) VALUES (1, 94.8, 2, 3, 1, 2, 38.5, 24, 6.2, 5, ?);
        """, (json.dumps([88, 92, 90, 95, 96, 91, 95]),))

        # Seed initial tasks & habits
        initial_tasks = [
            ("task-001", "Review Q4 High-Velocity Roadmap & Technical Milestones", "task", "Strategic", "high", 0, now, None, "2026-10-27", 45, 0, json.dumps(["strategy", "executive", "q4"])),
            ("task-002", "Automate AWS Cloud Cost Anomaly Pipeline", "task", "Engineering", "critical", 1, now, None, "2026-10-26", 60, 0, json.dumps(["devops", "cloud", "infra"])),
            ("task-003", "Review Multi-Agent Consensus Security Architecture", "task", "Architecture", "medium", 0, now, None, "2026-10-28", 30, 0, json.dumps(["ai", "security"])),
            ("habit-001", "Morning 45-min Deep Focus Block (Zero Notifications)", "habit", "Focus & Flow", "high", 1, now, None, "Daily", 45, 18, json.dumps(["habit", "focus", "flow"])),
            ("habit-002", "Technical Reading & Architecture Whitepapers", "habit", "Continuous Mastery", "medium", 1, now, None, "Daily", 30, 24, json.dumps(["habit", "reading"])),
            ("habit-003", "Post-Work Cognitive Shutdown & Habit Reconciliation", "habit", "Mindfulness", "medium", 0, now, None, "Daily", 15, 12, json.dumps(["habit", "recovery"]))
        ]

        cursor.executemany("""
            INSERT INTO tasks (id, title, type, category, priority, completed, created_at, updated_at, due_date, estimated_minutes, streak_days, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, initial_tasks)
        logger.info("CorePulse SQLite database initialized with enterprise demo seed.")

    def get_journal_mode(self) -> str:
        """Queries and returns the current SQLite journal_mode."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode;")
            mode = cursor.fetchone()[0]
            cursor.close()
            return str(mode).lower()

    def get_health(self) -> Dict[str, Any]:
        """Returns system operational metrics and health status."""
        uptime = time.time() - self.start_time
        hours, rem = divmod(int(uptime), 3600)
        minutes, seconds = divmod(rem, 60)
        uptime_str = f"{hours:02d}h {minutes:02d}m {seconds:02d}s"

        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks;")
            task_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA journal_mode;")
            journal_mode = cursor.fetchone()[0]
            cursor.close()

            return {
                "status": "healthy",
                "service": "CorePulse Engine (SQLite WAL)",
                "version": VERSION,
                "build_id": BUILD_ID,
                "uptime_seconds": round(uptime, 2),
                "uptime_human": uptime_str,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "db_status": "sqlite-wal-active",
                "records_tracked": task_count,
                "thread_count": threading.active_count(),
                "journal_mode": str(journal_mode).lower()
            }

    def _row_to_task_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Maps a SQLite tasks row to an API-compliant task dict."""
        tags = []
        if row["tags"]:
            try:
                tags = json.loads(row["tags"])
            except Exception:
                tags = []

        return {
            "id": row["id"],
            "title": row["title"],
            "type": row["type"],
            "category": row["category"],
            "priority": row["priority"],
            "completed": bool(row["completed"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "due_date": row["due_date"],
            "estimated_minutes": int(row["estimated_minutes"]),
            "streak_days": int(row["streak_days"]),
            "tags": tags
        }

    def get_tasks(self, item_type: Optional[str] = None, completed: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Retrieves tasks and habits with optional filtering, sorted by status, priority, and date."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM tasks WHERE 1=1"
            params: List[Any] = []

            if item_type is not None:
                query += " AND type = ?"
                params.append(item_type)

            if completed is not None:
                query += " AND completed = ?"
                params.append(1 if completed else 0)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()

            items = [self._row_to_task_dict(r) for r in rows]

            # Priority sort order
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            items.sort(key=lambda x: (
                1 if x.get("completed") else 0,
                priority_order.get(x.get("priority", "medium"), 2),
                x.get("created_at", "")
            ))
            return items

    def create_or_update_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates or updates a task/habit entity, enforcing tier gates for new items."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            task_id = data.get("id")
            existing_row = None
            if task_id:
                cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                existing_row = cursor.fetchone()

            now = datetime.now(timezone.utc).isoformat()

            if existing_row:
                # Update existing task
                current_dict = self._row_to_task_dict(existing_row)
                updated_title = data.get("title", current_dict["title"]).strip()
                updated_type = data.get("type", current_dict["type"])
                updated_category = data.get("category", current_dict["category"])
                updated_priority = data.get("priority", current_dict["priority"])
                updated_completed = bool(data.get("completed", current_dict["completed"]))
                updated_due_date = data.get("due_date", current_dict["due_date"])
                updated_est = int(data.get("estimated_minutes", current_dict["estimated_minutes"]))
                updated_streak = int(data.get("streak_days", current_dict["streak_days"]))
                updated_tags = json.dumps(data.get("tags", current_dict["tags"]))

                cursor.execute("""
                    UPDATE tasks
                    SET title = ?, type = ?, category = ?, priority = ?, completed = ?,
                        updated_at = ?, due_date = ?, estimated_minutes = ?, streak_days = ?, tags = ?
                    WHERE id = ?;
                """, (
                    updated_title, updated_type, updated_category, updated_priority,
                    1 if updated_completed else 0, now, updated_due_date, updated_est,
                    updated_streak, updated_tags, task_id
                ))

                result = {
                    **current_dict,
                    "title": updated_title,
                    "type": updated_type,
                    "category": updated_category,
                    "priority": updated_priority,
                    "completed": updated_completed,
                    "updated_at": now,
                    "due_date": updated_due_date,
                    "estimated_minutes": updated_est,
                    "streak_days": updated_streak,
                    "tags": data.get("tags", current_dict["tags"])
                }
            else:
                # Enforce subscription tier limits
                cursor.execute("SELECT tier FROM subscription WHERE id = 1;")
                sub_row = cursor.fetchone()
                tier_key = (sub_row["tier"] if sub_row else "starter").lower()
                gates = TIER_FEATURE_GATES.get(tier_key, TIER_FEATURE_GATES["starter"])
                item_type = data.get("type", "task")

                if item_type == "habit":
                    cursor.execute("SELECT COUNT(*) FROM tasks WHERE type = 'habit';")
                    current_habits = cursor.fetchone()[0]
                    max_habits = gates.get("max_habits", 5)
                    if max_habits != -1 and current_habits >= max_habits:
                        cursor.close()
                        raise ValueError(f"Limit of {max_habits} habits reached for '{tier_key}' tier. Upgrade required.")
                else:
                    cursor.execute("SELECT COUNT(*) FROM tasks WHERE type != 'habit';")
                    current_tasks = cursor.fetchone()[0]
                    max_tasks = gates.get("max_tasks", 20)
                    if max_tasks != -1 and current_tasks >= max_tasks:
                        cursor.close()
                        raise ValueError(f"Limit of {max_tasks} tasks reached for '{tier_key}' tier. Upgrade required.")

                new_id = task_id or (f"task-{uuid.uuid4().hex[:8]}" if item_type != "habit" else f"habit-{uuid.uuid4().hex[:8]}")
                title = data.get("title", "Untitled Task").strip()
                category = data.get("category", "General")
                priority = data.get("priority", "medium")
                completed = bool(data.get("completed", False))
                due_date = data.get("due_date", "Today")
                est_min = int(data.get("estimated_minutes", 30))
                streak = int(data.get("streak_days", 1 if item_type == "habit" else 0))
                tags = data.get("tags", [])

                cursor.execute("""
                    INSERT INTO tasks (id, title, type, category, priority, completed, created_at, updated_at, due_date, estimated_minutes, streak_days, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?);
                """, (new_id, title, item_type, category, priority, 1 if completed else 0, now, due_date, est_min, streak, json.dumps(tags)))

                result = {
                    "id": new_id,
                    "title": title,
                    "type": item_type,
                    "category": category,
                    "priority": priority,
                    "completed": completed,
                    "created_at": now,
                    "updated_at": None,
                    "due_date": due_date,
                    "estimated_minutes": est_min,
                    "streak_days": streak,
                    "tags": tags
                }

            self._recalculate_metrics_unlocked(cursor)
            self._enqueue_supabase_mutation(cursor, "task", result["id"], "update" if existing_row else "create", result)
            cursor.close()
            return result

    def toggle_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Toggles completed status of a task or habit."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                cursor.close()
                return None

            now_completed = 0 if row["completed"] else 1
            now_iso = datetime.now(timezone.utc).isoformat()
            new_streak = row["streak_days"]

            if row["type"] == "habit":
                if now_completed:
                    new_streak += 1
                else:
                    new_streak = max(0, new_streak - 1)

            cursor.execute("""
                UPDATE tasks
                SET completed = ?, streak_days = ?, updated_at = ?
                WHERE id = ?;
            """, (now_completed, new_streak, now_iso, task_id))

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            updated_row = cursor.fetchone()
            result = self._row_to_task_dict(updated_row)

            self._recalculate_metrics_unlocked(cursor)
            self._enqueue_supabase_mutation(cursor, "task", task_id, "update", result)
            cursor.close()
            return result

    def delete_task(self, task_id: str) -> bool:
        """Deletes a task by ID."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            affected = cursor.rowcount > 0

            if affected:
                self._recalculate_metrics_unlocked(cursor)
                self._enqueue_supabase_mutation(cursor, "task", task_id, "delete", {"id": task_id, "is_deleted": True})

            cursor.close()
            return affected

    def _enqueue_supabase_mutation(self, cursor: sqlite3.Cursor, entity_type: str, entity_id: str, action: str, payload: Dict[str, Any]):
        """Safely enqueues a mutation into supabase_sync_outbox in < 2ms."""
        try:
            now_us = int(time.time() * 1_000_000)
            node_id = "local"
            hlc = f"{now_us}:0:{node_id}"
            tenant_id = os.getenv("SUPABASE_TENANT_ID", "org_enterprise_alpha")
            cursor.execute("""
                INSERT INTO supabase_sync_outbox (
                    entity_type, entity_id, action, payload, hlc,
                    lamport_clock, client_id, tenant_id, is_synced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0);
            """, (
                entity_type,
                entity_id,
                action,
                json.dumps(payload),
                hlc,
                now_us,
                node_id,
                tenant_id
            ))
            cursor.execute("SELECT COUNT(*) FROM supabase_sync_outbox WHERE is_synced = 0;")
            pending = cursor.fetchone()[0]
            cursor.execute("INSERT OR REPLACE INTO supabase_sync_state (key, value) VALUES ('pending_count', ?);", (str(pending),))
            cursor.execute("INSERT OR REPLACE INTO supabase_sync_state (key, value) VALUES ('sync_state', 'PENDING');")
        except Exception as ex:
            logger.debug("Non-critical supabase outbox enqueue: %s", ex)

    def _recalculate_metrics_unlocked(self, cursor: sqlite3.Cursor):
        """Recomputes internal productivity metrics dynamically within the active connection."""
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE type = 'habit';")
        total_habits = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE type = 'habit' AND completed = 1;")
        habits_done = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE type != 'habit';")
        total_tasks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE type != 'habit' AND completed = 1;")
        tasks_done = cursor.fetchone()[0]

        tasks_pending = total_tasks - tasks_done
        total_tracked = total_habits + total_tasks

        cursor.execute("SELECT streak_record_days FROM metrics WHERE id = 1;")
        streak_row = cursor.fetchone()
        streak_record = streak_row["streak_record_days"] if streak_row else 24

        if total_tracked > 0:
            total_done = habits_done + tasks_done
            completion_ratio = total_done / total_tracked
            streak_bonus = min(15.0, (streak_record * 0.4))
            score = min(99.4, round(60.0 + (completion_ratio * 30.0) + streak_bonus, 1))
        else:
            score = 75.0

        cursor.execute("""
            UPDATE metrics
            SET productivity_score = ?,
                habits_completed_today = ?,
                total_habits_active = ?,
                tasks_completed_today = ?,
                tasks_pending = ?
            WHERE id = 1;
        """, (score, habits_done, total_habits, tasks_done, tasks_pending))

    def get_metrics(self) -> Dict[str, Any]:
        """Returns real-time productivity metrics."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM metrics WHERE id = 1;")
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return {}

            weekly_velocity = [88, 92, 90, 95, 96, 91, 95]
            if row["weekly_velocity"]:
                try:
                    weekly_velocity = json.loads(row["weekly_velocity"])
                except Exception:
                    pass

            return {
                "productivity_score": float(row["productivity_score"]),
                "habits_completed_today": int(row["habits_completed_today"]),
                "total_habits_active": int(row["total_habits_active"]),
                "tasks_completed_today": int(row["tasks_completed_today"]),
                "tasks_pending": int(row["tasks_pending"]),
                "total_time_saved_hours": float(row["total_time_saved_hours"]),
                "streak_record_days": int(row["streak_record_days"]),
                "focus_hours_logged": float(row["focus_hours_logged"]),
                "automations_triggered_today": int(row["automations_triggered_today"]),
                "weekly_velocity": weekly_velocity
            }

    def record_workflow_execution(self, workflow_name: str, time_saved_minutes: float, logs: List[str]) -> Dict[str, Any]:
        """Logs workflow execution and increments total time saved and automations count."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            exec_id = f"wf-run-{uuid.uuid4().hex[:8]}"
            now_iso = datetime.now(timezone.utc).isoformat()
            hours_saved = round(time_saved_minutes / 60.0, 2)

            # Insert execution history
            cursor.execute("""
                INSERT INTO workflow_history (id, workflow_name, timestamp, time_saved_minutes, status, step_count, logs)
                VALUES (?, ?, ?, ?, 'success', ?, ?);
            """, (exec_id, workflow_name, now_iso, time_saved_minutes, len(logs), json.dumps(logs)))

            # Update metrics
            cursor.execute("SELECT total_time_saved_hours, automations_triggered_today FROM metrics WHERE id = 1;")
            m_row = cursor.fetchone()
            current_saved = float(m_row["total_time_saved_hours"]) if m_row else 38.5
            current_automations = int(m_row["automations_triggered_today"]) if m_row else 5

            new_saved = round(current_saved + hours_saved, 2)
            new_automations = current_automations + 1

            cursor.execute("""
                UPDATE metrics
                SET total_time_saved_hours = ?, automations_triggered_today = ?
                WHERE id = 1;
            """, (new_saved, new_automations))

            cursor.close()

            return {
                "id": exec_id,
                "workflow_name": workflow_name,
                "timestamp": now_iso,
                "time_saved_minutes": time_saved_minutes,
                "status": "success",
                "step_count": len(logs)
            }

    def get_subscription(self) -> Dict[str, Any]:
        """Returns subscription details and active feature gates."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subscription WHERE id = 1;")
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return {}

            tier_key = str(row["tier"]).lower()
            features = TIER_FEATURE_GATES.get(tier_key, TIER_FEATURE_GATES["pro"])

            return {
                "tier": tier_key,
                "status": row["status"],
                "customer_name": row["customer_name"],
                "organization": row["organization"],
                "license_key": row["license_key"],
                "renews_at": row["renews_at"],
                "features": features
            }

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
            conn = self._get_connection()
            cursor = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()

            cursor.execute("""
                UPDATE subscription
                SET tier = ?,
                    customer_name = COALESCE(?, customer_name),
                    organization = COALESCE(?, organization),
                    license_key = COALESCE(?, license_key),
                    renews_at = COALESCE(?, renews_at),
                    updated_at = ?
                WHERE id = 1;
            """, (tier_key, customer_name, organization, license_key, renews_at, now_iso))

            cursor.close()
            return self.get_subscription()

    def close(self):
        """Closes the underlying SQLite database connection cleanly."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception as ex:
                    logger.warning("Error closing SQLite connection: %s", ex)
                finally:
                    self._conn = None

# Singleton SQLite DB instance
sqlite_db = Database()
