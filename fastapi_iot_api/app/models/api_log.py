from sqlalchemy import Column, Integer, String, DateTime, func

from app.core.database import Base


class ApiLog(Base):
    """Registro de auditoría de cada petición que recibe la API."""
    __tablename__ = "api_logs"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String(150), nullable=False)
    metodo = Column(String(10), nullable=False)
    ip_origen = Column(String(50), nullable=True)
    status_code = Column(Integer, nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
