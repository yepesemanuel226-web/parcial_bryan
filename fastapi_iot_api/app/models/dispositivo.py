from sqlalchemy import Column, SmallInteger, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Dispositivo(Base):
    __tablename__ = "dispositivos"

    id_dispositivo = Column(SmallInteger, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    modelo = Column(String(50), nullable=False)
    direccion_mac = Column(String(17), unique=True, nullable=True, index=True)
    id_ubicacion = Column(SmallInteger, ForeignKey("ubicaciones.id_ubicacion"), nullable=False)
    intervalo_envio_seg = Column(SmallInteger, nullable=False, default=20)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ubicacion = relationship("Ubicacion", back_populates="dispositivos")
    sensores = relationship("Sensor", back_populates="dispositivo")
    estados_conexion = relationship("EstadoConexion", back_populates="dispositivo")
    consultas_menu = relationship("ConsultaMenu", back_populates="dispositivo")
