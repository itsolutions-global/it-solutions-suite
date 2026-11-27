"""
ClauseGuard Legal Risk Scanner & Redline Counter-Clause Engine
100% offline, zero-dependency contract & NDA analyzer.
Evaluates contracts, NDAs, and Statements of Work (SOWs) for predatory legal
traps, uncapped liabilities, and scope creep.

Honesty Guard: Automated heuristic review — not legal advice.
Have a qualified lawyer review important agreements.
"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List

DISCLAIMER = "Automated heuristic review — not legal advice. Have a qualified lawyer review important agreements."

LEGAL_RISK_RULES: List[Dict[str, Any]] = [
    {
        "id": "CLG-UNCAPPED-LIABILITY",
        "title": "Uncapped / Unlimited Financial Liability",
        "severity": "CRITICAL",
        "penalty": 30,
        "category": "Liability & Indemnification",
        "pattern": re.compile(
            r"(?i)\b(?:unlimited\s+liability|liable\s+for\s+all\s+damages\s+without\s+limitation|no\s+limit\s+on\s+liability|indemnify\s+and\s+hold\s+harmless\s+from\s+any\s+and\s+all\s+claims\s+without\s+cap)\b"
        ),
        "plain_english_risk": (
            "Exposes you or your company to unlimited financial damages—even far exceeding "
            "the total value of the contract."
        ),
        "suggested_alternative": (
            "Notwithstanding anything to the contrary, neither party's aggregate liability under this "
            "Agreement shall exceed the total fees actually paid or payable in the twelve (12) months "
            "immediately preceding the claim, and neither party shall be liable for indirect, incidental, "
            "or consequential damages."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: 'Notwithstanding anything to the contrary, neither party's aggregate "
            "liability under this Agreement shall exceed the total fees actually paid or payable in the "
            "twelve (12) months immediately preceding the claim, and neither party shall be liable for "
            "indirect, incidental, or consequential damages.'"
        )
    },
    {
        "id": "CLG-AUTO-RENEWAL-TRAP",
        "title": "Evergreen Auto-Renewal Trap with Narrow Notice Window",
        "severity": "HIGH",
        "penalty": 18,
        "category": "Term & Termination",
        "pattern": re.compile(
            r"(?i)\b(?:automatically\s+renew(?:s)?\s+for\s+successive|shall\s+automatically\s+renew\s+unless\s+written\s+notice.*?(?:60|90|120)\s+days)\b"
        ),
        "plain_english_risk": (
            "Automatically locks you into another multi-month or multi-year billing cycle unless "
            "you cancel 60–120 days in advance."
        ),
        "suggested_alternative": (
            "This Agreement may renew for additional terms only upon mutual written agreement of both "
            "parties at least thirty (30) days prior to expiration, or either party may opt out of renewal "
            "with fifteen (15) days prior written notice."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: 'This Agreement may renew for additional terms only upon mutual written "
            "agreement of both parties at least thirty (30) days prior to expiration, or either party "
            "may opt out of renewal with fifteen (15) days prior written notice.'"
        )
    },
    {
        "id": "CLG-BROAD-IP-GRAB",
        "title": "Overbroad Pre-Existing Intellectual Property Assignment",
        "severity": "CRITICAL",
        "penalty": 28,
        "category": "Intellectual Property",
        "pattern": re.compile(
            r"(?i)\b(?:assigns\s+all\s+right,\s+title,\s+and\s+interest\s+in\s+and\s+to\s+all\s+prior\s+inventions|including\s+pre-existing\s+intellectual\s+property\s+shall\s+become\s+the\s+sole\s+property|all\s+tools,\s+know-how,\s+and\s+background\s+technology\s+shall\s+vest\s+exclusively)\b"
        ),
        "plain_english_risk": (
            "Transfers ownership of your pre-existing code, tools, templates, or background IP to the "
            "counterparty instead of just the custom deliverables paid for."
        ),
        "suggested_alternative": (
            "Provider retains all right, title, and interest in its pre-existing Intellectual Property, "
            "reusable tools, and general know-how. Upon full payment, Client receives ownership of custom "
            "Deliverables, plus a non-exclusive license to any embedded Background IP solely as incorporated "
            "in the Deliverables."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: 'Provider retains all right, title, and interest in its pre-existing "
            "Intellectual Property, reusable tools, and general know-how. Upon full payment, Client "
            "receives ownership of custom Deliverables, plus a non-exclusive license to any embedded "
            "Background IP solely as incorporated in the Deliverables.'"
        )
    },
    {
        "id": "CLG-NON-COMPETE-OVERREACH",
        "title": "Restrictive Non-Compete / Industry Ban Clause",
        "severity": "HIGH",
        "penalty": 20,
        "category": "Restrictive Covenants",
        "pattern": re.compile(
            r"(?i)\b(?:shall\s+not\s+directly\s+or\s+indirectly\s+engage\s+in\s+any\s+competing\s+business|prohibited\s+from\s+providing\s+similar\s+services\s+to\s+any\s+company\s+in\s+the\s+industry)\b"
        ),
        "plain_english_risk": (
            "Blocks you from working with other clients in your own industry or profession after "
            "this engagement ends."
        ),
        "suggested_alternative": (
            "Strike the non-compete clause in its entirety and rely strictly on mutual Confidentiality "
            "and Non-Disclosure obligations regarding proprietary information."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: Strike the non-compete clause in its entirety and rely strictly on "
            "mutual Confidentiality and Non-Disclosure obligations regarding proprietary information."
        )
    },
    {
        "id": "CLG-DELAYED-PAYMENT-TERMS",
        "title": "Extended Payment Delay (Net-60 / Net-90 / Pay-When-Paid)",
        "severity": "MEDIUM",
        "penalty": 12,
        "category": "Payment & Cash Flow",
        "pattern": re.compile(
            r"(?i)\b(?:net\s*(?:60|90|120)\s*days|payable\s+within\s+(?:sixty|ninety|60|90)\s+days|pay-when-paid|contingent\s+upon\s+client's\s+receipt\s+of\s+payment)\b"
        ),
        "plain_english_risk": (
            "Forces you to wait 60–90+ days to get paid (or makes your payment contingent on a third party)."
        ),
        "suggested_alternative": (
            "All undisputed invoices shall be due and payable within fifteen (15) or thirty (30) days of "
            "invoice date (Net-30), independent of any third-party payment."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: 'All undisputed invoices shall be due and payable within fifteen (15) "
            "or thirty (30) days of invoice date (Net-30), independent of any third-party payment.'"
        )
    },
    {
        "id": "CLG-UNILATERAL-TERMINATION",
        "title": "One-Sided Termination Without Cause or Payment for Work Done",
        "severity": "HIGH",
        "penalty": 16,
        "category": "Term & Termination",
        "pattern": re.compile(
            r"(?i)\b(?:may\s+terminate\s+this\s+agreement\s+immediately\s+without\s+notice\s+and\s+without\s+liability\s+for\s+work\s+in\s+progress|sole\s+discretion\s+terminate\s+without\s+compensation)\b"
        ),
        "plain_english_risk": (
            "Allows the other party to cancel at any moment without paying for hours or milestones "
            "already worked."
        ),
        "suggested_alternative": (
            "Either party may terminate this Agreement for convenience upon thirty (30) days prior written "
            "notice, provided that Client shall pay Provider for all services performed and non-cancellable "
            "expenses incurred through the effective date of termination."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: 'Either party may terminate this Agreement for convenience upon thirty "
            "(30) days prior written notice, provided that Client shall pay Provider for all services "
            "performed and non-cancellable expenses incurred through the effective date of termination.'"
        )
    },
    {
        "id": "CLG-UNILATERAL-AMENDMENT",
        "title": "Unilateral Modification of Terms or Pricing Without Consent",
        "severity": "MEDIUM",
        "penalty": 12,
        "category": "Governance",
        "pattern": re.compile(
            r"(?i)\b(?:reserves\s+the\s+right\s+to\s+modify\s+these\s+terms\s+at\s+any\s+time\s+without\s+notice|may\s+increase\s+fees\s+at\s+its\s+sole\s+discretion\s+at\s+any\s+time)\b"
        ),
        "plain_english_risk": (
            "Allows the counterparty to change contract terms or raise prices mid-contract without "
            "your written approval."
        ),
        "suggested_alternative": (
            "No amendment, modification, or fee adjustment to this Agreement shall be valid unless executed "
            "in writing and signed by authorized representatives of both parties."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: 'No amendment, modification, or fee adjustment to this Agreement shall "
            "be valid unless executed in writing and signed by authorized representatives of both parties.'"
        )
    },
    # --- SOW & Commercial Rules (v1.2 Expansion) ---
    {
        "id": "CLG-SOW-UNLIMITED-REVISIONS",
        "title": "SOW Scope Creep: Unlimited / Unbounded Revisions",
        "severity": "HIGH",
        "penalty": 18,
        "category": "Scope & Deliverables",
        "pattern": re.compile(
            r"(?i)\b(?:unlimited\s+(?:number\s+of\s+)?revisions|infinite\s+revisions|revisions\s+without\s+limit|revise\s+until\s+(?:client\s+is\s+)?satisfied|as\s+many\s+revisions\s+as\s+(?:client\s+)?(?:desires|requires|requests)|unlimited\s+rounds\s+of\s+(?:revisions|changes))\b"
        ),
        "plain_english_risk": (
            "Commits you to indefinite rounds of free revisions without milestone sign-off, "
            "leading to severe scope creep and uncompensated labor."
        ),
        "suggested_alternative": (
            "Services shall include up to two (2) rounds of minor revisions per deliverable. "
            "Any additional revisions, material scope changes, or work requested after deliverable "
            "acceptance shall be billed at Provider's standard hourly rate."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: 'Services shall include up to two (2) rounds of minor revisions per deliverable. "
            "Any additional revisions, material scope changes, or work requested after deliverable "
            "acceptance shall be billed at Provider's standard hourly rate.'"
        )
    },
    {
        "id": "CLG-SOW-DEEMED-REJECTION",
        "title": "Unilateral Acceptance Window / Deemed Rejection Trap",
        "severity": "HIGH",
        "penalty": 18,
        "category": "Acceptance & Milestones",
        "pattern": re.compile(
            r"(?i)\b(?:deemed\s+rejected\s+if\s+not\s+(?:expressly\s+)?approved|failure\s+to\s+approve\s+shall\s+be\s+deemed\s+rejection|deemed\s+rejected\s+unless\s+written|client\s+has\s+no\s+deadline\s+to\s+accept|acceptance\s+at\s+client's\s+sole\s+discretion\s+without\s+time\s+limit|client\s+shall\s+have\s+unlimited\s+time\s+to\s+inspect|no\s+time\s+limit\s+for\s+client\s+acceptance)\b"
        ),
        "plain_english_risk": (
            "Allows client to withhold payment indefinitely by failing to review work, "
            "or treats silence as rejection rather than acceptance."
        ),
        "suggested_alternative": (
            "Deliverables shall be deemed accepted within ten (10) business days of delivery unless "
            "Client provides detailed written notice specifying material non-conformities with the "
            "agreed specifications. Provider shall have ten (10) business days to cure any verified defects."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: 'Deliverables shall be deemed accepted within ten (10) business days of "
            "delivery unless Client provides detailed written notice specifying material non-conformities with "
            "the agreed specifications. Provider shall have ten (10) business days to cure any verified defects.'"
        )
    },
    {
        "id": "CLG-SOW-OPEN-WARRANTY",
        "title": "Open-Ended / Perpetual Free Warranty & Bug-Fix Obligations",
        "severity": "HIGH",
        "penalty": 20,
        "category": "Warranty & Maintenance",
        "pattern": re.compile(
            r"(?i)\b(?:perpetual\s+warranty|unlimited\s+warranty|free\s+bug\s+fixes\s+(?:in\s+perpetuity|forever|indefinitely)|fix\s+all\s+bugs\s+at\s+no\s+cost\s+in\s+perpetuity|warrant(?:s)?\s+forever|ongoing\s+maintenance\s+at\s+no\s+(?:additional\s+)?charge|free\s+support\s+for\s+the\s+lifetime)\b"
        ),
        "plain_english_risk": (
            "Forces you to provide free technical support and bug fixes indefinitely without compensation."
        ),
        "suggested_alternative": (
            "Provider warrants that Deliverables will substantially conform to specifications for a period "
            "of thirty (30) days following acceptance. After expiration of this warranty period, maintenance, "
            "updates, or bug fixes shall be subject to a separate mutual maintenance agreement or billed at standard rates."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: 'Provider warrants that Deliverables will substantially conform to "
            "specifications for a period of thirty (30) days following acceptance. After expiration of this "
            "warranty period, maintenance, updates, or bug fixes shall be subject to a separate mutual "
            "maintenance agreement or billed at standard rates.'"
        )
    },
    {
        "id": "CLG-SOW-IP-BEFORE-PAYMENT",
        "title": "Premature IP Assignment Before Receipt of Full Payment",
        "severity": "CRITICAL",
        "penalty": 28,
        "category": "Intellectual Property & Payment",
        "pattern": re.compile(
            r"(?i)\b(?:assigns?\s+all\s+(?:intellectual\s+property|rights|ip)\s+upon\s+creation|ip\s+transfers?\s+immediately\s+upon\s+delivery|intellectual\s+property\s+vests\s+in\s+client\s+upon\s+creation\s+regardless\s+of\s+payment|assigns?\s+all\s+rights\s+prior\s+to\s+(?:full\s+)?payment|work\s+for\s+hire\s+prior\s+to\s+full\s+payment|ip\s+transfer\s+before\s+payment)\b"
        ),
        "plain_english_risk": (
            "Transfers ownership of all deliverables and IP before you have received full payment, "
            "leaving you with zero leverage if the client refuses to pay."
        ),
        "suggested_alternative": (
            "All right, title, and interest in and to the custom Deliverables shall transfer to Client "
            "exclusively upon Provider's receipt of full and final payment of all agreed fees. Until full "
            "payment is received, Provider retains all intellectual property rights."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: 'All right, title, and interest in and to the custom Deliverables shall "
            "transfer to Client exclusively upon Provider's receipt of full and final payment of all "
            "agreed fees. Until full payment is received, Provider retains all intellectual property rights.'"
        )
    },
    # --- Multi-Jurisdiction & NDA Residuals Expansion (v1.1) ---
    {
        "id": "CLG-NDA-RESIDUALS-MEMORY",
        "title": "NDA 'Residuals' / Unaided Memory Loophole",
        "severity": "CRITICAL",
        "penalty": 26,
        "category": "Confidentiality & Trade Secrets",
        "pattern": re.compile(
            r"(?i)\b(?:unaided\s+memory|retained\s+in\s+the\s+(?:unaided\s+)?memories|residual\s+information|residuals\s+clause|use\s+ideas,\s+concepts,\s+know-how\s+or\s+techniques\s+retained)\b"
        ),
        "plain_english_risk": (
            "Allows the receiving party's engineers or executives to freely use your trade secrets and "
            "architecture so long as they claim they 'remembered it without looking at notes.'"
        ),
        "suggested_alternative": (
            "Delete the Residuals / Unaided Memory exception in its entirety, or explicitly clarify that "
            "nothing herein grants any license under Disclosing Party's copyrights, patents, or trade secrets."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: Delete the Residuals / Unaided Memory clause in its entirety; clarify that "
            "'Nothing in this Agreement grants Receiving Party any right or license to use Disclosing Party's "
            "Confidential Information, whether retained in memory or otherwise.'"
        )
    },
    {
        "id": "CLG-UK-UCTA-EXCLUSION",
        "title": "UK UCTA 1977 Overbroad Statutory Liability Exclusion",
        "severity": "HIGH",
        "penalty": 18,
        "category": "UK Commercial Law (UCTA 1977)",
        "pattern": re.compile(
            r"(?i)\b(?:exclude\s+all\s+liability\s+for\s+breach\s+of\s+statutory|no\s+liability\s+for\s+fundamental\s+breach|exclusion\s+of\s+implied\s+terms\s+under\s+sale\s+of\s+goods|exclude\s+liability\s+for\s+death\s+or\s+personal\s+injury\s+caused\s+by\s+negligence)\b"
        ),
        "plain_english_risk": (
            "Attempts to exclude mandatory statutory protections or negligence liability restricted under "
            "the UK Unfair Contract Terms Act 1977 (UCTA §§ 2, 6, 11)."
        ),
        "suggested_alternative": (
            "Nothing in this Agreement shall limit or exclude either party's liability for death or personal "
            "injury caused by negligence, fraud, or any other liability that cannot be lawfully excluded under "
            "applicable UK statute."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: 'Nothing in this Agreement shall limit or exclude either party's liability for "
            "death or personal injury caused by negligence, fraud, fraudulent misrepresentation, or any other "
            "liability that cannot be lawfully limited under the Unfair Contract Terms Act 1977.'"
        )
    },
    {
        "id": "CLG-EU-GDPR-AI-TRAINING",
        "title": "Unconsented AI Model Training on Customer Data / Missing GDPR Art. 28 DPA",
        "severity": "CRITICAL",
        "penalty": 25,
        "category": "EU GDPR Art. 28 & AI Governance",
        "pattern": re.compile(
            r"(?i)\b(?:use\s+(?:all\s+)?customer\s+data\s+to\s+train\s+(?:ai|machine\s+learning|internal\s+models)|transfer\s+personal\s+data\s+without\s+(?:standard\s+contractual|dpa)|no\s+data\s+processing\s+addendum)\b"
        ),
        "plain_english_risk": (
            "Grants vendor rights to train foundation/ML models on confidential customer or personal data, "
            "or processes EU personal data without a mandatory GDPR Article 28 Data Processing Addendum."
        ),
        "suggested_alternative": (
            "Vendor shall process Customer Data solely to deliver the contracted Services in accordance with "
            "an executed GDPR Article 28 Data Processing Addendum and shall never use Customer Data to train, "
            "fine-tune, or enrich machine learning models."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: 'Vendor shall process Customer Data strictly to provide the Services under a "
            "binding GDPR Article 28 DPA and shall not use Customer Data or Confidential Information to train "
            "or fine-tune any artificial intelligence or machine learning models.'"
        )
    },
    {
        "id": "CLG-IN-SECTION27-RESTRAINT",
        "title": "Post-Term Restraint of Trade (Indian Contract Act, 1872 § 27)",
        "severity": "HIGH",
        "penalty": 20,
        "category": "India Statutory Law (§ 27)",
        "pattern": re.compile(
            r"(?i)\b(?:restrained\s+from\s+exercising\s+a\s+lawful\s+profession|restraint\s+of\s+trade|shall\s+not\s+practice\s+any\s+profession\s+or\s+trade\s+in\s+india)\b"
        ),
        "plain_english_risk": (
            "Under Section 27 of the Indian Contract Act, 1872, post-termination agreements restraining "
            "anyone from exercising a lawful profession, trade, or business are generally void."
        ),
        "suggested_alternative": (
            "Remove post-termination restraint of profession language and limit restrictions strictly to "
            "protection of proprietary Confidential Information and non-solicitation of active client accounts."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: Strike post-termination restraint of trade pursuant to Section 27 of the "
            "Indian Contract Act, 1872, and narrow obligations strictly to Confidential Information protection."
        )
    },
    {
        "id": "CLG-CA-16600-NONCOMPETE",
        "title": "Unenforceable California Non-Compete Covenant (Cal. Bus. & Prof. Code § 16600)",
        "severity": "HIGH",
        "penalty": 20,
        "category": "US / California Law (§ 16600)",
        "pattern": re.compile(
            r"(?i)(?:california.*non-compete|governed\s+by\s+california\s+law.*shall\s+not\s+compete|subject\s+to\s+california.*restricting\s+employment)"
        ),
        "plain_english_risk": (
            "Under California Business & Professions Code § 16600 and § 16600.1, non-compete covenants "
            "are void and attempting to enforce them carries statutory civil liability."
        ),
        "suggested_alternative": (
            "Remove the non-compete covenant in compliance with California Business & Professions Code § 16600."
        ),
        "redline_counter_clause": (
            "PROPOSED REDLINE: Delete non-compete restriction in its entirety as void under California "
            "Business & Professions Code § 16600."
        )
    }
]


class ContractRiskScanner:
    """Scans legal contracts, NDAs, and SOWs locally for predatory clauses."""

    DISCLAIMER = DISCLAIMER

    def __init__(self):
        self.rules = LEGAL_RISK_RULES

    def scan_contract(self, contract_text: str, document_name: str = "Contract.txt") -> Dict[str, Any]:
        """
        Analyzes contract text, computes a Safety Score (0-100), extracts risky clauses,
        and generates ready-to-paste suggested alternative wording.
        """
        lines = contract_text.splitlines()
        findings: List[Dict[str, Any]] = []
        total_penalty = 0

        for line_idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            for rule in self.rules:
                m = rule["pattern"].search(stripped)
                if m:
                    total_penalty += rule["penalty"]
                    findings.append({
                        "id": rule["id"],
                        "title": rule["title"],
                        "severity": rule["severity"],
                        "category": rule["category"],
                        "line": line_idx,
                        "matched_excerpt": stripped[:220],
                        "plain_english_risk": rule["plain_english_risk"],
                        "suggested_alternative": rule["suggested_alternative"],
                        "redline_counter_clause": rule["redline_counter_clause"]
                    })

        score = max(0.0, round(100.0 - total_penalty, 1))
        if score >= 90:
            grade = "A+"
            verdict = "SAFE TO SIGN"
        elif score >= 75:
            grade = "B"
            verdict = "MINOR REDLINES RECOMMENDED"
        elif score >= 50:
            grade = "C"
            verdict = "HIGH RISK — NEGOTIATE BEFORE SIGNING"
        else:
            grade = "F"
            verdict = "DANGEROUS CONTRACT — DO NOT SIGN WITHOUT REDLINING"

        counts = {
            "CRITICAL": sum(1 for f in findings if f["severity"] == "CRITICAL"),
            "HIGH": sum(1 for f in findings if f["severity"] == "HIGH"),
            "MEDIUM": sum(1 for f in findings if f["severity"] == "MEDIUM"),
        }

        return {
            "document": document_name,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "safety_score": score,
            "grade": grade,
            "verdict": verdict,
            "counts": counts,
            "findings_count": len(findings),
            "findings": findings,
            "disclaimer": self.DISCLAIMER
        }
