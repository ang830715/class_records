from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from os import getenv
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

PASSWORD_ITERATIONS = 260_000
TOKEN_TTL_HOURS = int(getenv("AUTH_TOKEN_TTL_HOURS", "168"))
AUTH_SECRET = getenv("AUTH_SECRET", "dev-only-change-me")

bearer_scheme = HTTPBearer(auto_error=False)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, iterations_text, salt_text, digest_text = stored_hash.split("$", maxsplit=3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        expected = _b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _b64decode(salt_text), iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user: User) -> str:
    expires_at = datetime.now(UTC) + timedelta(hours=TOKEN_TTL_HOURS)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": int(expires_at.timestamp()),
        "nonce": secrets.token_urlsafe(12),
    }
    payload_text = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), payload_text.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_text}.{_b64encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload_text, signature_text = token.split(".", maxsplit=1)
        expected = hmac.new(AUTH_SECRET.encode("utf-8"), payload_text.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64decode(signature_text)):
            raise ValueError
        payload = json.loads(_b64decode(payload_text))
        if int(payload["exp"]) < int(datetime.now(UTC).timestamp()):
            raise ValueError
        return payload
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
