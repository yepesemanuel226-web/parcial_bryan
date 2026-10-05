from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.schemas.lectura import (
    PayloadESP32,
    LecturaOut,
    EstadoConexionIn,
    EstadoConexionOut,
    ConsultaMenuIn,
    ConsultaMenuOut,
    OutlierOut,
    AlertaOut,
)
from app.services.lectura_service import LecturaService, DispositivoNoRegistradoError
from app.repositories.lectura_repository import LecturaRepository

router = APIRouter(prefix="/api/v1", tags=["Lecturas"])


def verificar_api_key(x_api_key: str = Header(...)):
    """El ESP32 debe enviar el header 'X-API-Key' para poder escribir datos."""
    if x_api_key != settings.api_key_esp32:
        raise HTTPException(status_code=401, detail="API key inválida")


# ----------------------------------------------------------------
#  Lecturas
# ----------------------------------------------------------------

@router.post("/lecturas", status_code=201)
def recibir_lectura(
    payload: PayloadESP32,
    db: Session = Depends(get_db),
    _=Depends(verificar_api_key),
):
    """
    El ESP32 llama este endpoint cada 20 segundos con temperatura
    y humedad. Guarda la lectura, verifica umbrales y detecta outliers.
    """
    service = LecturaService(db)
    try:
        resultado = service.procesar_payload_esp32(payload)
    except DispositivoNoRegistradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"guardado": True, "lecturas": resultado}


@router.get("/lecturas", response_model=list[LecturaOut])
def listar_lecturas(
    id_sensor: int | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limite: int = 500,
    db: Session = Depends(get_db),
):
    """Historial de lecturas con filtros opcionales de sensor y fecha."""
    repo = LecturaRepository(db)
    return repo.listar(id_sensor=id_sensor, desde=desde, hasta=hasta, limite=limite)


# ----------------------------------------------------------------
#  Alertas
# ----------------------------------------------------------------

@router.get("/alertas", response_model=list[AlertaOut])
def listar_alertas(limite: int = 100, db: Session = Depends(get_db)):
    """Últimas alertas generadas por lecturas fuera de umbral."""
    repo = LecturaRepository(db)
    return repo.listar_alertas(limite=limite)


# ----------------------------------------------------------------
#  Outliers
# ----------------------------------------------------------------

@router.get("/outliers", response_model=list[OutlierOut])
def listar_outliers(
    id_sensor: int | None = None,
    limite: int = 100,
    db: Session = Depends(get_db),
):
    """Outliers detectados por z-score."""
    repo = LecturaRepository(db)
    return repo.listar_outliers(id_sensor=id_sensor, limite=limite)


# ----------------------------------------------------------------
#  Estado de conexión
# ----------------------------------------------------------------

@router.post("/conexion", response_model=EstadoConexionOut, status_code=201)
def reportar_conexion(
    payload: EstadoConexionIn,
    db: Session = Depends(get_db),
    _=Depends(verificar_api_key),
):
    """El ESP32 reporta su estado de conexión WiFi/nube."""
    service = LecturaService(db)
    try:
        return service.registrar_estado_conexion(payload)
    except DispositivoNoRegistradoError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ----------------------------------------------------------------
#  Consultas de menú (teclado matricial)
# ----------------------------------------------------------------

@router.post("/menu", response_model=ConsultaMenuOut, status_code=201)
def registrar_consulta_menu(
    payload: ConsultaMenuIn,
    db: Session = Depends(get_db),
    _=Depends(verificar_api_key),
):
    """Registra qué tecla pulsó el usuario en el teclado matricial del ESP32."""
    service = LecturaService(db)
    try:
        return service.registrar_consulta_menu(payload)
    except DispositivoNoRegistradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
