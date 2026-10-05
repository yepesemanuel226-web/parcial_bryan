from sqlalchemy import Column, String, Text, CHAR

from app.core.database import Base


class MenuOpcion(Base):
    __tablename__ = "menu_opciones"

    tecla = Column(CHAR(1), primary_key=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    concepto_analitica = Column(String(100), nullable=False)
