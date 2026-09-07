from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Grupo(Base):
    """Grupo de trabajo (1 de los 5 equipos del taller)."""
    __tablename__ = "grupos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    integrantes = Column(String(300), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    dispositivos = relationship("Dispositivo", back_populates="grupo")
