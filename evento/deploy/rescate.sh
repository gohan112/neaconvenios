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
if [ -z "$PROYECTO" ] || [ "$PROYECTO" = "(unset)" ]; then
  echo "Esta sesión de Cloud Shell no tiene proyecto puesto."
  SUELTOS="$(gcloud projects list --format 'value(projectId)' 2>/dev/null || true)"
  if [ "$(printf '%s\n' "$SUELTOS" | grep -c .)" = "1" ]; then
    PROYECTO="$SUELTOS"
    echo "   Solo tienes uno, así que uso ese: $PROYECTO"
    gcloud config set project "$PROYECTO" >/dev/null 2>&1 || true
  else
    echo ""
    echo "   Tus proyectos:"
    printf '%s\n' "$SUELTOS" | sed 's/^/      /'
    echo ""
    echo "   Elige uno y repite:"
    echo "      gcloud config set project EL-QUE-SEA"
    echo "      bash $0"
    exit 1
  fi
fi
BUCKET="${BUCKET:-${PROYECTO}-neaevento}"
RUTA="${RUTA:-neaevento}"
DESTINO="${DESTINO:-$HOME/rescate.db}"
FORZAR="${1:-}"          # bash deploy/rescate.sh <generacion> para elegir a mano
TRABAJO="$(mktemp -d)"
trap 'rm -rf "$TRABAJO"' EXIT

echo ">> Bucket: gs://$BUCKET/$RUTA"
if ! gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1; then
  echo ""
  echo "  Ese bucket no existe. Los que tienes son:"
  gcloud storage ls 2>/dev/null | sed 's/^/     /'
  echo ""
  echo "  Repite indicándolo:   BUCKET=el-que-sea bash $0"
  exit 1
fi

# Para mirar dentro de cada copia hace falta poder leer SQLite. Si no se
# puede, se para: dar un cero cuando en realidad no se ha podido contar es
# exactamente el fallo que nos trajo hasta aquí.
if command -v sqlite3 >/dev/null 2>&1; then
  consulta(){ sqlite3 "$1" "$2" 2>/dev/null; }
elif command -v python3 >/dev/null 2>&1; then
  consulta(){ python3 -c "import sqlite3,sys
try: print(sqlite3.connect(sys.argv[1]).execute(sys.argv[2]).fetchone()[0])
except Exception: print('')" "$1" "$2"; }
else
  echo "  Hace falta sqlite3 o python3 para poder mirar dentro de las copias."
  exit 1
fi

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

if [ -n "$FORZAR" ]; then GENS="$FORZAR"; echo ""; echo ">> Solo la que has pedido: $FORZAR"; fi

MEJOR=""; MEJOR_N=-1; MEJOR_VIDA=-1
echo ""
echo ">> Probando cada una (esto no cambia nada). Puede tardar un par de minutos:"
printf '     %-18s %5s %5s %7s %6s   %s\n' generación gente equipos sorteos tiempos "último movimiento"
for G in $GENS; do
  SALIDA="$TRABAJO/$G.db"
  if ! "$LITESTREAM" restore -generation "$G" -o "$SALIDA" \
       "gcs://$BUCKET/$RUTA" >/dev/null 2>&1; then
    printf '     %-18s %s\n' "$G" "✘ no se pudo recuperar"
    continue
  fi
  N=$(consulta "$SALIDA" "SELECT count(*) FROM participantes")
  E=$(consulta "$SALIDA" "SELECT count(*) FROM equipos")
  V=$(consulta "$SALIDA" "SELECT count(*) FROM participantes WHERE revelado_en IS NOT NULL")
  C=$(consulta "$SALIDA" "SELECT count(*) FROM participantes WHERE trim(coalesce(tiempo_karts,''))!=''")
  if [ -z "$N" ]; then
    printf '     %-18s %s\n' "$G" "✘ recuperada, pero no se puede leer (copia rota)"
    continue
  fi
  # Lo más tardío que se hizo dentro: sirve para saber cuál es la más fresca
  ULT=$(consulta "$SALIDA" "SELECT coalesce(max(x),'—') FROM (
          SELECT max(revelado_en) x FROM participantes
          UNION ALL SELECT max(confirmado_en) FROM participantes
          UNION ALL SELECT max(visto_en) FROM participantes)")
  [ -z "$ULT" ] && ULT="—"
  printf '     %-18s %5s %5s %7s %6s   %s\n' "$G" "$N" "$E" "$V" "$C" "$ULT"
  # Se queda la que más gente tenga; a igualdad, la que llegó más lejos
  VIDA="$V$C$ULT"
  if [ "$N" -gt "$MEJOR_N" ] || { [ "$N" -eq "$MEJOR_N" ] && [ "$VIDA" \> "$MEJOR_VIDA" ]; }; then
    MEJOR="$G"; MEJOR_N="$N"; MEJOR_VIDA="$VIDA"
  fi
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
echo ""
echo "  Si en la tabla de arriba ves otra generación que te cuadra más:"
echo "     bash deploy/rescate.sh LA-QUE-SEA"
echo "============================================================"
