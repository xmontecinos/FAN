import streamlit as st
import pandas as pd
import plotly.express as px
import os
from pathlib import Path

# ==========================================
# CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Monitor FAN Huawei", layout="wide")

UMBRAL_CRITICO_FAN = 90 
FOLDER_PATH = 'FANF' 
PARQUET_FILE = 'base_historica_fan.parquet'

# ==========================================
# CARGA DE DATOS OPTIMIZADA
# ==========================================
@st.cache_data(ttl=600) # Se refresca automáticamente cada 10 minutos
def cargar_base():
    if os.path.exists(PARQUET_FILE):
        try:
            return pd.read_parquet(PARQUET_FILE)
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# ==========================================
# INTERFAZ GRÁFICA
# ==========================================
st.title("📊 Monitor de Ventiladores Huawei")

df_total = cargar_base()

if not df_total.empty:
    # 1. Indicador de Alertas (Visualización rápida)
    st.markdown("## 🚨 Resumen de Estado")
    
    # Filtro rápido para mostrar solo lo crítico (sin procesar todo el historial)
    ultimos_datos = df_total.sort_values("Timestamp").groupby(["Sitio", "Slot"]).last().reset_index()
    criticos = ultimos_datos[ultimos_datos['Fan_Speed_Rate'] >= UMBRAL_CRITICO_FAN]
    
    if not criticos.empty:
        st.error(f"⚠️ ¡Atención! Se detectaron **{len(criticos)} ventiladores** en estado crítico actualmente.")
        st.dataframe(criticos[["Sitio", "Slot", "Fan_Speed_Rate", "Timestamp"]], use_container_width=True)
    else:
        st.success("✅ Todos los ventiladores operan en niveles normales.")

    # 2. Pestañas de Visualización
    tab1, tab2 = st.tabs(["🔥 Top 20 Carga Actual", "📈 Histórico por Sitio"])

    with tab1:
        st.subheader("Top 20 Ventiladores con Mayor Carga")
        df_top20 = ultimos_datos.nlargest(20, "Fan_Speed_Rate")
        fig = px.bar(
            df_top20, x="ID_Full", y="Fan_Speed_Rate", color="Estado",
            color_discrete_map={"Crítico": "red", "Normal": "green"}, 
            text_auto=True, height=500
        )
        fig.add_hline(y=UMBRAL_CRITICO_FAN, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        sitios = sorted(df_total["Sitio"].dropna().unique())
        sitio_h = st.selectbox("Seleccione un Sitio para inspeccionar:", sitios)

        if sitio_h:
            # Filtramos directo desde el parquet para no cargar memoria innecesaria
            df_plot = pd.read_parquet(PARQUET_FILE, filters=[("Sitio", "==", sitio_h)])
            fig_h = px.line(
                df_plot.sort_values("Timestamp"), 
                x="Timestamp", y="Fan_Speed_Rate", color="Slot", 
                markers=True, title=f"Historial - {sitio_h}"
            )
            fig_h.add_hline(y=UMBRAL_CRITICO_FAN, line_dash="dash", line_color="red")
            st.plotly_chart(fig_h, use_container_width=True)

else:
    st.warning("La base de datos está vacía o el script de procesamiento (etl_fan.py) aún no ha generado el archivo.")
    st.info("Asegúrate de que el script `etl_fan.py` esté funcionando correctamente en segundo plano.")
