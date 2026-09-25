from __future__ import annotations

from typing import Any


class AppException(Exception):
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            error_code='NOT_FOUND',
            message=f'{resource} not found',
            status_code=404,
            details={'resource': resource, 'identifier': str(identifier)},
        )


class ValidationError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            error_code='VALIDATION_ERROR',
            message=message,
            status_code=422,
            details=details,
        )


class ConflictError(AppException):
    def __init__(self, resource: str, message: str):
        super().__init__(
            error_code='CONFLICT',
            message=message,
            status_code=409,
            details={'resource': resource},
        )


class UnauthorizedError(AppException):
    def __init__(self, message: str = 'Unauthorized'):
        super().__init__(
            error_code='UNAUTHORIZED',
            message=message,
            status_code=401,
        )


class ForbiddenError(AppException):
    def __init__(self, message: str = 'Forbidden'):
        super().__init__(
            error_code='FORBIDDEN',
            message=message,
            status_code=403,
        )
