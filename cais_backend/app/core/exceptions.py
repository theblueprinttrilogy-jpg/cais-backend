"""
Core Exceptions - Custom Application Exceptions

This module defines custom exceptions for the CAIS Code Compliance system.
"""

from typing import Optional


class AppException(Exception):
    """
    Base application exception.

    Attributes:
        status_code: HTTP status code
        message: Error message
        code: Error code
    """

    def __init__(
        self,
        status_code: int = 500,
        message: str = "Internal server error",
        code: str = "INTERNAL_ERROR"
    ):
        self.status_code = status_code
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundException(AppException):
    """Resource not found exception (404)."""

    def __init__(self, resource: str = "Resource", id: Optional[str] = None):
        message = f"{resource} not found"
        if id:
            message = f"{resource} with id '{id}' not found"
        super().__init__(status_code=404, message=message, code="NOT_FOUND")


class ValidationException(AppException):
    """Validation error exception (400)."""

    def __init__(self, message: str = "Validation error"):
        super().__init__(status_code=400, message=message, code="VALIDATION_ERROR")


class UnauthorizedException(AppException):
    """Unauthorized access exception (401)."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(status_code=401, message=message, code="UNAUTHORIZED")


class ForbiddenException(AppException):
    """Forbidden access exception (403)."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(status_code=403, message=message, code="FORBIDDEN")


class ConflictException(AppException):
    """Conflict exception (409)."""

    def __init__(self, message: str = "Conflict"):
        super().__init__(status_code=409, message=message, code="CONFLICT")


class PaymentRequiredException(AppException):
    """Payment required exception (402)."""

    def __init__(self, message: str = "Payment required"):
        super().__init__(status_code=402, message=message, code="PAYMENT_REQUIRED")


class ServiceUnavailableException(AppException):
    """Service unavailable exception (503)."""

    def __init__(self, message: str = "Service unavailable"):
        super().__init__(status_code=503, message=message, code="SERVICE_UNAVAILABLE")
