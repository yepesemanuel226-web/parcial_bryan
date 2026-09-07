from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Sensor(Base):
    """Un sensor físico conectado a un dispositivo (ESP32)."""
    __tablename__ = "sensores"

    id = Column(Integer, primary_key=True, index=True)
    dispositivo_id = Column(Integer, ForeignKey("dispositivos.id"), nullable=False)
    tipo_sensor_id = Column(Integer, ForeignKey("tipos_sensor.id"), nullable=False)
    pin = Column(String(20), nullable=True)  # ej: "GPIO4" o "ADC1_CH6"
    descripcion = Column(String(150), nullable=True)
    activo = Column(Boolean, default=True)

    dispositivo = relationship("Dispositivo", back_populates="sensores")
    tipo_sensor = relationship("TipoSensor", back_populates="sensores")
    lecturas = relationship("Lectura", back_populates="sensor")
