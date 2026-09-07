"""
Esquemas de validación para las lecturas que envía el ESP32.
Aquí es donde FastAPI valida tipo, rango y formato automáticamente
antes de que el dato llegue a la base de datos.
"""
from datetime import datetime
from typing import Literal, List

from pydantic import BaseModel, Field, ConfigDict


# Códigos válidos de sensor para este grupo (deben coincidir con
# la columna "codigo" de la tabla tipos_sensor)
TipoSensorCodigo = Literal["temperatura_ds18b20", "humedad_suelo_capacitivo"]


class LecturaSensorIn(BaseModel):
    """Una medición individual dentro del payload del ESP32."""
    tipo_sensor: TipoSensorCodigo
    valor: float = Field(..., description="Valor medido por el sensor")


class PayloadESP32(BaseModel):
    """
    Cuerpo esperado en el POST que envía el ESP32 cada 5-10 segundos.
    Ejemplo:
    {
      "mac_address": "AA:BB:CC:DD:EE:FF",
      "lecturas": [
        {"tipo_sensor": "temperatura_ds18b20", "valor": 24.6},
        {"tipo_sensor": "humedad_suelo_capacitivo", "valor": 63.2}
      ]
    }
    """
    mac_address: str = Field(..., min_length=11, max_length=17)
    lecturas: List[LecturaSensorIn] = Field(..., min_length=1, max_length=2)


class LecturaOut(BaseModel):
    """Lo que la API devuelve al consultar lecturas (lo consume Streamlit/Power BI vía API)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    sensor_id: int
    valor: float
    timestamp: datetime
