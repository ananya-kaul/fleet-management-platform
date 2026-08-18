"""Domain-level exceptions mapped to HTTP responses by the app error handlers."""

from fastapi import status


class AppError(Exception):
    """Base class for expected, user-facing failures."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    """Raised when a request violates a business invariant."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_failed"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"
