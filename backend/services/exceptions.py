"""
Custom exceptions for the backend services.
"""

from typing import Optional


class AppError(Exception):
    """Base class for application-specific exceptions."""

    status_code = 500
    default_message = "An unexpected error occurred."

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or self.default_message)
        self.message = message or self.default_message


class ValidationError(AppError):
    """Exception raised for validation errors."""

    status_code = 400
    default_message = "Validation error."


class ConflictError(AppError):
    """Exception raised for conflicts, such as duplicate entries."""

    status_code = 409
    default_message = "Conflict error."


class NotFoundError(AppError):
    """Exception raised when a requested resource is not found."""

    status_code = 404
    default_message = "Resource not found."


class ForbiddenError(AppError):
    """Exception raised for forbidden actions."""

    status_code = 403
    default_message = "Forbidden."

class AuthError(AppError):
    """Exception raised when authentication credentials are invalid."""

    status_code = 401
    default_message = "Invalid credentials."
