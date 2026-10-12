from typing import Any, Optional


class AppException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "BAD_REQUEST",
        status_code: int = 400,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
            details=details,
        )


class ForbiddenException(AppException):
    def __init__(self, message: str = "Access forbidden", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
            details=details,
        )


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=details,
        )
