#!/bin/bash
# Doble clic para abrir la app de convenios en el navegador.
# (Para cerrarla: pulsa Control+C en esta ventana, o ciérrala.)

cd "$(dirname "$0")" || exit 1

# Clave de Claude OPCIONAL: si existe un fichero "clave_claude.txt" en esta
# carpeta con tu API key dentro, se usa automáticamente. No compartas ese fichero.
if [ -f "clave_claude.txt" ]; then
  export ANTHROPIC_API_KEY="$(tr -d '[:space:]' < clave_claude.txt)"
fi

# Comprobar que las dependencias están instaladas; si no, avisar.
if ! python3 -c "import streamlit" 2>/dev/null; then
  echo "Faltan dependencias. Ejecuta primero 'Instalar (primera vez).command'."
  echo "Pulsa Enter para cerrar."
  read -r
  exit 1
fi

echo "Abriendo la app... (se abrirá el navegador en unos segundos)"
exec python3 -m streamlit run app.py
