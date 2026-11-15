"""Autonomous Zoho Mail Inbox Monitor
IT Solutions Global Corporation

Connects via CDP (NexusBridge) to the active Chrome profile running Zoho Mail.
Monitors the unread inbox for:
- Prospective customer inquiries & enterprise tier leads
- Platform moderation and review updates (Product Hunt, AlternativeTo, Indie Hackers)
- Bug reports and feedback from the portal's mailto:isgc@sedain.com
Logs all unread messages and triage action items into INBOUND_LOG.json.
"""

import asyncio
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import websockets

WORKSPACE_ROOT = Path(r"e:\It solution")
INBOUND_LOG_PATH = WORKSPACE_ROOT / "company" / "growth" / "INBOUND_LOG.json"
CDP_BASE_URL = "http://localhost:9222"


def get_zoho_tab():
    try:
        tabs = json.loads(urllib.request.urlopen(f"{CDP_BASE_URL}/json", timeout=5).read().decode())
    except Exception as e:
        return None, f"Could not reach Chrome CDP on {CDP_BASE_URL}: {e}"

    zoho_tabs = [t for t in tabs if "mail.zoho" in t.get("url", "").lower()]
    if zoho_tabs:
        return zoho_tabs[0], None
    return None, "No active Zoho Mail tab found in Chrome."


async def scan_unread_zoho():
    tab, err = get_zoho_tab()
    if err or not tab:
        return {"status": "offline", "error": err}

    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        return {"status": "error", "error": "No webSocketDebuggerUrl available"}

    async with websockets.connect(ws_url) as ws:
        # Script to extract unread items from Zoho Mail DOM
        expr = """
        (() => {
            const items = [];
            // Zoho mail list items
            const rows = document.querySelectorAll('tr, .zmListRow, .zmRow');
            rows.forEach(r => {
                const text = (r.innerText || '').trim();
                if (text && text.length > 5) {
                    const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                    if (lines.length >= 2) {
                        items.push({
                            raw: text.replace(/\\s+/g, ' ').substring(0, 200),
                            preview: lines.slice(0, 3).join(' | ')
                        });
                    }
                }
            });

            // Extract total unread count from title or badge
            let unreadCount = 0;
            const titleMatch = document.title.match(/\\((\\d+)\\s+unread\\)/i);
            if (titleMatch) {
                unreadCount = parseInt(titleMatch[1], 10);
            }

            return {
                title: document.title,
                url: window.location.href,
                unreadCount: unreadCount,
                itemsFound: items.length,
                samples: items.slice(0, 15)
            };
        })()
        """
        req = {"id": 1, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True}}
        await ws.send(json.dumps(req))
        resp = await ws.recv()
        data = json.loads(resp).get("result", {}).get("result", {}).get("value", {})
        return {
            "status": "active",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "telemetry": data
        }


def record_zoho_scan(result):
    if not INBOUND_LOG_PATH.exists():
        existing = {}
    else:
        try:
            existing = json.loads(INBOUND_LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    existing["zoho_inbox"] = result
    INBOUND_LOG_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    print(f"[Zoho Monitor] Scan complete at {datetime.now(timezone.utc).isoformat()}")
    print(f"Status: {result.get('status')} | Unread Count: {result.get('telemetry', {}).get('unreadCount', 0)}")


if __name__ == "__main__":
    scan_res = asyncio.run(scan_unread_zoho())
    record_zoho_scan(scan_res)
