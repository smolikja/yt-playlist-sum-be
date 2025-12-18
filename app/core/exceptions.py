"""
Custom exception classes and RFC 7807 error handling.
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict
from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorResponse(BaseModel):
    """RFC 7807 Problem Details response model."""
    type: str
    title: str
    status: int
    detail: str
    instance: Optional[str] = None
    
    model_config = ConfigDict(frozen=True)


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        status_code: int,
        error_type: str,
        title: str,
        detail: str,
    ):
        self.status_code = status_code
        self.error_type = error_type
        self.title = title
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppException):
    """Resource not found exception."""
    
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            status_code=404,
            error_type="https://problems.example.com/not-found",
            title="Resource Not Found",
            detail=f"{resource} with id '{resource_id}' was not found.",
        )


class ForbiddenError(AppException):
    """Access forbidden exception."""
    
    def __init__(self, detail: str = "You do not have permission to access this resource."):
        super().__init__(
            status_code=403,
            error_type="https://problems.example.com/forbidden",
            title="Forbidden",
            detail=detail,
        )


class BadRequestError(AppException):
    """Bad request exception."""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=400,
            error_type="https://problems.example.com/bad-request",
            title="Bad Request",
            detail=detail,
        )


class RateLimitError(AppException):
    """Rate limit exceeded exception."""
    
    def __init__(self, detail: str = "Rate limit exceeded. Please try again later."):
        super().__init__(
            status_code=429,
            error_type="https://problems.example.com/rate-limit-exceeded",
            title="Too Many Requests",
            detail=detail,
        )


class InternalServerError(AppException):
    """Internal server error exception."""
    
    def __init__(self, detail: str = "An unexpected error occurred."):
        super().__init__(
            status_code=500,
            error_type="https://problems.example.com/internal-error",
            title="Internal Server Error",
            detail=detail,
        )


def create_error_response(
    request: Request,
    status_code: int,
    error_type: str,
    title: str,
    detail: str,
) -> JSONResponse:
    """Create a RFC 7807 compliant JSON error response."""
    error = ErrorResponse(
        type=error_type,
        title=title,
        status=status_code,
        detail=detail,
        instance=str(request.url.path),
    )
    return JSONResponse(
        status_code=status_code,
        content=error.model_dump(),
        media_type="application/problem+json",
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle AppException and return RFC 7807 response."""
    return create_error_response(
        request=request,
        status_code=exc.status_code,
        error_type=exc.error_type,
        title=exc.title,
        detail=exc.detail,
    )
