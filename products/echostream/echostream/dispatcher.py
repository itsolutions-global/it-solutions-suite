"""
EchoStream CorePulse Dispatcher
Transmits extracted action items directly into the local CorePulse REST API (/api/tasks)
with resilient in-process database fallback when the HTTP daemon is offline.
"""

import json
import logging
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("echostream.dispatcher")

DEFAULT_API_URL = "http://127.0.0.1:8080/api/tasks"


class CorePulseDispatcher:
    """
    Client for transmitting EchoStream tasks into CorePulse.
    Supports HTTP REST API transmission and direct internal database persistence.
    """

    def __init__(self, api_url: str = DEFAULT_API_URL, timeout: float = 3.0):
        self.api_url = api_url
        self.timeout = timeout

    def dispatch_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches a single task into CorePulse."""
        payload = {
            "title": task.get("title", "Untitled Spoken Task"),
            "type": task.get("type", "task"),
            "category": task.get("category", "Voice Intake"),
            "priority": task.get("priority", "medium"),
            "completed": bool(task.get("completed", False)),
            "due_date": task.get("due_date", "Today"),
            "estimated_minutes": int(task.get("estimated_minutes", 30)),
            "tags": task.get("tags", ["echostream", "voice-intake"])
        }

        # 1. Attempt REST API dispatch
        try:
            req = urllib.request.Request(
                self.api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "EchoStream-Dispatcher/1.0"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status in (200, 201):
                    res_json = json.loads(resp.read().decode("utf-8"))
                    return {
                        "status": "success",
                        "mode": "rest_api",
                        "task_id": res_json.get("task", {}).get("id"),
                        "task": res_json.get("task", payload)
                    }
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as net_err:
            logger.debug("CorePulse HTTP daemon unavailable (%s). Engaging direct DB fallback.", net_err)

        # 2. Resilient Direct Database Fallback
        try:
            from corepulse.database import db
            created = db.create_or_update_task(payload)
            return {
                "status": "success",
                "mode": "direct_db",
                "task_id": created.get("id"),
                "task": created
            }
        except Exception as db_err:
            logger.error("Failed to persist task to CorePulse: %s", db_err)
            return {
                "status": "failed",
                "mode": "error",
                "error": str(db_err),
                "task": payload
            }

    def dispatch_batch(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Dispatches a collection of parsed commitments into CorePulse.
        Returns aggregate summary.
        """
        results: List[Dict[str, Any]] = []
        successful_count = 0
        failed_count = 0
        modes_used = set()

        for t in tasks:
            res = self.dispatch_task(t)
            results.append(res)
            if res["status"] == "success":
                successful_count += 1
                modes_used.add(res["mode"])
            else:
                failed_count += 1

        primary_mode = list(modes_used)[0] if len(modes_used) == 1 else ("mixed" if modes_used else "none")

        return {
            "status": "success" if failed_count == 0 else "partial_failure",
            "total": len(tasks),
            "dispatched": successful_count,
            "failed": failed_count,
            "mode": primary_mode,
            "results": results
        }
