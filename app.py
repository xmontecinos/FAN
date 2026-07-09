import streamlit as st
import pandas as pd
import plotly.express as px

# Función para cargar la base
def cargar_base():
    return pd.read_parquet('base_historica_fan.parquet')

# Configuración
UMBRAL_CRITICO_FAN = 80 

st.title("📊 Monitor de Ventiladores Huawei")

# Cargar datos
df_total = cargar_base()

# --- LÍNEA DE DIAGNÓSTICO ---
# Esto imprimirá en tu app los nombres exactos de tus columnas.
# Si "Slot" da error, revisa qué dice exactamente esta lista.
st.write("Columnas detectadas en el archivo:", df_total.columns.tolist())
# ----------------------------

if not df_total.empty:
    st.markdown("## 🚨 Resumen de Estado")

    # 1. Procesamiento de datos
    # NOTA: Asegúrate de que los nombres "NE_Name" y "Slot" coincidan 
    # exactamente con lo que imprime la línea de diagnóstico arriba.
    ultimos_datos = df_total.sort_values("Timestamp").groupby(["NE_Name", "Slot"]).last().reset_index()
    
    # Filtro de críticos
    criticos = ultimos_datos[ultimos_datos['Fan_Speed'] >= UMBRAL_CRITICO_FAN]

    if not criticos.empty:
        st.error(f"⚠️ ¡Atención! Se detectaron {len(criticos)} ventiladores en estado crítico.")
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