import pandas as pd
import os
import glob
import re
from datetime import datetime, timedelta

ruta_carpeta = 'D:/FAN/FANF/'
nombre_archivo_salida = 'base_historica_fan.parquet'

def procesar_etl():
    archivos_txt = glob.glob(os.path.join(ruta_carpeta, "*.txt"))
    data = []
    
    # Definimos la fecha límite de hace 14 días
    fecha_limite = datetime.now() - timedelta(days=14)
    print(f"Filtrando datos desde: {fecha_limite.strftime('%Y-%m-%d')}")

    for archivo in archivos_txt:
        with open(archivo, 'r', encoding='utf-8', errors='ignore') as f:
            contenido = f.read()
            bloques = re.split(r'NE Name:', contenido)
            
            for bloque in bloques:
                if "DSP FAN" in bloque:
                    fecha_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', bloque)
                    if fecha_match:
                        fecha_registro = datetime.strptime(fecha_match.group(0), '%Y-%m-%d %H:%M:%S')
                        
                        # Solo agregamos si es de los últimos 14 días
                        if fecha_registro >= fecha_limite:
                            ne_name = re.search(r'\s*(\S+)', bloque).group(1)
                            temp_match = re.search(r'Temperature\(degree Celsius\)\s*=\s*(\d+)', bloque)
                            fan_match = re.search(r'Fan Speed Rate\(%\)\s*=\s*(\d+)', bloque)
                            
                            data.append({
                                'Timestamp': fecha_registro,
                                'NE_Name': ne_name,
                                'Temperature': int(temp_match.group(1)) if temp_match else None,
                                'Fan_Speed': int(fan_match.group(1)) if fan_match else None
                            })

    if not data:
        print("No se encontraron registros en los últimos 14 días.")
        return

    df = pd.DataFrame(data)
    df.to_parquet(nombre_archivo_salida, index=False)
    print(f"¡Éxito! Archivo guardado con {len(df)} registros correspondientes a los últimos 14 días.")

if __name__ == "__main__":
    procesar_etl()