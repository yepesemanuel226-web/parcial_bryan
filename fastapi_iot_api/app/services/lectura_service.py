"""
Capa de servicio: contiene la lógica de negocio.
- Valida que el valor recibido esté dentro del rango físico del sensor.
- Registra alertas cuando detecta un valor atípico.
- Orquesta los repositorios (dispositivo + sensor + lectura).
No sabe nada de HTTP ni de FastAPI: solo recibe datos y aplica reglas.
"""
from sqlalchemy.orm import Session

from app.repositories.dispositivo_repository import DispositivoRepository
from app.repositories.lectura_repository import LecturaRepository
from app.schemas.lectura import PayloadESP32


class RangoInvalidoError(Exception):
    """Se lanza cuando el valor recibido está fuera del rango físico esperado."""


class DispositivoNoRegistradoError(Exception):
    """Se lanza cuando la MAC no corresponde a ningún dispositivo registrado."""


class LecturaService:
    def __init__(self, db: Session):
        self.db = db
        self.dispositivo_repo = DispositivoRepository(db)
        self.lectura_repo = LecturaRepository(db)

    def procesar_payload_esp32(self, payload: PayloadESP32) -> list[dict]:
        dispositivo = self.dispositivo_repo.obtener_por_mac(payload.mac_address)
        if dispositivo is None:
            raise DispositivoNoRegistradoError(
                f"No existe un dispositivo registrado con MAC {payload.mac_address}. "
                "Regístralo primero con POST /api/v1/dispositivos"
            )

        resultados = []
        for lectura_in in payload.lecturas:
            tipo_sensor = self.dispositivo_repo.obtener_tipo_sensor(lectura_in.tipo_sensor)

            # --- Validación de tipo, rango y formato (requerimiento del taller) ---
            if tipo_sensor is None:
                raise ValueError(f"Tipo de sensor desconocido: {lectura_in.tipo_sensor}")

            valor = float(lectura_in.valor)
            fuera_de_rango = not (float(tipo_sensor.valor_min) <= valor <= float(tipo_sensor.valor_max))

            sensor = self.dispositivo_repo.obtener_o_crear_sensor(
                dispositivo.id, lectura_in.tipo_sensor
            )
            lectura = self.lectura_repo.crear(sensor_id=sensor.id, valor=valor)

            if fuera_de_rango:
                self.lectura_repo.registrar_alerta(
                    lectura_id=lectura.id,
                    tipo_anomalia="fuera_de_rango",
                    descripcion=(
                        f"Valor {valor}{tipo_sensor.unidad_medida} fuera del rango "
                        f"[{tipo_sensor.valor_min}, {tipo_sensor.valor_max}]"
                    ),
                )

            resultados.append(
                {
                    "sensor": lectura_in.tipo_sensor,
                    "valor": valor,
                    "unidad": tipo_sensor.unidad_medida,
                    "anomalia": fuera_de_rango,
                    "timestamp": lectura.timestamp,
                }
            )
        return resultados
