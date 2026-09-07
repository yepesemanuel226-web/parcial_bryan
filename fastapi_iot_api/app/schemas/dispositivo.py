from pydantic import BaseModel, ConfigDict


class DispositivoCreate(BaseModel):
    grupo_id: int
    nombre: str
    mac_address: str
    ubicacion: str | None = None


class DispositivoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    grupo_id: int
    nombre: str
    mac_address: str
    ubicacion: str | None
    activo: bool
