import uuid
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import Base, engine
from app.error_handlers import (
    app_exception_handler,
    db_operational_error_handler,
    global_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.exceptions import AppException
from app.routers import expenses

# Ensure DB tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)


# Correlation / Trace ID Middleware
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Centralized Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(OperationalError, db_operational_error_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Include Routers
app.include_router(expenses.router)