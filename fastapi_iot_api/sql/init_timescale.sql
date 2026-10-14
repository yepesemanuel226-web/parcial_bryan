-- =============================================================
-- Script de creación de base de datos - Taller IoT
-- Proyecto: iot-taller | Rama: production | BD: neondb
-- 12 tablas + hypertable TimescaleDB
-- =============================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 1) Ubicaciones
CREATE TABLE IF NOT EXISTS ubicaciones (
    id_ubicacion  SMALLINT PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    descripcion   TEXT
);

-- 2) Dispositivos (ESP32)
CREATE TABLE IF NOT EXISTS dispositivos (
    id_dispositivo       SMALLINT PRIMARY KEY,
    nombre               VARCHAR(100) NOT NULL,
    modelo               VARCHAR(50) NOT NULL,
    direccion_mac        VARCHAR(17) UNIQUE,
    id_ubicacion         SMALLINT NOT NULL REFERENCES ubicaciones(id_ubicacion),
    intervalo_envio_seg  SMALLINT NOT NULL DEFAULT 20,
    activo               BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3) Tipos de sensor
CREATE TABLE IF NOT EXISTS tipos_sensor (
    id_tipo_sensor    SMALLINT PRIMARY KEY,
    nombre            VARCHAR(100) NOT NULL,
    magnitud          VARCHAR(50) NOT NULL,
    unidad            VARCHAR(20) NOT NULL,
    valor_min_fisico  NUMERIC NOT NULL,
    valor_max_fisico  NUMERIC NOT NULL
);

-- 4) Sensores (instancia física por dispositivo)
CREATE TABLE IF NOT EXISTS sensores (
    id_sensor         SMALLINT PRIMARY KEY,
    id_dispositivo    SMALLINT NOT NULL REFERENCES dispositivos(id_dispositivo),
    id_tipo_sensor    SMALLINT NOT NULL REFERENCES tipos_sensor(id_tipo_sensor),
    codigo            VARCHAR(50) NOT NULL,
    modelo            VARCHAR(50),
    pin_conexion      VARCHAR(20),
    activo            BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_instalacion DATE NOT NULL
);

-- 5) Lecturas (hypertable TimescaleDB)
CREATE TABLE IF NOT EXISTS lecturas (
    tiempo       TIMESTAMPTZ NOT NULL,
    id_sensor    SMALLINT NOT NULL REFERENCES sensores(id_sensor),
    valor        DOUBLE PRECISION,
    reenviada    BOOLEAN NOT NULL DEFAULT FALSE,
    recibido_en  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tiempo, id_sensor)
);

SELECT create_hypertable('lecturas', 'tiempo', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_lecturas_sensor_tiempo ON lecturas (id_sensor, tiempo DESC);

-- 6) Niveles de alerta
CREATE TABLE IF NOT EXISTS niveles_alerta (
    id_nivel   SMALLINT PRIMARY KEY,
    nombre     VARCHAR(50) NOT NULL,
    prioridad  SMALLINT NOT NULL
);

-- 7) Umbrales de alerta
CREATE TABLE IF NOT EXISTS umbrales_alerta (
    id_umbral       SMALLINT PRIMARY KEY,
    id_tipo_sensor  SMALLINT NOT NULL REFERENCES tipos_sensor(id_tipo_sensor),
    id_nivel        SMALLINT NOT NULL REFERENCES niveles_alerta(id_nivel),
    limite_inferior NUMERIC,
    limite_superior NUMERIC,
    activo          BOOLEAN NOT NULL DEFAULT TRUE
);

-- 8) Alertas
CREATE TABLE IF NOT EXISTS alertas (
    id_alerta      BIGINT PRIMARY KEY,
    id_sensor      SMALLINT NOT NULL REFERENCES sensores(id_sensor),
    id_umbral      SMALLINT NOT NULL REFERENCES umbrales_alerta(id_umbral),
    tiempo_lectura TIMESTAMPTZ NOT NULL,
    valor          DOUBLE PRECISION NOT NULL,
    estado         VARCHAR(20) NOT NULL DEFAULT 'ACTIVA'
                   CHECK (estado IN ('ACTIVA', 'RECONOCIDA', 'RESUELTA')),
    creada_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
    resuelta_en    TIMESTAMPTZ
);

-- 9) Outliers detectados
CREATE TABLE IF NOT EXISTS outliers_detectados (
    id_outlier     BIGINT PRIMARY KEY,
    id_sensor      SMALLINT NOT NULL REFERENCES sensores(id_sensor),
    tiempo_lectura TIMESTAMPTZ NOT NULL,
    valor          DOUBLE PRECISION NOT NULL,
    z_score        NUMERIC,
    metodo         VARCHAR(30) NOT NULL DEFAULT 'zscore',
    detectado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 10) Estado de conexión
CREATE TABLE IF NOT EXISTS estado_conexion (
    id_evento          BIGINT PRIMARY KEY,
    id_dispositivo     SMALLINT NOT NULL REFERENCES dispositivos(id_dispositivo),
    tiempo             TIMESTAMPTZ NOT NULL DEFAULT now(),
    conectado          BOOLEAN NOT NULL,
    rssi_dbm           SMALLINT,
    reintentos         SMALLINT NOT NULL DEFAULT 0,
    lecturas_en_buffer SMALLINT NOT NULL DEFAULT 0
);

-- 11) Consultas del menú (teclado matricial)
CREATE TABLE IF NOT EXISTS consultas_menu (
    id_consulta    BIGINT PRIMARY KEY,
    id_dispositivo SMALLINT NOT NULL REFERENCES dispositivos(id_dispositivo),
    tecla          CHAR(1) NOT NULL,
    tiempo         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 12) Opciones del menú
CREATE TABLE IF NOT EXISTS menu_opciones (
    tecla               CHAR(1) PRIMARY KEY,
    nombre              VARCHAR(100) NOT NULL,
    descripcion         TEXT,
    concepto_analitica  VARCHAR(100) NOT NULL
);

-- Vista materializada de promedios por hora (lecturas_horarias)
CREATE MATERIALIZED VIEW IF NOT EXISTS lecturas_horarias AS
SELECT
    time_bucket('1 hour', tiempo) AS hora,
    id_sensor,
    AVG(valor)    AS promedio,
    MIN(valor)    AS minimo,
    MAX(valor)    AS maximo,
    STDDEV(valor) AS desviacion,
    COUNT(*)      AS n_lecturas
FROM lecturas
GROUP BY 1, 2
WITH NO DATA;

-- =============================================================
-- Datos semilla
-- =============================================================

INSERT INTO ubicaciones (id_ubicacion, nombre, descripcion)
VALUES (1, 'Laboratorio de Sistemas', 'Sitio donde se instala el prototipo IoT')
ON CONFLICT DO NOTHING;

INSERT INTO tipos_sensor (id_tipo_sensor, nombre, magnitud, unidad, valor_min_fisico, valor_max_fisico)
VALUES
    (1, 'temperatura_ds18b20',     'Temperatura ambiente', '°C', -40, 80),
    (2, 'humedad_suelo_capacitivo','Humedad relativa',      '%',   0, 100)
ON CONFLICT DO NOTHING;

INSERT INTO niveles_alerta (id_nivel, nombre, prioridad)
VALUES
    (1, 'bajo',  1),
    (2, 'medio', 2),
    (3, 'alto',  3)
ON CONFLICT DO NOTHING;

INSERT INTO umbrales_alerta (id_umbral, id_tipo_sensor, id_nivel, limite_inferior, limite_superior, activo)
VALUES
    (1, 1, 2, 5.0,  35.0, TRUE),
    (2, 2, 2, 10.0, 90.0, TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO dispositivos (id_dispositivo, nombre, modelo, direccion_mac, id_ubicacion, intervalo_envio_seg, activo)
VALUES (1, 'ESP32 Grupo D', 'ESP32-WROOM-32', '20:43:a8:66:81:5c', 1, 20, TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO sensores (id_sensor, id_dispositivo, id_tipo_sensor, codigo, modelo, pin_conexion, activo, fecha_instalacion)
VALUES
    (1, 1, 1, 'temperatura_ds18b20',     'DS18B20',       'GPIO4',  TRUE, CURRENT_DATE),
    (2, 1, 2, 'humedad_suelo_capacitivo','Capacitivo v2.0','GPIO34', TRUE, CURRENT_DATE)
ON CONFLICT DO NOTHING;

INSERT INTO menu_opciones (tecla, nombre, descripcion, concepto_analitica)
VALUES
    ('1', 'Tiempo real',    'Valor actual de cada sensor',         'Estadística descriptiva'),
    ('2', 'Promedio hora',  'Promedio de la última hora',          'Media aritmética'),
    ('3', 'Max/Min día',    'Máximo y mínimo del día',             'Rango estadístico'),
    ('4', 'Desv/Tendencia', 'Desviación estándar y tendencia',     'Dispersión y regresión'),
    ('5', 'Outliers',       'Detección de valores atípicos',       'Z-score'),
    ('6', 'Alertas',        'Conteo de alertas activas',           'Umbrales y anomalías'),
    ('7', 'Conexión nube',  'Estado de conexión WiFi y API',       'Monitoreo del sistema')
ON CONFLICT DO NOTHING;
