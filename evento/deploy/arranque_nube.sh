#!/bin/sh
# Arranque en la nube: primero recupera la base del bucket (el contenedor es
# nuevo en cada despliegue y en cada reinicio), y después levanta la app con la
# copia continua en marcha.
#
# La regla de oro: si en el bucket HAY copia, o se recupera o no se arranca.
# Antes se arrancaba igual con la base vacía y la copia continua empezaba a
# replicar ese vacío — o sea, el fallo se comía los datos en vez de avisar.
set -e

mkdir -p "$(dirname "$EVENTO_DB_PATH")"

if [ -z "$REPLICA_URL" ]; then
  echo ">> Sin REPLICA_URL: la base vive solo dentro del contenedor."
  exec python /app/app.py
fi

if [ ! -f "$EVENTO_DB_PATH" ]; then
  echo ">> Mirando si hay copia en $REPLICA_URL…"
  # ¿Existe ya alguna copia? Si la hay, recuperarla no es opcional.
  if litestream generations "$REPLICA_URL" 2>/dev/null | grep -q '[0-9a-f]\{16\}'; then
    echo ">> Hay copia: recuperando…"
    if ! litestream restore -o "$EVENTO_DB_PATH" "$REPLICA_URL"; then
      echo ""
      echo "  !!  HAY COPIA EN EL BUCKET PERO NO SE HA PODIDO RECUPERAR."
      echo "  !!  No se arranca: si arrancara, la copia continua empezaría a"
      echo "  !!  replicar una base vacía y se perdería el evento."
      echo "  !!"
      echo "  !!  Para recuperarla a mano:  bash deploy/rescate.sh"
      echo ""
      exit 1
    fi
    echo ">> Recuperada."
  else
    echo ">> No hay copia todavía: se empieza de cero (primera vez)."
  fi
fi

echo ">> Copia continua activada: $REPLICA_URL"
exec litestream replicate -exec "python /app/app.py"
