@echo off
REM Doble clic UNA sola vez para instalar lo que necesita la app (requiere Python instalado).
cd /d "%~dp0"
echo Instalando dependencias (puede tardar 1-2 minutos)...
python -m pip install -r requirements.txt
echo.
echo Listo. Ya puedes abrir la app con "Abrir Convenios.bat".
pause
