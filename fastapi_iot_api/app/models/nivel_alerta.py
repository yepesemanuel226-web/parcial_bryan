from sqlalchemy import Column, SmallInteger, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class NivelAlerta(Base):
    __tablename__ = "niveles_alerta"

    id_nivel = Column(SmallInteger, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    prioridad = Column(SmallInteger, nullable=False)

    umbrales = relationship("UmbralAlerta", back_populates="nivel")
