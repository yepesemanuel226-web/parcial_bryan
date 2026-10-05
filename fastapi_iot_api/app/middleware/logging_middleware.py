"""
Middleware que registra cada petición HTTP en la consola.
La tabla api_logs fue reemplazada por logs de consola en la nueva BD.
"""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("api")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        ip = request.client.host if request.client else "-"
        logger.info(f"{request.method} {request.url.path} {response.status_code} [{ip}]")
        return response
