#!/usr/bin/env bash
# Recupera el evento del bucket cuando la app aparece vacía.
#
#     bash deploy/rescate.sh
#
# Litestream guarda las copias por «generaciones». Si el contenedor arrancó
# alguna vez sin poder recuperar la copia, empezó una generación nueva y vacía
# — pero la anterior, con los datos buenos, sigue en el bucket.
#
# Esto prueba TODAS las generaciones, cuenta lo que hay dentro de cada una y
# se queda con la que más tenga. No toca nada: solo deja un fichero .db que
# tú restauras desde el panel cuando lo hayas mirado.
set -euo pipefail

PROYECTO="${PROYECTO:-$(gcloud config get-value project 2>/dev/null || true)}"
BUCKET="${BUCKET:-${PROYECTO}-neaevento}"
RUTA="${RUTA:-neaevento}"
DESTINO="${DESTINO:-$HOME/rescate.db}"
TRABAJO="$(mktemp -d)"
trap 'rm -rf "$TRABAJO"' EXIT

echo ">> Bucket: gs://$BUCKET/$RUTA"

if ! command -v litestream >/dev/null 2>&1; then
  echo ">> Bajando litestream (no viene en Cloud Shell)…"
  curl -fsSL "https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.tar.gz" \
    -o "$TRABAJO/ls.tgz"
  tar -C "$TRABAJO" -xzf "$TRABAJO/ls.tgz" litestream
  LITESTREAM="$TRABAJO/litestream"
else
  LITESTREAM="litestream"
fi

echo ">> Generaciones que hay guardadas:"
GENS="$(gcloud storage ls "gs://$BUCKET/$RUTA/generations/" 2>/dev/null \
        | sed 's|.*/generations/||; s|/$||' | grep . || true)"
if [ -z "$GENS" ]; then
  echo ""
  echo "  No hay ninguna copia en gs://$BUCKET/$RUTA."
  echo "  Comprueba que el bucket es ese:   gcloud storage ls"
  exit 1
fi
printf '%s\n' "$GENS" | sed 's/^/     /'

MEJOR=""; MEJOR_N=-1
echo ""
echo ">> Probando cada una (esto no cambia nada):"
for G in $GENS; do
  SALIDA="$TRABAJO/$G.db"
  if ! "$LITESTREAM" restore -generation "$G" -o "$SALIDA" \
       "gcs://$BUCKET/$RUTA" >/dev/null 2>&1; then
    echo "     $G  ✘ no se pudo recuperar"
    continue
  fi
  N=$(sqlite3 "$SALIDA" "SELECT count(*) FROM participantes" 2>/dev/null || echo 0)
  E=$(sqlite3 "$SALIDA" "SELECT count(*) FROM equipos" 2>/dev/null || echo 0)
  V=$(sqlite3 "$SALIDA" "SELECT count(*) FROM participantes WHERE revelado_en IS NOT NULL" 2>/dev/null || echo 0)
  FECHA=$(date -r "$SALIDA" '+%d/%m %H:%M' 2>/dev/null || echo "?")
  echo "     $G  → $N participantes · $E equipos · $V ya vieron su sorteo"
  if [ "$N" -gt "$MEJOR_N" ]; then MEJOR="$G"; MEJOR_N="$N"; fi
done

echo ""
if [ -z "$MEJOR" ] || [ "$MEJOR_N" -le 0 ]; then
  echo "  Ninguna generación tiene participantes. Antes de nada, NO reinicies"
  echo "  el servicio: cada arranque nuevo escribe encima. Dímelo y lo miramos."
  exit 1
fi

cp "$TRABAJO/$MEJOR.db" "$DESTINO"
echo "============================================================"
echo "  Recuperado en:  $DESTINO"
echo "     $MEJOR_N participantes, de la generación $MEJOR"
echo ""
echo "  Ahora:"
echo "   1. En Cloud Shell, los tres puntos ⋮ de arriba → «Descargar»,"
echo "      y escribe la ruta:   $DESTINO"
echo "   2. En el panel: ⚙️ Evento → restaurar copia → ese fichero."
echo ""
echo "  Míralo antes de repartir nada: que estén los 18 y sus equipos."
echo "============================================================"
