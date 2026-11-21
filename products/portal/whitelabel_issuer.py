"""
IT Solutions Global — Cryptographic White-Label License Key Issuer & Verifier
100% Pure Python Standard Library.
Bit-for-bit compatible with client-side browser verifier in `company/growth/portal/whitelabel.js`.
"""

import sys
from typing import Dict, Any

VERIFY_PRIME_A = 0x811C9DC5
VERIFY_PRIME_B = 0x01000193
MASTER_NAMESPACE = "ITSG::WHITELABEL::2026::ENTERPRISE::v1"
VALID_TIERS = ("PRO", "AGENCY", "FIRM", "ENT")


def _imul32(a: int, b: int) -> int:
    """Emulates JavaScript Math.imul(a, b) >>> 0 in 32-bit unsigned arithmetic."""
    return ((a & 0xFFFFFFFF) * (b & 0xFFFFFFFF)) & 0xFFFFFFFF


def compute_signature(firm_code: str, tier_code: str = "PRO") -> str:
    """Computes the 8-character uppercase hex signature matching whitelabel.js."""
    clean_firm = firm_code.strip().upper()
    clean_tier = tier_code.strip().upper()
    raw = f"{MASTER_NAMESPACE}|{clean_firm}|{clean_tier}"

    h1 = VERIFY_PRIME_A & 0xFFFFFFFF
    h2 = 0x9E3779B9 & 0xFFFFFFFF

    for ch in raw:
        c = ord(ch)
        h1 = (h1 ^ c) & 0xFFFFFFFF
        h1 = _imul32(h1, VERIFY_PRIME_B)
        h2 = (_imul32((h2 ^ c) & 0xFFFFFFFF, 0x85EBCA6B) + 0xC2B2AE35) & 0xFFFFFFFF

    hex1 = f"{h1:08X}"
    hex2 = f"{h2:08X}"
    return f"{hex1[:4]}{hex2[:4]}"


def issue_whitelabel_key(firm_code: str, tier_code: str = "PRO") -> str:
    """Issues a signed White-Label license key: ITSG-WL-<TIER>-<FIRMCODE>-<SIG>."""
    clean_firm = "".join(ch for ch in firm_code.upper() if ch.isalnum())[:16]
    if len(clean_firm) < 2:
        raise ValueError("firm_code must contain at least 2 alphanumeric characters.")
    clean_tier = tier_code.strip().upper()
    if clean_tier not in VALID_TIERS:
        raise ValueError(f"tier_code must be one of {VALID_TIERS}")

    sig = compute_signature(clean_firm, clean_tier)
    return f"ITSG-WL-{clean_tier}-{clean_firm}-{sig}"


def verify_whitelabel_key(key_str: str) -> Dict[str, Any]:
    """Verifies a White-Label license key string."""
    if not key_str or not isinstance(key_str, str):
        return {"valid": False, "reason": "Empty license key"}
    parts = key_str.strip().upper().split("-")
    if len(parts) != 5 or parts[0] != "ITSG" or parts[1] != "WL":
        return {"valid": False, "reason": "Invalid format"}
    tier, firm_code, sig = parts[2], parts[3], parts[4]
    if tier not in VALID_TIERS:
        return {"valid": False, "reason": "Invalid tier"}
    if not (2 <= len(firm_code) <= 16):
        return {"valid": False, "reason": "Invalid firm code length"}
    expected = compute_signature(firm_code, tier)
    if sig != expected:
        return {"valid": False, "reason": "Signature mismatch"}
    return {"valid": True, "tier": tier, "firm_code": firm_code, "signature": sig}


if __name__ == "__main__":
    firm = sys.argv[1] if len(sys.argv) > 1 else "APEXLEGAL"
    tier = sys.argv[2] if len(sys.argv) > 2 else "PRO"
    key = issue_whitelabel_key(firm, tier)
    print(f"Issued Key for {firm} ({tier}): {key}")
    print("Verification:", verify_whitelabel_key(key))
