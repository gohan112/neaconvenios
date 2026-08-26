#!/bin/bash
# Doble clic para abrir NeaEvento en este ordenador.
# (Para cerrarla: pulsa Control+C en esta ventana, o ciérrala.)

cd "$(dirname "$0")" || exit 1

# Contraseña del panel OPCIONAL: si existe "clave_admin.txt" con la contraseña
# dentro, se usa. En local no hace falta.
if [ -f "clave_admin.txt" ]; then
  export EVENTO_ADMIN_PASSWORD="$(tr -d '[:space:]' < clave_admin.txt)"
fi

if ! python3 -c "import flask" 2>/dev/null; then
  echo "Faltan dependencias. Ejecuta primero 'Instalar (primera vez).command'."
  echo "Pulsa Enter para cerrar."
  read -r
  exit 1
fi

echo "Abriendo la app... El panel de organización es http://localhost:8502/admin"
( sleep 2 && open "http://localhost:8502/admin" ) &
exec python3 app.py
