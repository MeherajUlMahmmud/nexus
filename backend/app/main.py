from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import logging
import os

from app.config import settings
from app.database import init_db
from app.api import auth, users, sessions, messages, models, transcribe
from app.middleware.security import SecurityMiddleware
from app.middleware.ip_blocking import IPBlockingMiddleware
from app.utils.redis_client import close_redis
from app.exceptions import (
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    BadRequestError,
    ConflictError,
    ValidationError
)
from app.utils.response import fail_response
from app.schemas.response import APIResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.environment == "development" else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down application...")
    await close_redis()
    logger.info("Redis connection closed")


# Create FastAPI app
app = FastAPI(
    title="Nexus",
    description="A comprehensive backend API for a ChatGPT-like web application",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add IP blocking middleware (check blocked IPs first, before other checks)
app.add_middleware(IPBlockingMiddleware)

# Add security middleware (check for sensitive URLs and track attempts)
app.add_middleware(SecurityMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return fail_response(
        message=exc.detail,
        status_code=exc.status_code
    )


@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request: Request, exc: UnauthorizedError):
    response = fail_response(
        message=exc.detail,
        status_code=exc.status_code
    )
    if exc.headers:
        response.headers.update(exc.headers)
    return response


@app.exception_handler(ForbiddenError)
async def forbidden_handler(request: Request, exc: ForbiddenError):
    return fail_response(
        message=exc.detail,
        status_code=exc.status_code
    )


@app.exception_handler(BadRequestError)
async def bad_request_handler(request: Request, exc: BadRequestError):
    return fail_response(
        message=exc.detail,
        status_code=exc.status_code
    )


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return fail_response(
        message=exc.detail,
        status_code=exc.status_code
    )


@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError):
    return fail_response(
        message=exc.detail,
        status_code=exc.status_code
    )


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors."""
    errors = exc.errors()
    error_messages = []
    for error in errors:
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "Validation error")
        error_messages.append(f"{field}: {msg}")
    
    message = "Validation error: " + "; ".join(error_messages)
    return fail_response(
        message=message,
        data={"errors": errors},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions."""
    return fail_response(
        message=exc.detail,
        status_code=exc.status_code
    )


# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(messages.router)
app.include_router(models.router)
app.include_router(transcribe.router)

# Serve uploaded files as static files
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/", tags=["Root"], response_model=APIResponse)
async def root():
    """Root endpoint."""
    logger.info("Root endpoint accessed")
    from app.utils.response import success_response
    return success_response(
        message="Nexus API",
        data={
            "version": "1.0.0",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    )


@app.get("/health", tags=["Health"], response_model=APIResponse)
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check endpoint accessed")
    from app.utils.response import success_response
    return success_response(
        message="Service is healthy",
        data={"status": "healthy"}
    )

