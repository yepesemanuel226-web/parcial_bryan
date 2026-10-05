from sqlalchemy import Column, SmallInteger, String, Numeric
from sqlalchemy.orm import relationship

from app.core.database import Base


class TipoSensor(Base):
    __tablename__ = "tipos_sensor"

    id_tipo_sensor = Column(SmallInteger, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    magnitud = Column(String(50), nullable=False)
    unidad = Column(String(20), nullable=False)
    valor_min_fisico = Column(Numeric, nullable=False)
    valor_max_fisico = Column(Numeric, nullable=False)

    sensores = relationship("Sensor", back_populates="tipo_sensor")
    umbrales = relationship("UmbralAlerta", back_populates="tipo_sensor")
