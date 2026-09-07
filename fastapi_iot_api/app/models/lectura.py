from sqlalchemy import Column, Integer, Numeric, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Lectura(Base):
    """
    Cada fila = una medición de un sensor en un instante de tiempo.
    Esta es la tabla que se convierte en hypertable de TimescaleDB
    (particionada por 'timestamp'), por eso 'timestamp' forma parte
    de la llave primaria compuesta.
    """
    __tablename__ = "lecturas"

    # unique=True porque la PK real es compuesta (id, timestamp) -- lo exige
    # TimescaleDB al convertir la tabla en hypertable -- pero "alertas"
    # necesita referenciar "id" solo, y eso requiere una restricción UNIQUE.
    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    sensor_id = Column(Integer, ForeignKey("sensores.id"), nullable=False)
    valor = Column(Numeric(10, 3), nullable=False)
    timestamp = Column(DateTime(timezone=True), primary_key=True, server_default=func.now())

    sensor = relationship("Sensor", back_populates="lecturas")
