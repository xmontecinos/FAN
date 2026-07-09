import ftplib
import os
import tarfile
import io

# --- Configuración ---
FTP_USER = "ftpuser"
FTP_PASS = "Claro@2023"
FTP_PATH = "/export/home/sysm/ftproot/MMLTaskResult/88844/history/"
SERVERS = [
    "172.27.37.8", "172.27.37.10", "172.27.37.11", "172.27.37.12", 
    "172.27.37.13", "172.27.37.14", "172.27.37.15", "172.27.37.16", 
    "172.27.37.17", "172.27.37.85,172.27.37.7"
]

LOCAL_BASE_DIR = r"D:\FAN\FANF"

if not os.path.exists(LOCAL_BASE_DIR):
    os.makedirs(LOCAL_BASE_DIR)

for ip in SERVERS:
    print(f"\n--- Conectando a: {ip} ---")
    try:
        ftp = ftplib.FTP(ip, timeout=20)
        ftp.login(FTP_USER, FTP_PASS)
        
        try:
            ftp.cwd(FTP_PATH)
        except:
            print(f"[!] Error: No existe la ruta {FTP_PATH}")
            ftp.quit()
            continue
        
        all_files = ftp.nlst()

        for filename in all_files:
            if filename in [".", ".."]: continue
            
            # --- MEJORA: LÓGICA DE NOMBRE LIMPIO (Reemplaza al .bat) ---
            # Quitamos extensiones para procesar el nombre base
            clean_name = filename.replace(".tar", "").replace(".TAR", "").replace(".txt", "")
            
            # Si el nombre del archivo contiene un guion bajo (como en tu .bat), 
            # tomamos solo lo que está después del primer "_"
            if "_" in clean_name:
                clean_name = clean_name.split("_", 1)[1]
            
            # Definimos la ruta final sin el prefijo de la IP [cite: 3]
            final_path = os.path.join(LOCAL_BASE_DIR, f"{clean_name}.txt")

            if os.path.exists(final_path):
                print(f"[-] Ya existe: {clean_name}.txt")
                continue

            print(f"[+] Descargando y limpiando: {filename} -> {clean_name}.txt...")
            
            buffer = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", buffer.write)
            buffer.seek(0)

            try:
                if tarfile.is_tarfile(buffer):
                    buffer.seek(0)
                    with tarfile.open(fileobj=buffer) as tar:
                        for member in tar.getmembers():
                            if member.name.lower().endswith(('.txt', '.mml')):
                                content = tar.extractfile(member)
                                if content:
                                    with open(final_path, "wb") as f:
                                        f.write(content.read())
                                    print(f"    [OK] Extraído y renombrado: {clean_name}.txt")
                                    break
                else:
                    buffer.seek(0)
                    with open(final_path, "wb") as f:
                        f.write(buffer.read())
                    print(f"    [OK] Guardado directo y renombrado: {clean_name}.txt")
            except Exception as e:
                print(f"    [!] Error procesando contenido: {e}")
            finally:
                buffer.close()

        ftp.quit()
    except Exception as e:
        print(f"[!!!] Error de conexión con {ip}: {e}")

print(f"\n>>> Revisión terminada. Archivos limpios en {LOCAL_BASE_DIR}")