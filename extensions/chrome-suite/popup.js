/**
 * IT Solutions Suite - Chrome Extension Studio Logic
 * 100% Client-Side Local-First • Zero Cloud Dependency
 */

(function () {
  'use strict';

  const PORTAL_URL = "https://it-solutions-global.vercel.app";
  let activeTabName = "clauseguard";

  let lastClgOutput = "";
  let lastDocCsv = "";
  let lastDocInv = "INV-001";
  let lastEchoOutput = "";
  let lastNxsOutput = "";

  // Samples for 1-click demo loading
  const SAMPLES = {
    clauseguard:
      "MASTER SERVICES AGREEMENT\n" +
      "1. Liability: Consultant shall have unlimited liability for any and all damages arising out of this Agreement.\n" +
      "2. Intellectual Property: Consultant assigns all right, title, and interest in and to all prior inventions and including pre-existing intellectual property shall become the sole property of Client.\n" +
      "3. Term & Renewal: This Agreement shall automatically renew for successive 24-month periods unless written notice is provided 90 days prior.\n" +
      "4. Payment Terms: All undisputed invoices are payable Net 90 days after Client receipt.\n" +
      "5. Restrictive Covenants: Consultant shall not directly or indirectly engage in any competing business during the term.\n" +
      "6. Termination: Client may at its sole discretion terminate without compensation for work in progress.",

    docupulse:
      "Vendor: CloudScale Infrastructure Inc.\n" +
      "Invoice Number: INV-2026-8841\n" +
      "Date: 2026-11-10\n" +
      "Due Date: 2026-12-10\n\n" +
      "1. Dedicated Kubernetes Cluster Node (2x @ $400.00) $800.00\n" +
      "2. Managed Postgres High-Availability Storage $350.00\n" +
      "3. Zero-Trust DDoS Edge Protection $150.00\n\n" +
      "Subtotal: $1,300.00\n" +
      "Tax (8%): $104.00\n" +
      "Total Due: $1,404.00",

    echostream:
      "# Scratchpad Notes:\n" +
      "- Client wants SOC2 compliance report before November 25\n" +
      "- Todo: Send updated project roadmap proposal to David by tomorrow\n\n" +
      "# Meeting Transcript:\n" +
      "[David CTO] We agreed to migrate the staging cluster to zero-trust mTLS.\n" +
      "[Sarah] I will deploy the new mTLS certificates before Wednesday afternoon.\n" +
      "[David CTO] Question: can we clarify the multi-region failover SLA for Q1?",

    nexusshield:
      "# Production Environment Config\n" +
      "PORT=8080\n" +
      "AWS_ACCESS_KEY_ID=\"AKIAIOSFODNN7EXAMPLE9\"\n" +
      "OPENAI_API_KEY=\"sk-proj-98723418726354128937123987123987abcd\"\n" +
      "DATABASE_URL=\"postgres://admin:SuperSecretPass99@db.internal:5432/prod\"\n" +
      "DEBUG_MODE=false"
  };

  // =========================================================================
  // 1. DOM Initialization & Tab Routing
  // =========================================================================

  document.addEventListener("DOMContentLoaded", () => {
    initTabs();
    initClauseGuard();
    initDocuPulse();
    initEchoStream();
    initNexusShield();
    initCorePulse();
    checkDesktopConnection();

    // Check if background script passed highlighted text via context menu
    chrome.storage.local.get(["pendingSelection", "targetTool", "autoRun"], (data) => {
      if (data && data.pendingSelection && data.targetTool) {
        switchTab(data.targetTool);
        const inputId = {
          clauseguard: "clgInput",
          docupulse: "docInput",
          echostream: "echoInput",
          nexusshield: "nxsInput",
          corepulse: "cpTaskInput"
        }[data.targetTool];

        const targetEl = document.getElementById(inputId);
        if (targetEl) {
          targetEl.value = data.pendingSelection;
          if (data.autoRun) {
            if (data.targetTool === "clauseguard") runClauseGuard();
            else if (data.targetTool === "docupulse") runDocuPulse();
            else if (data.targetTool === "echostream") runEchoStream();
            else if (data.targetTool === "nexusshield") runNexusShield();
          }
        }
        // Clear pending selection flag
        chrome.storage.local.remove(["pendingSelection", "targetTool", "autoRun"]);
      }
    });
  });

  function initTabs() {
    const tabButtons = document.querySelectorAll(".tab-btn");
    tabButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        const tabName = btn.getAttribute("data-tab");
        switchTab(tabName);
      });
    });
  }

  function switchTab(tabName) {
    activeTabName = tabName;
    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabName);
    });
    document.querySelectorAll(".tab-panel").forEach(panel => {
      panel.classList.toggle("active", panel.id === `panel-${tabName}`);
    });
  }

  // =========================================================================
  // 2. ClauseGuard Contract Scanner Engine
  // =========================================================================

  function initClauseGuard() {
    const btnRun = document.getElementById("btnClgRun");
    const btnSample = document.getElementById("btnClgSample");
    const btnClear = document.getElementById("btnClgClear");
    const btnCopy = document.getElementById("btnClgCopy");
    const btnDownload = document.getElementById("btnClgDownload");

    if (btnRun) btnRun.addEventListener("click", runClauseGuard);
    if (btnSample) btnSample.addEventListener("click", () => {
      document.getElementById("clgInput").value = SAMPLES.clauseguard;
      runClauseGuard();
    });
    if (btnClear) btnClear.addEventListener("click", () => {
      document.getElementById("clgInput").value = "";
      document.getElementById("clgOutput").textContent = "Paste contract text above and click Scan...";
      setBadge("clgBadge", "READY", "green");
    });
    if (btnCopy) btnCopy.addEventListener("click", () => copyToClipboard(lastClgOutput, btnCopy));
    if (btnDownload) btnDownload.addEventListener("click", () => downloadFile("clauseguard-redline-audit.txt", lastClgOutput));

    // Pre-canned redlines 1-click copy buttons
    setupCopyButton("btnCopyRedline1", "Neither party's aggregate liability under this Agreement shall exceed the total fees paid in the 12 months preceding the claim, excluding indirect or consequential damages.");
    setupCopyButton("btnCopyRedline2", "Provider retains all right, title, and interest in and to pre-existing intellectual property and reusable tools; Client receives ownership of custom Deliverables upon full payment.");
    setupCopyButton("btnCopyRedline3", "All undisputed invoices shall be due and payable within thirty (30) days (Net-30) of invoice transmission date.");
  }

  function runClauseGuard() {
    const text = (document.getElementById("clgInput").value || "").trim();
    if (!text) return;

    const rules = [
      {
        id: "CLG-UNCAPPED-LIABILITY",
        title: "Uncapped / Unlimited Financial Liability",
        severity: "CRITICAL",
        penalty: 30,
        regex: /unlimited\s+liability|liable\s+for\s+all\s+damages\s+without\s+limitation|no\s+limit\s+on\s+liability/i,
        risk: "Exposes you to unlimited financial damages far exceeding the contract value.",
        redline: "PROPOSED REDLINE: 'Neither party's aggregate liability under this Agreement shall exceed the total fees paid in the 12 months preceding the claim, excluding indirect or consequential damages.'"
      },
      {
        id: "CLG-BROAD-IP-GRAB",
        title: "Overbroad Pre-Existing IP Assignment Grab",
        severity: "CRITICAL",
        penalty: 28,
        regex: /prior\s+inventions|pre-existing\s+intellectual\s+property\s+shall\s+become\s+the\s+sole\s+property|background\s+technology\s+shall\s+vest/i,
        risk: "Transfers ownership of your pre-existing code, tools, and reusable templates to the client.",
        redline: "PROPOSED REDLINE: 'Provider retains all right, title, and interest in and to pre-existing intellectual property and reusable tools; Client receives ownership of custom Deliverables upon full payment.'"
      },
      {
        id: "CLG-AUTO-RENEWAL-TRAP",
        title: "Evergreen Auto-Renewal Trap",
        severity: "HIGH",
        penalty: 18,
        regex: /automatically\s+renew(?:s)?\s+for\s+successive|automatically\s+renew\s+unless\s+written\s+notice/i,
        risk: "Locks you into multi-month/year renewals unless cancelled 60–90 days early.",
        redline: "PROPOSED REDLINE: 'This Agreement shall renew only upon mutual written agreement, or either party may opt out with 15 days prior notice.'"
      },
      {
        id: "CLG-NON-COMPETE",
        title: "Restrictive Industry Non-Compete Ban",
        severity: "HIGH",
        penalty: 20,
        regex: /not\s+directly\s+or\s+indirectly\s+engage\s+in\s+any\s+competing\s+business|prohibited\s+from\s+providing\s+similar\s+services/i,
        risk: "Blocks you from working with other clients in your own profession.",
        redline: "PROPOSED REDLINE: Strike non-compete clause entirely and rely strictly on mutual Non-Disclosure obligations."
      },
      {
        id: "CLG-DELAYED-PAYMENT",
        title: "Extended Payment Delay (Net-60 / Net-90 / Pay-When-Paid)",
        severity: "MEDIUM",
        penalty: 12,
        regex: /net\s*(?:60|90|120)|payable\s+within\s+(?:sixty|ninety|60|90)\s+days|pay-when-paid/i,
        risk: "Forces you to wait 60–90+ days to get paid for completed work.",
        redline: "PROPOSED REDLINE: 'All undisputed invoices shall be due and payable within thirty (30) days (Net-30) of invoice transmission date.'"
      },
      {
        id: "CLG-UNILATERAL-TERMINATION",
        title: "Unilateral Termination Without Payment for Work Done",
        severity: "HIGH",
        penalty: 16,
        regex: /terminate\s+without\s+compensation|without\s+liability\s+for\s+work\s+in\s+progress/i,
        risk: "Lets the counterparty cancel mid-project without paying for hours already worked.",
        redline: "PROPOSED REDLINE: 'Either party may terminate upon 30 days written notice; Client shall pay Provider for all services performed through the effective termination date.'"
      }
    ];

    const lines = text.split(/\r?\n/);
    const findings = [];
    let penalty = 0;

    lines.forEach((line, idx) => {
      rules.forEach(r => {
        if (r.regex.test(line)) {
          penalty += r.penalty;
          findings.push({
            line: idx + 1,
            id: r.id,
            title: r.title,
            severity: r.severity,
            excerpt: line.trim(),
            risk: r.risk,
            redline: r.redline
          });
        }
      });
    });

    const score = Math.max(0, 100 - penalty);
    const grade = score >= 90 ? "A+" : (score >= 75 ? "B" : (score >= 50 ? "C" : "F"));
    const verdict = score >= 90 ? "SAFE TO SIGN" : (score >= 50 ? "NEGOTIATE BEFORE SIGNING" : "DANGEROUS — DO NOT SIGN WITHOUT REDLINING");

    let out = `====================================================================\n`;
    out += `  CLAUSEGUARD CONTRACT RISK AUDIT | Score: ${grade} (${score}/100)\n`;
    out += `  Verdict: ${verdict} | Risks Found: ${findings.length}\n`;
    out += `====================================================================\n\n`;

    if (findings.length === 0) {
      out += `✔ Clean Contract! Zero predatory or high-risk clauses detected.\n`;
      setBadge("clgBadge", `SAFE • ${grade} (${score}/100)`, "green");
    } else {
      findings.forEach((f, i) => {
        out += `${i + 1}. [${f.severity}] ${f.title} (Line ${f.line})\n`;
        out += `   • Why It Hurts: ${f.risk}\n`;
        out += `   • ${f.redline}\n\n`;
      });
      setBadge("clgBadge", `${findings.length} RISKS • ${grade}`, score >= 75 ? "amber" : "red");
    }
    out += `--------------------------------------------------------------------\n`;
    out += `⚡ Audited 100% locally via ClauseGuard (${PORTAL_URL})`;

    lastClgOutput = out;
    document.getElementById("clgOutput").textContent = out;
  }

  // =========================================================================
  // 3. DocuPulse Invoice Extractor Engine
  // =========================================================================

  function initDocuPulse() {
    const btnRun = document.getElementById("btnDocRun");
    const btnSample = document.getElementById("btnDocSample");
    const btnClear = document.getElementById("btnDocClear");
    const btnCopy = document.getElementById("btnDocCopy");
    const btnDownload = document.getElementById("btnDocDownloadCsv");

    if (btnRun) btnRun.addEventListener("click", runDocuPulse);
    if (btnSample) btnSample.addEventListener("click", () => {
      document.getElementById("docInput").value = SAMPLES.docupulse;
      runDocuPulse();
    });
    if (btnClear) btnClear.addEventListener("click", () => {
      document.getElementById("docInput").value = "";
      document.getElementById("docOutput").textContent = "Extracted invoice details will appear here...";
      document.getElementById("docVendor").textContent = "—";
      document.getElementById("docInvNum").textContent = "—";
      document.getElementById("docDate").textContent = "—";
      document.getElementById("docTotal").textContent = "$0.00";
      setBadge("docBadge", "READY", "green");
    });
    if (btnCopy) btnCopy.addEventListener("click", () => copyToClipboard(document.getElementById("docOutput").textContent, btnCopy));
    if (btnDownload) btnDownload.addEventListener("click", () => downloadFile(`invoice-ledger-${lastDocInv}.csv`, lastDocCsv));
  }

  function runDocuPulse() {
    const text = (document.getElementById("docInput").value || "").trim();
    if (!text) return;

    const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    let vendor = "Unknown Vendor";
    let invNum = "INV-AUTO-001";
    let issueDate = new Date().toISOString().slice(0, 10);
    let dueDate = "Upon Receipt";
    let subtotal = null;
    let tax = 0;
    let total = null;
    const items = [];

    lines.forEach(line => {
      const vMatch = line.match(/^(?:vendor|from|merchant|billed by)\s*[:\-]\s*(.+)$/i);
      if (vMatch) vendor = vMatch[1].trim();
      const iMatch = line.match(/(?:invoice\s*(?:no|number|#)?|receipt\s*#?)\s*[:\-]?\s*([A-Z0-9\-_]{3,25})/i);
      if (iMatch && !/^(number|date|due)$/i.test(iMatch[1])) invNum = iMatch[1];
      const dMatch = line.match(/^(?:date|invoice date)\s*[:\-]\s*(.+)$/i);
      if (dMatch) issueDate = dMatch[1].trim();
      const dueMatch = line.match(/^(?:due date|payment due)\s*[:\-]\s*(.+)$/i);
      if (dueMatch) dueDate = dueMatch[1].trim();

      const numMatches = line.match(/([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})|[0-9]+\.[0-9]{2})/g);
      const lastAmt = numMatches ? parseFloat(numMatches[numMatches.length - 1].replace(/,/g, '')) : null;

      if (/^sub[\s\-]?total/i.test(line) && lastAmt !== null) {
        subtotal = lastAmt;
      } else if (/^(?:tax|vat|gst)/i.test(line) && lastAmt !== null) {
        tax = lastAmt;
      } else if (/^(?:total|total due|amount due|grand total)/i.test(line) && lastAmt !== null) {
        total = lastAmt;
      } else if (lastAmt !== null && !/invoice|date|due/i.test(line)) {
        const desc = line.replace(/[\$€£₹]?\s*[0-9,]+\.[0-9]{2}\s*$/, '').replace(/^[\d\.\-\*\s]+/, '').trim();
        if (desc.length > 2) {
          items.push({ description: desc, amount: lastAmt });
        }
      }
    });

    const itemsSum = items.reduce((acc, it) => acc + it.amount, 0);
    if (subtotal === null) subtotal = itemsSum > 0 ? itemsSum : (total !== null ? total - tax : 0);
    if (total === null) total = subtotal + tax;

    const expectedTotal = Math.round((subtotal + tax) * 100) / 100;
    const mathOk = Math.abs(expectedTotal - total) < 0.05;

    // Update Summary Grid
    document.getElementById("docVendor").textContent = vendor;
    document.getElementById("docInvNum").textContent = invNum;
    document.getElementById("docDate").textContent = issueDate;
    document.getElementById("docTotal").textContent = `$${total.toFixed(2)}`;

    let out = `====================================================================\n`;
    out += `  DOCUPULSE INVOICE EXTRACTION & MATH AUDIT\n`;
    out += `====================================================================\n`;
    out += `  Vendor:         ${vendor}\n`;
    out += `  Invoice #:      ${invNum}\n`;
    out += `  Issue Date:     ${issueDate}  |  Due Date: ${dueDate}\n`;
    out += `--------------------------------------------------------------------\n`;
    out += `  Extracted Line Items (${items.length}):\n`;
    items.forEach((it, idx) => {
      out += `    ${idx + 1}. ${it.description} — $${it.amount.toFixed(2)}\n`;
    });
    out += `--------------------------------------------------------------------\n`;
    out += `  Subtotal:       $${subtotal.toFixed(2)}\n`;
    out += `  Tax / VAT:      $${tax.toFixed(2)}\n`;
    out += `  TOTAL AMOUNT:   $${total.toFixed(2)}\n`;
    out += `  Math Audit:     ${mathOk ? '✔ VERIFIED (Subtotal + Tax == Total)' : '⚠ DISCREPANCY (Expected $' + expectedTotal.toFixed(2) + ')'}\n`;
    out += `====================================================================\n`;

    let csv = "Vendor,Invoice Number,Issue Date,Due Date,Subtotal,Tax,Total,Math Verified\n";
    csv += `"${vendor.replace(/"/g, '""')}","${invNum}","${issueDate}","${dueDate}",${subtotal.toFixed(2)},${tax.toFixed(2)},${total.toFixed(2)},${mathOk ? "YES" : "FLAGGED"}\n`;

    lastDocCsv = csv;
    lastDocInv = invNum;
    document.getElementById("docOutput").textContent = out;
    setBadge("docBadge", mathOk ? `VERIFIED • $${total.toFixed(2)}` : `DISCREPANCY • $${total.toFixed(2)}`, mathOk ? "green" : "amber");
  }

  // =========================================================================
  // 4. EchoStream Meeting Follow-Up Engine
  // =========================================================================

  function initEchoStream() {
    const btnRun = document.getElementById("btnEchoRun");
    const btnSample = document.getElementById("btnEchoSample");
    const btnClear = document.getElementById("btnEchoClear");
    const btnCopy = document.getElementById("btnEchoCopy");
    const btnDownload = document.getElementById("btnEchoDownload");

    if (btnRun) btnRun.addEventListener("click", runEchoStream);
    if (btnSample) btnSample.addEventListener("click", () => {
      document.getElementById("echoInput").value = SAMPLES.echostream;
      runEchoStream();
    });
    if (btnClear) btnClear.addEventListener("click", () => {
      document.getElementById("echoInput").value = "";
      document.getElementById("echoOutput").textContent = "Follow-up email draft will appear here...";
      setBadge("echoBadge", "READY", "green");
    });
    if (btnCopy) btnCopy.addEventListener("click", () => copyToClipboard(lastEchoOutput, btnCopy));
    if (btnDownload) btnDownload.addEventListener("click", () => downloadFile("meeting-followup.md", lastEchoOutput));
  }

  function runEchoStream() {
    const text = (document.getElementById("echoInput").value || "").trim();
    if (!text) return;

    // Redact accidental secrets first
    const redacted = text.replace(/\b(sk-(?:proj-)?[A-Za-z0-9_\-]{20,}|AKIA[0-9A-Z]{16})\b/g, "[REDACTED_CREDENTIAL]");
    const lines = redacted.split(/\r?\n/).map(l => l.trim()).filter(Boolean);

    const notes = [];
    const decisions = [];
    const actions = [];
    const questions = [];

    lines.forEach(line => {
      if (line.startsWith("#")) return;
      if (line.startsWith("-") || line.startsWith("*")) {
        const cleanNote = line.replace(/^[\-\*\s]+/, "");
        notes.push(cleanNote);
        if (/\b(todo|send|deploy|must|need to|follow up)\b/i.test(cleanNote)) {
          actions.push({ owner: "Me", task: cleanNote.replace(/^todo:\s*/i, "") });
        }
        return;
      }
      const spkMatch = line.match(/^\[([^\]]+)\]\s*(.+)$/);
      const speaker = spkMatch ? spkMatch[1] : "Team";
      const utt = spkMatch ? spkMatch[2] : line;

      if (/\b(agreed to|decided to|approved)\b/i.test(utt)) {
        decisions.push(`${utt} (${speaker})`);
      }
      if (/\b(i will|i'll|we need to|must|deploy|send)\b/i.test(utt)) {
        actions.push({ owner: speaker, task: utt });
      }
      if (utt.endsWith("?") || /\bquestion:/i.test(utt)) {
        questions.push(`${utt} (${speaker})`);
      }
    });

    const today = new Date().toISOString().slice(0, 10);
    let email = `Subject: Meeting Recap, Decisions & Next Steps (${today})\n\n`;
    email += `Hi Team,\n\nThank you for the productive session today. Here is our structured summary and action plan:\n\n`;

    if (notes.length > 0) {
      email += `KEY HIGHLIGHTS:\n`;
      notes.forEach(n => { email += `• ${n}\n`; });
      email += `\n`;
    }
    if (decisions.length > 0) {
      email += `DECISIONS APPROVED:\n`;
      decisions.forEach(d => { email += `✔ ${d}\n`; });
      email += `\n`;
    }
    if (actions.length > 0) {
      email += `ACTION ITEMS & OWNERS:\n`;
      actions.forEach(a => { email += `[ ] [${a.owner}] ${a.task}\n`; });
      email += `\n`;
    }
    if (questions.length > 0) {
      email += `OPEN QUESTIONS:\n`;
      questions.forEach(q => { email += `? ${q}\n`; });
      email += `\n`;
    }
    email += `Best regards,\n`;
    email += `---\n⚡ Drafted in 1 click via EchoStream Local Co-Pilot (${PORTAL_URL})`;

    lastEchoOutput = email;
    document.getElementById("echoOutput").textContent = email;
    setBadge("echoBadge", `${actions.length} ACTIONS • ${decisions.length} DECISIONS`, "green");
  }

  // =========================================================================
  // 5. NexusShield Secret Scanner Engine
  // =========================================================================

  function initNexusShield() {
    const btnRun = document.getElementById("btnNxsRun");
    const btnSample = document.getElementById("btnNxsSample");
    const btnClear = document.getElementById("btnNxsClear");
    const btnCopy = document.getElementById("btnNxsCopy");
    const btnDownload = document.getElementById("btnNxsDownload");

    if (btnRun) btnRun.addEventListener("click", runNexusShield);
    if (btnSample) btnSample.addEventListener("click", () => {
      document.getElementById("nxsInput").value = SAMPLES.nexusshield;
      runNexusShield();
    });
    if (btnClear) btnClear.addEventListener("click", () => {
      document.getElementById("nxsInput").value = "";
      document.getElementById("nxsOutput").textContent = "Security scan results will appear here...";
      setBadge("nxsBadge", "CLEAN", "green");
    });
    if (btnCopy) btnCopy.addEventListener("click", () => copyToClipboard(lastNxsOutput, btnCopy));
    if (btnDownload) btnDownload.addEventListener("click", () => downloadFile("nexusshield-audit.json", lastNxsOutput));
  }

  function runNexusShield() {
    const text = (document.getElementById("nxsInput").value || "").trim();
    if (!text) return;

    const rules = [
      { id: "SEC-AWS-KEY", name: "AWS Access Key ID", sev: "CRITICAL", regex: /\b(AKIA[0-9A-Z]{16})\b/ },
      { id: "SEC-OPENAI-KEY", name: "OpenAI API Key", sev: "CRITICAL", regex: /\b(sk-(?:proj-)?[A-Za-z0-9_\-]{24,})\b/ },
      { id: "SEC-STRIPE-KEY", name: "Stripe Live Secret Key", sev: "CRITICAL", regex: /\b((?:sk|rk)_live_[0-9a-zA-Z]{20,})\b/ },
      { id: "SEC-GITHUB-PAT", name: "GitHub Personal Access Token", sev: "HIGH", regex: /\b(ghp_[0-9a-zA-Z]{30,})\b/ },
      { id: "SEC-DB-URI", name: "Database Connection URI with Password", sev: "CRITICAL", regex: /\b((?:postgres|postgresql|mysql|mongodb|redis):\/\/[^:\s]+:[^@\s]+@[^\s"']+)/ }
    ];

    const lines = text.split(/\r?\n/);
    const findings = [];

    lines.forEach((line, idx) => {
      rules.forEach(r => {
        const m = line.match(r.regex);
        if (m) {
          const raw = m[1];
          const masked = raw.length > 10 ? raw.slice(0, 6) + "..." + raw.slice(-4) : "***REDACTED***";
          findings.push({ line: idx + 1, id: r.id, name: r.name, severity: r.sev, preview: masked });
        }
      });
    });

    const score = Math.max(0, 100 - findings.length * 25);
    const grade = score >= 90 ? "A+" : (score >= 70 ? "B" : "F");

    let out = `====================================================================\n`;
    out += `  NEXUSSHIELD SAST & SECRET AUDIT | Score: ${grade} (${score}/100)\n`;
    out += `====================================================================\n\n`;
    if (findings.length === 0) {
      out += `✔ Clean Bill of Health! Zero exposed credentials detected across ${lines.length} lines.\n`;
      setBadge("nxsBadge", `SAFE • ${grade} (100/100)`, "green");
    } else {
      out += `[!] DETECTED ${findings.length} EXPOSED CREDENTIAL(S):\n\n`;
      findings.forEach((f, i) => {
        out += `  ${i + 1}. [${f.severity}] ${f.name} (${f.id}) at Line ${f.line}\n`;
        out += `     Masked Preview: ${f.preview}\n`;
        out += `     Remediation: Store in .env and access via environment variables\n\n`;
      });
      setBadge("nxsBadge", `${findings.length} LEAKS • ${grade}`, "red");
    }
    out += `--------------------------------------------------------------------\n`;
    out += `⚡ Audited 100% locally in browser via NexusShield (${PORTAL_URL})`;

    lastNxsOutput = JSON.stringify({ score, grade, findings, timestamp: new Date().toISOString() }, null, 2);
    document.getElementById("nxsOutput").textContent = out;
  }

  // =========================================================================
  // 6. CorePulse Quick Capture & Snippet Engine
  // =========================================================================

  function initCorePulse() {
    const btnAddTask = document.getElementById("btnCpAddTask");
    const taskInput = document.getElementById("cpTaskInput");
    const btnSync = document.getElementById("btnCpSync");

    if (btnAddTask && taskInput) {
      btnAddTask.addEventListener("click", () => handleQuickCapture());
      taskInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") handleQuickCapture();
      });
    }

    if (btnSync) {
      btnSync.addEventListener("click", () => syncWithDesktopCorePulse());
    }

    renderSnippets();
    renderTasks();
  }

  function handleQuickCapture() {
    const input = document.getElementById("cpTaskInput");
    if (!input) return;
    const raw = input.value.trim();
    if (!raw) return;

    let priority = "medium";
    if (raw.includes("!p1") || /!(?:critical|urgent)/i.test(raw)) priority = "critical";
    else if (raw.includes("!p2") || /!(?:high)/i.test(raw)) priority = "high";
    else if (raw.includes("!p3") || /!(?:low)/i.test(raw)) priority = "low";

    const tags = [];
    const tagMatches = raw.match(/#([a-zA-Z0-9_\-]+)/g);
    if (tagMatches) {
      tagMatches.forEach(t => tags.push(t.replace("#", "").toLowerCase()));
    }

    let duration = "30m";
    const durMatch = raw.match(/~(\d+[mh])/i);
    if (durMatch) duration = durMatch[1].toLowerCase();

    const cleanTitle = raw
      .replace(/!p[1-3]/gi, "")
      .replace(/!(?:critical|high|medium|low|urgent)/gi, "")
      .replace(/#[a-zA-Z0-9_\-]+/g, "")
      .replace(/~\d+[mh]/gi, "")
      .trim();

    const task = {
      id: "task-" + Date.now(),
      title: cleanTitle || raw,
      priority: priority,
      tags: tags.length > 0 ? tags : ["web-capture"],
      duration: duration,
      completed: false,
      created_at: new Date().toISOString()
    };

    chrome.storage.local.get(["corepulse_tasks"], (res) => {
      const tasks = res.corepulse_tasks || [];
      tasks.unshift(task);
      chrome.storage.local.set({ corepulse_tasks: tasks }, () => {
        input.value = "";
        renderTasks();

        // Optional non-blocking sync with desktop server
        fetch("http://127.0.0.1:8080/api/tasks", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: task.title,
            priority: task.priority,
            tags: task.tags,
            estimated_minutes: parseInt(duration.replace(/[mh]/, "")) || 30
          })
        }).catch(() => {});
      });
    });
  }

  function renderTasks() {
    chrome.storage.local.get(["corepulse_tasks"], (res) => {
      const tasks = res.corepulse_tasks || [];
      const listEl = document.getElementById("cpTaskList");
      const countEl = document.getElementById("cpTaskCount");
      if (countEl) countEl.textContent = tasks.length;
      if (!listEl) return;

      if (tasks.length === 0) {
        listEl.innerHTML = `<div style="font-size: 11px; color: var(--text-dim); text-align: center; padding: 12px;">No active tasks. Capture one above!</div>`;
        return;
      }

      listEl.innerHTML = "";
      tasks.forEach(task => {
        const item = document.createElement("div");
        item.className = `task-item ${task.completed ? "completed" : ""}`;

        const left = document.createElement("div");
        left.className = "task-left";

        const chk = document.createElement("input");
        chk.type = "checkbox";
        chk.className = "task-checkbox";
        chk.checked = !!task.completed;
        chk.addEventListener("change", () => toggleTask(task.id));

        const dot = document.createElement("span");
        dot.className = `task-prio-dot ${task.priority || "medium"}`;

        const title = document.createElement("span");
        title.className = "task-title";
        title.textContent = task.title;

        left.appendChild(chk);
        left.appendChild(dot);
        left.appendChild(title);

        const delBtn = document.createElement("button");
        delBtn.className = "task-delete-btn";
        delBtn.innerHTML = "×";
        delBtn.title = "Delete task";
        delBtn.addEventListener("click", () => deleteTask(task.id));

        item.appendChild(left);
        item.appendChild(delBtn);
        listEl.appendChild(item);
      });
    });
  }

  function toggleTask(taskId) {
    chrome.storage.local.get(["corepulse_tasks"], (res) => {
      const tasks = res.corepulse_tasks || [];
      const target = tasks.find(t => t.id === taskId);
      if (target) {
        target.completed = !target.completed;
        chrome.storage.local.set({ corepulse_tasks: tasks }, renderTasks);
      }
    });
  }

  function deleteTask(taskId) {
    chrome.storage.local.get(["corepulse_tasks"], (res) => {
      const tasks = (res.corepulse_tasks || []).filter(t => t.id !== taskId);
      chrome.storage.local.set({ corepulse_tasks: tasks }, renderTasks);
    });
  }

  function renderSnippets() {
    chrome.storage.local.get(["corepulse_snippets"], (res) => {
      const snippets = res.corepulse_snippets || [];
      const grid = document.getElementById("cpSnippetGrid");
      if (!grid) return;

      grid.innerHTML = "";
      snippets.forEach(snip => {
        const card = document.createElement("div");
        card.className = "snippet-card";
        card.title = `Click to copy "${snip.title}"`;

        card.innerHTML = `
          <div>
            <div class="snippet-trigger">${snip.trigger}</div>
            <div class="snippet-name">${snip.title}</div>
          </div>
          <span style="font-size: 11px; color: var(--accent-emerald);">📋</span>
        `;

        card.addEventListener("click", () => {
          copyToClipboard(snip.content);
        });

        grid.appendChild(card);
      });
    });
  }

  function syncWithDesktopCorePulse() {
    const btnSync = document.getElementById("btnCpSync");
    if (btnSync) btnSync.textContent = "Syncing...";

    fetch("http://127.0.0.1:8080/api/tasks")
      .then(r => r.json())
      .then(data => {
        if (data && data.tasks && Array.isArray(data.tasks)) {
          chrome.storage.local.get(["corepulse_tasks"], (res) => {
            const local = res.corepulse_tasks || [];
            const existingIds = new Set(local.map(t => t.id));

            data.tasks.forEach(dt => {
              if (!existingIds.has(dt.id)) {
                local.push({
                  id: dt.id,
                  title: dt.title,
                  priority: dt.priority || "medium",
                  tags: dt.tags || [],
                  duration: `${dt.estimated_minutes || 30}m`,
                  completed: !!dt.completed,
                  created_at: dt.created_at || new Date().toISOString()
                });
              }
            });

            chrome.storage.local.set({ corepulse_tasks: local }, () => {
              renderTasks();
              if (btnSync) {
                btnSync.textContent = "✔ Synced!";
                setTimeout(() => { btnSync.textContent = "🔄 Sync Desktop (:8080)"; }, 2000);
              }
            });
          });
        }
      })
      .catch(() => {
        if (btnSync) {
          btnSync.textContent = "Offline (:8080)";
          setTimeout(() => { btnSync.textContent = "🔄 Sync Desktop (:8080)"; }, 2000);
        }
      });
  }

  // =========================================================================
  // 7. Desktop Health & Status Polling
  // =========================================================================

  function checkDesktopConnection() {
    const dot = document.getElementById("statusDot");
    const txt = document.getElementById("statusText");

    fetch("http://127.0.0.1:8080/api/health", { method: "GET" })
      .then(r => r.json())
      .then(res => {
        if (dot) dot.classList.add("online");
        if (txt) txt.textContent = "CorePulse Desktop Online";
      })
      .catch(() => {
        if (dot) dot.classList.remove("online");
        if (txt) txt.textContent = "Local Storage (Standalone)";
      });
  }

  // =========================================================================
  // 8. Shared Helpers (Clipboard, Download, Badges)
  // =========================================================================

  function copyToClipboard(text, btnEl) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      if (btnEl) {
        const orig = btnEl.textContent;
        btnEl.textContent = "✔ Copied!";
        setTimeout(() => { btnEl.textContent = orig; }, 1800);
      }
    });
  }

  function setupCopyButton(btnId, text) {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.addEventListener("click", () => copyToClipboard(text, btn));
    }
  }

  function downloadFile(filename, content) {
    if (!content) return;
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function setBadge(badgeId, text, color) {
    const el = document.getElementById(badgeId);
    if (!el) return;
    el.textContent = text;
    el.className = `metric-badge badge-${color}`;
  }

})();
