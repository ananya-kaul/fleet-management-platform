from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models import Driver, User
from app.schemas.auth import (
    AccessToken,
    ChangePasswordRequest,
    ConfirmResetRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    ResetTokenResponse,
    TokenPair,
    UserCreate,
    UserRead,
)
from app.schemas.common import Message
from app.services import auth_service
from app.services.auth_service import RESET_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_user_read(db, user: User) -> UserRead:
    driver = db.query(Driver).filter(Driver.user_id == user.id).one_or_none()
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        driver_id=driver.id if driver else None,
    )


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession) -> TokenPair:
    user = auth_service.register_user(db, payload)
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_to_user_read(db, user),
    )


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: DbSession) -> TokenPair:
    user = auth_service.authenticate(db, payload.email, payload.password)
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_to_user_read(db, user),
    )


@router.post("/refresh", response_model=AccessToken)
def refresh(payload: RefreshRequest, db: DbSession) -> AccessToken:
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        from app.core.errors import AuthenticationError

        raise AuthenticationError("Could not refresh this session")
    return AccessToken(access_token=create_access_token(user.id))


@router.post("/logout", response_model=Message)
def logout(_: CurrentUser) -> Message:
    """Stateless JWT logout.

    The client discards its tokens. Access tokens are short lived, so no
    server-side revocation list is kept; adding one would mean persisting a
    denylist keyed by the token's jti.
    """
    return Message(detail="Signed out")


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser, db: DbSession) -> UserRead:
    return _to_user_read(db, user)


@router.post("/change-password", response_model=Message)
def change_password(
    payload: ChangePasswordRequest, user: CurrentUser, db: DbSession
) -> Message:
    auth_service.change_password(db, user, payload.current_password, payload.new_password)
    return Message(detail="Password updated")


@router.post("/forgot-password", response_model=ResetTokenResponse)
def forgot_password(payload: ResetPasswordRequest, db: DbSession) -> ResetTokenResponse:
    token = auth_service.create_reset_token(db, payload.email)
    return ResetTokenResponse(
        reset_token=token, expires_in_minutes=RESET_TOKEN_EXPIRE_MINUTES
    )


@router.post("/reset-password", response_model=Message)
def reset_password(payload: ConfirmResetRequest, db: DbSession) -> Message:
    auth_service.confirm_reset(db, payload.reset_token, payload.new_password)
    return Message(detail="Password reset")
