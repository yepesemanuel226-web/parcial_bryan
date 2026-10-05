from sqlalchemy import Column, BigInteger, SmallInteger, Float, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Alerta(Base):
    __tablename__ = "alertas"

    id_alerta = Column(BigInteger, primary_key=True, index=True)
    id_sensor = Column(SmallInteger, ForeignKey("sensores.id_sensor"), nullable=False)
    id_umbral = Column(SmallInteger, ForeignKey("umbrales_alerta.id_umbral"), nullable=False)
    tiempo_lectura = Column(DateTime(timezone=True), nullable=False)
    valor = Column(Float, nullable=False)
    estado = Column(String(20), nullable=False, default="activa")
    creada_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resuelta_en = Column(DateTime(timezone=True), nullable=True)

    sensor = relationship("Sensor", back_populates="alertas")
    umbral = relationship("UmbralAlerta", back_populates="alertas")
