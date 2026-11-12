"""
ClauseGuard v1.2 - Local-First Contract, NDA & Legal Redline Risk Scanner
Detects predatory legal clauses (Uncapped Liability, Auto-Renewal Traps, Broad IP Grabs,
Non-Compete Overreach, Net-90 Payment Delays, SOW Scope Creep) 100% offline,
generates word-level visual redlines ([-deleted-] / {+proposed+}), and drafts collaborative
negotiation cover letters.

Honesty Guard: Automated heuristic review — not legal advice.
Have a qualified lawyer review important agreements.
"""

from clauseguard.negotiator import NegotiationDrafter
from clauseguard.scanner import ContractRiskScanner

__product__ = "ClauseGuard"
__version__ = "1.2.0"
__tagline__ = "Local-First Contract, NDA & Legal Redline Risk Scanner"

__all__ = [
    "ContractRiskScanner",
    "NegotiationDrafter",
    "__product__",
    "__version__",
    "__tagline__"
]
