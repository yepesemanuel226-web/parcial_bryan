"""
Configuración global de la aplicación.
Lee las variables desde el archivo .env usando pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Cadena de conexión a Neon (PostgreSQL)
    # Formato: postgresql://neondb_owner:PASSWORD@host.neon.tech/neondb?sslmode=require
    database_url: str = "postgresql://usuario:password@localhost:5432/neondb"

    # Clave que debe mandar el ESP32 en el header X-API-Key
    api_key_esp32: str = "cambia-esta-clave"

    # Nombre del proyecto (aparece en /docs)
    proyecto_nombre: str = "IoT Taller Integrador - API"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Instancia única (singleton) que se importa en el resto del proyecto
settings = Settings()
