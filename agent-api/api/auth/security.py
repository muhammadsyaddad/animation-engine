"""
Minimal auth/security utilities for local development.

Features:
- Password hashing & verification using PBKDF2-HMAC-SHA256 (no external deps).
- JWT creation & decoding (HS256) without external libraries (manual implementation).
- Helper functions for access & refresh token generation.
- Random secure secret & salt utilities.

IMPORTANT:
- This is intended for LOCAL DEV ONLY.
- In production (e.g. Supabase), replace with provider-managed auth or
  use vetted libraries (e.g., passlib + PyJWT).
- PBKDF2 iterations kept moderate for dev speed; increase for production.

Suggested production improvements:
- Increase PBKDF2 iterations (e.g. 200_000 or higher).
- Use argon2 or bcrypt (passlib).
- Store password hash algorithm/version for future migrations.
- Rotate JWT secret periodically.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

# ------------------------------------------------------------------------------
# Password Hashing (PBKDF2-HMAC-SHA256)
# ------------------------------------------------------------------------------

PBKDF2_ITERATIONS = int(os.getenv("AUTH_PBKDF2_ITERATIONS", "50000"))  # increase for prod
PASSWORD_HASH_ALGO = "pbkdf2_sha256"


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def generate_salt(length: int = 16) -> str:
    """Generate cryptographically strong salt."""
    return secrets.token_hex(length)


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Hash password using PBKDF2-HMAC-SHA256.
    Stored format: algo$iterations$salt$hash
    """
    if salt is None:
        salt = generate_salt()
    if not password:
        raise ValueError("Password must not be empty")

    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    hashed = _b64_encode(dk)
    return f"{PASSWORD_HASH_ALGO}${PBKDF2_ITERATIONS}${salt}${hashed}"


def verify_password(password: str, stored: str) -> bool:
    """
    Verify password against stored hash.
    Accepts format produced by hash_password().
    """
    try:
        algo, iter_str, salt, stored_hash = stored.split("$", 3)
    except ValueError:
        return False
    if algo != PASSWORD_HASH_ALGO:
        return False
    try:
        iterations = int(iter_str)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    candidate = _b64_encode(dk)
    # Use hmac.compare_digest for constant-time comparison
    return hmac.compare_digest(candidate, stored_hash)


# ------------------------------------------------------------------------------
# JWT (HS256) Minimal Implementation
# ------------------------------------------------------------------------------

def _json_dumps(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _sign(message: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _base64url(sig)


def create_jwt(
    claims: Dict[str, Any],
    secret: str,
    expires_delta: Optional[timedelta] = None,
    issued_at: Optional[datetime] = None,
) -> str:
    """
    Create a HS256 JWT manually.
    Adds 'iat' and 'exp' automatically if expires_delta provided.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    if issued_at is None:
        issued_at = datetime.now(timezone.utc)
    payload = claims.copy()
    payload.setdefault("iat", int(issued_at.timestamp()))
    if expires_delta:
        exp = issued_at + expires_delta
        payload["exp"] = int(exp.timestamp())

    header_b64 = _base64url(_json_dumps(header).encode("utf-8"))
    payload_b64 = _base64url(_json_dumps(payload).encode("utf-8"))
    message = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature_b64 = _sign(message, secret)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


class JWTError(Exception):
    pass


class JWTExpiredError(JWTError):
    pass


def decode_jwt(token: str, secret: str, verify_exp: bool = True) -> Dict[str, Any]:
    """
    Decode and verify HS256 JWT. Raises JWTError/JWTExpiredError on failure.
    """
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        raise JWTError("Malformed token")

    message = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = _sign(message, secret)
    if not hmac.compare_digest(expected_sig, sig_b64):
        raise JWTError("Invalid signature")

    try:
        payload_json = _b64_decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)
    except Exception:
        raise JWTError("Invalid payload")

    if verify_exp and "exp" in payload:
        if int(time.time()) > int(payload["exp"]):
            raise JWTExpiredError("Token expired")

    return payload


# ------------------------------------------------------------------------------
# Token Helpers (Access / Refresh)
# ------------------------------------------------------------------------------

DEFAULT_ACCESS_MINUTES = int(os.getenv("AUTH_ACCESS_MINUTES", "1440"))
DEFAULT_REFRESH_DAYS = int(os.getenv("AUTH_REFRESH_DAYS", "7"))


def create_access_token(
    subject: str,
    secret: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    claims = {"sub": subject}
    if extra_claims:
        claims.update(extra_claims)
    exp_delta = timedelta(minutes=expires_minutes or DEFAULT_ACCESS_MINUTES)
    return create_jwt(claims, secret, expires_delta=exp_delta)


def create_refresh_token(
    subject: str,
    secret: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_days: Optional[int] = None,
) -> str:
    claims = {"sub": subject, "type": "refresh"}
    if extra_claims:
        claims.update(extra_claims)
    exp_delta = timedelta(days=expires_days or DEFAULT_REFRESH_DAYS)
    return create_jwt(claims, secret, expires_delta=exp_delta)


def rotate_tokens(
    subject: str,
    secret: str,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """
    Convenience: generate new (access, refresh) pair.
    """
    return (
        create_access_token(subject, secret, extra_claims),
        create_refresh_token(subject, secret, extra_claims),
    )


# ------------------------------------------------------------------------------
# Secrets & Utilities
# ------------------------------------------------------------------------------

def get_auth_secret() -> str:
    """
    Retrieve or generate an auth secret for signing JWTs.
    In production: set AUTH_SECRET env var.
    """
    secret = os.getenv("AUTH_SECRET")
    if not secret:
        # For local dev fallback (not secure for prod)
        secret = os.getenv("DEV_RANDOM_SECRET")
        if not secret:
            secret = secrets.token_urlsafe(48)
            # Not persisted; regenerate each process start.
    return secret


# ------------------------------------------------------------------------------
# Example usage (for documentation / testing)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    # Demo flow
    secret = get_auth_secret()
    pwd = "hunter2"
    stored = hash_password(pwd)
    assert verify_password("hunter2", stored)
    assert not verify_password("wrong", stored)

    access = create_access_token("user-123", secret)
    refresh = create_refresh_token("user-123", secret)
    decoded = decode_jwt(access, secret)
    print("Access token decoded:", decoded)
    print("Refresh token decoded:", decode_jwt(refresh, secret))
