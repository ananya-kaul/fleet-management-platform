from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    role: UserRole = UserRole.DRIVER


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    driver_id: int | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ResetPasswordRequest(BaseModel):
    """Password reset for an account the caller can prove ownership of.

    A production deployment would email a signed, single-use token; the reset
    token issued here is the same signed JWT so the flow is identical.
    """

    email: EmailStr


class ResetTokenResponse(BaseModel):
    reset_token: str
    expires_in_minutes: int


class ConfirmResetRequest(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8, max_length=128)
