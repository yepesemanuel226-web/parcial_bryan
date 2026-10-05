from sqlalchemy import Column, BigInteger, SmallInteger, Float, Numeric, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class OutlierDetectado(Base):
    __tablename__ = "outliers_detectados"

    id_outlier = Column(BigInteger, primary_key=True, index=True)
    id_sensor = Column(SmallInteger, ForeignKey("sensores.id_sensor"), nullable=False)
    tiempo_lectura = Column(DateTime(timezone=True), nullable=False)
    valor = Column(Float, nullable=False)
    z_score = Column(Numeric, nullable=True)
    metodo = Column(String(30), nullable=False, default="zscore")
    detectado_en = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    sensor = relationship("Sensor", back_populates="outliers")
