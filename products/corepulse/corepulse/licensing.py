"""
CorePulse Cryptographic Licensing Engine (Q1 2027 Open-Core Architecture)
Implements offline cryptographic license key generation, signature verification,
and tier activation using HMAC-SHA256 signatures.
Zero external pip dependencies. Pure Python standard library (hmac, hashlib, base64, json).
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from corepulse.config import TIER_FEATURE_GATES

logger = logging.getLogger("corepulse.licensing")

# Master signing secret (Can be overridden by corporate root environment variable)
DEFAULT_MASTER_SECRET = "IT_SOLUTIONS_CORP_COREPULSE_MASTER_SALT_2026_Q4"


def _get_signing_secret(custom_secret: Optional[str] = None) -> bytes:
    """Returns the master signing secret key in bytes."""
    secret_str = custom_secret or os.getenv("COREPULSE_LICENSE_SECRET", DEFAULT_MASTER_SECRET)
    return secret_str.encode("utf-8")


def _b64_url_encode(data_bytes: bytes) -> str:
    """Encodes bytes to unpadded URL-safe base64 string."""
    return base64.urlsafe_b64encode(data_bytes).decode("ascii").rstrip("=")


def _b64_url_decode(encoded_str: str) -> bytes:
    """Decodes unpadded URL-safe base64 string into bytes."""
    padding = "=" * ((4 - len(encoded_str) % 4) % 4)
    return base64.urlsafe_b64decode((encoded_str + padding).encode("ascii"))


class LicenseEngine:
    """
    Enterprise Offline Cryptographic Licensing Engine.
    Handles cryptographic license generation, tamper-proof verification,
    and automatic database activation across SQLite and JSON state stores.
    """

    def __init__(self, secret: Optional[str] = None):
        self.secret = secret

    def generate_license_key(
        self,
        tier: str,
        customer_name: str = "Executive User",
        organization: str = "Enterprise Corp",
        days_valid: Optional[int] = 365,
        seats: Optional[int] = None,
        secret: Optional[str] = None
    ) -> str:
        """
        Generates a signed, offline verifiable cryptographic license key.
        Format: CP-<TIER>-<PAYLOAD_B64>-<SIGNATURE_HEX>
        """
        tier_key = tier.lower().strip()
        if tier_key not in TIER_FEATURE_GATES:
            raise ValueError(f"Invalid tier '{tier}'. Must be one of: {list(TIER_FEATURE_GATES.keys())}")

        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=days_valid)).isoformat() if days_valid is not None else None

        # Determine seats
        if seats is None:
            seats = TIER_FEATURE_GATES[tier_key].get("seats", 1)

        payload = {
            "lid": f"cp-lic-{uuid.uuid4().hex[:12].upper()}",
            "tier": tier_key,
            "sub": customer_name.strip(),
            "org": organization.strip(),
            "iat": now.isoformat(),
            "exp": expires_at,
            "seats": seats,
            "ver": "1.0"
        }

        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        payload_b64 = _b64_url_encode(payload_json.encode("utf-8"))

        # Compute HMAC-SHA256 signature
        secret_bytes = _get_signing_secret(secret or self.secret)
        sign_target = f"CP:{tier_key.upper()}:{payload_b64}".encode("utf-8")
        signature_hex = hmac.new(secret_bytes, sign_target, hashlib.sha256).hexdigest()[:32]

        return f"CP-{tier_key.upper()}-{payload_b64}-{signature_hex}"

    def verify_license_key(self, key: str, secret: Optional[str] = None) -> Dict[str, Any]:
        """
        Verifies cryptographic integrity, signature, and expiration of a license key.
        Returns validation result dict.
        """
        if not key or not isinstance(key, str):
            return {"valid": False, "error": "License key must be a non-empty string."}

        parts = key.strip().split("-")
        if len(parts) < 4 or parts[0] != "CP":
            return {
                "valid": False,
                "error": "Invalid license key format. Expected format: CP-<TIER>-<PAYLOAD>-<SIGNATURE>"
            }

        prefix = parts[0]
        tier_from_key = parts[1].lower()
        payload_b64 = parts[2]
        sig_provided = parts[3]

        if tier_from_key not in TIER_FEATURE_GATES:
            return {"valid": False, "error": f"Unknown subscription tier '{parts[1]}' in license key."}

        # Verify signature
        secret_bytes = _get_signing_secret(secret or self.secret)
        sign_target = f"CP:{tier_from_key.upper()}:{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(secret_bytes, sign_target, hashlib.sha256).hexdigest()[:32]

        if not hmac.compare_digest(expected_sig.lower(), sig_provided.lower()):
            return {
                "valid": False,
                "error": "Cryptographic signature mismatch. The license key has been tampered with or corrupted."
            }

        # Decode payload
        try:
            payload_raw = _b64_url_decode(payload_b64).decode("utf-8")
            payload = json.loads(payload_raw)
        except Exception as ex:
            return {"valid": False, "error": f"Failed to parse license payload: {ex}"}

        # Check payload tier consistency
        if payload.get("tier", "").lower() != tier_from_key:
            return {"valid": False, "error": "Internal payload tier does not match license key header."}

        # Check expiration date
        exp_str = payload.get("exp")
        if exp_str:
            try:
                exp_dt = datetime.fromisoformat(exp_str)
                if datetime.now(timezone.utc) > exp_dt:
                    return {
                        "valid": False,
                        "error": f"License expired on {exp_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}.",
                        "expired": True,
                        "payload": payload,
                        "tier": tier_from_key
                    }
            except Exception:
                pass

        return {
            "valid": True,
            "tier": tier_from_key,
            "payload": payload,
            "key": key.strip(),
            "features": TIER_FEATURE_GATES.get(tier_from_key, {}),
            "error": None
        }

    def get_active_license(self) -> Dict[str, Any]:
        """
        Retrieves active license metadata, subscription tier, and feature gates
        from the persistent CorePulse storage backend.
        """
        try:
            from corepulse.database_sqlite import sqlite_db
            sub = sqlite_db.get_subscription()
        except Exception:
            try:
                from corepulse.database import db
                sub = db.get_subscription()
            except Exception as ex:
                sub = {
                    "tier": "starter",
                    "status": "active",
                    "customer_name": "Community User",
                    "organization": "Open Source",
                    "license_key": None,
                    "renews_at": None,
                    "features": TIER_FEATURE_GATES["starter"]
                }
        return sub

    def activate_license_key(self, key: str, secret: Optional[str] = None) -> Dict[str, Any]:
        """
        Verifies and activates a cryptographic license key, updating both SQLite
        and JSON state persistence stores.
        """
        verification = self.verify_license_key(key, secret=secret)
        if not verification.get("valid"):
            err_msg = verification.get("error", "Invalid license key.")
            logger.warning("License activation rejected: %s", err_msg)
            return {
                "success": False,
                "error": err_msg,
                "key": key
            }

        payload = verification["payload"]
        tier = verification["tier"]
        customer_name = payload.get("sub", "Executive User")
        organization = payload.get("org", "Enterprise Corp")
        expires_at = payload.get("exp")

        # 1. Update SQLite Database
        sqlite_ok = False
        try:
            from corepulse.database_sqlite import sqlite_db
            sqlite_db.upgrade_subscription(
                tier=tier,
                customer_name=customer_name,
                organization=organization,
                license_key=key.strip(),
                renews_at=expires_at
            )
            sqlite_ok = True
        except Exception as ex:
            logger.warning("Failed to update SQLite subscription: %s", ex)

        # 2. Update JSON State Store
        json_ok = False
        try:
            from corepulse.database import db
            db.upgrade_subscription(
                tier=tier,
                customer_name=customer_name,
                organization=organization,
                license_key=key.strip(),
                renews_at=expires_at
            )
            json_ok = True
        except Exception as ex:
            logger.warning("Failed to update JSON store subscription: %s", ex)

        features = TIER_FEATURE_GATES.get(tier, {})
        logger.info("Successfully activated '%s' license for %s (%s)", tier.upper(), customer_name, organization)

        return {
            "success": True,
            "tier": tier,
            "customer_name": customer_name,
            "organization": organization,
            "license_id": payload.get("lid"),
            "expires_at": expires_at,
            "features": features,
            "storage_updated": {"sqlite": sqlite_ok, "json": json_ok},
            "summary": f"✔ CorePulse {features.get('name', tier.title())} tier activated successfully."
        }


# Singleton Engine Instance
default_engine = LicenseEngine()

# Module-Level Convenience Functions
def generate_license_key(
    tier: str,
    customer_name: str = "Executive User",
    organization: str = "Enterprise Corp",
    days_valid: Optional[int] = 365,
    seats: Optional[int] = None,
    secret: Optional[str] = None
) -> str:
    """Generates a cryptographic license key."""
    return default_engine.generate_license_key(
        tier=tier,
        customer_name=customer_name,
        organization=organization,
        days_valid=days_valid,
        seats=seats,
        secret=secret
    )


def verify_license_key(key: str, secret: Optional[str] = None) -> Dict[str, Any]:
    """Verifies a cryptographic license key."""
    return default_engine.verify_license_key(key, secret=secret)


def get_active_license() -> Dict[str, Any]:
    """Queries active license and subscription details."""
    return default_engine.get_active_license()


def activate_license_key(key: str, secret: Optional[str] = None) -> Dict[str, Any]:
    """Verifies and activates a cryptographic license key."""
    return default_engine.activate_license_key(key, secret=secret)
