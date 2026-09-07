from sqlalchemy import Column, Integer, String, Numeric
from sqlalchemy.orm import relationship

from app.core.database import Base


class TipoSensor(Base):
    """
    Catálogo de tipos de sensor soportados. Guarda el rango válido
    de cada uno, que la API usa para validar antes de insertar.
    """
    __tablename__ = "tipos_sensor"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False)  # ej: "temperatura_ds18b20"
    nombre = Column(String(100), nullable=False)
    unidad_medida = Column(String(20), nullable=False)  # "°C" o "%"
    valor_min = Column(Numeric(8, 2), nullable=False)
    valor_max = Column(Numeric(8, 2), nullable=False)

    sensores = relationship("Sensor", back_populates="tipo_sensor")
