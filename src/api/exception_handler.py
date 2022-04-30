"""Custom exception handlers"""
# pylint: disable=unused-argument

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


async def default_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """overriding default_exception_handler"""
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": str(exc)},
    )
