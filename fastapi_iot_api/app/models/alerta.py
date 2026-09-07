from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Alerta(Base):
    """Se guarda automáticamente cuando una lectura sale del rango esperado."""
    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    lectura_id = Column(Integer, ForeignKey("lecturas.id"), nullable=False)
    tipo_anomalia = Column(String(50), nullable=False)  # ej: "fuera_de_rango"
    descripcion = Column(String(250), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    lectura = relationship("Lectura")
