-- =============================================================
-- Script de creación de base de datos - Taller Integrador IoT
-- Sensores del grupo: DS18B20 (temperatura) + Humedad de suelo
-- capacitivo v2.0
--
-- IMPORTANTE: estos nombres de tabla y columna deben coincidir
-- EXACTO con los modelos SQLAlchemy de la carpeta app/models/.
-- Si cambias algo aquí, avísale a quien tiene la API.
-- =============================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 1) Grupos --------------------------------------------------
CREATE TABLE IF NOT EXISTS grupos (
    id            SERIAL PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    integrantes   VARCHAR(300),
    creado_en     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2) Dispositivos (ESP32) -------------------------------------
CREATE TABLE IF NOT EXISTS dispositivos (
    id            SERIAL PRIMARY KEY,
    grupo_id      INTEGER NOT NULL REFERENCES grupos(id),
    nombre        VARCHAR(100) NOT NULL,
    mac_address   VARCHAR(17) NOT NULL UNIQUE,
    ubicacion     VARCHAR(150),
    activo        BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3) Catálogo de tipos de sensor -------------------------------
CREATE TABLE IF NOT EXISTS tipos_sensor (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(50) NOT NULL UNIQUE,
    nombre        VARCHAR(100) NOT NULL,
    unidad_medida VARCHAR(20) NOT NULL,
    valor_min     NUMERIC(8,2) NOT NULL,
    valor_max     NUMERIC(8,2) NOT NULL
);

-- 4) Sensores (instancia física por dispositivo) ---------------
CREATE TABLE IF NOT EXISTS sensores (
    id              SERIAL PRIMARY KEY,
    dispositivo_id  INTEGER NOT NULL REFERENCES dispositivos(id),
    tipo_sensor_id  INTEGER NOT NULL REFERENCES tipos_sensor(id),
    pin             VARCHAR(20),
    descripcion     VARCHAR(150),
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);

-- 5) Lecturas (hypertable de TimescaleDB) -----------------------
CREATE TABLE IF NOT EXISTS lecturas (
    id          SERIAL,
    sensor_id   INTEGER NOT NULL REFERENCES sensores(id),
    valor       NUMERIC(10,3) NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, timestamp)
);

-- Convierte "lecturas" en hypertable particionada por timestamp
SELECT create_hypertable('lecturas', 'timestamp', if_not_exists => TRUE);

-- "id" ya es único (viene de una secuencia global), pero como la PK de
-- un hypertable debe incluir la columna de tiempo, agregamos esta
-- restricción UNIQUE aparte para poder referenciar "lecturas.id"
-- desde la tabla "alertas" con una llave foránea.
ALTER TABLE lecturas ADD CONSTRAINT lecturas_id_unique UNIQUE (id);

-- 6) Alertas / anomalías -----------------------------------------
CREATE TABLE IF NOT EXISTS alertas (
    id             SERIAL PRIMARY KEY,
    lectura_id     INTEGER NOT NULL REFERENCES lecturas(id),
    tipo_anomalia  VARCHAR(50) NOT NULL,
    descripcion    VARCHAR(250),
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7) Logs de la API -----------------------------------------------
CREATE TABLE IF NOT EXISTS api_logs (
    id           SERIAL PRIMARY KEY,
    endpoint     VARCHAR(150) NOT NULL,
    metodo       VARCHAR(10) NOT NULL,
    ip_origen    VARCHAR(50),
    status_code  INTEGER,
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices útiles para los filtros que usará Streamlit / Power BI
CREATE INDEX IF NOT EXISTS idx_lecturas_sensor_timestamp ON lecturas (sensor_id, timestamp DESC);

-- =============================================================
-- Datos semilla: catálogo de sensores de ESTE grupo
-- =============================================================
INSERT INTO tipos_sensor (codigo, nombre, unidad_medida, valor_min, valor_max)
VALUES
    ('temperatura_ds18b20', 'Temperatura DS18B20', '°C', -10, 60),
    ('humedad_suelo_capacitivo', 'Humedad de suelo capacitivo v2.0', '%', 0, 100)
ON CONFLICT (codigo) DO NOTHING;

-- Grupo y dispositivo de ejemplo (ajusta el nombre/integrantes reales)
INSERT INTO grupos (nombre, integrantes)
VALUES ('Grupo D', 'Integrante 1, Integrante 2, Integrante 3, Integrante 4, Integrante 5')
ON CONFLICT DO NOTHING;
