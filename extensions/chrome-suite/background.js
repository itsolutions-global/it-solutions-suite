/**
 * IT Solutions Suite - Manifest V3 Background Service Worker
 * 100% Local-First • Zero Cloud Telemetry • Context Menus & SidePanel Ingress
 */

// Register context menus on installation
chrome.runtime.onInstalled.addListener(() => {
  // Clear any pre-existing menus
  chrome.contextMenus.removeAll(() => {
    // Parent Menu
    chrome.contextMenus.create({
      id: "its_root",
      title: "⚡ IT Solutions Suite",
      contexts: ["selection", "page"]
    });

    // 1. ClauseGuard
    chrome.contextMenus.create({
      id: "clg_scan",
      parentId: "its_root",
      title: "⚖️ Scan Contract with ClauseGuard",
      contexts: ["selection"]
    });

    // 2. DocuPulse
    chrome.contextMenus.create({
      id: "doc_extract",
      parentId: "its_root",
      title: "📄 Extract Invoice with DocuPulse",
      contexts: ["selection"]
    });

    // 3. EchoStream
    chrome.contextMenus.create({
      id: "echo_notes",
      parentId: "its_root",
      title: "🎙️ Draft Meeting Follow-Up with EchoStream",
      contexts: ["selection"]
    });

    // 4. NexusShield
    chrome.contextMenus.create({
      id: "nxs_scan",
      parentId: "its_root",
      title: "🛡️ Scan Code / Secrets with NexusShield",
      contexts: ["selection"]
    });

    // 5. CorePulse
    chrome.contextMenus.create({
      id: "cp_task",
      parentId: "its_root",
      title: "⚡ Quick Save Task to CorePulse",
      contexts: ["selection"]
    });
  });

  // Initialize default local storage if needed
  chrome.storage.local.get(["corepulse_snippets", "corepulse_tasks"], (res) => {
    const updates = {};
    if (!res.corepulse_snippets) {
      updates.corepulse_snippets = [
        {
          trigger: ";;standup",
          title: "Daily Standup Brief",
          content: "Yesterday: [Completed item]\nToday: [Focus item]\nBlockers: [None]"
        },
        {
          trigger: ";;followup",
          title: "Executive Meeting Follow-up",
          content: "Hi [Name],\n\nThank you for our conversation today. Summarizing our key takeaways and deliverables below:\n\n1. [Deliverable 1]\n2. [Deliverable 2]\n\nBest regards,\n[My Name]"
        },
        {
          trigger: ";;nda",
          title: "Standard NDA Safe Harbor",
          content: "Attached is our standard bilateral Non-Disclosure Agreement with strict mutual confidentiality and reciprocal IP retention terms."
        },
        {
          trigger: ";;invoice",
          title: "Professional Net-30 Invoice",
          content: "Please find attached Invoice #[Number] for services rendered. Total due: $[Amount], payable within Net-30 days."
        }
      ];
    }
    if (!res.corepulse_tasks) {
      updates.corepulse_tasks = [
        {
          id: "task-" + Date.now(),
          title: "Welcome to IT Solutions Suite extension",
          priority: "high",
          tags: ["welcome", "local"],
          duration: "15m",
          completed: false,
          created_at: new Date().toISOString()
        }
      ];
    }
    if (Object.keys(updates).length > 0) {
      chrome.storage.local.set(updates);
    }
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  const selection = info.selectionText || "";
  let targetTool = "clauseguard";

  if (info.menuItemId === "clg_scan") {
    targetTool = "clauseguard";
  } else if (info.menuItemId === "doc_extract") {
    targetTool = "docupulse";
  } else if (info.menuItemId === "echo_notes") {
    targetTool = "echostream";
  } else if (info.menuItemId === "nxs_scan") {
    targetTool = "nexusshield";
  } else if (info.menuItemId === "cp_task") {
    targetTool = "corepulse";

    // Direct Quick-Capture for CorePulse tasks
    if (selection.trim()) {
      quickCaptureTask(selection.trim());
    }
  }

  // Persist the selection and tool so popup/sidepanel loads it immediately
  chrome.storage.local.set({
    pendingSelection: selection,
    targetTool: targetTool,
    autoRun: true,
    timestamp: Date.now()
  }, () => {
    // Open side panel if tab ID available in Chrome MV3
    if (tab && tab.id && chrome.sidePanel && chrome.sidePanel.open) {
      chrome.sidePanel.open({ tabId: tab.id }).catch(() => {
        // Fallback: If sidepanel open fails (e.g. restricted window), user opens action popup
      });
    }
  });
});

// Helper: parse and insert CorePulse task directly into local storage
function quickCaptureTask(rawText) {
  let priority = "medium";
  if (rawText.includes("!p1") || /!(?:critical|urgent)/i.test(rawText)) priority = "critical";
  else if (rawText.includes("!p2") || /!(?:high)/i.test(rawText)) priority = "high";
  else if (rawText.includes("!p3") || /!(?:low)/i.test(rawText)) priority = "low";

  const tags = [];
  const tagMatches = rawText.match(/#([a-zA-Z0-9_\-]+)/g);
  if (tagMatches) {
    tagMatches.forEach(t => tags.push(t.replace("#", "").toLowerCase()));
  }

  let duration = "30m";
  const durMatch = rawText.match(/~(\d+[mh])/i);
  if (durMatch) duration = durMatch[1].toLowerCase();

  const cleanTitle = rawText
    .replace(/!p[1-3]/gi, "")
    .replace(/!(?:critical|high|medium|low|urgent)/gi, "")
    .replace(/#[a-zA-Z0-9_\-]+/g, "")
    .replace(/~\d+[mh]/gi, "")
    .trim();

  const newTask = {
    id: "task-" + Date.now(),
    title: cleanTitle || rawText,
    priority: priority,
    tags: tags.length > 0 ? tags : ["web-capture"],
    duration: duration,
    completed: false,
    created_at: new Date().toISOString()
  };

  chrome.storage.local.get(["corepulse_tasks"], (res) => {
    const list = res.corepulse_tasks || [];
    list.unshift(newTask);
    chrome.storage.local.set({ corepulse_tasks: list });
  });

  // Attempt non-blocking sync with local desktop CorePulse server if active
  fetch("http://127.0.0.1:8080/api/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: newTask.title,
      priority: newTask.priority,
      tags: newTask.tags,
      estimated_minutes: parseInt(duration.replace(/[mh]/, "")) || 30
    })
  }).catch(() => {
    // Desktop CorePulse offline - safely stored in chrome.storage.local
  });
}
