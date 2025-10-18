"""
Service layer exception hierarchy.

Provides HTTP-agnostic error classes that carry enough context for the
router layer to convert them into proper HTTP responses.
"""

from __future__ import annotations

from fastapi import status


class ServiceError(Exception):
    """Base exception for service layer failures."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str, *, status_code: int | None = None) -> None:
        super().__init__(detail)
        if status_code is not None:
            self.status_code = status_code
        self.detail = detail


class NotFoundError(ServiceError):
    """Raised when a requested entity cannot be located."""

    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, detail: str = "Requested resource was not found.") -> None:
        super().__init__(detail)


class ValidationError(ServiceError):
    """Raised when service input fails validation."""

    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str = "Request validation failed.") -> None:
        super().__init__(detail)


class ConflictError(ServiceError):
    """Raised when the requested operation conflicts with current state."""

    status_code = status.HTTP_409_CONFLICT

    def __init__(self, detail: str = "Resource is in a conflicting state.") -> None:
        super().__init__(detail)


class AuthorizationError(ServiceError):
    """Raised when the caller lacks sufficient permissions."""

    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, detail: str = "You do not have permission to perform this action.") -> None:
        super().__init__(detail)


__all__ = [
    "ServiceError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "AuthorizationError",
]
