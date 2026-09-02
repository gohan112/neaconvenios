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

# Un proyecto de Google Cloud no tiene por qué tener Firebase: si se creó
# desde la consola de Cloud, no lo tiene, y entonces Hosting no existe ahí.
echo ">> 0/3 Comprobando que el proyecto tiene Firebase…"
if ! firebase projects:list 2>/dev/null | grep -q "[^a-z0-9-]$PROYECTO[^a-z0-9-]"; then
  echo ""
  echo "  «$PROYECTO» no aparece entre tus proyectos de Firebase."
  echo "  Es normal si lo creaste desde la consola de Google Cloud: entonces es"
  echo "  un proyecto de Cloud a secas y hay que añadirle Firebase. Se hace una"
  echo "  vez, no toca nada de lo que ya funciona (ni Cloud Run, ni la base):"
  echo ""
  echo "   1. Entra en https://console.firebase.google.com"
  echo "      con la MISMA cuenta que usas aquí:"
  echo "         $(gcloud config get-value account 2>/dev/null || echo '?')"
  echo "   2. «Añadir proyecto»."
  echo "   3. En el hueco del nombre NO escribas uno nuevo: despliega la lista"
  echo "      y elige «$PROYECTO», que ya existe."
  echo "   4. Analytics: no hace falta. Terminar."
  echo "   5. Vuelve aquí y repite:  bash deploy/dominio.sh"
  echo ""
  echo "  Mientras tanto la app sigue funcionando en su dirección larga."
  exit 1
fi
echo "   bien"

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
# La receta tiene que vivir JUNTO a la app: Firebase busca la carpeta «public»
# al lado del fichero de configuración, no desde donde se lanza el comando.
RECETA="$APP_DIR/.firebase-despliegue.json"
trap 'rm -f "$RECETA"' EXIT
mkdir -p "$APP_DIR/hosting"
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
    --config "$(basename "$RECETA")" )

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
