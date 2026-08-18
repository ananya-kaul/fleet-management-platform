"""Registration, login and password lifecycle."""

from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AuthenticationError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.security import decode_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import UserCreate

logger = get_logger(__name__)

RESET_TOKEN_EXPIRE_MINUTES = 30


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def register_user(db: Session, payload: UserCreate) -> User:
    if get_user_by_email(db, payload.email):
        raise ConflictError("An account with this email already exists", code="email_taken")

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Registered user id=%s role=%s", user.id, user.role)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    # Compare against a dummy hash when the user is missing so a bad email and a
    # bad password take the same amount of time.
    if user is None:
        verify_password(password, "$2b$12$" + "0" * 53)
        raise AuthenticationError("Incorrect email or password")

    if not verify_password(password, user.hashed_password):
        raise AuthenticationError("Incorrect email or password")

    if not user.is_active:
        raise AuthenticationError("This account has been deactivated", code="account_disabled")

    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise AuthenticationError("Current password is incorrect")

    user.hashed_password = hash_password(new_password)
    db.commit()
    logger.info("Password changed for user id=%s", user.id)


def create_reset_token(db: Session, email: str) -> str:
    user = get_user_by_email(db, email)
    if user is None:
        # Do not leak which emails are registered.
        raise NotFoundError("If that account exists, a reset link has been sent")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "type": "reset",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def confirm_reset(db: Session, reset_token: str, new_password: str) -> None:
    payload = decode_token(reset_token, expected_type="reset")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise AuthenticationError("Invalid reset token")

    user.hashed_password = hash_password(new_password)
    db.commit()
    logger.info("Password reset completed for user id=%s", user.id)
