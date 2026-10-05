from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dispositivo import DispositivoCreate, DispositivoOut
from app.repositories.dispositivo_repository import DispositivoRepository
from app.models.dispositivo import Dispositivo

router = APIRouter(prefix="/api/v1/dispositivos", tags=["Dispositivos"])


@router.post("", response_model=DispositivoOut, status_code=201)
def registrar_dispositivo(payload: DispositivoCreate, db: Session = Depends(get_db)):
    """
    Registra el ESP32 una sola vez (por su MAC) antes de que empiece
    a enviar lecturas. Requiere que la ubicación ya exista en la BD.
    """
    repo = DispositivoRepository(db)
    if repo.obtener_por_mac(payload.direccion_mac) is not None:
        raise HTTPException(status_code=409, detail="Ya existe un dispositivo con esa MAC")

    if repo.obtener_ubicacion(payload.id_ubicacion) is None:
        raise HTTPException(status_code=404, detail=f"Ubicación {payload.id_ubicacion} no existe")

    return repo.crear(
        nombre=payload.nombre,
        modelo=payload.modelo,
        direccion_mac=payload.direccion_mac,
        id_ubicacion=payload.id_ubicacion,
        intervalo_envio_seg=payload.intervalo_envio_seg,
    )


@router.get("", response_model=list[DispositivoOut])
def listar_dispositivos(db: Session = Depends(get_db)):
    """Lista todos los dispositivos registrados."""
    return db.query(Dispositivo).all()


@router.get("/{mac}", response_model=DispositivoOut)
def obtener_dispositivo(mac: str, db: Session = Depends(get_db)):
    """Obtiene un dispositivo por su dirección MAC."""
    repo = DispositivoRepository(db)
    dispositivo = repo.obtener_por_mac(mac)
    if dispositivo is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return dispositivo
