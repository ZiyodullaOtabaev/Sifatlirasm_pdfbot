"""
Stateless HMAC-SHA256 JWT authentication for Sifatli PDF Mobile API & Super Admin.
Zero external crypto/JWT library dependencies required.
"""
import hmac
import json
import time
import base64
import hashlib
from typing import Optional, Dict, Any

from bot.config import API_SECRET, SUPER_ADMIN_PASSWORD


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("ascii"))


def create_jwt(payload: Dict[str, Any], ttl_seconds: int = 365 * 86400) -> str:
    """Create a signed HS256 JWT token."""
    header = {"alg": "HS256", "typ": "JWT"}
    body = dict(payload)
    now = int(time.time())
    body.setdefault("iat", now)
    body["exp"] = now + ttl_seconds

    h_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p_b64 = _b64url_encode(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{h_b64}.{p_b64}".encode("ascii")

    sig = hmac.new(API_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{h_b64}.{p_b64}.{_b64url_encode(sig)}"


def verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Verify HS256 JWT signature and expiration. Returns payload dict or None."""
    if not token or token.count(".") != 2:
        return None
    try:
        h_b64, p_b64, s_b64 = token.split(".")
        signing_input = f"{h_b64}.{p_b64}".encode("ascii")
        expected_sig = hmac.new(API_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(s_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(p_b64).decode("utf-8"))
        exp = int(payload.get("exp", 0))
        if exp and int(time.time()) > exp:
            return None
        return payload
    except Exception:
        return None


def verify_super_admin_password(password: str) -> bool:
    """Constant-time verification of Super Admin password."""
    if not password or not SUPER_ADMIN_PASSWORD:
        return False
    return hmac.compare_digest(password.strip().encode("utf-8"), SUPER_ADMIN_PASSWORD.encode("utf-8"))
