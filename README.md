# 🌡️ Sistema IoT — Medición de Temperatura y Humedad
### Taller 1 — Corte 2 — Minería de Datos

Un ESP32 lee temperatura y humedad cada 20 segundos, los manda a una API en la nube, los guarda en PostgreSQL con TimescaleDB y los analiza con KNIME y FlowiseAI.

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        HARDWARE                             │
│         DS18B20 (temperatura) + Sensor capacitivo           │
│              ESP32 + Teclado 4x4 + LCD I2C                  │
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
├── 📄 requirements.txt
├── 📄 .env.example
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
    │   └── init_timescale.sql
    └── 📂 app/
        ├── main.py
        ├── 📂 core/                ← configuración y conexión a BD
        ├── 📂 models/              ← 12 modelos ORM
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
| DS18B20 (temperatura) | GPIO 4 | OneWire, resistencia pull-up 4.7kΩ |
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

| Tecla | Qué muestra en el LCD | Concepto analítico |
|-------|----------------------|--------------------|
| `1` | Temperatura y humedad actuales | Estadística descriptiva |
| `2` | Promedio de la última hora | Media aritmética |
| `3` | Máximo y mínimo desde el encendido | Rango estadístico |
| `4` | Desviación estándar y tendencia | Dispersión y regresión |
| `5` | Si la última lectura es outlier | Z-score > 2.0 |
| `6` | Cuántas lecturas superaron el umbral | Detección de anomalías |
| `7` | Estado WiFi y conexión a la nube | Monitoreo del sistema |
| `#` / `*` | Volver al inicio | — |

La pantalla vuelve sola al inicio tras 15 segundos de inactividad.

### Calibración del sensor de humedad

```cpp
int valorSeco   = 3400;  // lectura RAW al aire
int valorHumedo = 1600;  // lectura RAW en tierra saturada
```

Si los valores no tienen sentido, lee el RAW en el Serial Monitor
con el sensor al aire y en tierra, y ajusta estos dos números.

### Librerías requeridas en Arduino IDE

Instalar desde **Herramientas → Administrar bibliotecas**:

| Librería | Autor | Para qué |
|----------|-------|----------|
| `OneWire` | Paul Stoffregen | Comunicación DS18B20 |
| `DallasTemperature` | Miles Burton | Leer temperatura |
| `LiquidCrystal I2C` | Frank de Brabander | Pantalla LCD |
| `ArduinoJson` | Benoit Blanchon | Construir el JSON del POST |
| `Keypad` | Mark Stanley | Leer el teclado matricial |

**Board:** ESP32 Dev Module (paquete `esp32` de Espressif Systems)

---

## ☁️ Componente 2 — API REST (FastAPI en Render)

**URL:** https://parcial-bryan.onrender.com  
**Swagger:** https://parcial-bryan.onrender.com/docs

> ⚠️ Render en plan gratuito hiberna tras 15 min de inactividad.
> La primera petición puede tardar hasta 60s mientras despierta.

### Endpoints

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `GET` | `/health` | — | Verifica que la API está viva |
| `POST` | `/api/v1/dispositivos` | — | Registra el ESP32 por MAC |
| `GET` | `/api/v1/dispositivos` | — | Lista dispositivos registrados |
| `GET` | `/api/v1/dispositivos/{mac}` | — | Busca por MAC |
| `POST` | `/api/v1/lecturas` | `X-API-Key` | El ESP32 manda sus lecturas |
| `GET` | `/api/v1/lecturas` | — | Historial con filtros |
| `GET` | `/api/v1/alertas` | — | Lecturas que superaron umbral |
| `GET` | `/api/v1/outliers` | — | Outliers por z-score |
| `POST` | `/api/v1/conexion` | `X-API-Key` | Estado WiFi del ESP32 |
| `POST` | `/api/v1/menu` | `X-API-Key` | Tecla pulsada en el teclado |

### Formato del POST del ESP32

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

| Código | Qué significa |
|--------|--------------|
| `201` | ✅ Guardado correctamente |
| `401` | ❌ API key incorrecta |
| `404` | ❌ Dispositivo no registrado en la BD |
| `422` | ❌ JSON con campos incorrectos |
| `500` | ❌ Error interno — revisar logs en Render |

---

## 🗄️ Componente 3 — Base de datos (Neon)

**Proyecto:** iot-taller &nbsp;|&nbsp; **Rama:** production &nbsp;|&nbsp; **BD:** neondb

### Las 12 tablas

| Tabla | Descripción |
|-------|-------------|
| `ubicaciones` | Lugares donde están los dispositivos |
| `dispositivos` | ESP32 registrados por MAC |
| `tipos_sensor` | Catálogo con rangos físicos válidos |
| `sensores` | Cada sensor físico por dispositivo |
| `lecturas` | ⭐ Hypertable — todas las mediciones |
| `niveles_alerta` | Niveles: bajo, medio, alto |
| `umbrales_alerta` | Límites por tipo de sensor |
| `alertas` | Lecturas que pasaron un umbral |
| `outliers_detectados` | Valores atípicos por z-score |
| `estado_conexion` | Historial WiFi del ESP32 |
| `consultas_menu` | Teclas pulsadas en el teclado |
| `menu_opciones` | Catálogo de las 7 opciones del menú |

### Volumen esperado

Con 2 sensores enviando cada 20 segundos:

| Periodo | Por sensor | Total (2 sensores) |
|---------|-----------|-------------------|
| 1 hora | 180 | 360 |
| 1 día | 4.320 | 8.640 |
| 1 semana | 30.240 | 60.480 |
| 1 mes | 129.600 | 259.200 |

---

## 📊 Componente 4 — Análisis en KNIME

### Conexión a Neon

Usar el nodo **PostgreSQL Connector**:

| Campo | Valor |
|-------|-------|
| Hostname | `ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech` |
| Port | `5432` |
| Database | `neondb` |
| Username | `neondb_owner` |
| Password | pídela al equipo |
| SSL | activado (`sslmode=require`) |

URL JDBC directa:
```
jdbc:postgresql://ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech/neondb?sslmode=require
```

### Query principal

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

> El filtro `recibido_en >= '2026-10-05'` excluye datos de prueba anteriores.

### Flujo sugerido de nodos

```
PostgreSQL Connector
        │
        └── DB Query Reader
                │
                └── DB to Table
                        │
                        ├── Missing Value ──── imputar nulos
                        ├── Duplicate Row Filter
                        ├── Normalizer ──────── min-max o z-score
                        │
                        ├── Statistics ──────── descriptivos
                        ├── Line Plot ───────── serie temporal
                        ├── Scatter Plot ────── correlación
                        │
                        └── CSV Writer ──────── dataset limpio
```

### Tablas útiles según el análisis

| Análisis | Tabla |
|----------|-------|
| Serie temporal | `lecturas` |
| Anomalías | `alertas` + `umbrales_alerta` |
| Outliers | `outliers_detectados` |
| Disponibilidad | `estado_conexion` |
| Uso del menú físico | `consultas_menu` |

---

## 🤖 Componente 5 — Agente FlowiseAI

El agente está configurado en el archivo `Agente taller iot Chatflow.json`. Usa **Google Gemini** como modelo y se conecta directamente a Neon para responder preguntas en lenguaje natural sobre los datos de los sensores.

### Para importarlo en FlowiseAI

1. Tener Docker Desktop corriendo
2. Ejecutar en PowerShell:
   ```powershell
   docker start flowise
   ```
3. Abrir `http://localhost:3000`
4. Ir a **Chatflows** → **Add New** → importar `Agente taller iot Chatflow.json`
5. En el nodo **ChatGoogleGenerativeAI** agregar la credencial de Gemini
6. En el nodo **SqlDatabaseChain** reemplazar `TU_PASSWORD` con la contraseña real de Neon

### API Key de Gemini

Cada integrante debe crear la suya en **[aistudio.google.com](https://aistudio.google.com)** → Get API Key. Es gratis y tarda menos de un minuto. No compartir ni subir la clave al repo.

### Modelo

El agente usa `gemini-3-flash-preview`. Si ese modelo deja de estar disponible, cambiarlo en el nodo **ChatGoogleGenerativeAI** por el modelo más reciente disponible en AI Studio.

| Valor | Dónde aparece | Exactamente así |
|-------|--------------|-----------------|
| Código sensor temperatura | ESP32, `sensores.codigo`, `tipos_sensor.nombre` | `temperatura_ds18b20` |
| Código sensor humedad | ESP32, `sensores.codigo`, `tipos_sensor.nombre` | `humedad_suelo_capacitivo` |
| MAC del ESP32 | ESP32, `dispositivos.direccion_mac` | `20:43:a8:66:81:5c` |
| API Key | ESP32, `.env`, Render | `1UmaEZRqgtvfpNQx4zcYsVwn` |
| Estado de alerta | `alertas.estado` (check constraint) | `ACTIVA` / `RECONOCIDA` / `RESUELTA` |
