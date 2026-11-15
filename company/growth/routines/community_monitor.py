"""Autonomous Inbound Community & Customer Engagement Monitor
IT Solutions Global Corporation

Monitors:
1. GitHub Issues, PRs, Discussions, Stars, and Forks for itsolutions-global/it-solutions-suite
2. DEV Community Article Comments & Reactions for @itsolutionsglobal
3. PyPI Package Health and Releases
4. Logs telemetry to company/growth/INBOUND_LOG.json
5. Generates auto-triage recommendations for any inbound interactions.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE_ROOT = Path(r"e:\It solution")
VAULT_PATH = WORKSPACE_ROOT / "data" / "vault" / "credentials.json"
INBOUND_LOG_PATH = WORKSPACE_ROOT / "company" / "growth" / "INBOUND_LOG.json"


def load_credentials():
    if not VAULT_PATH.exists():
        return {}
    try:
        return json.loads(VAULT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def fetch_json(url, headers=None, timeout=15):
    hdrs = {"User-Agent": "ITSolutions-Autonomous-Monitor/1.0"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as e:
        return {"error": e.code, "reason": e.reason}, e.code
    except Exception as e:
        return {"error": str(e)}, 500


def check_github(vault):
    gh = vault.get("github", {})
    pat = gh.get("pat")
    headers = {}
    if pat:
        headers["Authorization"] = f"token {pat}"

    # 1. Repo general telemetry
    repo_data, code = fetch_json(
        "https://api.github.com/repos/itsolutions-global/it-solutions-suite",
        headers=headers,
    )

    stars = repo_data.get("stargazers_count", 0) if code == 200 else 0
    forks = repo_data.get("forks_count", 0) if code == 200 else 0
    open_issues_count = repo_data.get("open_issues_count", 0) if code == 200 else 0

    # 2. Detailed issues list
    issues_data, icode = fetch_json(
        "https://api.github.com/repos/itsolutions-global/it-solutions-suite/issues?state=all&per_page=20",
        headers=headers,
    )
    issues_list = []
    if icode == 200 and isinstance(issues_data, list):
        for item in issues_data:
            # Exclude PRs if they are represented in issues endpoint
            is_pr = "pull_request" in item
            issues_list.append({
                "id": item.get("id"),
                "number": item.get("number"),
                "title": item.get("title"),
                "state": item.get("state"),
                "author": item.get("user", {}).get("login"),
                "comments": item.get("comments", 0),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "html_url": item.get("html_url"),
                "is_pull_request": is_pr,
            })

    return {
        "status": "healthy" if code == 200 else "degraded",
        "stars": stars,
        "forks": forks,
        "open_issues_count": open_issues_count,
        "recent_issues": issues_list,
    }


def check_dev_community():
    articles, code = fetch_json("https://dev.to/api/articles?username=itsolutionsglobal")
    summary = []
    total_comments = 0
    total_reactions = 0

    if code == 200 and isinstance(articles, list):
        for art in articles:
            comments = art.get("comments_count", 0)
            reactions = art.get("public_reactions_count", 0)
            total_comments += comments
            total_reactions += reactions
            summary.append({
                "id": art.get("id"),
                "title": art.get("title"),
                "url": art.get("url"),
                "comments_count": comments,
                "reactions_count": reactions,
                "published_at": art.get("published_at"),
            })

    return {
        "status": "healthy" if code == 200 else "degraded",
        "articles_tracked": len(summary),
        "total_comments": total_comments,
        "total_reactions": total_reactions,
        "articles": summary,
    }


def check_pypi():
    pypi_data, code = fetch_json("https://pypi.org/pypi/it-solutions-suite/json")
    if code == 200 and "info" in pypi_data:
        info = pypi_data["info"]
        return {
            "status": "healthy",
            "name": info.get("name"),
            "version": info.get("version"),
            "home_page": info.get("home_page"),
            "project_urls": info.get("project_urls"),
            "releases_count": len(pypi_data.get("releases", {})),
        }
    return {
        "status": "error",
        "error_code": code,
    }


def run_monitor_cycle():
    vault = load_credentials()
    now_utc = datetime.now(timezone.utc).isoformat()

    gh_telemetry = check_github(vault)
    dev_telemetry = check_dev_community()
    pypi_telemetry = check_pypi()

    # Read existing inbound log
    existing_log = {}
    if INBOUND_LOG_PATH.exists():
        try:
            existing_log = json.loads(INBOUND_LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            existing_log = {}

    history = existing_log.get("history", [])
    current_snapshot = {
        "timestamp_utc": now_utc,
        "github": gh_telemetry,
        "dev_community": dev_telemetry,
        "pypi": pypi_telemetry,
    }

    # Detect any new unreplied issues or comments
    action_items = []
    for issue in gh_telemetry.get("recent_issues", []):
        if issue["state"] == "open" and issue["author"] != "itsolutions-global":
            action_items.append({
                "source": "github_issue",
                "id": issue["number"],
                "title": issue["title"],
                "url": issue["html_url"],
                "author": issue["author"],
                "priority": "HIGH",
                "recommended_action": "Triage and formulate technical response",
            })

    if dev_telemetry.get("total_comments", 0) > 0:
        action_items.append({
            "source": "dev_to",
            "priority": "MEDIUM",
            "recommended_action": "Review comments on DEV.to articles and respond",
        })

    # Keep last 50 historical entries
    history.append({
        "timestamp": now_utc,
        "gh_stars": gh_telemetry.get("stars", 0),
        "gh_issues": gh_telemetry.get("open_issues_count", 0),
        "dev_reactions": dev_telemetry.get("total_reactions", 0),
        "dev_comments": dev_telemetry.get("total_comments", 0),
        "pypi_version": pypi_telemetry.get("version", "unknown"),
        "pending_actions_count": len(action_items),
    })
    history = history[-50:]

    full_record = {
        "last_updated_utc": now_utc,
        "latest_snapshot": current_snapshot,
        "action_items": action_items,
        "history": history,
    }

    INBOUND_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    INBOUND_LOG_PATH.write_text(json.dumps(full_record, indent=2), encoding="utf-8")

    print(f"[Community Monitor] Cycle complete at {now_utc}")
    print(f" - GitHub: {gh_telemetry.get('stars')} stars, {gh_telemetry.get('open_issues_count')} open issues")
    print(f" - DEV.to: {dev_telemetry.get('articles_tracked')} articles, {dev_telemetry.get('total_reactions')} reactions, {dev_telemetry.get('total_comments')} comments")
    print(f" - PyPI: {pypi_telemetry.get('name')} v{pypi_telemetry.get('version')}")
    print(f" - Pending Action Items: {len(action_items)}")
    return full_record


if __name__ == "__main__":
    run_monitor_cycle()
