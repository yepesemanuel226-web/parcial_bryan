from sqlalchemy import Column, SmallInteger, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Ubicacion(Base):
    __tablename__ = "ubicaciones"

    id_ubicacion = Column(SmallInteger, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)

    dispositivos = relationship("Dispositivo", back_populates="ubicacion")
