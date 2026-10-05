# 🌱 Sistema de Monitoreo Agrícola IoT
### Taller 1 — Corte 2 — Minería de Datos

Sistema completo de extremo a extremo para monitoreo de cultivos en tiempo real. Un ESP32 lee temperatura del suelo y humedad cada 20 segundos, los envía a una API desplegada en la nube, los almacena en PostgreSQL con TimescaleDB y los analiza con KNIME y FlowiseAI.

---

## 🏗️ Arquitectura general

```
┌─────────────────────────────────────────────────────────────┐
│                        HARDWARE                             │
│  DS18B20 (temperatura) + Sensor capacitivo (humedad)        │
│                ESP32 + Teclado 4x4 + LCD I2C                │
└──────────────────────────┬──────────────────────────────────┘
                           │  HTTP POST cada 20s
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    API REST (Render)                        │
│         FastAPI + SQLAlchemy + Pydantic                     │
│      https://parcial-bryan.onrender.com                     │
└──────────────────────────┬──────────────────────────────────┘
                           │  psycopg2
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              BASE DE DATOS (Neon)                           │
│    PostgreSQL · Proyecto: iot-taller · Rama: production     │
│         12 tablas · Hypertable TimescaleDB                  │
└──────────┬───────────────────────────────┬──────────────────┘
           │                               │
           ▼                               ▼
┌──────────────────┐             ┌─────────────────────┐
│  KNIME Analytics │             │  FlowiseAI (Agente) │
│  Dashboard +     │             │  Chat en lenguaje   │
│  Dataset CSV     │             │  natural            │
└──────────────────┘             └─────────────────────┘
```

---

## 📁 Estructura del proyecto

```
parcial_bryan/
│
├── 📄 README.md                    ← estás aquí
├── 📄 requirements.txt             ← dependencias del proyecto completo
├── 📄 .env.example                 ← plantilla de variables de entorno
├── 📄 app.py                       ← dashboard Streamlit
│
├── 📂 esp32_sensor/
│   └── esp32_sensor.ino            ← código completo del ESP32
│
└── 📂 fastapi_iot_api/             ← API REST
    ├── 📄 .env                     ← variables reales (NO subir a git)
    ├── 📄 .env.example
    ├── 📄 requirements.txt
    ├── 📄 runtime.txt              ← fuerza Python 3.11 en Render
    ├── 📂 sql/
    │   └── init_timescale.sql      ← script original de creación de tablas
    └── 📂 app/
        ├── main.py                 ← punto de entrada FastAPI
        ├── 📂 core/                ← configuración y conexión a BD
        ├── 📂 models/              ← 12 modelos ORM (uno por tabla)
        ├── 📂 schemas/             ← validación Pydantic
        ├── 📂 repositories/        ← consultas SQL
        ├── 📂 services/            ← lógica de negocio
        ├── 📂 routers/             ← endpoints HTTP
        └── 📂 middleware/          ← logging de peticiones
```

---

## 🔌 Componente 1 — Circuito ESP32

### Mapa de pines

| Componente | Pin ESP32 | Notas |
|------------|-----------|-------|
| DS18B20 (temperatura) | GPIO 4 | Protocolo OneWire, requiere resistencia 4.7kΩ |
| Sensor capacitivo (humedad) | GPIO 34 | Señal analógica ADC |
| LCD I2C — SDA | GPIO 22 | Dirección I2C: 0x27 |
| LCD I2C — SCL | GPIO 23 | |
| Teclado fila 1 | GPIO 13 | |
| Teclado fila 2 | GPIO 12 | ⚠️ Puede afectar el boot si está en HIGH |
| Teclado fila 3 | GPIO 14 | |
| Teclado fila 4 | GPIO 27 | |
| Teclado columna 1 | GPIO 26 | |
| Teclado columna 2 | GPIO 25 | |
| Teclado columna 3 | GPIO 33 | |
| Teclado columna 4 | GPIO 32 | |

### Menú del teclado matricial

| Tecla | Qué muestra en el LCD | Concepto analítico aplicado |
|-------|----------------------|----------------------------|
| `1` | Valor actual de temperatura y humedad | Estadística descriptiva en tiempo real |
| `2` | Promedio de la última hora | Media aritmética sobre el buffer |
| `3` | Máximo y mínimo desde el encendido | Rango estadístico |
| `4` | Desviación estándar y tendencia | Dispersión + comparación de mitades |
| `5` | Si la última lectura es outlier | Z-score > 2.0 |
| `6` | Cuántas lecturas superaron el umbral | Detección de anomalías |
| `7` | Estado WiFi y conexión a la nube | Monitoreo del sistema |
| `#` / `*` | Volver a la pantalla de inicio | — |

La pantalla vuelve sola al inicio después de 15 segundos sin actividad.

### Calibración del sensor de humedad

El sensor capacitivo requiere calibración según el suelo donde se use:

```cpp
int valorSeco   = 3400;  // lectura RAW al aire (~3400-3500)
int valorHumedo = 1600;  // lectura RAW en tierra saturada (~1400-1600)
```

Si los valores de humedad no tienen sentido, ajusta estos dos números
leyendo el RAW en el Serial Monitor con el sensor al aire y sumergido.

### Librerías requeridas en Arduino IDE

Instálalas desde **Herramientas → Administrar bibliotecas**:

| Librería | Autor | Para qué se usa |
|----------|-------|-----------------|
| `OneWire` | Paul Stoffregen | Comunicación con el DS18B20 |
| `DallasTemperature` | Miles Burton | Leer temperatura del DS18B20 |
| `LiquidCrystal I2C` | Frank de Brabander | Controlar la pantalla LCD |
| `ArduinoJson` | Benoit Blanchon | Construir el JSON del POST |
| `Keypad` | Mark Stanley | Leer el teclado matricial |

**Board:** ESP32 Dev Module (paquete `esp32` de Espressif Systems)

---

## ☁️ Componente 2 — API REST (FastAPI en Render)

La API está desplegada en: **https://parcial-bryan.onrender.com**  
Documentación interactiva (Swagger): **https://parcial-bryan.onrender.com/docs**

> ⚠️ Render en el plan gratuito hiberna el servicio tras 15 minutos de inactividad.
> La primera petición puede tardar hasta 60 segundos mientras "despierta".

### Endpoints disponibles

| Método | Ruta | Autenticación | Descripción |
|--------|------|---------------|-------------|
| `GET` | `/health` | — | Verifica que la API está viva |
| `POST` | `/api/v1/dispositivos` | — | Registra un ESP32 por su MAC |
| `GET` | `/api/v1/dispositivos` | — | Lista todos los dispositivos |
| `GET` | `/api/v1/dispositivos/{mac}` | — | Busca un dispositivo por MAC |
| `POST` | `/api/v1/lecturas` | `X-API-Key` | El ESP32 manda sus lecturas aquí |
| `GET` | `/api/v1/lecturas` | — | Historial con filtros de fecha y sensor |
| `GET` | `/api/v1/alertas` | — | Lecturas que superaron un umbral |
| `GET` | `/api/v1/outliers` | — | Valores atípicos detectados por z-score |
| `POST` | `/api/v1/conexion` | `X-API-Key` | ESP32 reporta su estado WiFi |
| `POST` | `/api/v1/menu` | `X-API-Key` | Registra qué tecla se pulsó |

### Formato del POST que manda el ESP32

```json
POST /api/v1/lecturas
X-API-Key: 1UmaEZRqgtvfpNQx4zcYsVwn
Content-Type: application/json

{
  "mac_address": "20:43:a8:66:81:5c",
  "lecturas": [
    { "tipo_sensor": "temperatura_ds18b20",     "valor": 35.25 },
    { "tipo_sensor": "humedad_suelo_capacitivo", "valor": 60.0  }
  ]
}
```

### Códigos de respuesta

| Código | Significa |
|--------|-----------|
| `201` | ✅ Lecturas guardadas correctamente |
| `401` | ❌ La API key no coincide |
| `404` | ❌ El dispositivo no está registrado en la BD |
| `422` | ❌ El JSON tiene campos incorrectos |
| `500` | ❌ Error interno — revisar logs en Render |

### Correr la API localmente

```powershell
cd fastapi_iot_api
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Crear el .env con las variables reales (ver .env.example)
python -m uvicorn app.main:app --reload
```

### Variables de entorno (.env)

```env
DATABASE_URL=postgresql+psycopg2://neondb_owner:PASSWORD@ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
API_KEY_ESP32=1UmaEZRqgtvfpNQx4zcYsVwn
```

---

## 🗄️ Componente 3 — Base de datos (Neon)

**Proyecto:** iot-taller &nbsp;|&nbsp; **Rama:** production &nbsp;|&nbsp; **BD:** neondb

### Las 12 tablas

| Tabla | Descripción |
|-------|-------------|
| `ubicaciones` | Lugares donde están instalados los dispositivos |
| `dispositivos` | ESP32 registrados, identificados por MAC |
| `tipos_sensor` | Catálogo de sensores con rangos físicos válidos |
| `sensores` | Cada sensor físico conectado a cada dispositivo |
| `lecturas` | ⭐ Hypertable TimescaleDB — todas las mediciones |
| `niveles_alerta` | Niveles de severidad: bajo, medio, alto |
| `umbrales_alerta` | Límites por tipo de sensor para generar alertas |
| `alertas` | Lecturas que superaron un umbral |
| `outliers_detectados` | Valores atípicos detectados por z-score |
| `estado_conexion` | Historial de conexión WiFi del ESP32 |
| `consultas_menu` | Registro de teclas pulsadas en el teclado |
| `menu_opciones` | Catálogo de las 7 opciones del menú LCD |

### Volumen de datos esperado

Con 2 sensores enviando cada 20 segundos:

| Periodo | Lecturas por sensor | Total (2 sensores) |
|---------|--------------------|--------------------|
| 1 hora | 180 | 360 |
| 1 día | 4.320 | 8.640 |
| 1 semana | 30.240 | 60.480 |
| 1 mes | 129.600 | 259.200 |

---

## 📊 Componente 4 — Análisis en KNIME

### Conexión a Neon desde KNIME

Usar el nodo **PostgreSQL Connector** con estos datos:

| Campo | Valor |
|-------|-------|
| Hostname | `ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech` |
| Port | `5432` |
| Database | `neondb` |
| Username | `neondb_owner` |
| Password | pídela al equipo |
| SSL | activado (`sslmode=require`) |

URL JDBC (alternativa para pegar directo):
```
jdbc:postgresql://ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech/neondb?sslmode=require
```

### Query principal para el dataset

Pegar en el nodo **DB Query Reader**. Une todas las tablas relevantes en un solo dataset:

```sql
SELECT
    l.tiempo,
    l.valor,
    l.reenviada,
    s.codigo              AS sensor,
    t.nombre              AS tipo_sensor,
    t.unidad,
    t.valor_min_fisico,
    t.valor_max_fisico,
    d.nombre              AS dispositivo,
    d.intervalo_envio_seg,
    u.nombre              AS ubicacion
FROM lecturas l
JOIN sensores s      ON l.id_sensor      = s.id_sensor
JOIN tipos_sensor t  ON s.id_tipo_sensor = t.id_tipo_sensor
JOIN dispositivos d  ON s.id_dispositivo = d.id_dispositivo
JOIN ubicaciones u   ON d.id_ubicacion   = u.id_ubicacion
WHERE l.recibido_en >= '2026-10-05'
ORDER BY l.tiempo DESC;
```

> El filtro `recibido_en >= '2026-10-05'` es importante — excluye datos de prueba
> cargados antes y deja solo las lecturas reales del ESP32.

### Flujo de trabajo sugerido en KNIME

```
PostgreSQL Connector
        │
        └── DB Query Reader  ──────────────────────────────────────┐
                │                                                   │
                └── DB to Table                              (tabla alertas)
                        │
                        ├── Missing Value (imputación nulos)
                        │
                        ├── Duplicate Row Filter
                        │
                        ├── Normalizer (min-max o z-score)
                        │
                        ├── Statistics Node  ── descriptivos
                        │
                        ├── Scatter Plot / Line Plot  ── visualización
                        │
                        ├── Linear Regression / Moving Average  ── tendencia
                        │
                        └── CSV Writer  ── dataset limpio exportado
```

### Tablas útiles para cada análisis

| Análisis | Tabla principal |
|----------|----------------|
| Serie temporal de mediciones | `lecturas` |
| Análisis de anomalías | `alertas` + `umbrales_alerta` |
| Validación de outliers | `outliers_detectados` |
| Disponibilidad del sistema | `estado_conexion` |
| Uso del menú físico | `consultas_menu` |

---

## ⚠️ Convenciones importantes

Estos valores deben coincidir exactamente entre la BD, la API y el ESP32.
Si cambias uno en un lado, cámbialo en todos.

| Valor | Dónde aparece | Formato exacto |
|-------|--------------|----------------|
| Código sensor temperatura | ESP32 `tipo_sensor`, BD `sensores.codigo`, BD `tipos_sensor.nombre` | `temperatura_ds18b20` |
| Código sensor humedad | ESP32 `tipo_sensor`, BD `sensores.codigo`, BD `tipos_sensor.nombre` | `humedad_suelo_capacitivo` |
| MAC del ESP32 | ESP32 `MAC_ESP32`, BD `dispositivos.direccion_mac` | `20:43:a8:66:81:5c` |
| API Key | ESP32 `API_KEY`, `.env` `API_KEY_ESP32`, Render env vars | `1UmaEZRqgtvfpNQx4zcYsVwn` |
| Estado de alerta | BD `alertas.estado` (check constraint) | `ACTIVA` / `RECONOCIDA` / `RESUELTA` |
