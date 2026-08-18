"""Shared FastAPI dependencies: current user, role guards, pagination."""

from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models import Driver, User, UserRole
from app.services import driver_service

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Not authenticated")

    payload = decode_token(credentials.credentials, expected_type="access")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise AuthenticationError("User no longer exists")
    if not user.is_active:
        raise AuthenticationError("This account has been deactivated",
                                  code="account_disabled")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_fleet_manager(user: CurrentUser) -> User:
    if user.role != UserRole.FLEET_MANAGER:
        raise PermissionDeniedError("This action requires the fleet manager role")
    return user


def require_driver(user: CurrentUser) -> User:
    if user.role != UserRole.DRIVER:
        raise PermissionDeniedError("This action requires the driver role")
    return user


FleetManager = Annotated[User, Depends(require_fleet_manager)]
DriverUser = Annotated[User, Depends(require_driver)]


def get_current_driver(db: DbSession, user: DriverUser) -> Driver:
    """The driver profile linked to the authenticated driver account."""
    return driver_service.get_driver_for_user(db, user)


CurrentDriver = Annotated[Driver, Depends(get_current_driver)]


class Pagination:
    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ):
        self.limit = limit
        self.offset = offset


Paging = Annotated[Pagination, Depends(Pagination)]
