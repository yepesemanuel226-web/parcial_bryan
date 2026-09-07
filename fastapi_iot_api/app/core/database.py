"""
Configuración de la conexión a la base de datos PostgreSQL / TimescaleDB
usando SQLAlchemy.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base de la que heredan todos los modelos ORM
Base = declarative_base()


def get_db():
    """
    Dependencia de FastAPI: entrega una sesión de base de datos
    y la cierra automáticamente al terminar la petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
