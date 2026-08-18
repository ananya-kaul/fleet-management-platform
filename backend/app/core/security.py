"""Password hashing and JWT issuing/verification."""

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import AuthenticationError

TokenType = Literal["access", "refresh"]


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        # Malformed hash in the database - treat as a failed login, never a 500.
        return False


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str | int) -> str:
    return _create_token(
        str(subject), "access", timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(subject: str | int) -> str:
    return _create_token(
        str(subject), "refresh", timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str, expected_type: TokenType = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Could not validate credentials") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError(f"Expected a {expected_type} token")

    return payload
