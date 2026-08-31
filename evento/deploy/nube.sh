#!/usr/bin/env bash
# Sube NeaEvento a Google Cloud Run, con la base de datos replicada a un bucket.
# Es la misma cuenta que Firebase: un proyecto de Firebase ES un proyecto de
# Google Cloud, así que con el plan Blaze ya está todo activo.
#
#   bash deploy/nube.sh                      (usa el proyecto de gcloud)
#   bash deploy/nube.sh mi-proyecto          (o el que le digas)
#
# Antes hace falta, una sola vez:
#   gcloud auth login && gcloud config set project TU-PROYECTO
#
# Qué deja montado:
#   · Cloud Run con la app en https y un dominio fijo (…run.app)
#   · Un bucket con la copia continua de la base (Litestream)
#   · Una sola instancia: SQLite lo escribe uno cada vez
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROYECTO="${1:-$(gcloud config get-value project 2>/dev/null || true)}"
# Bélgica: es la región europea que admite todo, incluido poner Firebase
# Hosting delante para tener un dominio bonito. Madrid (europe-southwest1)
# está más cerca, pero son milisegundos: REGION=europe-southwest1 bash …
REGION="${REGION:-europe-west1}"
SERVICIO="${SERVICIO:-neaevento}"
BUCKET="${BUCKET:-${PROYECTO}-neaevento}"

if [ -z "$PROYECTO" ] || [ "$PROYECTO" = "(unset)" ]; then
  echo "No sé a qué proyecto subirlo. Prueba:"
  echo "   gcloud config set project TU-PROYECTO"
  echo "   bash deploy/nube.sh"
  exit 1
fi
echo ">> Proyecto: $PROYECTO · región: $REGION · servicio: $SERVICIO"

echo ">> 1/5 Activando lo que hace falta (la primera vez tarda un poco)…"
if ! gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
     storage.googleapis.com artifactregistry.googleapis.com --project "$PROYECTO"; then
  echo ""
  echo "  No se han podido activar los servicios. Casi siempre es una de dos:"
  echo ""
  echo "  · El proyecto sigue en el plan gratis (Spark). Cloud Run necesita"
  echo "    Blaze: en console.firebase.google.com, con el proyecto abierto,"
  echo "    ⚙️ → Uso y facturación → Modificar plan → Blaze. No hay que volver"
  echo "    a meter la tarjeta: se elige la cuenta de facturación que ya tienes."
  echo ""
  echo "  · O el proyecto no es este. Comprueba el ID (no el nombre bonito):"
  echo "        gcloud projects list"
  echo "        gcloud config set project EL-ID-DE-ARRIBA"
  echo ""
  exit 1
fi

echo ">> 2/5 Bucket para la copia de la base…"
if ! gcloud storage buckets describe "gs://$BUCKET" --project "$PROYECTO" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://$BUCKET" --project "$PROYECTO" \
    --location "$REGION" --uniform-bucket-level-access
else
  echo "   ya existía: gs://$BUCKET"
fi

echo ">> 3/5 Contraseña del panel…"
PASS="${EVENTO_ADMIN_PASSWORD:-}"
if [ -z "$PASS" ]; then
  PASS="$(head -c 256 /dev/urandom | tr -dc 'A-Za-z0-9' | cut -c1-14)"
  echo "   generada una nueva (apúntala): $PASS"
fi

echo ">> 4/5 Construyendo la imagen (Cloud Build)…"
IMAGEN="gcr.io/$PROYECTO/$SERVICIO"
# --tag solo sabe usar un fichero llamado «Dockerfile», y el nuestro es
# Dockerfile.nube, así que le pasamos una receta de Cloud Build de dos líneas.
RECETA="$(mktemp -t cloudbuild-neaevento-XXXXXX.yaml)"
trap 'rm -f "$RECETA"' EXIT
cat > "$RECETA" <<YAML
steps:
  - name: gcr.io/cloud-builders/docker
    args: ["build", "-f", "Dockerfile.nube", "-t", "$IMAGEN", "."]
images: ["$IMAGEN"]
YAML
gcloud builds submit "$APP_DIR" --project "$PROYECTO" --config "$RECETA" \
  --gcs-source-staging-dir "gs://$BUCKET/build"

echo ">> 5/5 Desplegando en Cloud Run…"
gcloud run deploy "$SERVICIO" --project "$PROYECTO" --region "$REGION" \
  --image "$IMAGEN" \
  --allow-unauthenticated \
  --min-instances 1 --max-instances 1 \
  --no-cpu-throttling \
  --memory 512Mi \
  --set-env-vars "REPLICA_URL=gcs://$BUCKET/neaevento,EVENTO_ADMIN_PASSWORD=$PASS,TZ=Europe/Madrid"

# La cuenta con la que corre el servicio tiene que poder escribir en el bucket
SA="$(gcloud run services describe "$SERVICIO" --project "$PROYECTO" \
      --region "$REGION" --format 'value(spec.template.spec.serviceAccountName)')"
[ -z "$SA" ] && SA="$(gcloud projects describe "$PROYECTO" \
      --format 'value(projectNumber)')-compute@developer.gserviceaccount.com"
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
  --member "serviceAccount:$SA" --role roles/storage.objectAdmin \
  --project "$PROYECTO" >/dev/null

URL="$(gcloud run services describe "$SERVICIO" --project "$PROYECTO" \
       --region "$REGION" --format 'value(status.url)')"

echo ""
echo "============================================================"
echo "  NeaEvento en la nube:"
echo "     $URL"
echo "     $URL/admin      (contraseña: $PASS)"
echo ""
echo "  Falta un paso: en ⚙️ Evento, pon esa dirección como URL pública"
echo "  y vuelve a repartir los enlaces (o restaura ahí tu copia)."
echo ""
echo "  · Va por https: se puede instalar como app de verdad."
echo "  · La base se replica sola a gs://$BUCKET (Litestream)."
echo "  · Una sola instancia a propósito: SQLite lo escribe uno."
echo ""
echo "  Cuando pase el evento, para no gastar:"
echo "     gcloud run services update $SERVICIO --region $REGION --min-instances 0"
echo "============================================================"
