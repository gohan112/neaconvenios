#!/usr/bin/env bash
# Deja la app en una dirección corta y decente:
#
#     https://neaevento.web.app      en vez de     https://neaevento-jeak2blh5q-ew.a.run.app
#
#   bash deploy/dominio.sh                 (intenta llamarse «neaevento»)
#   bash deploy/dominio.sh otro-nombre     (o como quieras, si está libre)
#
# Pone Firebase Hosting por delante de Cloud Run. No mueve la app de sitio: la
# dirección larga sigue funcionando igual, esta es otra puerta a lo mismo.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SITIO="${1:-neaevento}"
PROYECTO="${PROYECTO:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-europe-west1}"
SERVICIO="${SERVICIO:-neaevento}"

if ! command -v firebase >/dev/null 2>&1; then
  echo "Falta la herramienta de Firebase. En Cloud Shell ya viene puesta;"
  echo "en tu ordenador se instala con:   npm install -g firebase-tools"
  exit 1
fi
if [ -z "$PROYECTO" ] || [ "$PROYECTO" = "(unset)" ]; then
  echo "No sé de qué proyecto. Prueba: gcloud config set project TU-PROYECTO"
  exit 1
fi
echo ">> Proyecto: $PROYECTO · servicio: $SERVICIO ($REGION)"

echo ">> 1/3 Pidiendo el nombre «$SITIO»…"
if firebase hosting:sites:list --project "$PROYECTO" 2>/dev/null | grep -q "[^a-z0-9-]$SITIO[^a-z0-9-]"; then
  echo "   ya era tuyo"
elif firebase hosting:sites:create "$SITIO" --project "$PROYECTO" >/dev/null 2>&1; then
  echo "   conseguido"
else
  echo "   «$SITIO» está cogido por otro. Se usa el del proyecto: $PROYECTO"
  SITIO="$PROYECTO"
fi

echo ">> 2/3 Preparando la configuración…"
RECETA="$(mktemp -t firebase-neaevento-XXXXXX.json)"
trap 'rm -f "$RECETA"' EXIT
cat > "$RECETA" <<JSON
{
  "hosting": {
    "site": "$SITIO",
    "public": "hosting",
    "ignore": ["firebase.json", "LEEME.txt", "**/.*", "**/node_modules/**"],
    "rewrites": [
      { "source": "**", "run": { "serviceId": "$SERVICIO", "region": "$REGION" } }
    ],
    "headers": [
      { "source": "**", "headers": [
        { "key": "Cache-Control", "value": "no-store, max-age=0" },
        { "key": "Service-Worker-Allowed", "value": "/" }
      ]}
    ]
  }
}
JSON

echo ">> 3/3 Publicando…"
( cd "$APP_DIR" && firebase deploy --only hosting --project "$PROYECTO" \
    --config "$RECETA" )

echo ""
echo "============================================================"
echo "  Ya está en:"
echo "     https://$SITIO.web.app"
echo ""
echo "  Falta un paso, y es importante: en ⚙️ Evento pon esa dirección"
echo "  como URL pública, para que los enlaces se generen con ella."
echo "  Los códigos de cada uno NO cambian."
echo ""
echo "  La dirección larga de siempre sigue funcionando: esto es otra"
echo "  puerta al mismo sitio, no una mudanza."
echo "============================================================"
