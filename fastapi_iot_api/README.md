# API IoT — fastapi_iot_api

API REST en FastAPI que recibe los datos del ESP32 y los guarda en Neon.  
Está desplegada en Render: https://parcial-bryan.onrender.com

---

## Estructura

```
app/
  core/         configuración y conexión a la BD
  models/       tablas de PostgreSQL en SQLAlchemy
  schemas/      validación de entrada/salida con Pydantic
  repositories/ consultas SQL
  services/     lógica de negocio (rangos, alertas, outliers)
  routers/      endpoints HTTP
  middleware/   log de peticiones en consola
  main.py       punto de entrada
sql/
  init_timescale.sql  script original de creación de tablas
```

---

## Correr localmente

```powershell
cd fastapi_iot_api
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Swagger en: http://127.0.0.1:8000/docs

---

## Convenciones del código — léelas antes de tocar algo

Estos son los valores exactos que deben coincidir entre la BD, la API y el ESP32.
Si cambias uno en un lado, cámbialo en todos.

### Códigos de sensor

En la tabla `sensores` (columna `codigo`) y en el ESP32 (`tipo_sensor`), los valores son exactamente estos, en minúsculas y con guión bajo:

```
temperatura_ds18b20
humedad_suelo_capacitivo
```

En el ESP32 el payload se ve así:
```json
{
  "tipo_sensor": "temperatura_ds18b20",
  "valor": 35.25
}
```

En la BD la columna `sensores.codigo` tiene exactamente ese mismo texto.  
En `tipos_sensor.nombre` también debe coincidir exactamente.

### MAC address del ESP32

En el código del ESP32:
```cpp
const char* MAC_ESP32 = "20:43:a8:66:81:5c";
```

En la BD (`dispositivos.direccion_mac`) debe estar guardada igual:
```
20:43:a8:66:81:5c
```
Minúsculas, con dos puntos. Si la cambias en el ESP32, actualízala en la BD también.

### API Key

En el ESP32:
```cpp
const char* API_KEY = "1UmaEZRqgtvfpNQx4zcYsVwn";
```

En el `.env` de la API:
```env
API_KEY_ESP32=1UmaEZRqgtvfpNQx4zcYsVwn
```

En Render, en las variables de entorno, el mismo valor.  
El ESP32 la manda en el header `X-API-Key`. Si no coincide, la API devuelve 401.

### Estado de alertas

La tabla `alertas` tiene un check constraint que solo acepta estos valores en la columna `estado`, en mayúsculas:

```
ACTIVA
RECONOCIDA
RESUELTA
```

En el código de la API (`models/alerta.py` y `repositories/lectura_repository.py`) se usa `"ACTIVA"`. No cambies eso a minúsculas o la BD lo rechaza.

### Intervalo de envío

El ESP32 envía cada 20 segundos:
```cpp
const long intervaloCaptura = 20000;
```

En la BD (`dispositivos.intervalo_envio_seg`) el valor registrado es `20`.

### URL de la API en el ESP32

```cpp
const char* API_URL = "https://parcial-bryan.onrender.com/api/v1/lecturas";
```

Si cambian la URL de Render, hay que actualizar esa línea y volver a subir el código al ESP32.

---

## Endpoints

| Método | Ruta | Header requerido | Descripción |
|--------|------|-----------------|-------------|
| GET | `/health` | — | La API está viva |
| POST | `/api/v1/dispositivos` | — | Registrar ESP32 por MAC |
| GET | `/api/v1/dispositivos` | — | Ver dispositivos |
| GET | `/api/v1/dispositivos/{mac}` | — | Buscar por MAC |
| POST | `/api/v1/lecturas` | `X-API-Key` | El ESP32 manda lecturas |
| GET | `/api/v1/lecturas` | — | Historial de lecturas |
| GET | `/api/v1/alertas` | — | Alertas generadas |
| GET | `/api/v1/outliers` | — | Outliers por z-score |
| POST | `/api/v1/conexion` | `X-API-Key` | Estado WiFi del ESP32 |
| POST | `/api/v1/menu` | `X-API-Key` | Tecla pulsada en el teclado |

---

## Formato del POST que manda el ESP32

```json
POST /api/v1/lecturas
X-API-Key: 1UmaEZRqgtvfpNQx4zcYsVwn
Content-Type: application/json

{
  "mac_address": "20:43:a8:66:81:5c",
  "lecturas": [
    {"tipo_sensor": "temperatura_ds18b20",     "valor": 35.25},
    {"tipo_sensor": "humedad_suelo_capacitivo", "valor": 60.0}
  ]
}
```

Si la API responde `201` todo salió bien.  
Si responde `404` el dispositivo no está registrado en la BD.  
Si responde `401` la API key no coincide.  
Si responde `500` hay un error interno — revisar los logs en Render.

---

## Variables de entorno

Crear `fastapi_iot_api/.env` (no subir a git):

```env
DATABASE_URL=postgresql+psycopg2://neondb_owner:PASSWORD@ep-misty-snow-b76w9eax-pooler.c-13.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
API_KEY_ESP32=1UmaEZRqgtvfpNQx4zcYsVwn
```

En Render estas mismas dos variables van en **Environment → Add variable**.
