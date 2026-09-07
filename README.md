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

#### 📊 EDA y Filtros
Punto de entrada principal de la app. Muestra un resumen general de los datos capturados por el ESP32:
- **4 métricas** en la parte superior: total de registros, humedad promedio, temperatura promedio y rango de fechas activo.
- **Estadística descriptiva** (media, desviación estándar, mínimo, máximo, percentiles) de ambas variables.
- **Serie de tiempo interactiva** con los datos crudos y una media móvil ajustable (de 10 a 500 muestras) para suavizar el ruido del sensor.
- **Histogramas con boxplot** para visualizar la distribución de cada variable.
- **Filtros dinámicos** en la barra lateral:
  - Rango de fechas (desde / hasta)
  - Selección de variables a graficar
  - Filtro por rango de valor numérico de cualquier variable
  - Opción para excluir outliers con IQR

#### 🧹 Limpieza de datos
Muestra el proceso de limpieza aplicado automáticamente sobre los datos filtrados:
1. **Eliminación de duplicados** exactos.
2. **Imputación de nulos** por interpolación lineal temporal (apropiado para series de tiempo).
3. **Filtrado de outliers** por rango intercuartílico (IQR), activable desde la barra lateral.

Incluye un reporte con el número de filas originales, filas finales, nulos detectados por columna, duplicados eliminados y outliers removidos. También muestra un **boxplot comparativo antes/después** de la limpieza.

#### 🔍 Detección de Outliers
Detecta valores atípicos combinando dos métodos estadísticos:
- **IQR** (Rango Intercuartílico): marca como outlier todo valor fuera de Q1 − factor×IQR y Q3 + factor×IQR. El factor es ajustable desde la UI (1.0 a 3.0).
- **Z-Score**: marca como outlier todo valor cuyo puntaje Z supere un umbral configurable (1.5 a 4.0, por defecto ±3).

Un punto se considera anómalo si lo detecta **cualquiera** de los dos métodos. La sección muestra:
- Métricas: total de registros, cantidad y porcentaje de outliers detectados, rango normal IQR.
- **Serie de tiempo** con los outliers resaltados en rojo y líneas de límite.
- **Boxplot** con los puntos sospechosos marcados.
- **Tabla descargable** en CSV con todos los registros anómalos y sus puntajes Z.

#### 🔗 Correlación
Analiza la relación estadística entre humedad y temperatura:
- **Heatmap de correlación de Pearson** entre ambas variables, usando los datos ya limpios y filtrados.
- **Gráfico de dispersión** temperatura vs. humedad con línea de tendencia OLS y coloreado por hora del día (para identificar si el momento del día influye).
- Muestra el **coeficiente de correlación** exacto con interpretación directa.

#### 🤖 Machine Learning
Dos modelos entrenados con los datos reales del ESP32, usando temperatura y la hora del día (codificada en seno/coseno para capturar la ciclicidad) como variables predictoras.

**Modelo 1 — Random Forest Regressor** (pestaña "Regresión"):
- **Objetivo:** predecir el porcentaje de humedad del suelo.
- **Métricas:** R² (qué tanto explica el modelo), MAE (error absoluto medio en %), RMSE (error cuadrático medio en %).
- Gráfico de **real vs. predicho** sobre una muestra de 200 puntos.
- **Importancia de variables**: qué variable aporta más al modelo.
- **Prueba manual interactiva**: ingresás una temperatura y una hora y el modelo predice la humedad estimada.

**Modelo 2 — Random Forest Classifier** (pestaña "Clasificación"):
- **Objetivo:** clasificar si la planta necesita riego (humedad < 30%).
- **Métricas:** accuracy, cantidad de casos positivos en el set de prueba.
- **Matriz de confusión** para ver verdaderos/falsos positivos y negativos.
- Reporte de clasificación completo (precision, recall, F1).
- **Prueba manual interactiva**: ingresás temperatura y hora y el modelo dice si necesita riego con su probabilidad.

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
