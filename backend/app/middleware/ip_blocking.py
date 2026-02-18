import logging
from typing import Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.database import AsyncSessionLocal
from app.services.ip_blocking import IPBlockingService

logger = logging.getLogger(__name__)


class IPBlockingMiddleware(BaseHTTPMiddleware):
    """Middleware to check if IP is blocked and deny access."""

    def __init__(self, app, ip_blocking_service: IPBlockingService = None):
        super().__init__(app)
        self.ip_blocking_service = ip_blocking_service or IPBlockingService()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Skip blocking check for localhost/127.0.0.1 in development
        if client_ip in ["127.0.0.1", "localhost", "::1"]:
            response = await call_next(request)
            return response

        # Check if IP is blocked
        async with AsyncSessionLocal() as db:
            try:
                blocked_ip = await self.ip_blocking_service.is_ip_blocked(db, client_ip)
                if blocked_ip:
                    logger.warning(
                        f"Blocked IP {client_ip} attempted to access: {request.url.path} "
                        f"User-Agent: {request.headers.get('user-agent', 'unknown')}"
                    )

                    # Return 401 Unauthorized
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={
                            "detail": "Unauthorized",
                            "message": "Your IP address has been blocked due to suspicious activity."
                        }
                    )
            except Exception as e:
                logger.error(f"Error checking IP block status for {client_ip}: {str(e)}")
                # On error, allow the request to proceed (fail open)

        # If not blocked, continue with the request
        response = await call_next(request)
        return response
