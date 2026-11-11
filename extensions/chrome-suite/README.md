# IT Solutions Suite — Manifest V3 Chrome Extension & SidePanel Studio

> **100% Local-First • Unmetered • Zero Cloud Dependency • 5 Engines In-Browser**  
> Direct access to **ClauseGuard**, **DocuPulse**, **EchoStream**, **NexusShield**, and **CorePulse** inside Gmail, Google Docs, Upwork, LinkedIn, GitHub, and any webpage.

---

## ⚡ 30-Second Installation (Developer Mode)

You can load and run the extension immediately in Google Chrome, Brave, Edge, Arc, or any Chromium-based browser without building or compiling:

1. Open **Google Chrome** (or your Chromium browser).
2. Navigate to:
   ```text
   chrome://extensions
   ```
3. Enable **Developer mode** toggle in the top-right corner.
4. Click the **Load unpacked** button in the top-left corner.
5. Select this folder:
   ```text
   e:\It solution\extensions\chrome-suite
   ```
6. The **IT Solutions Studio** extension is now installed!
   - Pin the ⚡ icon to your browser toolbar for 1-click access.
   - Use shortcut `Ctrl+Shift+K` (or `Cmd+Shift+K` on Mac) to open the Studio instantly.
   - Open Chrome's Side Panel (`chrome://side-panel`) to keep the Studio docked beside your work!

---

## 🛠️ The 5 In-Browser Engines

### 1. ⚖️ ClauseGuard (Contract & NDA Redline Scanner)
- **Problem**: Upwork, freelance contracts, and vendor NDAs routinely slip in predatory clauses (uncapped liability, broad pre-existing IP grabs, 24-month evergreen auto-renewals, Net-90 delayed payment, unilateral termination).
- **In-Browser Action**:
  - Highlight any contract text on a webpage $\rightarrow$ Right-click $\rightarrow$ **"⚖️ Scan Contract with ClauseGuard"**.
  - Or paste text directly into the extension popup.
  - Instantly computes a contract safety score (A+ to F), highlights specific predatory clauses, explains the business risk, and generates **1-click copyable redline counter-clauses**.

### 2. 📄 DocuPulse (Invoice & Receipt Math Auditor)
- **Problem**: Manual invoice entry and verification from emails, PDFs, and billing portals is slow and prone to calculation errors.
- **In-Browser Action**:
  - Highlight any invoice or receipt text $\rightarrow$ Right-click $\rightarrow$ **"📄 Extract Invoice with DocuPulse"**.
  - Extracts Vendor, Invoice #, Dates, Line Items, Subtotal, Tax, and Total.
  - Automatically audits mathematics (`Subtotal + Tax == Total`) and flags discrepancies.
  - **1-Click Download**: Export clean `.csv` spreadsheet ready to open in Microsoft Excel, Google Sheets, or Apple Numbers.

### 3. 🎙️ EchoStream (Meeting Notes & Follow-Up Email Merger)
- **Problem**: Raw meeting transcripts and scratchpad bullet points take 20 minutes to format into a professional follow-up email.
- **In-Browser Action**:
  - Paste rough notes and speaker transcript into EchoStream.
  - Redacts accidental API keys and passwords automatically.
  - Separates decisions, commitments, action items with owners, and open questions into an executive-ready follow-up email draft.
  - **1-Click Copy**: Paste directly into Gmail, Outlook, or Slack.

### 4. 🛡️ NexusShield (Secret & High-Entropy Scanner)
- **Problem**: Developers and operators accidentally paste API keys, AWS credentials, and database passwords into public web forms, tickets, or code sandboxes.
- **In-Browser Action**:
  - Scans code, `.env` files, JSON configs, or snippets in real-time.
  - Detects AWS Keys (`AKIA...`), OpenAI tokens (`sk-...`), Stripe live keys, GitHub PATs (`ghp_...`), and Database URIs with embedded passwords.
  - Masks secrets and provides instantaneous safe remediation guidance.

### 5. ⚡ CorePulse (Quick-Capture & Dynamic Snippet Expander)
- **Quick Task Capture**:
  - Type quick syntax: `!p1 Review client security agreement #legal ~45m`
  - Automatically parses priority (`!p1` = critical), tags (`#tag`), and estimated time (`~45m`).
  - Stores tasks in persistent browser storage (`chrome.storage.local`).
  - **Dual Sync**: If your local CorePulse desktop engine is running on `http://127.0.0.1:8080`, tasks automatically sync locally via REST API!
- **Dynamic Text Snippets**:
  - Pre-loaded with common founder snippets:
    - `;;standup`: Instant daily standup update template.
    - `;;followup`: Professional executive meeting recap template.
    - `;;nda`: Standard bilateral safe-harbor NDA terms.
    - `;;invoice`: Standard Net-30 invoice submission template.
  - Click any snippet to copy to your clipboard instantly.

---

## 🔒 Privacy & Architecture Guarantees

- **100% Client-Side**: All parsing, auditing, and processing happens locally inside the extension sandbox.
- **Zero Cloud Telemetry**: No user text, contract data, invoice numbers, or code is ever sent to external third-party servers.
- **Manifest V3 Compliant**: Built strictly following Google Chrome's latest security, service worker, and side-panel standards.
- **100% Free & Unmetered**: Zero paywalls, zero pricing tables, and zero usage caps.

---

*Engineered by IT Solutions Global Corporation — Sovereign Productivity & Autonomous Systems.*
