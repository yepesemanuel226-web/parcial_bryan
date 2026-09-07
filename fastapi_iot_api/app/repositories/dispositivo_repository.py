"""
Repositorio: encapsula TODAS las consultas SQL relacionadas con
dispositivos, sensores y tipos de sensor. El resto de la app nunca
escribe SQL directamente, solo llama métodos de esta clase.
"""
from sqlalchemy.orm import Session

from app.models.dispositivo import Dispositivo
from app.models.sensor import Sensor
from app.models.tipo_sensor import TipoSensor


class DispositivoRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener_por_mac(self, mac_address: str) -> Dispositivo | None:
        return (
            self.db.query(Dispositivo)
            .filter(Dispositivo.mac_address == mac_address)
            .first()
        )

    def crear(self, grupo_id: int, nombre: str, mac_address: str, ubicacion: str | None) -> Dispositivo:
        dispositivo = Dispositivo(
            grupo_id=grupo_id, nombre=nombre, mac_address=mac_address, ubicacion=ubicacion
        )
        self.db.add(dispositivo)
        self.db.commit()
        self.db.refresh(dispositivo)
        return dispositivo

    def obtener_o_crear_sensor(self, dispositivo_id: int, codigo_tipo_sensor: str) -> Sensor:
        """
        Busca el sensor de ese tipo para ese dispositivo. Si no existe
        (primera vez que el ESP32 envía datos), lo crea automáticamente.
        """
        tipo_sensor = (
            self.db.query(TipoSensor).filter(TipoSensor.codigo == codigo_tipo_sensor).first()
        )
        if tipo_sensor is None:
            raise ValueError(f"Tipo de sensor '{codigo_tipo_sensor}' no existe en el catálogo")

        sensor = (
            self.db.query(Sensor)
            .filter(
                Sensor.dispositivo_id == dispositivo_id,
                Sensor.tipo_sensor_id == tipo_sensor.id,
            )
            .first()
        )
        if sensor is None:
            sensor = Sensor(dispositivo_id=dispositivo_id, tipo_sensor_id=tipo_sensor.id)
            self.db.add(sensor)
            self.db.commit()
            self.db.refresh(sensor)
        return sensor

    def obtener_tipo_sensor(self, codigo: str) -> TipoSensor | None:
        return self.db.query(TipoSensor).filter(TipoSensor.codigo == codigo).first()
