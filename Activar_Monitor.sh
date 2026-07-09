#!/bin/bash
cd "d:/FAN/FANF"

echo "---------------------------------------------------"
echo "   INICIANDO ROBOT DE ACTUALIZACION HUAWEI"
echo "---------------------------------------------------"

while true; do
  # Intentar traer cambios antes de subir para evitar bloqueos
  git pull origin main --rebase
  
  git add .
  git commit -m "Auto-update $(date +'%H:%M')"
  git push origin main
  
  echo "✅ Todo al día. Próxima revisión en 5 min..."
  sleep 300
done