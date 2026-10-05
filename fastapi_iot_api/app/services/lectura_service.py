"""
Capa de servicio: lógica de negocio para procesar lecturas del ESP32.
- Valida que el valor esté dentro del rango físico del sensor.
- Detecta outliers por z-score y los registra en outliers_detectados.
- Verifica umbrales y registra alertas cuando corresponde.
- No sabe nada de HTTP ni de FastAPI.
"""
import math
from datetime import datetime
from sqlalchemy.orm import Session

from app.repositories.dispositivo_repository import DispositivoRepository
from app.repositories.lectura_repository import LecturaRepository
from app.schemas.lectura import PayloadESP32, EstadoConexionIn, ConsultaMenuIn


class DispositivoNoRegistradoError(Exception):
    """MAC no corresponde a ningún dispositivo registrado."""


class LecturaService:
    def __init__(self, db: Session):
        self.db = db
        self.dispositivo_repo = DispositivoRepository(db)
        self.lectura_repo = LecturaRepository(db)

    # ----------------------------------------------------------------
    #  Procesar payload de lecturas del ESP32
    # ----------------------------------------------------------------

    def procesar_payload_esp32(self, payload: PayloadESP32) -> list[dict]:
        dispositivo = self.dispositivo_repo.obtener_por_mac(payload.mac_address)
        if dispositivo is None:
            raise DispositivoNoRegistradoError(
                f"No existe un dispositivo con MAC {payload.mac_address}. "
                "Regístralo primero con POST /api/v1/dispositivos"
            )

        resultados = []
        tiempo_ahora = datetime.utcnow()

        for lectura_in in payload.lecturas:
            # 1. Obtener o crear el sensor
            sensor = self.dispositivo_repo.obtener_o_crear_sensor(
                dispositivo.id_dispositivo, lectura_in.tipo_sensor
            )

            # 2. Validar rango físico del tipo de sensor
            tipo = sensor.tipo_sensor
            valor = float(lectura_in.valor)
            fuera_de_rango = not (
                float(tipo.valor_min_fisico) <= valor <= float(tipo.valor_max_fisico)
            )

            # 3. Guardar la lectura
            lectura = self.lectura_repo.crear(
                id_sensor=sensor.id_sensor,
                valor=valor,
                tiempo=tiempo_ahora,
            )

            # 4. Verificar umbral y registrar alerta si corresponde
            alerta_generada = False
            umbral = self.lectura_repo.obtener_umbral(tipo.id_tipo_sensor)
            if umbral is not None:
                supera = False
                if umbral.limite_inferior is not None and valor < float(umbral.limite_inferior):
                    supera = True
                if umbral.limite_superior is not None and valor > float(umbral.limite_superior):
                    supera = True
                if supera or fuera_de_rango:
                    self.lectura_repo.registrar_alerta(
                        id_sensor=sensor.id_sensor,
                        id_umbral=umbral.id_umbral,
                        tiempo_lectura=tiempo_ahora,
                        valor=valor,
                    )
                    alerta_generada = True

            # 5. Detección de outlier por z-score (usando rango físico como referencia)
            rango = float(tipo.valor_max_fisico) - float(tipo.valor_min_fisico)
            media_ref = (float(tipo.valor_max_fisico) + float(tipo.valor_min_fisico)) / 2
            desv_ref = rango / 4  # aproximación: 95% de valores dentro del rango
            outlier_detectado = False
            z_score = None
            if desv_ref > 0:
                z_score = abs(valor - media_ref) / desv_ref
                if z_score > 2.0:
                    outlier_detectado = True
                    self.lectura_repo.registrar_outlier(
                        id_sensor=sensor.id_sensor,
                        tiempo_lectura=tiempo_ahora,
                        valor=valor,
                        z_score=z_score,
                        metodo="zscore",
                    )

            resultados.append({
                "sensor": lectura_in.tipo_sensor,
                "valor": valor,
                "unidad": tipo.unidad,
                "tiempo": tiempo_ahora,
                "alerta": alerta_generada,
                "outlier": outlier_detectado,
                "fuera_de_rango": fuera_de_rango,
            })

        return resultados

    # ----------------------------------------------------------------
    #  Registrar estado de conexión
    # ----------------------------------------------------------------

    def registrar_estado_conexion(self, payload: EstadoConexionIn):
        dispositivo = self.dispositivo_repo.obtener_por_mac(payload.mac_address)
        if dispositivo is None:
            raise DispositivoNoRegistradoError(
                f"No existe un dispositivo con MAC {payload.mac_address}."
            )
        return self.lectura_repo.registrar_estado_conexion(
            id_dispositivo=dispositivo.id_dispositivo,
            conectado=payload.conectado,
            rssi_dbm=payload.rssi_dbm,
            reintentos=payload.reintentos,
            lecturas_en_buffer=payload.lecturas_en_buffer,
        )

    # ----------------------------------------------------------------
    #  Registrar consulta de menú
    # ----------------------------------------------------------------

    def registrar_consulta_menu(self, payload: ConsultaMenuIn):
        dispositivo = self.dispositivo_repo.obtener_por_mac(payload.mac_address)
        if dispositivo is None:
            raise DispositivoNoRegistradoError(
                f"No existe un dispositivo con MAC {payload.mac_address}."
            )
        return self.lectura_repo.registrar_consulta_menu(
            id_dispositivo=dispositivo.id_dispositivo,
            tecla=payload.tecla,
        )
