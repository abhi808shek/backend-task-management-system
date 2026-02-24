from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Any, Optional


def success(data: Any, message: str = "Success", status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status_code,
            "success": True,
            "message": message,
            "data": data,
        },
    )


def error(message: str, status_code: int, data: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status_code,
            "success": False,
            "message": message,
            "data": data,
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Catches all HTTPException (404, 403, 401, 400, 500) and wraps them."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "success": False,
            "message": exc.detail,
            "data": None,
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Catches Pydantic 422 validation errors.
    Returns ONE clean response instead of FastAPI's default verbose format.
    """
    # Extract first error message cleanly
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = " → ".join(str(l) for l in first.get("loc", []) if l != "body")
    message = f"Validation error on '{field}': {first.get('msg', 'Invalid input')}" if field else first.get("msg", "Invalid input")

    return JSONResponse(
        status_code=422,
        content={
            "status": 422,
            "success": False,
            "message": message,
            "data": None,
        },
    )