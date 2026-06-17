@echo off
REM Doble clic para abrir la app de convenios en el navegador.
REM (Para cerrarla: cierra esta ventana negra.)
cd /d "%~dp0"

REM Clave de Claude OPCIONAL: si existe "clave_claude.txt" con la API key, se usa.
if exist clave_claude.txt set /p ANTHROPIC_API_KEY=<clave_claude.txt

python -c "import streamlit" 2>nul
if errorlevel 1 (
  echo Faltan dependencias. Ejecuta primero "Instalar.bat".
  pause
  exit /b 1
)

echo Abriendo la app... (se abrira el navegador en unos segundos)
python -m streamlit run app.py
