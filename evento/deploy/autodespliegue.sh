#!/usr/bin/env bash
# Deja la app actualizándose sola: cada cambio nuevo en GitHub pasa las
# pruebas, se construye y se despliega en Cloud Run, sin que tengas que tocar
# nada. Es lo mismo que hacía el temporizador del servidor de Amazon.
#
#   bash deploy/autodespliegue.sh
#
# Solo hay que ejecutarlo UNA vez. Antes, en la consola, hay que haber
# conectado el repositorio a Cloud Build (una pantalla, dos clics): el script
# te dice exactamente dónde si hace falta.
set -euo pipefail

PROYECTO="${1:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-europe-west1}"          # donde vive la app (Cloud Run)
# El disparador va aparte: la conexión con GitHub se hace en «global», que es
# lo que ofrece la consola por defecto, y ahí tiene que vivir también él.
REGION_DISPARADOR="${REGION_DISPARADOR:-global}"
SERVICIO="${SERVICIO:-neaevento}"
DUENO="${DUENO:-gohan112}"
REPO="${REPO:-neaconvenios}"
RAMA="${RAMA:-claude/event-app-day-12-e4lcrp}"
NOMBRE="${NOMBRE:-neaevento-autodespliegue}"

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
echo ">> Proyecto: $PROYECTO · repositorio: $DUENO/$REPO · rama: $RAMA"

echo ">> 1/3 Permisos para que Cloud Build pueda desplegar…"
NUMERO="$(gcloud projects describe "$PROYECTO" --format 'value(projectNumber)')"
for CUENTA in "${NUMERO}@cloudbuild.gserviceaccount.com" \
              "${NUMERO}-compute@developer.gserviceaccount.com"; do
  for PAPEL in roles/run.admin roles/iam.serviceAccountUser \
               roles/artifactregistry.writer roles/logging.logWriter; do
    gcloud projects add-iam-policy-binding "$PROYECTO" \
      --member "serviceAccount:$CUENTA" --role "$PAPEL" \
      --condition=None >/dev/null 2>&1 || true
  done
done
echo "   hecho"

echo ">> 2/3 Creando el disparador…"
if gcloud builds triggers describe "$NOMBRE" --project "$PROYECTO" \
     --region "$REGION_DISPARADOR" >/dev/null 2>&1; then
  echo "   ya existía: $NOMBRE"
elif gcloud builds triggers create github \
       --project "$PROYECTO" --region "$REGION_DISPARADOR" --name "$NOMBRE" \
       --repo-owner "$DUENO" --repo-name "$REPO" \
       --branch-pattern "^$(printf '%s' "$RAMA" | sed 's/[.[\*^$]/\\&/g')$" \
       --build-config evento/cloudbuild.yaml \
       --substitutions "_REGION=$REGION,_SERVICIO=$SERVICIO" \
       --description "NeaEvento: pruebas + despliegue automático" 2>/tmp/nea_error; then
  echo "   creado: $NOMBRE"
else
  cat /tmp/nea_error >&2
  echo ""
  echo "  Casi seguro que falta conectar el repositorio con Cloud Build."
  echo "  Es una pantalla y dos clics, una sola vez:"
  echo ""
  echo "   1. Abre:"
  echo "      https://console.cloud.google.com/cloud-build/triggers?project=$PROYECTO"
  echo "   2. «Conectar repositorio» → GitHub → autoriza → elige $DUENO/$REPO"
  echo "   3. Vuelve aquí y repite:  bash deploy/autodespliegue.sh"
  echo ""
  exit 1
fi

echo ">> 3/3 Lanzando un despliegue ahora, para comprobar que funciona…"
gcloud builds triggers run "$NOMBRE" --project "$PROYECTO" --region "$REGION_DISPARADOR" \
  --branch "$RAMA" >/dev/null

echo ""
echo "============================================================"
echo "  Listo: la app se actualiza sola."
echo ""
echo "  A partir de ahora, cada cambio que se suba a la rama"
echo "     $RAMA"
echo "  pasa las pruebas y se despliega solo. Si las pruebas fallan NO se"
echo "  despliega: Cloud Run sigue sirviendo la versión buena."
echo ""
echo "  Ver cómo va:"
echo "     https://console.cloud.google.com/cloud-build/builds?project=$PROYECTO"
echo ""
echo "  Para desactivarlo:"
echo "     gcloud builds triggers delete $NOMBRE --region $REGION_DISPARADOR"
echo "============================================================"
