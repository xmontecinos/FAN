import os
import re
import pandas as pd
from pathlib import Path

UMBRAL_CRITICO_FAN = 90
PARQUET_FILE = "base_historica_fan.parquet"
BASE_DIR = Path(__file__).resolve().parent
FOLDER_PATH = BASE_DIR / "FANF"

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

        with open(path, 'rb') as f:
            content = f.read().decode('latin-1', errors='ignore')

        bloques = re.split(r'MML Command Result', content)
        for bloque in bloques[1:]:
            ne_match = re.search(r'NE Name\s*:\s*([\w_-]+)', bloque)
            if not ne_match:
                continue
            sitio = ne_match.group(1).strip()
            slots = re.findall(r'Slot No\.\s*=\s*(\d+)', bloque)
            speeds = re.findall(r'Fan Speed Rate\(%\)\s*=\s*(\d+)', bloque)
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
    except Exception as e:
        print(f"Error en {path.name}: {e}")
    return rows

def main():
    print("⚡ Iniciando procesamiento nativo de archivos MML...")
    if not FOLDER_PATH.exists():
        print(f"❌ No se encontró la carpeta {FOLDER_PATH}")
        return

    archivos = sorted([f for f in FOLDER_PATH.iterdir() if f.is_file() and f.suffix.lower() in [".txt", ".gz"]])
    print(f"📂 Se encontraron {len(archivos)} archivos para procesar.")

    todos_los_datos = []
    for idx, archivo in enumerate(archivos):
        todos_los_datos.extend(extraer_datos_fan(archivo))
        if (idx + 1) % 100 == 0:
            print(f"▓ Procesados {idx + 1}/{len(archivos)} archivos...")

    if todos_los_datos:
        df = pd.DataFrame(todos_los_datos)
        df.to_parquet(PARQUET_FILE, index=False, compression="snappy")
        print(f"💾 ¡Éxito! Base de datos guardada en '{PARQUET_FILE}' con {len(df)} registros.")
    else:
        print("⚠️ No se pudieron extraer datos de ningún archivo.")

if __name__ == "__main__":
    main()
