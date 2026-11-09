"""
NexusShield Security Health Scorer & Compliance Engine
Implements the PRD-mandated dynamic scoring formula, letter grade mapping, and compliance matrix.
"""

from typing import Any, Dict, List, Tuple

def compute_security_score(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes overall Security Health Score (0-100), letter grade (A+ through F),
    and compliance indicators based on PRD-mandated weightings:
      Score = 100 - (Critical * 25) - (High * 10) - (Medium * 3) - (Low * 0.5)
    """
    counts = {
        "Critical": 0,
        "High": 0,
        "Medium": 0,
        "Low": 0
    }

    for f in findings:
        sev = f.get("severity", "Medium").capitalize()
        if sev in counts:
            counts[sev] += 1
        else:
            counts["Medium"] += 1

    # Apply penalty formula
    deduction = (
        (counts["Critical"] * 25.0) +
        (counts["High"] * 10.0) +
        (counts["Medium"] * 3.0) +
        (counts["Low"] * 0.5)
    )

    raw_score = 100.0 - deduction
    score = max(0.0, min(100.0, round(raw_score, 1)))

    # Letter Grade Mapping
    if score >= 97.0:
        grade = "A+"
        status = "SECURE (OPTIMAL)"
    elif score >= 90.0:
        grade = "A"
        status = "SECURE"
    elif score >= 80.0:
        grade = "B"
        status = "ACCEPTABLE (MINOR RISK)"
    elif score >= 70.0:
        grade = "C"
        status = "WARNING (MODERATE RISK)"
    elif score >= 60.0:
        grade = "D"
        status = "ELEVATED RISK"
    else:
        grade = "F"
        status = "CRITICAL RISK (IMMEDIATE ACTION REQUIRED)"

    # Compliance Benchmarking
    owasp_pass = (counts["Critical"] == 0 and counts["High"] <= 1)
    soc2_percent = max(0, min(100, int(score * 0.95)))
    iso27001_compliant = (score >= 80.0 and counts["Critical"] == 0)

    # Prioritized Remediation Roadmap
    remediation_tips = []
    if counts["Critical"] > 0:
        remediation_tips.append(
            f"URGENT: Remediate {counts['Critical']} CRITICAL finding(s) immediately (revoke leaked credentials or patch vulnerable packages)."
        )
    if counts["High"] > 0:
        remediation_tips.append(
            f"HIGH PRIORITY: Upgrade {counts['High']} dependency/credential issue(s) before deploying to production."
        )
    if counts["Medium"] > 0:
        remediation_tips.append(
            f"MAINTENANCE: Resolve {counts['Medium']} moderate vulnerability finding(s) in next development sprint."
        )
    if not remediation_tips:
        remediation_tips.append("No active vulnerabilities or secret leaks detected. Codebase hygiene is optimal.")

    return {
        "score": score,
        "grade": grade,
        "status": status,
        "counts": counts,
        "total_findings": len(findings),
        "compliance": {
            "owasp_top_10": "PASS" if owasp_pass else "FAIL",
            "soc_2_readiness_pct": soc2_percent,
            "iso_27001_baseline": "COMPLIANT" if iso27001_compliant else "NON-COMPLIANT"
        },
        "remediation_tips": remediation_tips
    }
