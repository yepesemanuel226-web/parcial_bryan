"""
Importa todos los modelos aquí para que SQLAlchemy los registre
en Base.metadata cuando se ejecute create_all() (usado por scripts
de arranque o de pruebas locales).
"""
from app.models.grupo import Grupo
from app.models.dispositivo import Dispositivo
from app.models.tipo_sensor import TipoSensor
from app.models.sensor import Sensor
from app.models.lectura import Lectura
from app.models.alerta import Alerta
from app.models.api_log import ApiLog

__all__ = [
    "Grupo",
    "Dispositivo",
    "TipoSensor",
    "Sensor",
    "Lectura",
    "Alerta",
    "ApiLog",
]
