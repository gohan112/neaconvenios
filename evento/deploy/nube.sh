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
# (En Cloud Shell no hace falta: ya vas identificado.)
#
# Se puede repetir las veces que haga falta: no rompe nada y conserva la
# contraseña del panel. Si quieres poner tú la contraseña:
#   EVENTO_ADMIN_PASSWORD=lo-que-sea bash deploy/nube.sh
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
ALMACEN="${ALMACEN:-neaevento}"          # repositorio de imágenes
IMAGEN="$REGION-docker.pkg.dev/$PROYECTO/$ALMACEN/$SERVICIO"

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
echo ">> Proyecto: $PROYECTO · región: $REGION · servicio: $SERVICIO"
echo ">> Como: $(gcloud config get-value account 2>/dev/null || echo '?')"

echo ">> 1/6 Activando lo que hace falta (la primera vez tarda un poco)…"
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

echo ">> 2/6 Bucket para la copia de la base…"
if ! gcloud storage buckets describe "gs://$BUCKET" --project "$PROYECTO" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://$BUCKET" --project "$PROYECTO" \
    --location "$REGION" --uniform-bucket-level-access
else
  echo "   ya existía: gs://$BUCKET"
fi

echo ">> 3/6 Sitio donde guardar la imagen…"
if ! gcloud artifacts repositories describe "$ALMACEN" --project "$PROYECTO" \
     --location "$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$ALMACEN" --project "$PROYECTO" \
    --location "$REGION" --repository-format docker \
    --description "Imágenes de NeaEvento"
else
  echo "   ya existía: $ALMACEN"
fi

echo ">> 4/6 Contraseña del panel…"
PASS="${EVENTO_ADMIN_PASSWORD:-}"
if gcloud run services describe "$SERVICIO" --project "$PROYECTO" \
     --region "$REGION" >/dev/null 2>&1; then
  YA_ESTABA="si"
else
  YA_ESTABA="no"
fi
if [ -n "$PASS" ]; then
  echo "   se usa la que has puesto en EVENTO_ADMIN_PASSWORD"
elif [ "$YA_ESTABA" = "si" ]; then
  echo "   se conserva la que ya tenías"
else
  PASS="$(head -c 256 /dev/urandom | tr -dc 'A-Za-z0-9' | cut -c1-14)"
  echo "   generada una nueva (apúntala): $PASS"
fi

echo ">> 5/6 Construyendo la imagen…"
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

en_la_nube() {
  gcloud builds submit "$APP_DIR" --project "$PROYECTO" --config "$RECETA" \
    --gcs-source-staging-dir "gs://$BUCKET/build"
}
aqui_mismo() {
  gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet --project "$PROYECTO"
  ( cd "$APP_DIR" && docker build -f Dockerfile.nube -t "$IMAGEN" . )
  docker push "$IMAGEN"
}

LISTA=""
# Cloud Build recién activado tarda un par de minutos en repartir permisos, y
# mientras tanto contesta «no tienes permiso» aunque seas el dueño. Se reintenta.
for intento in 1 2; do
  if en_la_nube; then LISTA="si"; break; fi
  if [ "$intento" = "1" ]; then
    echo "   Cloud Build aún no responde (suele ser que acaba de activarse)."
    echo "   Reintento en 45 segundos…"
    sleep 45
  fi
done

if [ -z "$LISTA" ]; then
  if command -v docker >/dev/null 2>&1; then
    echo "   Cloud Build sigue sin dejarnos: construyo la imagen aquí mismo."
    aqui_mismo
  else
    echo ""
    echo "  No se ha podido construir la imagen y aquí no hay docker."
    echo "  Con la cuenta $(gcloud config get-value account 2>/dev/null) haría falta"
    echo "  el papel de «Editor» o «Cloud Build Editor» en el proyecto:"
    echo "        gcloud projects get-iam-policy $PROYECTO"
    echo ""
    exit 1
  fi
fi

echo ">> 6/6 Desplegando en Cloud Run…"
VARIABLES="REPLICA_URL=gcs://$BUCKET/neaevento,TZ=Europe/Madrid"
[ -n "$PASS" ] && VARIABLES="$VARIABLES,EVENTO_ADMIN_PASSWORD=$PASS"
gcloud run deploy "$SERVICIO" --project "$PROYECTO" --region "$REGION" \
  --image "$IMAGEN" \
  --allow-unauthenticated \
  --min-instances 1 --max-instances 1 \
  --no-cpu-throttling \
  --memory 512Mi \
  --update-env-vars "$VARIABLES"

# La cuenta con la que corre el servicio tiene que poder escribir en el bucket
SA="$(gcloud run services describe "$SERVICIO" --project "$PROYECTO" \
      --region "$REGION" --format 'value(spec.template.spec.serviceAccountName)' \
      2>/dev/null || true)"
if [ -z "$SA" ]; then
  NUMERO="$(gcloud projects describe "$PROYECTO" --format 'value(projectNumber)' \
            2>/dev/null || true)"
  SA="${NUMERO}-compute@developer.gserviceaccount.com"
fi
if ! gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
     --member "serviceAccount:$SA" --role roles/storage.objectAdmin \
     --project "$PROYECTO" >/dev/null 2>&1; then
  echo ""
  echo "  ⚠️  Ojo: no he podido darle permiso a $SA"
  echo "     para escribir en gs://$BUCKET. La app funciona, pero la copia de"
  echo "     seguridad NO se está guardando. Hay que arreglarlo antes del día 12:"
  echo "        gcloud storage buckets add-iam-policy-binding gs://$BUCKET \\"
  echo "          --member serviceAccount:$SA --role roles/storage.objectAdmin"
fi

URL="$(gcloud run services describe "$SERVICIO" --project "$PROYECTO" \
       --region "$REGION" --format 'value(status.url)' 2>/dev/null || true)"
[ -z "$URL" ] && URL="(míralo en console.cloud.google.com → Cloud Run)"

echo ""
echo "============================================================"
echo "  NeaEvento en la nube:"
echo "     $URL"
if [ -n "$PASS" ]; then
  echo "     $URL/admin      (contraseña: $PASS)"
else
  echo "     $URL/admin      (con la contraseña de siempre)"
fi
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
