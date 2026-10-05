# Proyecto Integrador IoT — Taller 1 Corte 2 Minería de Datos

Sistema completo de extremo a extremo: ESP32 con sensores → API REST en la nube → PostgreSQL en Neon → análisis en KNIME → agente FlowiseAI.

**Sensores:** Temperatura DS18B20 + Humedad de suelo capacitivo v2.0  
**API en producción:** https://parcial-bryan.onrender.com  
**Base de datos:** Neon (PostgreSQL)

---

## Arquitectura del sistema

```
ESP32 (sensores + teclado matricial + LCD)
    │
    │  HTTP POST cada 20s (JSON)
    ▼
FastAPI desplegada en Render
    │
    │  SQLAlchemy + psycopg2
    ▼
PostgreSQL en Neon (12 tablas)
    │
    ├── KNIME (análisis + dashboard)
    └── FlowiseAI (agente IA)
```

---

## Estructura del proyecto

```
parcial_bryan/
├── README.md
├── requirements.txt
├── .env.example
├── app.py                          # App analítica Streamlit
├── esp32_sensor/
│   └── esp32_sensor.ino            # Código ESP32 fusionado
└── fastapi_iot_api/
    ├── .env                        # Variables reales (NO subir a git)
    ├── .env.example
    ├── requirements.txt
    ├── runtime.txt                 # Fuerza Python 3.11 en Render
    ├── sql/
    │   └── init_timescale.sql
    └── app/
        ├── main.py
        ├── core/
        ├── models/                 # 12 modelos ORM
        ├── schemas/
        ├── repositories/
        ├── services/
        ├── routers/
        └── middleware/
```

---

## Componente 1 — Base de datos (Neon / PostgreSQL)

### 12 tablas

| Tabla | Descripción |
|-------|-------------|
| `ubicaciones` | Lugares donde se instalan los dispositivos |
| `dispositivos` | ESP32 registrados por MAC |
| `tipos_sensor` | Catálogo de sensores con rangos físicos |
| `sensores` | Instancia física de cada sensor por dispositivo |
| `lecturas` | **Hypertable** TimescaleDB — todas las mediciones |
| `niveles_alerta` | Niveles de severidad (bajo, medio, alto) |
| `umbrales_alerta` | Límites por tipo de sensor |
| `alertas` | Lecturas que superaron un umbral |
| `outliers_detectados` | Valores atípicos detectados por z-score |
| `estado_conexion` | Historial de conexión WiFi del ESP32 |
| `consultas_menu` | Registro de teclas pulsadas en el teclado |
| `menu_opciones` | Catálogo de opciones del menú LCD |

### Conexión directa a Neon

```
Host:     ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech
Puerto:   5432
Base de datos: neondb
Usuario:  neondb_owner
SSL:      requerido (sslmode=require)
```

---

## Componente 2 — Circuito ESP32

### Hardware

| Componente | Pin ESP32 |
|------------|-----------|
| DS18B20 (temperatura) | GPIO 4 |
| Sensor capacitivo (humedad) | GPIO 34 |
| LCD I2C (SDA) | GPIO 22 |
| LCD I2C (SCL) | GPIO 23 |
| Teclado fila 1 | GPIO 13 |
| Teclado fila 2 | GPIO 12 |
| Teclado fila 3 | GPIO 14 |
| Teclado fila 4 | GPIO 27 |
| Teclado col 1 | GPIO 26 |
| Teclado col 2 | GPIO 25 |
| Teclado col 3 | GPIO 33 |
| Teclado col 4 | GPIO 32 |

### Menú del teclado matricial

| Tecla | Función | Concepto analítico |
|-------|---------|-------------------|
| 1 | Valor actual de cada sensor | Estadística descriptiva |
| 2 | Promedio de la última hora | Media aritmética |
| 3 | Máximo y mínimo del día | Rango estadístico |
| 4 | Desviación estándar y tendencia | Dispersión y regresión |
| 5 | Detección de outliers | Z-score |
| 6 | Conteo de alertas activas | Umbral y anomalías |
| 7 | Estado de conexión WiFi/nube | Monitoreo de sistema |
| # / * | Volver al inicio | — |

### Calibración del sensor de humedad

```cpp
int valorSeco   = 3400;  // lectura al aire
int valorHumedo = 1600;  // lectura en tierra saturada
```

### Librerías Arduino requeridas

Instalar desde el Gestor de Librerías de Arduino IDE:
- `OneWire` by Paul Stoffregen
- `DallasTemperature` by Miles Burton
- `LiquidCrystal I2C` by Frank de Brabander
- `ArduinoJson` by Benoit Blanchon
- `Keypad` by Mark Stanley

Board: **ESP32 Dev Module** (esp32 by Espressif Systems)

---

## Componente 3 — API REST (FastAPI en Render)

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado de la API |
| POST | `/api/v1/dispositivos` | Registrar ESP32 por MAC |
| GET | `/api/v1/dispositivos` | Listar dispositivos |
| POST | `/api/v1/lecturas` | Recibir lecturas del ESP32 |
| GET | `/api/v1/lecturas` | Consultar historial |
| GET | `/api/v1/alertas` | Listar alertas |
| GET | `/api/v1/outliers` | Listar outliers detectados |
| POST | `/api/v1/conexion` | Reportar estado de conexión |
| POST | `/api/v1/menu` | Registrar tecla pulsada |

Documentación interactiva: https://parcial-bryan.onrender.com/docs

### Variables de entorno (.env)

```env
DATABASE_URL=postgresql+psycopg2://neondb_owner:PASSWORD@ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
API_KEY_ESP32=1UmaEZRqgtvfpNQx4zcYsVwn
```

### Correr localmente

```powershell
cd fastapi_iot_api
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# crear .env con las variables de arriba
python -m uvicorn app.main:app --reload
```

---

## Componente 4 — Análisis en KNIME

### Conexión a Neon desde KNIME

Usar el nodo **PostgreSQL Connector** con estos parámetros:

| Campo | Valor |
|-------|-------|
| Hostname | `ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech` |
| Port | `5432` |
| Database | `neondb` |
| Username | `neondb_owner` |
| Password | *(solicitar al equipo)* |
| SSL | Activado — `sslmode=require` |

O usar directamente la URL JDBC:
```
jdbc:postgresql://ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech/neondb?sslmode=require
```

### Query principal para el dataset

Pegar en el nodo **DB Query Reader**:

```sql
SELECT
    l.tiempo,
    l.valor,
    l.reenviada,
    s.codigo          AS sensor,
    t.nombre          AS tipo_sensor,
    t.unidad,
    t.valor_min_fisico,
    t.valor_max_fisico,
    d.nombre          AS dispositivo,
    u.nombre          AS ubicacion
FROM lecturas l
JOIN sensores s      ON l.id_sensor      = s.id_sensor
JOIN tipos_sensor t  ON s.id_tipo_sensor = t.id_tipo_sensor
JOIN dispositivos d  ON s.id_dispositivo = d.id_dispositivo
JOIN ubicaciones u   ON d.id_ubicacion   = u.id_ubicacion
WHERE l.recibido_en >= '2026-10-05'
ORDER BY l.tiempo DESC;
```

> **Nota:** el filtro `recibido_en >= '2026-10-05'` excluye datos de prueba anteriores y trabaja solo con las lecturas reales del ESP32.

### Tablas disponibles para análisis

| Tabla | Uso sugerido en KNIME |
|-------|----------------------|
| `lecturas` | Dataset principal — serie temporal |
| `alertas` | Análisis de anomalías |
| `outliers_detectados` | Validación de outliers z-score |
| `sensores` | Metadatos de cada sensor |
| `tipos_sensor` | Rangos físicos para normalización |
| `estado_conexion` | Análisis de disponibilidad del sistema |

### Flujo sugerido en KNIME

```
PostgreSQL Connector
    └── DB Query Reader (query principal)
            └── DB to Table
                    └── Missing Value (imputación)
                            └── Duplicate Row Filter
                                    └── Normalizer
                                            └── Statistics / Scatter Plot / ...
                                                    └── CSV Writer (dataset limpio)
```
