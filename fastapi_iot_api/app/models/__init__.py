# Importar todos los modelos para que SQLAlchemy los registre correctamente
from app.models.ubicacion import Ubicacion
from app.models.dispositivo import Dispositivo
from app.models.tipo_sensor import TipoSensor
from app.models.sensor import Sensor
from app.models.lectura import Lectura
from app.models.nivel_alerta import NivelAlerta
from app.models.umbral_alerta import UmbralAlerta
from app.models.alerta import Alerta
from app.models.outlier_detectado import OutlierDetectado
from app.models.consulta_menu import ConsultaMenu
from app.models.estado_conexion import EstadoConexion
from app.models.menu_opcion import MenuOpcion
