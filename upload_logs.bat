@echo off
cd /d "D:\FAN\FANF"
:: Copiar el archivo nuevo desde la carpeta donde se descargan los logs
copy "D:\FAN\FANF" .

:: Comandos de Git para subirlo
git add .
git commit -m "Auto-upload log: %date% %time%"
git push origin main