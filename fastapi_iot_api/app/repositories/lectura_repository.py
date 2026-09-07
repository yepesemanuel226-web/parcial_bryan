from datetime import datetime
from sqlalchemy.orm import Session

from app.models.lectura import Lectura
from app.models.alerta import Alerta


class LecturaRepository:
    def __init__(self, db: Session):
        self.db = db

    def crear(self, sensor_id: int, valor: float) -> Lectura:
        lectura = Lectura(sensor_id=sensor_id, valor=valor)
        self.db.add(lectura)
        self.db.commit()
        self.db.refresh(lectura)
        return lectura

    def registrar_alerta(self, lectura_id: int, tipo_anomalia: str, descripcion: str) -> Alerta:
        alerta = Alerta(lectura_id=lectura_id, tipo_anomalia=tipo_anomalia, descripcion=descripcion)
        self.db.add(alerta)
        self.db.commit()
        return alerta

    def listar(
        self,
        sensor_id: int | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limite: int = 500,
    ) -> list[Lectura]:
        query = self.db.query(Lectura)
        if sensor_id is not None:
            query = query.filter(Lectura.sensor_id == sensor_id)
        if desde is not None:
            query = query.filter(Lectura.timestamp >= desde)
        if hasta is not None:
            query = query.filter(Lectura.timestamp <= hasta)
        return query.order_by(Lectura.timestamp.desc()).limit(limite).all()
