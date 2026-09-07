# Proyecto Integrador IoT — Minería de Datos

Sistema completo de captura, almacenamiento, análisis y visualización de datos en tiempo real usando ESP32, FastAPI, PostgreSQL/TimescaleDB y Streamlit.

**Sensores:** Humedad de suelo capacitivo v2.0 + Temperatura DS18B20

---

## Arquitectura del sistema

```
ESP32 (sensores)
    │
    │  HTTP POST cada 10s (JSON)
    ▼
FastAPI (API REST)
    │
    │  SQLAlchemy + psycopg2
    ▼
TimescaleDB (TigerData Cloud)
    │
    │  GET /api/v1/lecturas
    ▼
Streamlit (app analítica)
```

---

## Estructura del proyecto

```
circuito/
├── app.py                        # Aplicación analítica Streamlit (Fase 3)
├── requirements.txt              # Dependencias unificadas
├── .env.example                  # Plantilla de variables de entorno
├── esp32_sensor/
│   └── esp32_sensor.ino          # Código Arduino para el ESP32 (Fase 1)
└── fastapi_iot_api/              # API REST (Fase 2)
    ├── .env                      # Variables de entorno reales (no subir a git)
    ├── .env.example
    ├── requirements.txt
    ├── README.md
    ├── sql/
    │   └── init_timescale.sql    # Script de creación de tablas y datos semilla
    └── app/
        ├── main.py               # Punto de entrada FastAPI
        ├── core/
        │   ├── config.py         # Configuración (pydantic-settings)
        │   └── database.py       # Conexión SQLAlchemy
        ├── models/               # Modelos ORM (SQLAlchemy)
        ├── schemas/              # Validación de datos (Pydantic)
        ├── repositories/         # Acceso a la BD
        ├── services/             # Lógica de negocio
        ├── routers/              # Endpoints REST
        └── middleware/           # Logging de peticiones
```

---

## Fase 1 — Circuito ESP32

El ESP32 captura datos de dos sensores cada 10 segundos y los envía a la API:

- **DS18B20** (temperatura) → pin 4, protocolo OneWire
- **Sensor capacitivo v2.0** (humedad de suelo) → pin 34, señal analógica

Valores de calibración del sensor de humedad:
- `valorSeco = 3400` (lectura al aire)
- `valorHumedo = 1600` (lectura sumergido en agua)

La LCD I2C muestra en tiempo real la temperatura, humedad y estado de conexión con la API (`API: OK` / `API: ERROR`).

El código completo está en `esp32_sensor/esp32_sensor.ino`.

---

## Fase 2 — API REST (FastAPI)

### Levantar la API

```powershell
# Activar entorno virtual
.venv\Scripts\Activate.ps1

# Desde la carpeta fastapi_iot_api/
cd fastapi_iot_api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado de la API |
| POST | `/api/v1/dispositivos` | Registrar ESP32 (por MAC) |
| POST | `/api/v1/lecturas` | Recibir lecturas del ESP32 |
| GET | `/api/v1/lecturas` | Consultar historial de lecturas |

Documentación interactiva: `http://localhost:8000/docs`

### Configuración (.env)

Crear `fastapi_iot_api/.env` basándose en `.env.example`:

```env
DATABASE_URL=postgresql+psycopg2://tsdbadmin:PASSWORD@host:33257/tsdb?sslmode=require
GRUPO_ID=1
API_KEY_ESP32=tu-clave-secreta
```

### Base de datos (7 tablas)

Creadas con `sql/init_timescale.sql`:

1. `grupos` — identificación del grupo de trabajo
2. `dispositivos` — registro de ESP32 por MAC address
3. `tipos_sensor` — catálogo de sensores (temperatura, humedad)
4. `sensores` — instancia física de cada sensor por dispositivo
5. `lecturas` — hypertable TimescaleDB con todas las mediciones
6. `alertas` — anomalías detectadas en las lecturas
7. `api_logs` — registro de peticiones HTTP a la API

---

## Fase 3 — Analítica en Streamlit

### Levantar la app

```powershell
# Desde la raíz del proyecto, con el venv activo
streamlit run app.py
```

Se abre en `http://localhost:8501`.

### Fuente de datos

En la barra lateral seleccionar **"API (FastAPI local)"** con:
- URL base: `http://localhost:8000`
- sensor_id de temperatura: `3`
- sensor_id de humedad: `5`

O **"Simulados (demo)"** para usar datos sintéticos sin necesidad de conexión.

### Secciones de la app

- **EDA y Filtros** — métricas generales, estadística descriptiva, serie de tiempo con media móvil, histogramas. Filtros dinámicos de fecha, variable y rango de valores.
- **Limpieza de datos** — eliminación de duplicados, imputación de nulos por interpolación temporal, filtrado de outliers por IQR. Comparación antes/después.
- **Detección de Outliers** — método IQR y Z-Score combinados. Visualización en serie de tiempo y boxplot. Descarga de registros anómalos en CSV.
- **Correlación** — heatmap de correlación de Pearson y dispersión temperatura vs. humedad con línea de tendencia.
- **Machine Learning** (2 algoritmos):
  1. **Random Forest Regressor** — predice el % de humedad del suelo a partir de temperatura y hora del día. Métricas: R², MAE, RMSE.
  2. **Random Forest Classifier** — clasifica si la planta necesita riego (humedad < 30%). Métricas: accuracy, matriz de confusión, reporte de clasificación.
  
  Ambos modelos incluyen prueba manual interactiva e importancia de variables.

---

## Instalación

```powershell
# Crear entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# Instalar todas las dependencias
pip install -r requirements.txt
```

---

## Librerías Arduino (necesarias para el ESP32)

Instalar desde el Gestor de Librerías de Arduino IDE:
- `OneWire` by Paul Stoffregen
- `DallasTemperature` by Miles Burton
- `LiquidCrystal I2C` by Frank de Brabander
- `ArduinoJson` by Benoit Blanchon

Board: **esp32 by Espressif Systems** — seleccionar **ESP32 Dev Module**.
