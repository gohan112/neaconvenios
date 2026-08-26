@echo off
REM Doble clic para abrir NeaEvento en este ordenador.
REM (Para cerrarla: cierra esta ventana negra.)
cd /d "%~dp0"

REM Contraseña del panel OPCIONAL: si existe "clave_admin.txt" con la
REM contraseña dentro, se usa. En local no hace falta.
if exist clave_admin.txt set /p EVENTO_ADMIN_PASSWORD=<clave_admin.txt

python -c "import flask" 2>nul
if errorlevel 1 (
  echo Faltan dependencias. Ejecuta primero "Instalar.bat".
  pause
  exit /b 1
)

echo Abriendo la app... El panel de organizacion es http://localhost:8502/admin
start "" http://localhost:8502/admin
python app.py
