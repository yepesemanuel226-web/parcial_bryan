from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DispositivoCreate(BaseModel):
    """Payload para registrar un ESP32 por primera vez."""
    nombre: str
    modelo: str
    direccion_mac: str
    id_ubicacion: int
    intervalo_envio_seg: int = 20


class DispositivoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_dispositivo: int
    nombre: str
    modelo: str
    direccion_mac: str | None
    id_ubicacion: int
    intervalo_envio_seg: int
    activo: bool
    fecha_registro: datetime
