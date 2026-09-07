from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dispositivo import DispositivoCreate, DispositivoOut
from app.repositories.dispositivo_repository import DispositivoRepository

router = APIRouter(prefix="/api/v1/dispositivos", tags=["Dispositivos"])


@router.post("", response_model=DispositivoOut, status_code=201)
def registrar_dispositivo(payload: DispositivoCreate, db: Session = Depends(get_db)):
    """Registra el ESP32 una sola vez (por su MAC) antes de que empiece a enviar datos."""
    repo = DispositivoRepository(db)
    if repo.obtener_por_mac(payload.mac_address) is not None:
        raise HTTPException(status_code=409, detail="Ya existe un dispositivo con esa MAC")

    return repo.crear(
        grupo_id=payload.grupo_id,
        nombre=payload.nombre,
        mac_address=payload.mac_address,
        ubicacion=payload.ubicacion,
    )
