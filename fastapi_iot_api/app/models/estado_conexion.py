from sqlalchemy import Column, BigInteger, SmallInteger, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class EstadoConexion(Base):
    __tablename__ = "estado_conexion"

    id_evento = Column(BigInteger, primary_key=True, index=True)
    id_dispositivo = Column(SmallInteger, ForeignKey("dispositivos.id_dispositivo"), nullable=False)
    tiempo = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    conectado = Column(Boolean, nullable=False)
    rssi_dbm = Column(SmallInteger, nullable=True)
    reintentos = Column(SmallInteger, nullable=False, default=0)
    lecturas_en_buffer = Column(SmallInteger, nullable=False, default=0)

    dispositivo = relationship("Dispositivo", back_populates="estados_conexion")
