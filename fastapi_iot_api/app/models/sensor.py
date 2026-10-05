from sqlalchemy import Column, SmallInteger, String, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship

from app.core.database import Base


class Sensor(Base):
    __tablename__ = "sensores"

    id_sensor = Column(SmallInteger, primary_key=True, index=True)
    id_dispositivo = Column(SmallInteger, ForeignKey("dispositivos.id_dispositivo"), nullable=False)
    id_tipo_sensor = Column(SmallInteger, ForeignKey("tipos_sensor.id_tipo_sensor"), nullable=False)
    codigo = Column(String(50), nullable=False)
    modelo = Column(String(50), nullable=True)
    pin_conexion = Column(String(20), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_instalacion = Column(Date, nullable=False)

    dispositivo = relationship("Dispositivo", back_populates="sensores")
    tipo_sensor = relationship("TipoSensor", back_populates="sensores")
    lecturas = relationship("Lectura", back_populates="sensor")
    alertas = relationship("Alerta", back_populates="sensor")
    outliers = relationship("OutlierDetectado", back_populates="sensor")
