"""
Repositorio: encapsula todas las consultas SQL relacionadas con
dispositivos, sensores y tipos de sensor.
"""
from datetime import date
from sqlalchemy.orm import Session

from app.models.dispositivo import Dispositivo
from app.models.sensor import Sensor
from app.models.tipo_sensor import TipoSensor
from app.models.ubicacion import Ubicacion


class DispositivoRepository:
    def __init__(self, db: Session):
        self.db = db

    # ----------------------------------------------------------------
    #  Dispositivos
    # ----------------------------------------------------------------

    def obtener_por_mac(self, mac: str) -> Dispositivo | None:
        return (
            self.db.query(Dispositivo)
            .filter(Dispositivo.direccion_mac == mac)
            .first()
        )

    def crear(
        self,
        nombre: str,
        modelo: str,
        direccion_mac: str,
        id_ubicacion: int,
        intervalo_envio_seg: int = 20,
    ) -> Dispositivo:
        dispositivo = Dispositivo(
            nombre=nombre,
            modelo=modelo,
            direccion_mac=direccion_mac,
            id_ubicacion=id_ubicacion,
            intervalo_envio_seg=intervalo_envio_seg,
        )
        self.db.add(dispositivo)
        self.db.commit()
        self.db.refresh(dispositivo)
        return dispositivo

    # ----------------------------------------------------------------
    #  Sensores
    # ----------------------------------------------------------------

    def obtener_o_crear_sensor(self, id_dispositivo: int, codigo: str) -> Sensor:
        """
        Busca el sensor por código para ese dispositivo.
        Si no existe (primera lectura), lo crea automáticamente.
        """
        sensor = (
            self.db.query(Sensor)
            .filter(
                Sensor.id_dispositivo == id_dispositivo,
                Sensor.codigo == codigo,
            )
            .first()
        )
        if sensor is None:
            tipo = self.obtener_tipo_sensor_por_codigo(codigo)
            if tipo is None:
                raise ValueError(f"Tipo de sensor '{codigo}' no existe en el catálogo")
            sensor = Sensor(
                id_dispositivo=id_dispositivo,
                id_tipo_sensor=tipo.id_tipo_sensor,
                codigo=codigo,
                activo=True,
                fecha_instalacion=date.today(),
            )
            self.db.add(sensor)
            self.db.commit()
            self.db.refresh(sensor)
        return sensor

    # ----------------------------------------------------------------
    #  Tipos de sensor
    # ----------------------------------------------------------------

    def obtener_tipo_sensor_por_codigo(self, codigo: str) -> TipoSensor | None:
        """
        Busca en tipos_sensor por la columna 'nombre' que contiene el
        código del sensor (ej: 'temperatura_ds18b20').
        """
        return (
            self.db.query(TipoSensor)
            .filter(TipoSensor.nombre == codigo)
            .first()
        )

    # ----------------------------------------------------------------
    #  Ubicaciones
    # ----------------------------------------------------------------

    def obtener_ubicacion(self, id_ubicacion: int) -> Ubicacion | None:
        return self.db.query(Ubicacion).filter(Ubicacion.id_ubicacion == id_ubicacion).first()
