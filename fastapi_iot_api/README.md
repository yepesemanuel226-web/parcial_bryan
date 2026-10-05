# ⚡ API REST — fastapi_iot_api

API en FastAPI que recibe las lecturas del ESP32 y las guarda en Neon.  
Desplegada en Render: **https://parcial-bryan.onrender.com**  
Swagger UI: **https://parcial-bryan.onrender.com/docs**

---

## 📁 Estructura interna

```
fastapi_iot_api/
│
├── 📄 .env                   ← variables reales (NO subir a git)
├── 📄 .env.example           ← plantilla
├── 📄 requirements.txt
├── 📄 runtime.txt            ← fuerza Python 3.11 en Render
│
├── 📂 sql/
│   └── init_timescale.sql    ← script original de creación de tablas
│
└── 📂 app/
    ├── main.py               ← registra routers y middleware
    │
    ├── 📂 core/
    │   ├── config.py         ← lee variables del .env con pydantic-settings
    │   └── database.py       ← crea el engine SQLAlchemy y get_db()
    │
    ├── 📂 models/            ← una clase por tabla (ORM SQLAlchemy)
    │   ├── ubicacion.py
    │   ├── dispositivo.py
    │   ├── tipo_sensor.py
    │   ├── sensor.py
    │   ├── lectura.py        ← hypertable TimescaleDB
    │   ├── nivel_alerta.py
    │   ├── umbral_alerta.py
    │   ├── alerta.py
    │   ├── outlier_detectado.py
    │   ├── estado_conexion.py
    │   ├── consulta_menu.py
    │   └── menu_opcion.py
    │
    ├── 📂 schemas/           ← validación Pydantic de entrada y salida
    │   ├── lectura.py        ← PayloadESP32, LecturaOut, AlertaOut, etc.
    │   └── dispositivo.py    ← DispositivoCreate, DispositivoOut
    │
    ├── 📂 repositories/      ← toda la lógica SQL aquí, nunca en routers
    │   ├── dispositivo_repository.py
    │   └── lectura_repository.py
    │
    ├── 📂 services/          ← reglas de negocio (rangos, alertas, outliers)
    │   └── lectura_service.py
    │
    ├── 📂 routers/           ← endpoints HTTP
    │   ├── lecturas.py       ← /api/v1/lecturas, /alertas, /outliers, etc.
    │   └── dispositivos.py   ← /api/v1/dispositivos
    │
    └── 📂 middleware/
        └── logging_middleware.py  ← loguea cada petición en consola
```

---

## 🚀 Correr localmente

```powershell
# Desde la carpeta fastapi_iot_api/
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Crear el .env con las variables reales (copiar desde .env.example)
python -m uvicorn app.main:app --reload
```

Swagger disponible en: http://127.0.0.1:8000/docs

---

## 🔗 Endpoints

### Dispositivos

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/dispositivos` | Registra el ESP32 por su MAC. Hacerlo una sola vez antes de que empiece a enviar datos. |
| `GET` | `/api/v1/dispositivos` | Lista todos los dispositivos registrados. |
| `GET` | `/api/v1/dispositivos/{mac}` | Busca un dispositivo por su dirección MAC. |

### Lecturas y analítica

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/api/v1/lecturas` | `X-API-Key` | El ESP32 manda temperatura y humedad cada 20s. |
| `GET` | `/api/v1/lecturas` | — | Historial. Filtra por `id_sensor`, `desde`, `hasta` y `limite`. |
| `GET` | `/api/v1/alertas` | — | Lecturas que superaron un umbral definido en la BD. |
| `GET` | `/api/v1/outliers` | — | Valores atípicos detectados por z-score. |

### Estado del sistema

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| `POST` | `/api/v1/conexion` | `X-API-Key` | El ESP32 reporta su estado WiFi y reintentos. |
| `POST` | `/api/v1/menu` | `X-API-Key` | Registra qué tecla pulsó el usuario en el teclado físico. |
| `GET` | `/health` | — | Verifica que la API está viva. |

---

## 📨 Payload del ESP32

El ESP32 manda este JSON cada 20 segundos al endpoint `POST /api/v1/lecturas`:

```json
{
  "mac_address": "20:43:a8:66:81:5c",
  "lecturas": [
    { "tipo_sensor": "temperatura_ds18b20",     "valor": 35.25 },
    { "tipo_sensor": "humedad_suelo_capacitivo", "valor": 60.0  }
  ]
}
```

Con el header:
```
X-API-Key: 1UmaEZRqgtvfpNQx4zcYsVwn
```

### Códigos de respuesta

| Código | Significa | Qué hacer |
|--------|-----------|-----------|
| `201` | ✅ Guardado | Todo bien |
| `401` | ❌ API key incorrecta | Verificar que coincide en el ESP32 y en el .env |
| `404` | ❌ Dispositivo no existe | Registrar el ESP32 primero con POST /api/v1/dispositivos |
| `422` | ❌ JSON malformado | Revisar los campos del payload |
| `500` | ❌ Error interno | Abrir los logs en Render y buscar el traceback |

---

## ⚙️ Variables de entorno

Crear `fastapi_iot_api/.env` (no subir a git):

```env
DATABASE_URL=postgresql+psycopg2://neondb_owner:PASSWORD@ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
API_KEY_ESP32=1UmaEZRqgtvfpNQx4zcYsVwn
```

En Render estas mismas dos variables van en **Environment → Add variable**.

---

## ⚠️ Convenciones del código

Estos valores deben coincidir exactamente entre la BD, la API y el ESP32.
Cámbialos en todos lados o en ninguno.

### Códigos de sensor

En `sensores.codigo`, en `tipos_sensor.nombre` y en el payload del ESP32,
los valores son exactamente estos — minúsculas con guión bajo:

```
temperatura_ds18b20
humedad_suelo_capacitivo
```

### MAC del dispositivo

En el ESP32:
```cpp
const char* MAC_ESP32 = "20:43:a8:66:81:5c";
```
En `dispositivos.direccion_mac`: exactamente igual, minúsculas con dos puntos.

### API Key

En el ESP32:
```cpp
const char* API_KEY = "1UmaEZRqgtvfpNQx4zcYsVwn";
```
En `.env`: `API_KEY_ESP32=1UmaEZRqgtvfpNQx4zcYsVwn`  
En Render: variable de entorno con el mismo valor.

### Estado de alertas

La columna `alertas.estado` tiene un check constraint en la BD.
Solo acepta estos valores, **en mayúsculas**:

```
ACTIVA
RECONOCIDA
RESUELTA
```

Si mandas `activa` en minúsculas, la BD lo rechaza con error 500.

### Intervalo de envío

```cpp
const long intervaloCaptura = 20000;  // 20 segundos
```

En `dispositivos.intervalo_envio_seg` el valor registrado es `20`.

---

## 🗄️ Capa de datos — cómo está organizado

La API sigue un patrón por capas. Cada capa tiene una responsabilidad:

```
Router  →  recibe el HTTP, valida con Pydantic, responde JSON
  │
Service →  aplica las reglas de negocio (rangos, alertas, outliers)
  │
Repository → hace las queries SQL, nunca hay SQL en otra capa
  │
Model   →  define la tabla en SQLAlchemy
```

**Lo que hace el service cuando llega una lectura:**
1. Busca el dispositivo por MAC — si no existe, devuelve 404
2. Busca o crea el sensor por código
3. Guarda la lectura en `lecturas`
4. Verifica si el valor supera algún umbral → crea registro en `alertas`
5. Calcula z-score → si > 2.0, crea registro en `outliers_detectados`
6. Devuelve 201 con el resumen de lo que guardó
