import streamlit as st
import pandas as pd
import plotly.express as px

# Función para cargar la base (asegúrate de que cargue el archivo correcto)
def cargar_base():
    # Ajusta la ruta si es necesario según donde esté tu archivo .parquet
    return pd.read_parquet('base_historica_fan.parquet')

# Configuración
UMBRAL_CRITICO_FAN = 80 

st.title("📊 Monitor de Ventiladores Huawei")

df_total = cargar_base()

if not df_total.empty:
    st.markdown("## 🚨 Resumen de Estado")

    # 1. Procesamiento de datos usando los nombres de columna correctos (NE_Name y Fan_Speed)
    ultimos_datos = df_total.sort_values("Timestamp").groupby(["NE_Name", "Slot"]).last().reset_index()
    
    # Filtro de críticos usando 'Fan_Speed'
    criticos = ultimos_datos[ultimos_datos['Fan_Speed'] >= UMBRAL_CRITICO_FAN]

    if not criticos.empty:
        st.error(f"⚠️ ¡Atención! Se detectaron {len(criticos)} ventiladores en estado crítico.")
        # Mostrar las columnas correctas
        st.dataframe(criticos[["NE_Name", "Slot", "Fan_Speed", "Timestamp"]], use_container_width=True)
    else:
        st.success("✅ Todos los ventiladores operan en niveles normales.")

    # 2. Visualización
    st.subheader("Gráfico de Carga")
    fig = px.bar(
        ultimos_datos, 
        x="NE_Name", 
        y="Fan_Speed", 
        color="Fan_Speed",
        color_continuous_scale="RdYlGn_r"
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("No hay datos disponibles para mostrar.")
