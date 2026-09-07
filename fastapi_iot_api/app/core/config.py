"""
Configuración global de la aplicación.
Lee las variables desde el archivo .env usando pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://usuario:password@localhost:5432/iot_taller"
    grupo_id: int = 1
    api_key_esp32: str = "cambia-esta-clave"
    proyecto_nombre: str = "IoT Taller Integrador - API"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Instancia única (singleton) que se importa en el resto del proyecto
settings = Settings()
