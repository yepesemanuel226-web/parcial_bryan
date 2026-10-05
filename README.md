# Proyecto IoT — Taller 1 Corte 2 Minería de Datos

ESP32 con sensores que manda datos cada 20 segundos a una API en Render, que los guarda en Neon (PostgreSQL). Desde ahí KNIME analiza los datos y FlowiseAI responde preguntas sobre ellos.

**Sensores:** Temperatura DS18B20 + Humedad de suelo capacitivo v2.0  
**API:** https://parcial-bryan.onrender.com  
**BD:** Neon (PostgreSQL)

---

## Cómo funciona

```
ESP32 (sensores + teclado + LCD)
    │  POST cada 20s
    ▼
FastAPI en Render
    │
    ▼
PostgreSQL en Neon (12 tablas)
    │
    ├── KNIME
    └── FlowiseAI
```

---

## Archivos del proyecto

```
parcial_bryan/
├── README.md
├── requirements.txt
├── app.py                      # Streamlit
├── esp32_sensor/
│   └── esp32_sensor.ino        # Código del ESP32
└── fastapi_iot_api/
    ├── .env                    # No subir a git
    ├── .env.example
    ├── requirements.txt
    ├── runtime.txt
    ├── sql/
    │   └── init_timescale.sql
    └── app/
        ├── main.py
        ├── core/
        ├── models/
        ├── schemas/
        ├── repositories/
        ├── services/
        ├── routers/
        └── middleware/
```

---

## Circuito ESP32

### Pines

| Componente | Pin |
|------------|-----|
| DS18B20 (temperatura) | GPIO 4 |
| Sensor capacitivo (humedad) | GPIO 34 |
| LCD SDA | GPIO 22 |
| LCD SCL | GPIO 23 |
| Teclado fila 1 | GPIO 13 |
| Teclado fila 2 | GPIO 12 |
| Teclado fila 3 | GPIO 14 |
| Teclado fila 4 | GPIO 27 |
| Teclado col 1 | GPIO 26 |
| Teclado col 2 | GPIO 25 |
| Teclado col 3 | GPIO 33 |
| Teclado col 4 | GPIO 32 |

### Menú del teclado

| Tecla | Qué muestra | Concepto |
|-------|-------------|----------|
| 1 | Valor actual de cada sensor | Estadística descriptiva |
| 2 | Promedio de la última hora | Media aritmética |
| 3 | Máximo y mínimo del día | Rango estadístico |
| 4 | Desviación estándar y tendencia | Dispersión y regresión |
| 5 | Outliers detectados | Z-score |
| 6 | Alertas activas | Umbrales y anomalías |
| 7 | Estado WiFi y nube | Monitoreo del sistema |
| # / * | Volver al inicio | — |

### Calibración humedad

```cpp
int valorSeco   = 3400;  // al aire
int valorHumedo = 1600;  // en tierra saturada
```

### Librerías que hay que instalar en Arduino IDE

- `OneWire` — Paul Stoffregen
- `DallasTemperature` — Miles Burton
- `LiquidCrystal I2C` — Frank de Brabander
- `ArduinoJson` — Benoit Blanchon
- `Keypad` — Mark Stanley

Board: **ESP32 Dev Module**

---

## API (FastAPI)

### Endpoints

| Método | Ruta | Qué hace |
|--------|------|----------|
| GET | `/health` | Verificar que la API está viva |
| POST | `/api/v1/dispositivos` | Registrar el ESP32 por MAC |
| GET | `/api/v1/dispositivos` | Ver dispositivos registrados |
| POST | `/api/v1/lecturas` | El ESP32 manda sus lecturas aquí |
| GET | `/api/v1/lecturas` | Consultar el historial |
| GET | `/api/v1/alertas` | Ver alertas generadas |
| GET | `/api/v1/outliers` | Ver outliers detectados |
| POST | `/api/v1/conexion` | El ESP32 reporta su estado de conexión |
| POST | `/api/v1/menu` | Registra qué tecla se pulsó |

Swagger: https://parcial-bryan.onrender.com/docs

### .env

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
python -m uvicorn app.main:app --reload
```

---

## Base de datos (Neon)

### Tablas

| Tabla | Para qué es |
|-------|-------------|
| `ubicaciones` | Dónde está instalado el dispositivo |
| `dispositivos` | El ESP32, identificado por MAC |
| `tipos_sensor` | Catálogo de sensores con rangos válidos |
| `sensores` | Cada sensor físico conectado al ESP32 |
| `lecturas` | Todas las mediciones — es la hypertable |
| `niveles_alerta` | Bajo, medio, alto |
| `umbrales_alerta` | Límites por tipo de sensor |
| `alertas` | Lecturas que pasaron un umbral |
| `outliers_detectados` | Valores raros detectados por z-score |
| `estado_conexion` | Historial de conexión WiFi del ESP32 |
| `consultas_menu` | Registro de teclas pulsadas |
| `menu_opciones` | Las 7 opciones del menú LCD |

---

## Para KNIME

### Conexión a Neon

En el nodo **PostgreSQL Connector** pon esto:

| Campo | Valor |
|-------|-------|
| Hostname | `ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech` |
| Port | `5432` |
| Database | `neondb` |
| Username | `neondb_owner` |
| Password | pídela al equipo |
| SSL | activado |

O si prefieres usar la URL JDBC directa:
```
jdbc:postgresql://ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech/neondb?sslmode=require
```

### Query para el dataset principal

Pégala en el nodo **DB Query Reader**:

```sql
SELECT
    l.tiempo,
    l.valor,
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

El filtro `recibido_en >= '2026-10-05'` es importante — excluye datos de prueba que se cargaron antes y deja solo las lecturas reales del ESP32.

### Nodos sugeridos

```
PostgreSQL Connector
    └── DB Query Reader
            └── DB to Table
                    └── Missing Value
                            └── Duplicate Row Filter
                                    └── Normalizer
                                            └── Statistics / Gráficas / ...
                                                    └── CSV Writer
```
