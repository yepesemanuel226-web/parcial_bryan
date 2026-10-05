from sqlalchemy import Column, BigInteger, SmallInteger, CHAR, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ConsultaMenu(Base):
    __tablename__ = "consultas_menu"

    id_consulta = Column(BigInteger, primary_key=True, index=True)
    id_dispositivo = Column(SmallInteger, ForeignKey("dispositivos.id_dispositivo"), nullable=False)
    tecla = Column(CHAR(1), nullable=False)
    tiempo = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    dispositivo = relationship("Dispositivo", back_populates="consultas_menu")
