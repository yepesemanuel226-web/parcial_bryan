from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Dispositivo(Base):
    """Un ESP32 físico. Cada grupo tiene normalmente un dispositivo."""
    __tablename__ = "dispositivos"

    id = Column(Integer, primary_key=True, index=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    mac_address = Column(String(17), unique=True, nullable=False, index=True)
    ubicacion = Column(String(150), nullable=True)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    grupo = relationship("Grupo", back_populates="dispositivos")
    sensores = relationship("Sensor", back_populates="dispositivo")
