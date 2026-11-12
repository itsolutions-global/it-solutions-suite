/**
 * IT Solutions Global - Production Portal & Live Client-Side Web App Studio
 * Pure Vanilla JavaScript • Zero External Dependencies • 100% In-Browser Execution
 */

(function () {
  'use strict';

  const PORTAL_URL = "https://it-solutions-global.vercel.app";

  // 1. Multi-Platform Install Commands
  const installCommands = {
    pip: "pip install it-solutions-suite",
    ps: "irm https://it-solutions-global.vercel.app/install.ps1 | iex",
    sh: "curl -fsSL https://it-solutions-global.vercel.app/install.sh | bash",
    docker: "docker run -d -p 8080:8080 itsolutionsglobal/corepulse:latest",
    git: "git clone https://github.com/itsolutions-global/it-solutions-suite.git"
  };

  let currentCliPlatform = 'pip';

  window.setCliPlatform = function (platform) {
    currentCliPlatform = platform;
    document.querySelectorAll('.tab-btn-cli[data-cli]').forEach(tab => {
      tab.classList.toggle('active', tab.getAttribute('data-cli') === platform);
    });
    const cmdEl = document.getElementById('cliCommandText');
    if (cmdEl) {
      cmdEl.textContent = installCommands[platform];
    }
    resetCopyBtn();
  };

  window.copyCliCommand = function () {
    const textToCopy = installCommands[currentCliPlatform];
    navigator.clipboard.writeText(textToCopy).then(() => {
      const copyBtn = document.getElementById('copyCliBtn');
      const copyBtnText = document.getElementById('copyCliBtnText');
      if (copyBtn && copyBtnText) {
        copyBtn.classList.add('copied');
        copyBtnText.textContent = "Copied to Clipboard!";
        setTimeout(resetCopyBtn, 2500);
      }
    }).catch(err => {
      console.error('Clipboard copy failed: ', err);
    });
  };

  function resetCopyBtn() {
    const copyBtn = document.getElementById('copyCliBtn');
    const copyBtnText = document.getElementById('copyCliBtnText');
    if (copyBtn && copyBtnText) {
      copyBtn.classList.remove('copied');
      copyBtnText.textContent = "Copy Command";
    }
  }

  // 2. Product Showcase Tab Switcher
  window.switchProductTab = function (pillar) {
    const tabs = ['action', 'defense', 'perception', 'federation'];
    tabs.forEach(t => {
      const card = document.getElementById(`tab-${t}`);
      const panel = document.getElementById(`panel-${t}`);
      if (t === pillar) {
        if (card) {
          card.classList.add('active');
          if (t === 'defense') card.classList.add('defense');
          if (t === 'perception') card.classList.add('perception');
          if (t === 'federation') card.classList.add('federation');
        }
        if (panel) panel.classList.add('active');
      } else {
        if (card) card.classList.remove('active', 'defense', 'perception', 'federation');
        if (panel) panel.classList.remove('active');
      }
    });
  };

  // =========================================================================
  // 3. LIVE INTERACTIVE BROWSER WEB APP STUDIO (100% Client-Side Engines)
  // =========================================================================

  let activeStudioTool = 'clauseguard';
  let lastDownloadContent = '';
  let lastDownloadFilename = 'it-solutions-report.txt';

  const STUDIO_SAMPLES = {
    clauseguard: {
      title: "⚖️ Paste Contract, NDA, or Terms of Service",
      downloadLabel: "📥 Download Redline Report (.txt)",
      sample:
        "MASTER SERVICES AGREEMENT\n" +
        "1. Liability: Consultant shall have unlimited liability for any and all damages arising out of this Agreement.\n" +
        "2. Intellectual Property: Consultant assigns all right, title, and interest in and to all prior inventions and including pre-existing intellectual property shall become the sole property of Client.\n" +
        "3. Term & Renewal: This Agreement shall automatically renew for successive 24-month periods unless written notice is provided 90 days prior.\n" +
        "4. Payment Terms: All undisputed invoices are payable Net 90 days after Client receipt.\n" +
        "5. Termination: Client may at its sole discretion terminate without compensation for work in progress."
    },
    docupulse: {
      title: "📄 Paste Invoice, Receipt, or Purchase Order Text",
      downloadLabel: "📥 Download Excel / CSV Ledger (.csv)",
      sample:
        "Vendor: CloudScale Infrastructure Inc.\n" +
        "Invoice Number: INV-2026-8841\n" +
        "Date: 2026-11-10\n" +
        "Due Date: 2026-12-10\n\n" +
        "1. Dedicated Kubernetes Cluster Node (2x @ $400.00) $800.00\n" +
        "2. Managed Postgres High-Availability Storage $350.00\n" +
        "3. Zero-Trust DDoS Edge Protection $150.00\n\n" +
        "Subtotal: $1,300.00\n" +
        "Tax (8%): $104.00\n" +
        "Total Due: $1,404.00"
    },
    echostream: {
      title: "🎙️ Paste Meeting Notes & Transcript",
      downloadLabel: "📥 Download Follow-Up Email (.md)",
      sample:
        "# Scratchpad Notes:\n" +
        "- Client wants SOC2 compliance report before November 25\n" +
        "- Todo: Send updated pricing proposal to David by tomorrow\n\n" +
        "# Meeting Transcript:\n" +
        "[David CTO] We agreed to migrate the staging cluster to zero-trust mTLS.\n" +
        "[Sarah] I will deploy the new mTLS certificates before Wednesday afternoon.\n" +
        "[David CTO] Question: can we clarify the multi-region failover SLA for Q1?"
    },
    nexusshield: {
      title: "🛡️ Paste Source Code, Config, or .env File",
      downloadLabel: "📥 Download Security Audit (.json)",
      sample:
        "# Production Environment Config\n" +
        "PORT=8080\n" +
        "AWS_ACCESS_KEY_ID=\"AKIAIOSFODNN7EXAMPLE9\"\n" +
        "OPENAI_API_KEY=\"sk-proj-98723418726354128937123987123987abcd\"\n" +
        "DATABASE_URL=\"postgres://admin:SuperSecretPass99@db.internal:5432/prod\"\n" +
        "DEBUG_MODE=false"
    }
  };

  window.switchStudioTool = function (tool) {
    activeStudioTool = tool;
    ['clauseguard', 'docupulse', 'echostream', 'nexusshield'].forEach(t => {
      const btn = document.getElementById(`studioBtn-${t}`);
      if (btn) btn.classList.toggle('active', t === tool);
    });
    const cfg = STUDIO_SAMPLES[tool];
    const titleEl = document.getElementById('studioInputTitle');
    const dlBtn = document.getElementById('studioDownloadBtn');
    if (titleEl && cfg) titleEl.textContent = cfg.title;
    if (dlBtn && cfg) dlBtn.textContent = cfg.downloadLabel;
    window.loadStudioSample();
    window.runStudioEngine();
  };

  window.loadStudioSample = function () {
    const cfg = STUDIO_SAMPLES[activeStudioTool];
    const input = document.getElementById('studioInputText');
    if (input && cfg) {
      input.value = cfg.sample;
    }
  };

  window.clearStudioWorkspace = function () {
    const input = document.getElementById('studioInputText');
    const out = document.getElementById('studioOutputContainer');
    const badge = document.getElementById('studioOutputBadge');
    if (input) input.value = '';
    if (out) out.textContent = 'Paste your input on the left and click "⚡ Run Instant Local Audit"...';
    if (badge) {
      badge.textContent = 'IDLE • 100% BROWSER LOCAL';
      badge.style.color = '#94a3b8';
    }
  };

  // --- Engine 1: ClauseGuard Client-Side Scanner ---
  function runClauseGuardBrowser(text) {
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
        redline: "PROPOSED REDLINE: 'Provider retains all right, title, and interest in pre-existing IP and reusable tools; Client receives ownership of custom Deliverables upon full payment.'"
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
        redline: "PROPOSED REDLINE: Strike non-compete clause and rely strictly on mutual Non-Disclosure obligations."
      },
      {
        id: "CLG-DELAYED-PAYMENT",
        title: "Extended Payment Delay (Net-60 / Net-90 / Pay-When-Paid)",
        severity: "MEDIUM",
        penalty: 12,
        regex: /net\s*(?:60|90|120)|payable\s+within\s+(?:sixty|ninety|60|90)\s+days|pay-when-paid/i,
        risk: "Forces you to wait 60–90+ days to get paid for completed work.",
        redline: "PROPOSED REDLINE: 'All undisputed invoices shall be due and payable within 15 or 30 days (Net-30) of invoice date.'"
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
    } else {
      findings.forEach((f, i) => {
        out += `${i + 1}. [${f.severity}] ${f.title} (Line ${f.line})\n`;
        out += `   • Why It Hurts: ${f.risk}\n`;
        out += `   • ${f.redline}\n\n`;
      });
    }
    out += `--------------------------------------------------------------------\n`;
    out += `⚠ Automated heuristic review — not legal advice. Have a qualified lawyer review important agreements.\n`;
    out += `⚡ Audited 100% locally via ClauseGuard (${PORTAL_URL})`;

    lastDownloadContent = out;
    lastDownloadFilename = "clauseguard-redline-audit.txt";
    return { badge: `SCORE: ${grade} (${score}/100) • ${findings.length} RISKS`, ok: score >= 75, text: out };
  }

  // --- Engine 2: DocuPulse Client-Side Invoice Extractor ---
  function runDocuPulseBrowser(text) {
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
    out += `  Math Audit:     ${mathOk ? '✔ VERIFIED (Subtotal + Tax == Total)' : '⚠ DISCREPANCY FLAGGED (Expected $' + expectedTotal.toFixed(2) + ')'}\n`;
    out += `====================================================================\n`;
    out += `⚡ Click "📥 Download Excel / CSV Ledger (.csv)" above to open in Excel.`;

    let csv = "Vendor,Invoice Number,Issue Date,Due Date,Subtotal,Tax,Total,Math Verified\n";
    csv += `"${vendor.replace(/"/g, '""')}","${invNum}","${issueDate}","${dueDate}",${subtotal.toFixed(2)},${tax.toFixed(2)},${total.toFixed(2)},${mathOk ? "YES" : "FLAGGED"}\n`;
    lastDownloadContent = csv;
    lastDownloadFilename = `docupulse-ledger-${invNum}.csv`;

    return { badge: mathOk ? `VERIFIED • TOTAL $${total.toFixed(2)}` : `MATH ALERT • $${total.toFixed(2)}`, ok: mathOk, text: out };
  }

  // --- Engine 3: EchoStream Client-Side Meeting Merger & Email Generator ---
  function runEchoStreamBrowser(text) {
    // Redact any accidental keys first
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

    lastDownloadContent = email;
    lastDownloadFilename = `meeting-followup-${today}.md`;
    return { badge: `DRAFTED • ${actions.length} ACTIONS & ${decisions.length} DECISIONS`, ok: true, text: email };
  }

  // --- Engine 4: NexusShield Client-Side Secret & Entropy Scanner ---
  function runNexusShieldBrowser(text) {
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
    } else {
      out += `[!] DETECTED ${findings.length} EXPOSED CREDENTIAL(S):\n\n`;
      findings.forEach((f, i) => {
        out += `  ${i + 1}. [${f.severity}] ${f.name} (${f.id}) at Line ${f.line}\n`;
        out += `     Masked Preview: ${f.preview}\n`;
        out += `     Remediation: Move to .env and replace with os.environ.get()\n\n`;
      });
    }
    out += `--------------------------------------------------------------------\n`;
    out += `⚡ Audited 100% locally in browser via NexusShield (${PORTAL_URL})`;

    lastDownloadContent = JSON.stringify({ score, grade, findings }, null, 2);
    lastDownloadFilename = "nexusshield-audit.json";
    return { badge: `SECURITY: ${grade} (${score}/100) • ${findings.length} LEAKS`, ok: findings.length === 0, text: out };
  }

  window.runStudioEngine = function () {
    const inputEl = document.getElementById('studioInputText');
    const outEl = document.getElementById('studioOutputContainer');
    const badgeEl = document.getElementById('studioOutputBadge');
    if (!inputEl || !outEl) return;

    const raw = inputEl.value.trim();
    if (!raw) {
      outEl.textContent = "Please paste some text or click '✨ Load Sample' first.";
      return;
    }

    let result;
    if (activeStudioTool === 'clauseguard') {
      result = runClauseGuardBrowser(raw);
    } else if (activeStudioTool === 'docupulse') {
      result = runDocuPulseBrowser(raw);
    } else if (activeStudioTool === 'echostream') {
      result = runEchoStreamBrowser(raw);
    } else {
      result = runNexusShieldBrowser(raw);
    }

    outEl.textContent = result.text;
    if (badgeEl) {
      badgeEl.textContent = result.badge;
      badgeEl.style.color = result.ok ? '#34d399' : '#fbbf24';
      badgeEl.style.borderColor = result.ok ? 'rgba(16, 185, 129, 0.4)' : 'rgba(251, 191, 36, 0.4)';
      badgeEl.style.background = result.ok ? 'rgba(16, 185, 129, 0.14)' : 'rgba(251, 191, 36, 0.14)';
    }
  };

  window.copyStudioOutput = function () {
    const outEl = document.getElementById('studioOutputContainer');
    if (!outEl) return;
    navigator.clipboard.writeText(outEl.textContent).then(() => {
      const badgeEl = document.getElementById('studioOutputBadge');
      if (badgeEl) {
        const prev = badgeEl.textContent;
        badgeEl.textContent = "✔ COPIED TO CLIPBOARD!";
        setTimeout(() => { badgeEl.textContent = prev; }, 2000);
      }
    });
  };

  window.downloadStudioOutput = function () {
    if (!lastDownloadContent) window.runStudioEngine();
    const blob = new Blob([lastDownloadContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = lastDownloadFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  window.sharePortal = function (channel) {
    const text = encodeURIComponent("Check out this 100% free, local-first browser studio for scanning contracts (ClauseGuard), extracting invoices to CSV (DocuPulse), drafting meeting emails (EchoStream), and scanning secrets (NexusShield):");
    const url = encodeURIComponent(PORTAL_URL);
    if (channel === 'twitter') {
      window.open(`https://twitter.com/intent/tweet?text=${text}&url=${url}`, '_blank');
    } else if (channel === 'linkedin') {
      window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${url}`, '_blank');
    } else if (channel === 'whatsapp') {
      window.open(`https://api.whatsapp.com/send?text=${text}%20${url}`, '_blank');
    } else if (channel === 'copy') {
      navigator.clipboard.writeText(PORTAL_URL).then(() => {
        const btn = document.getElementById('shareCopyBtn');
        if (btn) {
          btn.textContent = "✔ Link Copied!";
          setTimeout(() => { btn.textContent = "🔗 Copy Link"; }, 2000);
        }
      });
    }
  };

  // 4. Animated Metric Counter Engine
  function animateValue(id, start, end, duration, suffix = '') {
    const el = document.getElementById(id);
    if (!el) return;
    let startTimestamp = null;
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      const val = Math.floor(progress * (end - start) + start);
      el.textContent = val + suffix;
      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        el.textContent = end + suffix;
      }
    };
    window.requestAnimationFrame(step);
  }

  // 5. Initialize on DOM Load
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
      animateValue('metricTests', 0, 175, 1200, '/175');
      animateValue('metricDeps', 10, 0, 800, '');
      animateValue('metricLatency', 60, 15, 1000, 'ms');
      animateValue('metricLocal', 0, 100, 1200, '%');
    }, 200);

    window.setCliPlatform('pip');
    window.switchStudioTool('clauseguard');
  });

})();
