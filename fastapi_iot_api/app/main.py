from fastapi import FastAPI

from app.core.config import settings
from app.middleware.logging_middleware import LoggingMiddleware
from app.routers import lecturas, dispositivos

app = FastAPI(
    title=settings.proyecto_nombre,
    description="API REST que recibe datos del ESP32 (DS18B20 + sensor de humedad "
    "de suelo capacitivo v2.0), los valida y los almacena en PostgreSQL/TimescaleDB.",
    version="1.0.0",
)

app.add_middleware(LoggingMiddleware)

app.include_router(dispositivos.router)
app.include_router(lecturas.router)


@app.get("/health", tags=["Sistema"])
def health_check():
    return {"status": "ok"}
