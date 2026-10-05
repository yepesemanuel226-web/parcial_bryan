"""
Schemas de validación para las lecturas que envía el ESP32
y para las respuestas que consume Streamlit / KNIME.
"""
from datetime import datetime
from typing import Literal, List

from pydantic import BaseModel, Field, ConfigDict


# Códigos válidos — deben coincidir con la columna "codigo" de sensores
TipoSensorCodigo = Literal["temperatura_ds18b20", "humedad_suelo_capacitivo"]


class LecturaSensorIn(BaseModel):
    """Una medición individual dentro del payload del ESP32."""
    tipo_sensor: TipoSensorCodigo
    valor: float = Field(..., description="Valor medido por el sensor")


class PayloadESP32(BaseModel):
    """
    Cuerpo del POST que envía el ESP32 cada 20 segundos.
    {
      "mac_address": "20:43:a8:66:81:5c",
      "lecturas": [
        {"tipo_sensor": "temperatura_ds18b20",     "valor": 24.6},
        {"tipo_sensor": "humedad_suelo_capacitivo", "valor": 63.2}
      ]
    }
    """
    mac_address: str = Field(..., min_length=11, max_length=17)
    lecturas: List[LecturaSensorIn] = Field(..., min_length=1, max_length=2)


class LecturaOut(BaseModel):
    """Respuesta al consultar lecturas (Streamlit / KNIME)."""
    model_config = ConfigDict(from_attributes=True)

    tiempo: datetime
    id_sensor: int
    valor: float | None
    reenviada: bool
    recibido_en: datetime


class EstadoConexionIn(BaseModel):
    """Payload que envía el ESP32 para reportar su estado de conexión."""
    mac_address: str = Field(..., min_length=11, max_length=17)
    conectado: bool
    rssi_dbm: int | None = None
    reintentos: int = 0
    lecturas_en_buffer: int = 0


class EstadoConexionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_evento: int
    id_dispositivo: int
    tiempo: datetime
    conectado: bool
    rssi_dbm: int | None
    reintentos: int
    lecturas_en_buffer: int


class ConsultaMenuIn(BaseModel):
    """Payload que envía el ESP32 cuando el usuario pulsa una tecla del menú."""
    mac_address: str = Field(..., min_length=11, max_length=17)
    tecla: str = Field(..., min_length=1, max_length=1)


class ConsultaMenuOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_consulta: int
    id_dispositivo: int
    tecla: str
    tiempo: datetime


class OutlierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_outlier: int
    id_sensor: int
    tiempo_lectura: datetime
    valor: float
    z_score: float | None
    metodo: str
    detectado_en: datetime


class AlertaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_alerta: int
    id_sensor: int
    id_umbral: int
    tiempo_lectura: datetime
    valor: float
    estado: str
    creada_en: datetime
    resuelta_en: datetime | None
