"""
================================================================================
 APLICACIÓN ANALÍTICA - FASE 3 (Streamlit)
 Proyecto IoT: Sensor de Humedad de Suelo Capacitivo v2.0 + DS18B20
--------------------------------------------------------------------------------
 Cumple con los requerimientos de la rúbrica:
   - EDA (Análisis Exploratorio de Datos)
   - Interfaz dinámica: interactuar con cada variable
   - Matriz de correlación
   - Limpieza básica de datos
   - Filtros dinámicos: fecha, rango de valores y variable
   - Detección visual de outliers (IQR + Z-Score)
   - Media móvil en serie de tiempo
   - Dos algoritmos de Machine Learning (regresión + clasificación)

 FUENTE DE DATOS:
   - "Simulados (demo)": datos sintéticos, sin necesidad de conexión.
   - "API (FastAPI local)": consume el endpoint GET /api/v1/lecturas de la
     API que corre en fastapi_iot_api/. Requiere la API activa y la BD lista.
   - "PostgreSQL directo": conexión directa a TimescaleDB por si la API no
     está levantada.
================================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

import requests

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import (
    r2_score, mean_absolute_error, mean_squared_error,
    accuracy_score, confusion_matrix, classification_report
)

# ------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Analítica IoT - Humedad de Suelo & Temperatura",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

UMBRAL_RIEGO = 30.0  # % de humedad por debajo del cual se considera "necesita riego"

# Códigos de sensor tal como están en tipos_sensor de la BD
CODIGO_TEMP = "temperatura_ds18b20"
CODIGO_HUM  = "humedad_suelo_capacitivo"


# ------------------------------------------------------------------
# 1. CARGA DE DATOS
# ------------------------------------------------------------------

def generar_datos_simulados(n_dias: int = 7, frecuencia_seg: int = 10) -> pd.DataFrame:
    """
    Genera datos sintéticos realistas de:
      - humedad_suelo (%): decae con el tiempo y sube abruptamente al "regar"
      - temperatura_suelo (°C): sigue un ciclo diario (más caliente al mediodía)
    Esto simula exactamente lo que enviaría el ESP32 a la API cada 10s.
    """
    np.random.seed(42)
    n_puntos = int((n_dias * 24 * 3600) / frecuencia_seg)
    n_puntos = min(n_puntos, 20000)  # limitar tamaño para que la app sea ágil

    timestamps = pd.date_range(
        end=datetime.now(), periods=n_puntos, freq=f"{frecuencia_seg}s"
    )

    horas = timestamps.hour + timestamps.minute / 60

    # Temperatura: ciclo diario senoidal entre ~18°C (madrugada) y ~30°C (mediodía)
    temperatura = 24 + 6 * np.sin((horas - 9) / 24 * 2 * np.pi) + np.random.normal(0, 0.6, n_puntos)

    # Humedad: decae exponencialmente y "salta" cuando el sistema riega
    humedad = np.zeros(n_puntos)
    humedad[0] = 65
    riego_umbral = 32
    for i in range(1, n_puntos):
        if humedad[i - 1] <= riego_umbral:
            humedad[i] = np.random.uniform(60, 70)  # evento de riego
        else:
            decaimiento = 0.02 + 0.01 * max(temperatura[i] - 24, 0)  # decae más rápido con calor
            humedad[i] = humedad[i - 1] - decaimiento + np.random.normal(0, 0.3)
    humedad = np.clip(humedad, 5, 95)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "device_id": "ESP32_GRUPO_X",
        "humedad_suelo": humedad.round(2),
        "temperatura_suelo": temperatura.round(2),
    })

    # Inyectar algunos valores nulos y outliers para poder mostrar la limpieza básica
    idx_nulos = np.random.choice(df.index, size=int(n_puntos * 0.01), replace=False)
    df.loc[idx_nulos, "humedad_suelo"] = np.nan

    idx_outliers = np.random.choice(df.index, size=int(n_puntos * 0.003), replace=False)
    df.loc[idx_outliers, "temperatura_suelo"] = (
        df.loc[idx_outliers, "temperatura_suelo"]
        + np.random.choice([-20, 25], size=len(idx_outliers))
    )

    return df


def load_data_from_api(
    base_url: str,
    sensor_id_temp: int | None,
    sensor_id_hum: int | None,
    limite: int = 2000,
) -> pd.DataFrame:
    """
    Consume el endpoint GET /api/v1/lecturas de la FastAPI local.
    Trae todas las lecturas y pivotea por sensor_id para obtener
    las columnas humedad_suelo / temperatura_suelo.
    """
    endpoint = f"{base_url.rstrip('/')}/api/v1/lecturas"

    # Traer lecturas de temperatura
    rows = []
    for sid, col_name in [
        (sensor_id_temp, "temperatura_suelo"),
        (sensor_id_hum,  "humedad_suelo"),
    ]:
        params: dict = {"limite": limite}
        if sid is not None:
            params["sensor_id"] = sid
        resp = requests.get(endpoint, params=params, timeout=10)
        resp.raise_for_status()
        for item in resp.json():
            rows.append({
                "timestamp": item["timestamp"],
                "sensor_id": item["sensor_id"],
                "valor":     item["valor"],
                "col":       col_name,
            })

    if not rows:
        raise ValueError("La API no devolvió datos. Verifica que haya lecturas en la BD.")

    df_all = pd.DataFrame(rows)
    df_all["timestamp"] = pd.to_datetime(df_all["timestamp"])
    # Redondear a 10s para alinear las dos lecturas del mismo ciclo del ESP32
    df_all["ts_key"] = df_all["timestamp"].dt.round("10s")

    # Pivotear: una fila por ciclo con columnas temperatura_suelo y humedad_suelo
    df_pivot = df_all.pivot_table(
        index="ts_key",
        columns="col",
        values="valor",
        aggfunc="mean",
    ).reset_index()
    df_pivot.columns.name = None
    df_pivot = df_pivot.rename(columns={"ts_key": "timestamp"})

    for col in ["humedad_suelo", "temperatura_suelo"]:
        if col not in df_pivot.columns:
            df_pivot[col] = np.nan

    df_pivot["device_id"] = "ESP32_API"
    return df_pivot.sort_values("timestamp").reset_index(drop=True)


def load_data_from_db(host, port, dbname, user, password) -> pd.DataFrame:
    """
    Consulta directa a PostgreSQL/TimescaleDB usando el esquema real
    definido en fastapi_iot_api/sql/init_timescale.sql.

    Hace un JOIN lecturas → sensores → tipos_sensor para obtener el
    código del sensor y pivotea las dos mediciones por timestamp.
    """
    from sqlalchemy import create_engine, text

    conn_str = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    engine = create_engine(conn_str)

    query = text("""
        SELECT
            l.timestamp,
            d.nombre        AS device_id,
            ts.codigo       AS tipo_sensor,
            l.valor
        FROM lecturas     l
        JOIN sensores     s  ON s.id = l.sensor_id
        JOIN tipos_sensor ts ON ts.id = s.tipo_sensor_id
        JOIN dispositivos d  ON d.id = s.dispositivo_id
        ORDER BY l.timestamp ASC
        LIMIT 50000
    """)

    with engine.connect() as conn:
        df_raw = pd.read_sql(query, conn, parse_dates=["timestamp"])

    if df_raw.empty:
        raise ValueError("La consulta no devolvió filas. Verifica que haya datos en la BD.")

    # Pivotear: una fila por timestamp+device con columnas por tipo de sensor
    df_pivot = df_raw.pivot_table(
        index=["timestamp", "device_id"],
        columns="tipo_sensor",
        values="valor",
        aggfunc="mean",
    ).reset_index()

    df_pivot.columns.name = None

    # Renombrar a los nombres que espera la app
    rename_map = {
        CODIGO_TEMP: "temperatura_suelo",
        CODIGO_HUM:  "humedad_suelo",
    }
    df_pivot = df_pivot.rename(columns=rename_map)

    for col in ["humedad_suelo", "temperatura_suelo"]:
        if col not in df_pivot.columns:
            df_pivot[col] = np.nan

    return df_pivot.sort_values("timestamp").reset_index(drop=True)


@st.cache_data(show_spinner="Cargando datos...", ttl=300)
def get_data(fuente: str, params: dict | None = None) -> pd.DataFrame:
    """
    fuente puede ser:
      "simulados" → datos sintéticos
      "api"       → FastAPI local
      "db"        → PostgreSQL directo
    """
    if fuente == "simulados" or params is None:
        return generar_datos_simulados()
    if fuente == "api":
        return load_data_from_api(**params)
    if fuente == "db":
        return load_data_from_db(**params)
    return generar_datos_simulados()


# ------------------------------------------------------------------
# 2. LIMPIEZA BÁSICA
# ------------------------------------------------------------------

def limpiar_datos(df: pd.DataFrame, quitar_outliers: bool) -> tuple[pd.DataFrame, dict]:
    reporte = {}
    df_limpio = df.copy()

    reporte["filas_originales"] = len(df_limpio)
    reporte["nulos_por_columna"] = df_limpio[["humedad_suelo", "temperatura_suelo"]].isna().sum().to_dict()

    # 1. Eliminar duplicados exactos
    duplicados = df_limpio.duplicated().sum()
    df_limpio = df_limpio.drop_duplicates()
    reporte["duplicados_eliminados"] = int(duplicados)

    # 2. Imputar nulos con interpolación temporal (más adecuado para series de tiempo)
    df_limpio = df_limpio.sort_values("timestamp")
    df_limpio["humedad_suelo"] = df_limpio["humedad_suelo"].interpolate(method="linear")
    df_limpio["temperatura_suelo"] = df_limpio["temperatura_suelo"].interpolate(method="linear")
    df_limpio = df_limpio.dropna(subset=["humedad_suelo", "temperatura_suelo"])

    # 3. Filtrar outliers usando rango IQR (opcional, activable desde la UI)
    outliers_removidos = 0
    if quitar_outliers:
        for col in ["humedad_suelo", "temperatura_suelo"]:
            q1, q3 = df_limpio[col].quantile([0.25, 0.75])
            iqr = q3 - q1
            lim_inf, lim_sup = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            antes = len(df_limpio)
            df_limpio = df_limpio[(df_limpio[col] >= lim_inf) & (df_limpio[col] <= lim_sup)]
            outliers_removidos += antes - len(df_limpio)

    reporte["outliers_removidos"] = int(outliers_removidos)
    reporte["filas_finales"] = len(df_limpio)
    return df_limpio, reporte


# ------------------------------------------------------------------
# 3. FEATURES PARA ML
# ------------------------------------------------------------------

def construir_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["hora"] = out["timestamp"].dt.hour + out["timestamp"].dt.minute / 60
    out["hora_sin"] = np.sin(2 * np.pi * out["hora"] / 24)
    out["hora_cos"] = np.cos(2 * np.pi * out["hora"] / 24)
    out["necesita_riego"] = (out["humedad_suelo"] < UMBRAL_RIEGO).astype(int)
    return out


# ==================================================================
# BARRA LATERAL: CONEXIÓN Y NAVEGACIÓN
# ==================================================================

st.sidebar.title("🌱 Panel de control")

with st.sidebar.expander("⚙️ Fuente de datos", expanded=True):
    modo_datos = st.radio(
        "Fuente de datos",
        ["API (FastAPI local)", "Simulados (demo)"],
        index=0,
        help="API: requiere que la FastAPI esté corriendo (uvicorn).\nSimulados: datos sintéticos sin necesidad de conexión.",
    )

    fuente = "api"
    params: dict | None = None

    if modo_datos == "API (FastAPI local)":
        fuente = "api"
        st.caption("La API debe estar corriendo: `uvicorn app.main:app --reload --host 0.0.0.0` dentro de fastapi_iot_api/")
        api_url = st.text_input("URL base de la API", "http://localhost:8000")
        st.markdown("**IDs de sensor** (ver tabla `sensores` en la BD)")
        sid_temp = st.number_input("sensor_id de temperatura", min_value=1, value=3, step=1)
        sid_hum  = st.number_input("sensor_id de humedad",     min_value=1, value=5, step=1)
        limite_api = st.number_input("Máx. lecturas por sensor", min_value=100, max_value=10000, value=2000, step=100)
        params = dict(
            base_url=api_url,
            sensor_id_temp=int(sid_temp),
            sensor_id_hum=int(sid_hum),
            limite=int(limite_api),
        )
    else:
        fuente = "simulados"

seccion = st.sidebar.radio(
    "Navegación",
    ["📊 EDA y Filtros", "🧹 Limpieza de datos", "🔍 Detección de Outliers", "🔗 Correlación", "🤖 Machine Learning"]
)

# Carga de datos (con manejo de error si falla la conexión real)
try:
    df_raw = get_data(fuente, params)
except Exception as e:
    st.sidebar.error(f"No se pudo conectar: {e}\nUsando datos simulados.")
    df_raw = get_data("simulados", None)

df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])

# ------------------------------------------------------------------
# FILTROS DINÁMICOS (comunes a toda la app)
# ------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("🔎 Filtros dinámicos")

from datetime import date as _date
fecha_min = df_raw["timestamp"].min().date()
fecha_max = _date.today()          # siempre hasta hoy, sin importar los datos
rango_fechas = st.sidebar.date_input(
    "Rango de fechas", value=(fecha_min, fecha_max),
    min_value=fecha_min, max_value=fecha_max
)

variables_disponibles = ["humedad_suelo", "temperatura_suelo"]
variables_sel = st.sidebar.multiselect(
    "Variables a analizar", variables_disponibles, default=variables_disponibles
)

variable_para_rango = st.sidebar.selectbox("Variable para filtrar por rango de valor", variables_disponibles)
val_min = float(df_raw[variable_para_rango].min(skipna=True))
val_max = float(df_raw[variable_para_rango].max(skipna=True))
# Si min == max (ej. todos los valores de humedad son 0), ampliar rango para evitar error del slider
if val_min == val_max:
    val_min = val_min - 1.0
    val_max = val_max + 1.0
rango_valor = st.sidebar.slider(
    f"Rango de {variable_para_rango}", min_value=val_min, max_value=val_max,
    value=(val_min, val_max)
)

quitar_outliers_ui = st.sidebar.checkbox("Excluir outliers (IQR)", value=True)

# Aplicar filtros de fecha y rango de valor
if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
    ini, fin = rango_fechas
else:
    ini, fin = fecha_min, fecha_max

mask = (
    (df_raw["timestamp"].dt.date >= ini) &
    (df_raw["timestamp"].dt.date <= fin) &
    (df_raw[variable_para_rango].between(rango_valor[0], rango_valor[1]))
)
df_filtrado = df_raw.loc[mask].copy()

# Limpieza aplicada de forma global (para que ML y correlación usen datos limpios)
df_limpio, reporte_limpieza = limpiar_datos(df_filtrado, quitar_outliers_ui)
df_features = construir_features(df_limpio)


# ==================================================================
# SECCIÓN 1: EDA Y FILTROS
# ==================================================================


if seccion == "📊 EDA y Filtros":
    st.title("📊 Análisis Exploratorio de Datos (EDA)")
    st.caption("Sensores: Humedad de suelo capacitivo v2.0 + Temperatura DS18B20")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registros (filtrados)", f"{len(df_filtrado):,}")
    c2.metric("Humedad promedio", f"{df_filtrado['humedad_suelo'].mean():.1f} %")
    c3.metric("Temp. promedio", f"{df_filtrado['temperatura_suelo'].mean():.1f} °C")
    c4.metric("Rango de fechas", f"{(fin - ini).days} días")

    st.markdown("### Estadística descriptiva")
    st.dataframe(df_filtrado[variables_disponibles].describe().T, use_container_width=True)

    st.markdown("### Serie de tiempo interactiva")
    if variables_sel:
        ventana_mm = st.slider(
            "Ventana de media móvil (número de muestras)", 10, 500, 100, step=10,
            help="A 10 s por muestra, 100 muestras ≈ 17 min de suavizado"
        )
        fig = go.Figure()
        for var in variables_sel:
            # Datos originales (semitransparentes para no saturar)
            fig.add_trace(go.Scatter(
                x=df_filtrado["timestamp"], y=df_filtrado[var],
                mode="lines", name=f"{var} (raw)",
                line=dict(width=1), opacity=0.4
            ))
            # Media móvil
            mm = df_filtrado[var].rolling(window=ventana_mm, min_periods=1, center=True).mean()
            fig.add_trace(go.Scatter(
                x=df_filtrado["timestamp"], y=mm,
                mode="lines", name=f"{var} (media móvil {ventana_mm})",
                line=dict(width=2.5)
            ))
        fig.update_layout(
            height=480, xaxis_title="Tiempo", yaxis_title="Valor",
            legend_title="Variable", hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Selecciona al menos una variable en la barra lateral.")

    st.markdown("### Distribución por variable")
    col_a, col_b = st.columns(2)
    for i, var in enumerate(variables_sel):
        fig_hist = px.histogram(df_filtrado, x=var, nbins=40, marginal="box",
                                 title=f"Distribución de {var}")
        (col_a if i % 2 == 0 else col_b).plotly_chart(fig_hist, use_container_width=True)

    with st.expander("Ver datos crudos filtrados"):
        st.dataframe(df_filtrado, use_container_width=True)


# ==================================================================
# SECCIÓN 2: LIMPIEZA DE DATOS
# ==================================================================
elif seccion == "🧹 Limpieza de datos":
    st.title("🧹 Limpieza básica de datos")
    st.markdown("""
    Pasos aplicados automáticamente (con los filtros activos en la barra lateral):
    1. Eliminación de registros duplicados.
    2. Imputación de valores nulos por interpolación temporal.
    3. (Opcional) Filtrado de outliers usando el rango intercuartílico (IQR).
    """)

    c1, c2, c3 = st.columns(3)
    c1.metric("Filas originales", reporte_limpieza["filas_originales"])
    c2.metric("Filas finales", reporte_limpieza["filas_finales"])
    c3.metric("Outliers removidos", reporte_limpieza["outliers_removidos"])

    st.markdown("#### Valores nulos detectados antes de limpiar")
    st.json(reporte_limpieza["nulos_por_columna"])
    st.markdown(f"**Duplicados eliminados:** {reporte_limpieza['duplicados_eliminados']}")

    st.markdown("### Comparación antes / después (boxplot)")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(px.box(df_filtrado, y="humedad_suelo", title="Humedad — antes"),
                         use_container_width=True)
    with col2:
        st.plotly_chart(px.box(df_limpio, y="humedad_suelo", title="Humedad — después"),
                         use_container_width=True)

    st.markdown("### Datos limpios (muestra)")
    st.dataframe(df_limpio.head(200), use_container_width=True)


# ==================================================================
# SECCIÓN 3: DETECCIÓN DE OUTLIERS
# ==================================================================
elif seccion == "🔍 Detección de Outliers":
    st.title("🔍 Detección de Valores Atípicos (Outliers)")
    st.markdown("""
    Se combinan **dos métodos** para identificar anomalías:
    - **IQR (Rango Intercuartílico):** marca como outlier todo valor fuera de Q1 − 1.5·IQR y Q3 + 1.5·IQR.
    - **Z-Score:** marca como outlier todo valor cuyo puntaje Z supere el umbral configurado (normalmente ±3).
    """)

    var_outlier = st.selectbox("Variable a analizar", variables_disponibles, key="var_out")

    col_met1, col_met2 = st.columns(2)
    with col_met1:
        st.markdown("#### Método IQR")
        factor_iqr = st.slider("Factor IQR", 1.0, 3.0, 1.5, step=0.1, key="iqr_factor")
    with col_met2:
        st.markdown("#### Método Z-Score")
        umbral_z = st.slider("Umbral Z-Score", 1.5, 4.0, 3.0, step=0.1, key="z_umbral")

    serie = df_filtrado[["timestamp", var_outlier]].copy()
    serie = serie.dropna(subset=[var_outlier])

    # --- IQR ---
    q1 = serie[var_outlier].quantile(0.25)
    q3 = serie[var_outlier].quantile(0.75)
    iqr = q3 - q1
    lim_inf_iqr = q1 - factor_iqr * iqr
    lim_sup_iqr = q3 + factor_iqr * iqr
    serie["outlier_iqr"] = ~serie[var_outlier].between(lim_inf_iqr, lim_sup_iqr)

    # --- Z-Score ---
    media = serie[var_outlier].mean()
    std = serie[var_outlier].std()
    serie["z_score"] = (serie[var_outlier] - media) / std
    serie["outlier_z"] = serie["z_score"].abs() > umbral_z

    # --- Combinado (cualquiera de los dos métodos) ---
    serie["es_outlier"] = serie["outlier_iqr"] | serie["outlier_z"]

    n_outliers = int(serie["es_outlier"].sum())
    pct_outliers = n_outliers / len(serie) * 100

    kp1, kp2, kp3, kp4 = st.columns(4)
    kp1.metric("Total registros", f"{len(serie):,}")
    kp2.metric("Outliers detectados", f"{n_outliers:,}")
    kp3.metric("Porcentaje", f"{pct_outliers:.2f}%")
    kp4.metric("Rango normal (IQR)", f"[{lim_inf_iqr:.1f}, {lim_sup_iqr:.1f}]")

    # --- Gráfica: serie de tiempo con outliers resaltados en rojo ---
    st.markdown("### Serie de tiempo — outliers resaltados en rojo")
    normales = serie[~serie["es_outlier"]]
    anomalos = serie[serie["es_outlier"]]

    fig_out = go.Figure()
    fig_out.add_trace(go.Scatter(
        x=normales["timestamp"], y=normales[var_outlier],
        mode="lines", name="Normal",
        line=dict(color="#2196F3", width=1.2)
    ))
    fig_out.add_trace(go.Scatter(
        x=anomalos["timestamp"], y=anomalos[var_outlier],
        mode="markers", name="Outlier",
        marker=dict(color="red", size=7, symbol="x")
    ))
    fig_out.add_hline(y=lim_sup_iqr, line_dash="dash", line_color="orange",
                      annotation_text=f"Límite sup IQR ({lim_sup_iqr:.1f})",
                      annotation_position="top right")
    fig_out.add_hline(y=lim_inf_iqr, line_dash="dash", line_color="orange",
                      annotation_text=f"Límite inf IQR ({lim_inf_iqr:.1f})",
                      annotation_position="bottom right")
    fig_out.update_layout(height=460, xaxis_title="Tiempo",
                          yaxis_title=var_outlier, hovermode="x unified")
    st.plotly_chart(fig_out, use_container_width=True)

    # --- Boxplot con outliers marcados ---
    st.markdown("### Boxplot con distribución de outliers")
    fig_box = go.Figure()
    fig_box.add_trace(go.Box(
        y=serie[var_outlier], name=var_outlier,
        boxpoints="suspectedoutliers",
        marker=dict(color="#2196F3", outliercolor="red",
                    line=dict(outliercolor="red", outlierwidth=2)),
        line_color="#1565C0"
    ))
    fig_box.update_layout(height=380, yaxis_title=var_outlier)
    st.plotly_chart(fig_box, use_container_width=True)

    # --- Tabla de registros anómalos ---
    st.markdown("### Registros anómalos detectados")
    if n_outliers == 0:
        st.success("No se detectaron outliers con los parámetros actuales.")
    else:
        tabla_out = anomalos[["timestamp", var_outlier, "z_score", "outlier_iqr", "outlier_z"]].copy()
        tabla_out.columns = ["Timestamp", var_outlier, "Z-Score", "Outlier IQR", "Outlier Z"]
        tabla_out = tabla_out.sort_values("Timestamp", ascending=False).reset_index(drop=True)
        st.dataframe(
            tabla_out.style.format({var_outlier: "{:.2f}", "Z-Score": "{:.2f}"}),
            use_container_width=True,
            height=300
        )
        st.download_button(
            "⬇️ Descargar outliers como CSV",
            data=tabla_out.to_csv(index=False).encode("utf-8"),
            file_name=f"outliers_{var_outlier}.csv",
            mime="text/csv"
        )


# ==================================================================
# SECCIÓN 4: MATRIZ DE CORRELACIÓN
# ==================================================================
elif seccion == "🔗 Correlación":
    st.title("🔗 Matriz de correlación")

    corr_cols = ["humedad_suelo", "temperatura_suelo"]
    corr = df_limpio[corr_cols].corr()

    fig_corr = px.imshow(
        corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
        title="Correlación entre variables (datos limpios y filtrados)"
    )
    st.plotly_chart(fig_corr, use_container_width=True)

    st.markdown("### Dispersión entre variables")
    fig_scatter = px.scatter(
        df_features, x="temperatura_suelo", y="humedad_suelo",
        color="hora" if "hora" in df_features.columns else None,
        trendline="ols",
        title="Temperatura vs. Humedad de suelo"
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    coef = corr.loc["humedad_suelo", "temperatura_suelo"]
    st.info(f"Coeficiente de correlación (Pearson) entre humedad y temperatura: **{coef:.3f}**")


# ==================================================================
# SECCIÓN 5: MACHINE LEARNING (2 algoritmos)
# ==================================================================
elif seccion == "🤖 Machine Learning":
    st.title("🤖 Modelos de Machine Learning")
    st.caption("Modelo 1: Regresión (predicción de humedad) · Modelo 2: Clasificación (necesidad de riego) · Sensores: Capacitivo v2.0 + DS18B20")

    if len(df_features) < 30:
        st.warning("Muy pocos datos después de filtrar. Amplía el rango de fechas o valores.")
        st.stop()

    tab1, tab2 = st.tabs(["📈 Regresión: predecir humedad", "🚦 Clasificación: ¿necesita riego?"])

    # -------------------- MODELO 1: REGRESIÓN --------------------
    with tab1:
        st.subheader("Random Forest Regressor")
        st.markdown("Predice la **humedad del suelo (%)** a partir de la temperatura y la hora del día.")

        X = df_features[["temperatura_suelo", "hora_sin", "hora_cos"]]
        y = df_features["humedad_suelo"]

        test_size = st.slider("Tamaño del conjunto de prueba (%)", 10, 40, 20, key="reg_test") / 100
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

        n_estimators = st.slider("Número de árboles", 50, 300, 150, step=50, key="reg_trees")
        modelo_reg = RandomForestRegressor(n_estimators=n_estimators, max_depth=8, random_state=42)
        modelo_reg.fit(X_train, y_train)
        y_pred = modelo_reg.predict(X_test)

        c1, c2, c3 = st.columns(3)
        c1.metric("R²", f"{r2_score(y_test, y_pred):.3f}")
        c2.metric("MAE", f"{mean_absolute_error(y_test, y_pred):.2f} %")
        c3.metric("RMSE", f"{np.sqrt(mean_squared_error(y_test, y_pred)):.2f} %")

        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(y=y_test.values[:200], name="Valor real", mode="lines"))
        fig_pred.add_trace(go.Scatter(y=y_pred[:200], name="Predicción", mode="lines"))
        fig_pred.update_layout(title="Real vs. Predicho (muestra de 200 puntos)",
                                xaxis_title="Índice", yaxis_title="Humedad (%)")
        st.plotly_chart(fig_pred, use_container_width=True)

        importancias = pd.DataFrame({
            "variable": X.columns, "importancia": modelo_reg.feature_importances_
        }).sort_values("importancia", ascending=False)
        st.plotly_chart(px.bar(importancias, x="variable", y="importancia",
                                title="Importancia de variables"), use_container_width=True)

        st.markdown("#### Prueba manual del modelo")
        col_a, col_b = st.columns(2)
        temp_input = col_a.number_input("Temperatura (°C)", 10.0, 45.0, 25.0)
        hora_input = col_b.slider("Hora del día", 0.0, 23.9, 12.0)
        pred_manual = modelo_reg.predict([[
            temp_input, np.sin(2 * np.pi * hora_input / 24), np.cos(2 * np.pi * hora_input / 24)
        ]])[0]
        st.success(f"Humedad de suelo estimada: **{pred_manual:.1f}%**")

    # -------------------- MODELO 2: CLASIFICACIÓN --------------------
    with tab2:
        st.subheader("Random Forest Classifier")
        st.markdown(f"Clasifica si la planta **necesita riego** (humedad < {UMBRAL_RIEGO}%) según temperatura y hora.")

        Xc = df_features[["temperatura_suelo", "hora_sin", "hora_cos"]]
        yc = df_features["necesita_riego"]

        if yc.nunique() < 2:
            st.warning("Con el filtro actual todos los registros están en una sola clase. Amplía el rango de humedad en la barra lateral.")
        else:
            test_size_c = st.slider("Tamaño del conjunto de prueba (%)", 10, 40, 20, key="clf_test") / 100
            Xc_train, Xc_test, yc_train, yc_test = train_test_split(
                Xc, yc, test_size=test_size_c, random_state=42, stratify=yc
            )

            n_estimators_c = st.slider("Número de árboles", 50, 300, 150, step=50, key="clf_trees")
            modelo_clf = RandomForestClassifier(n_estimators=n_estimators_c, max_depth=6, random_state=42)
            modelo_clf.fit(Xc_train, yc_train)
            yc_pred = modelo_clf.predict(Xc_test)

            c1, c2 = st.columns(2)
            c1.metric("Accuracy", f"{accuracy_score(yc_test, yc_pred):.1%}")
            c2.metric("Casos 'necesita riego' (test)", int(yc_test.sum()))

            cm = confusion_matrix(yc_test, yc_pred)
            fig_cm = px.imshow(
                cm, text_auto=True, color_continuous_scale="Blues",
                labels=dict(x="Predicho", y="Real"),
                x=["No riego", "Riego"], y=["No riego", "Riego"],
                title="Matriz de confusión"
            )
            st.plotly_chart(fig_cm, use_container_width=True)

            with st.expander("Ver reporte de clasificación completo"):
                st.text(classification_report(yc_test, yc_pred, target_names=["No riego", "Riego"]))

            st.markdown("#### Prueba manual del modelo")
            col_a, col_b = st.columns(2)
            temp_input_c = col_a.number_input("Temperatura (°C)", 10.0, 45.0, 25.0, key="temp_clf")
            hora_input_c = col_b.slider("Hora del día", 0.0, 23.9, 12.0, key="hora_clf")
            pred_c = modelo_clf.predict([[
                temp_input_c, np.sin(2 * np.pi * hora_input_c / 24), np.cos(2 * np.pi * hora_input_c / 24)
            ]])[0]
            proba_c = modelo_clf.predict_proba([[
                temp_input_c, np.sin(2 * np.pi * hora_input_c / 24), np.cos(2 * np.pi * hora_input_c / 24)
            ]])[0]
            if pred_c == 1:
                st.error(f"🚨 Necesita riego (probabilidad: {proba_c[1]:.0%})")
            else:
                st.success(f"✅ No necesita riego (probabilidad: {proba_c[0]:.0%})")
