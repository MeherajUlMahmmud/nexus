import logging
import re
import asyncio
from typing import Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.database import AsyncSessionLocal
from app.services.ip_blocking import IPBlockingService

logger = logging.getLogger(__name__)

# Sensitive patterns for URL blocking
SENSITIVE_URL_PATTERNS = [
    # Original patterns
    r'\.env',
    r'\.git',
    r'\.htaccess',
    r'wp-config\.php',
    r'config\.php',
    r'\.sql',
    r'\.bak',
    r'\.old',
    r'\.backup',
    r'\.swp',
    r'\.config',
    r'geoserver',
    r'nginx',
    r'webui',
    r's3',
    r'configs',
    r'k8s',
    r'subdomains',

    # Config and credential files
    r'\.aws',
    r'aws[-_]config',
    r'aws[-_]credentials',
    r'credentials\.(json|yml|yaml|xml|ini|csv)',
    r'config\.(js|json|yml|yaml|xml|ini|env|php|conf|toml)',
    r'\.circleci',
    r'\.github/workflows',
    r'\.gitlab-ci',
    r'\.terraformrc',
    r'\.tfvars',
    r'terraform',
    r'secrets\.',
    r'parameters\.(yml|yaml|xml|json|ini)',
    r'sendgrid[-_]keys',
    r'\.kube/config',
    r'\.env\.',
    r'\.env[-_]',
    r'env\..*',
    r'\.production',
    r'\.dockerenv',

    # Database and admin access
    r'phpmyadmin',
    r'php.*info',
    r'info\.php',
    r'db(admin|web|manager)',
    r'mysql(admin|manager)',
    r'adminer\.php',
    r'sqladmin',
    r'wp-admin',
    r'administrator',
    r'admin\.php',

    # System/file access attempts
    r'\.ssh',
    r'\.vscode',
    r'_profiler',
    r'\.svn',
    r'\.idea',
    r'\.DS_Store',
    r'actuator',
    r'solr/admin',
    r'jenkins',
    r'hudson',
    r'console',
    r'wp-content',
    r'wp-includes',

    # API and web vulnerabilities
    r'cgi-bin',
    r'owa/auth',
    r'dana-na',
    r'boaform',
    r'HNAP1',
    r'phpunit',
    r'eval-stdin\.php',
    r'api/sonicos',
    r'Autodiscover',
    r'wp-json',
    r'rest/applinks',
    r'confluence/rest',
    r'Telerik\.Web\.UI',
    r'vendor/phpunit',
    r'ckeditor',
    r'portal/redlion',
    r'nmaplowercheck',
    r'logincheck',

    # Cloud metadata access attempts
    r'latest/meta-data',
    r'169\.254\.169\.254',

    # WebShells/Backdoors
    r'(sh|up|tz|token|time|test.*|temp|old_phpinfo|lindex|jo|inf|in|i)\.php$',

    # Server Status and Diagnostics
    r'server[-_]status',
    r'status\.php',
    r'server[-_]info',

    # Docker/Kubernetes
    r'docker[-_]',
    r'containers/json',
    r'pools/default/buckets',

    # Authentication endpoints
    r'login\.(php|jsp|do|action|htm|html|aspx|cc)',
    r'logon\.',
    r'auth\.',
    r'j_spring_security_check',
    r'identity',
]

# Compile regex patterns for better performance
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in SENSITIVE_URL_PATTERNS]


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware to block access to sensitive URLs and track attempts."""

    def __init__(self, app, ip_blocking_service: IPBlockingService = None):
        super().__init__(app)
        self.ip_blocking_service = ip_blocking_service or IPBlockingService()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get the request path
        path = request.url.path
        query_string = str(request.url.query)
        full_path = f"{path}?{query_string}" if query_string else path

        # Get client IP and user agent
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get('user-agent', 'unknown')

        # Check against sensitive patterns
        for pattern in COMPILED_PATTERNS:
            if pattern.search(full_path):
                # Log the attempt
                logger.warning(
                    f"Sensitive URL access attempt detected: {full_path} "
                    f"from IP: {client_ip} "
                    f"User-Agent: {user_agent}"
                )

                # Track the attempt in Redis (with timeout to prevent hanging)
                try:
                    should_block = await asyncio.wait_for(
                        self.ip_blocking_service.track_sensitive_url_attempt(client_ip, user_agent),
                        timeout=1.0  # 1 second timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Redis operation timeout for IP {client_ip}, continuing without blocking")
                    should_block = False
                except Exception as e:
                    logger.error(f"Error tracking sensitive URL attempt: {str(e)}")
                    should_block = False

                # If threshold reached, block the IP in database
                if should_block:
                    async with AsyncSessionLocal() as db:
                        try:
                            await self.ip_blocking_service.block_ip(
                                db=db,
                                ip_address=client_ip,
                                user_agent=user_agent,
                                reason=f"Sensitive URL access attempts: {full_path}"
                            )
                        except Exception as e:
                            logger.error(f"Error blocking IP {client_ip}: {str(e)}")

                # Return 404 Not Found (to not reveal that we're blocking)
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"detail": "Not Found"}
                )

        # If no sensitive pattern matched, continue with the request
        response = await call_next(request)
        return response
