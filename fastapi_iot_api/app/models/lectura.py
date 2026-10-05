from sqlalchemy import Column, SmallInteger, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Lectura(Base):
    """
    Hypertable principal de TimescaleDB.
    PK compuesta: (tiempo, id_sensor) — requerido por TimescaleDB.
    """
    __tablename__ = "lecturas"

    tiempo = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    id_sensor = Column(SmallInteger, ForeignKey("sensores.id_sensor"), primary_key=True, nullable=False)
    valor = Column(Float, nullable=True)
    reenviada = Column(Boolean, nullable=False, default=False)
    recibido_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    sensor = relationship("Sensor", back_populates="lecturas")
