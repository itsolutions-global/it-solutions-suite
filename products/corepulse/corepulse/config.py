"""
CorePulse Configuration Module
Defines runtime configurations, feature gates, and operational constants.
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("COREPULSE_DATA_DIR", str(BASE_DIR / "data")))
STATIC_DIR = BASE_DIR / "corepulse" / "static"
DB_FILE = Path(os.getenv("COREPULSE_DB_FILE", str(DATA_DIR / "corepulse_store.json")))
SQLITE_DB_FILE = Path(os.getenv("COREPULSE_SQLITE_FILE", str(DATA_DIR / "corepulse.sqlite3")))

# Server Settings
HOST = os.getenv("COREPULSE_HOST", "127.0.0.1")
PORT = int(os.getenv("COREPULSE_PORT", "8080"))
DEBUG = os.getenv("COREPULSE_DEBUG", "True").lower() in ("true", "1", "yes")

# Product Metadata
APP_NAME = "CorePulse"
APP_TAGLINE = "Autonomous Productivity & Life OS"
VERSION = "1.0.0"
BUILD_ID = "CP-2026-RELEASE-1.0"

# Feature Gates by Subscription Tier (Open-Core Commercial Model - Path A)
TIER_FEATURE_GATES = {
    "starter": {
        "name": "Community Starter",
        "price_monthly": 0,
        "max_tasks": -1,  # Unmetered local tasks
        "max_habits": -1,  # Unmetered local habits
        "workflow_automation": True,
        "max_workflows_per_day": -1,  # Unmetered local workflow triggers
        "analytics_history_days": 30,
        "export_data": True,
        "custom_webhooks": True,
        "priority_support": False,
        "ai_insights": True,
        "cloud_sync": False,
        "team_workspaces": False,
        "central_audit_fleet": False,
    },
    "pro": {
        "name": "Professional",
        "price_monthly": 9.99,
        "max_tasks": -1,
        "max_habits": -1,
        "workflow_automation": True,
        "max_workflows_per_day": -1,
        "analytics_history_days": 365,
        "export_data": True,
        "custom_webhooks": True,
        "priority_support": True,
        "ai_insights": True,
        "cloud_sync": True,
        "team_workspaces": False,
        "central_audit_fleet": False,
    },
    "team": {
        "name": "Team",
        "price_monthly": 19,
        "max_tasks": -1,
        "max_habits": -1,
        "workflow_automation": True,
        "max_workflows_per_day": -1,
        "analytics_history_days": 365,
        "export_data": True,
        "custom_webhooks": True,
        "priority_support": True,
        "ai_insights": True,
        "cloud_sync": True,
        "team_workspaces": True,
        "central_audit_fleet": False,
        "seats": 5,
    },
    "enterprise": {
        "name": "Enterprise Elite",
        "price_monthly": 199,
        "max_tasks": -1,
        "max_habits": -1,
        "workflow_automation": True,
        "max_workflows_per_day": -1,
        "analytics_history_days": -1,  # Unlimited historical analytics
        "export_data": True,
        "custom_webhooks": True,
        "priority_support": True,
        "ai_insights": True,
        "cloud_sync": True,
        "team_workspaces": True,
        "central_audit_fleet": True,
        "dedicated_sla": True,
        "multi_tenant_sync": True,
        "seats": -1,
    }
}

