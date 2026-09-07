from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.schemas.lectura import PayloadESP32, LecturaOut
from app.services.lectura_service import (
    LecturaService,
    DispositivoNoRegistradoError,
)
from app.repositories.lectura_repository import LecturaRepository

router = APIRouter(prefix="/api/v1/lecturas", tags=["Lecturas"])


def verificar_api_key(x_api_key: str = Header(...)):
    """El ESP32 debe mandar el header 'X-API-Key' para poder escribir datos."""
    if x_api_key != settings.api_key_esp32:
        raise HTTPException(status_code=401, detail="API key inválida")


@router.post("", status_code=201)
def recibir_lectura(
    payload: PayloadESP32,
    db: Session = Depends(get_db),
    _=Depends(verificar_api_key),
):
    """
    Endpoint que llama el ESP32 por POST cada 5-10 segundos con las
    dos lecturas (temperatura DS18B20 + humedad de suelo capacitiva).
    """
    service = LecturaService(db)
    try:
        resultado = service.procesar_payload_esp32(payload)
    except DispositivoNoRegistradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {"guardado": True, "lecturas": resultado}


@router.get("", response_model=list[LecturaOut])
def listar_lecturas(
    sensor_id: int | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limite: int = 500,
    db: Session = Depends(get_db),
):
    """
    Endpoint de solo lectura para que Streamlit y/o Power BI consuman
    el histórico con filtros dinámicos de fecha y sensor.
    """
    repo = LecturaRepository(db)
    return repo.listar(sensor_id=sensor_id, desde=desde, hasta=hasta, limite=limite)
