"""
Middleware que registra cada petición HTTP recibida en la tabla api_logs.
Sirve para auditar cuántas veces escribe el ESP32 y detectar caídas
de conexión (si dejan de llegar peticiones).
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.database import SessionLocal
from app.models.api_log import ApiLog


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        db = SessionLocal()
        try:
            log = ApiLog(
                endpoint=request.url.path,
                metodo=request.method,
                ip_origen=request.client.host if request.client else None,
                status_code=response.status_code,
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        return response
