# API IoT - Taller Integrador (Grupo D)

API REST en FastAPI que recibe datos de un ESP32 con dos sensores:
- **DS18B20** (temperatura digital, 1-Wire)
- **Sensor de humedad de suelo capacitivo v2.0** (analógico)

Los valida y los guarda en PostgreSQL con **TimescaleDB**.

## Estructura del proyecto (POO por capas)

```
app/
  core/         -> configuración y conexión a la base de datos
  models/       -> modelos SQLAlchemy (= tablas de PostgreSQL)
  schemas/      -> validación de entrada/salida con Pydantic
  repositories/ -> clases que hacen las consultas SQL (una por entidad)
  services/     -> lógica de negocio (validación de rango, anomalías)
  routers/      -> endpoints HTTP
  middleware/   -> log de auditoría de cada petición
  main.py       -> arma la app y registra routers/middleware
sql/
  init_timescale.sql -> script para que tu compañera cree la BD (usa
                         EXACTAMENTE los mismos nombres que los modelos)
```

## Cómo correrla localmente

```bash
python -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # y edita DATABASE_URL con los datos reales
# tu compañera te pasa host/usuario/password de PostgreSQL

uvicorn app.main:app --reload
```

Documentación interactiva automática: http://127.0.0.1:8000/docs

## Coordinación con tu compañera (base de datos)

1. Pásale `sql/init_timescale.sql` — es el script que crea las 7 tablas
   (grupos, dispositivos, tipos_sensor, sensores, lecturas, alertas,
   api_logs) con TimescaleDB ya configurado.
2. Ella corre ese script en PostgreSQL (necesita la extensión
   `timescaledb` instalada) y te devuelve la cadena de conexión.
3. Si ella necesita cambiar un nombre de columna, avísale a quien toque
   el modelo correspondiente en `app/models/` — **los dos archivos
   tienen que coincidir siempre**.

## Flujo completo para probar con tus compañeros

1. **Base de datos**: correr `sql/init_timescale.sql`.
2. **API** (tú): `uvicorn app.main:app --reload`.
3. Registrar el dispositivo una vez (lo hace quien programa el ESP32,
   o tú mismo para probar):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/dispositivos \
  -H "Content-Type: application/json" \
  -d '{"grupo_id": 1, "nombre": "ESP32-D", "mac_address": "AA:BB:CC:DD:EE:01", "ubicacion": "Maceta 1"}'
```

4. **ESP32** (o `curl` para probar sin el hardware) envía lecturas:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/lecturas \
  -H "Content-Type: application/json" \
  -H "X-API-Key: cambia-esta-clave-por-una-segura" \
  -d '{
        "mac_address": "AA:BB:CC:DD:EE:01",
        "lecturas": [
          {"tipo_sensor": "temperatura_ds18b20", "valor": 24.6},
          {"tipo_sensor": "humedad_suelo_capacitivo", "valor": 63.2}
        ]
      }'
```

5. **Streamlit / Power BI** consumen:
   - `GET /api/v1/lecturas` (con filtros `sensor_id`, `desde`, `hasta`)
     para pruebas rápidas desde la API.
   - Power BI, según el taller, debe conectarse **directo a
     PostgreSQL** (no a la API), así que a tu compañera de BD le sirve
     tener el connection string listo para eso también.

## Notas

- Los rangos válidos de cada sensor están en la tabla `tipos_sensor`
  (`valor_min`/`valor_max`). Ahora mismo puse -10°C a 60°C para la
  temperatura y 0% a 100% para la humedad — ajústalos si tu docente
  definió otros rangos.
- Cualquier lectura fuera de rango se guarda igual (para no perder el
  dato) pero además genera un registro en `alertas`, que es lo que
  pide el punto de "identificar valores atípicos".
- La API key del ESP32 (`X-API-Key`) es solo un control simple para
  que no cualquiera pueda escribir en la base de datos.
