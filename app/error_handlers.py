import logging
import uuid
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import AppException

logger = logging.getLogger("expense_app")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [ReqID: %(request_id)s] %(message)s",
)


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def create_error_response(status_code: int, code: str, message: str, request_id: str, details=None, headers=None):
    payload = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }
    if details:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=payload, headers=headers)


async def app_exception_handler(request: Request, exc: AppException):
    req_id = get_request_id(request)
    logger.warning("Application domain error: %s (%s)", exc.message, exc.code, extra={"request_id": req_id})
    return create_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=req_id,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = get_request_id(request)
    details = []
    for err in exc.errors():
        field_loc = " -> ".join(str(loc) for loc in err.get("loc", []) if loc != "body")
        details.append({
            "field": field_loc or "body",
            "message": err.get("msg", "Invalid input value."),
        })

    logger.info("Request validation failed on %s: %s", request.url.path, details, extra={"request_id": req_id})
    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Invalid request payload or query parameters.",
        request_id=req_id,
        details=details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id = get_request_id(request)
    return create_error_response(
        status_code=exc.status_code,
        code="HTTP_ERROR",
        message=str(exc.detail),
        request_id=req_id,
    )


async def db_operational_error_handler(request: Request, exc: OperationalError):
    req_id = get_request_id(request)
    logger.error("Database operational/lock failure: %s", str(exc), exc_info=True, extra={"request_id": req_id})
    return create_error_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="DATABASE_BUSY",
        message="Database is temporarily busy or unavailable. Please retry your request shortly.",
        request_id=req_id,
        headers={"Retry-After": "2"},
    )


async def global_exception_handler(request: Request, exc: Exception):
    req_id = get_request_id(request)
    # Log the complete stack trace alongside request_id for debugging
    logger.error("Unhandled internal exception: %s", str(exc), exc_info=True, extra={"request_id": req_id})
    # Shield internal implementation details from the client
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please provide the request_id to support.",
        request_id=req_id,
    )
    