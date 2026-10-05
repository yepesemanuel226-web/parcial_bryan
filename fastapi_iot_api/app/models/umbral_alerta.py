from sqlalchemy import Column, SmallInteger, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class UmbralAlerta(Base):
    __tablename__ = "umbrales_alerta"

    id_umbral = Column(SmallInteger, primary_key=True, index=True)
    id_tipo_sensor = Column(SmallInteger, ForeignKey("tipos_sensor.id_tipo_sensor"), nullable=False)
    id_nivel = Column(SmallInteger, ForeignKey("niveles_alerta.id_nivel"), nullable=False)
    limite_inferior = Column(Numeric, nullable=True)
    limite_superior = Column(Numeric, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)

    tipo_sensor = relationship("TipoSensor", back_populates="umbrales")
    nivel = relationship("NivelAlerta", back_populates="umbrales")
    alertas = relationship("Alerta", back_populates="umbral")
