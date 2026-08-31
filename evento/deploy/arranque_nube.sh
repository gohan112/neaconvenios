#!/bin/sh
# Arranque en la nube: primero recupera la base del bucket (si el contenedor es
# nuevo, que es lo normal), y después levanta la app con la copia continua en
# marcha. Sin REPLICA_URL funciona igual, pero sin red de seguridad.
set -e

mkdir -p "$(dirname "$EVENTO_DB_PATH")"

if [ -n "$REPLICA_URL" ]; then
  if [ ! -f "$EVENTO_DB_PATH" ]; then
    echo ">> Recuperando la base del bucket…"
    litestream restore -if-replica-exists -v "$EVENTO_DB_PATH" || \
      echo ">> No había copia todavía: se empieza de cero."
  fi
  echo ">> Copia continua activada: $REPLICA_URL"
  exec litestream replicate -exec "python /app/app.py"
fi

echo ">> Sin REPLICA_URL: la base vive solo dentro del contenedor."
exec python /app/app.py
