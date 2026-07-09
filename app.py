import streamlit as st
import pandas as pd
import os
import re
import gc
import numpy as np
import plotly.express as px
from pathlib import Path

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
st.set_page_config(page_title="Monitor FAN Huawei", layout="wide")

UMBRAL_CRITICO_FAN = 90
PARQUET_FILE = "base_historica_fan.parquet"

BASE_DIR = Path(__file__).resolve().parent
FOLDER_PATH = BASE_DIR / "FANF"

# ==========================================
# EXTRACCIÓN ROBUSTA DE DATOS
# ==========================================
def extraer_datos_fan(path):
    rows = []
    try:
        nombre_archivo = path.name
        nums = re.findall(r'\d{6,8}', nombre_archivo)

        if len(nums) >= 2:
            fecha_str = nums[0] + nums[1]
            ts = pd.to_datetime(fecha_str[:14], format='%Y%m%d%H%M%S', errors='coerce')
        else:
            ts = pd.to_datetime(os.path.getmtime(path), unit='s')

        if pd.isna(ts):
            ts = pd.Timestamp.now()

        with open(path, 'r', encoding='latin-1', errors='ignore') as f:
            content = f.read()

        bloques = re.split(r'MML Command Result', content)

        for bloques_item in bloques[1:]:
            ne_match = re.search(r'NE Name\s*:\s*([\w_-]+)', bloques_item)
            if not ne_match:
                continue

            sitio = ne_match.group(1).strip()
            slots = re.findall(r'Slot No\.\s*=\s*(\d+)', bloques_item)
            speeds = re.findall(r'Fan Speed Rate\(%\)\s*=\s*(\d+)', bloques_item)

            for s, v in zip(slots, speeds):
                val = int(v)
                rows.append({
                    "Timestamp": ts,
                    "Sitio": sitio,
                    "Slot": str(s),
                    "Fan_Speed_Rate": val,
                    "ID_Full": f"{sitio} (S:{s})",
                    "Estado": "Crítico" if val >= UMBRAL_CRITICO_FAN else "Normal"
                })
    except Exception:
        pass
    return rows

def listar_archivos():
    if not FOLDER_PATH.exists():
        return []
    todos = sorted([
        f for f in FOLDER_PATH.iterdir()
        if f.is_file() and (f.suffix.lower() == ".txt" or f.suffix.lower() == ".gz")
    ])
    return todos[-400:]

# ==========================================
# RECONSTRUCCIÓN SÓLIDA DE LA BASE DE DATOS
# ==========================================
def reconstruir_base():
    archivos = listar_archivos()
    if not archivos:
        st.error(f"❌ No se encontraron archivos en la carpeta: {FOLDER_PATH}")
        return False

    if os.path.exists(PARQUET_FILE):
        try:
            os.remove(PARQUET_FILE)
        except Exception:
            pass

    barra = st.progress(0)
    todos_los_datos = []

    for i, archivo in enumerate(archivos):
        todos_los_datos.extend(extraer_datos_fan(archivo))
        barra.progress((i + 1) / len(archivos))

    barra.empty()

    if todos_los_datos:
        df_final = pd.DataFrame(todos_los_datos)
        df_final.to_parquet(PARQUET_FILE, index=False, compression="snappy")
        del df_final
        gc.collect()
        return True
    else:
        st.error("❌ No se pudieron extraer filas válidas de los archivos logs.")
        return False

@st.cache_data(ttl=15)
def cargar_base():
    if os.path.exists(PARQUET_FILE):
        try:
            return pd.read_parquet(PARQUET_FILE)
        except Exception:
            pass
    return pd.DataFrame()

# ==========================================
# ESCANEO FILTRADO: INESTABILIDAD FUERTE
# ==========================================
def escanear_alertas_globales(df_total, ventana_corta=6, ventana_larga=24, umbral_z=1.5, umbral_oscilacion=35):
    """
    Filtra y extrae de forma exclusiva los ventiladores con comportamiento
    de Inestabilidad Fuerte (Quiebre de Z-Score combinado con alta amplitud cíclica).
    """
    if df_total.empty:
        return pd.DataFrame()

    df = df_total.sort_values("Timestamp").reset_index(drop=True)
    
    # Análisis de tendencias
    df['Media_Corta'] = df.groupby(['Sitio', 'Slot'])['Fan_Speed_Rate'].transform(lambda x: x.rolling(window=ventana_corta, min_periods=1).mean())
    df['Media_Larga'] = df.groupby(['Sitio', 'Slot'])['Fan_Speed_Rate'].transform(lambda x: x.rolling(window=ventana_larga, min_periods=4).mean())
    df['Std_Larga'] = df.groupby(['Sitio', 'Slot'])['Fan_Speed_Rate'].transform(lambda x: x.rolling(window=ventana_larga, min_periods=4).std()).replace(0, 0.1)
    
    df['Z_Score'] = (df['Media_Corta'] - df['Media_Larga']) / df['Std_Larga']
    df['Alerta_Tendencia'] = (df['Z_Score'] > umbral_z) & (df['Fan_Speed_Rate'] > df['Media_Larga'])
    
    # Corte temporal de la última semana
    ultima_fecha_red = df['Timestamp'].max()
    limite_temporal = ultima_fecha_red - pd.Timedelta(days=5)
    ventana_reciente = df[df['Timestamp'] >= limite_temporal].copy()
    
    if ventana_reciente.empty:
        return pd.DataFrame()
        
    # Agrupación estadística de extremos
    resumen_alertas = (
        ventana_reciente.groupby(['Sitio', 'Slot'], as_index=False)
        .agg(
            Picos_Tendencia=('Alerta_Tendencia', 'sum'),
            Vel_Max=('Fan_Speed_Rate', 'max'),
            Vel_Min=('Fan_Speed_Rate', 'min'),
            Ultimo_Reporte=('Timestamp', 'last')
        )
    )
    
    resumen_alertas['Variabilidad'] = resumen_alertas['Vel_Max'] - resumen_alertas['Vel_Min']
    
    # Identificar diagnóstico
    def definir_motivo(row):
        if row['Variabilidad'] >= umbral_oscilacion and row['Picos_Tendencia'] == 0:
            return "Oscilación Cíclica"
        elif row['Variabilidad'] >= umbral_oscilacion and row['Picos_Tendencia'] > 0:
            return "Inestabilidad Fuerte"
        return "Normal"
        
    resumen_alertas['Diagnóstico'] = resumen_alertas.apply(definir_motivo, axis=1)
    
    # 📌 FILTRO EXCLUSIVO: Conservar únicamente las filas de Inestabilidad Fuerte
    alertas_criticas = resumen_alertas[resumen_alertas['Diagnóstico'] == "Inestabilidad Fuerte"].copy()
    
    # Ordenar de mayor a menor criticidad por su velocidad máxima alcanzada
    return alertas_criticas.sort_values("Vel_Max", ascending=False)

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.title("Configuración")
st.sidebar.info(f"📂 Origen: `{FOLDER_PATH.name}`")
st.sidebar.warning("📉 Historial configurado a 5 días.")

forzar_recarga = False
if st.sidebar.button("🔥 Reconstruir Base Histórica"):
    with st.spinner("Procesando historial de red..."):
        st.cache_data.clear()
        if reconstruir_base():
            st.sidebar.success("¡Sincronizado!")
            forzar_recarga = True

if not os.path.exists(PARQUET_FILE) and not forzar_recarga:
    st.info("👋 Presiona 'Reconstruir Base Histórica' para inicializar.")
    st.stop()

df_total = cargar_base()

# ==========================================
# INTERFAZ GRÁFICA PRINCIPAL
# ==========================================
if not df_total.empty:
    
    st.markdown("## 🚨 ALERTAS AUTOMÁTICAS: INESTABILIDAD FUERTE DETECTADA")
    
    with st.spinner("Filtrando anomalías críticas en la red..."):
        df_anomalias = escanear_alertas_globales(df_total)
    
    if not df_anomalias.empty:
        st.error(f"⚠️ Se detectaron **{len(df_anomalias)} ventiladores** con cuadros de Inestabilidad Fuerte en la última semana:")
        
        tabla_alertas = df_anomalias[["Sitio", "Slot", "Vel_Max", "Vel_Min", "Ultimo_Reporte"]].copy()
        tabla_alertas["Ultimo_Reporte"] = tabla_alertas["Ultimo_Reporte"].dt.strftime('%d/%m %H:%M')
        tabla_alertas = tabla_alertas.rename(columns={
            "Vel_Max": "Máx Velocidad (%)",
            "Vel_Min": "Mín Velocidad (%)",
            "Ultimo_Reporte": "Último Reporte"
        })
        
        st.dataframe(tabla_alertas, use_container_width=True, hide_index=True)
    else:
        st.success("✅ **Comportamiento Estable:** Ningún sitio presenta cuadros de inestabilidad fuerte detectados en la red.")
        
    st.markdown("---")

    # --- PESTAÑAS ---
    tab1, tab2 = st.tabs(["📊 ACTUAL (Top 20)", "📈 HISTÓRICO POR HORA"])

    with tab1:
        df_actual = df_total.sort_values("Timestamp").groupby(["Sitio", "Slot"]).last().reset_index()
        df_top20 = df_actual.nlargest(20, "Fan_Speed_Rate")

        st.subheader("🔥 Top 20 Ventiladores con Mayor Carga")
        fig = px.bar(
            df_top20, x="ID_Full", y="Fan_Speed_Rate", color="Estado",
            color_discrete_map={"Crítico": "red", "Normal": "green"}, text_auto=True, height=450
        )
        fig.add_hline(y=UMBRAL_CRITICO_FAN, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        sitios = sorted(df_total["Sitio"].dropna().unique())
        sitio_h = st.selectbox("Seleccione un Sitio para inspeccionar su historial:", sitios)

        if sitio_h:
            df_plot = pd.read_parquet(PARQUET_FILE, filters=[("Sitio", "==", sitio_h)]).sort_values("Timestamp")
            
            fig_h = px.line(
                df_plot, 
                x="Timestamp", 
                y="Fan_Speed_Rate", 
                color="Slot", 
                markers=True, 
                title=f"Evolución Temporal - Sitio: {sitio_h}"
            )
            fig_h.add_hline(y=UMBRAL_CRITICO_FAN, line_dash="dash", line_color="red")
            st.plotly_chart(fig_h, use_container_width=True)
else:
    st.warning("La base de datos está vacía.")
