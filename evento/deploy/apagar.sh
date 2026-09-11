#!/usr/bin/env bash
# Deja de pagar la máquina encendida cuando el evento ya ha pasado.
#
#     bash deploy/apagar.sh
#
# Lo caro de esta app NO es la copia de seguridad: es que hay un ordenador
# despierto 24 h al día (--min-instances 1). Eso se paga esté usándose o no,
# también a las 4 de la mañana. Se puso así porque Litestream, que es quien
# copia la base al bucket, es un proceso de fondo: si la máquina se duerme,
# deja de copiar.
#
# Cuando el evento ya ha terminado no hay nada que copiar, así que se puede
# dejar que se duerma. Entonces solo se enciende cuando alguien entra, y con
# 18 personas mirando los resultados de vez en cuando la factura es ~0 €.
#
# El precio: la primera visita tras un rato sin nadie tarda unos segundos en
# cargar. Es lo mismo que les pasa a tus otras apps de Firebase.
set -euo pipefail

PROYECTO="${PROYECTO:-$(gcloud config get-value project 2>/dev/null || true)}"
if [ -z "$PROYECTO" ] || [ "$PROYECTO" = "(unset)" ]; then
  echo "Esta sesión no tiene proyecto puesto. Ponlo y repite:"
  echo "   gcloud config set project EL-QUE-SEA"
  exit 1
fi
SERVICIO="${SERVICIO:-neaevento}"
REGION="${REGION:-europe-west1}"
BUCKET="${BUCKET:-${PROYECTO}-neaevento}"

echo ">> 1/3 ¿Está la copia de seguridad al día?"
ULTIMA="$(gcloud storage ls -l "gs://$BUCKET/neaevento/**" --project "$PROYECTO" \
          2>/dev/null | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z' \
          | sort | tail -1 || true)"
if [ -z "$ULTIMA" ]; then
  echo ""
  echo "  ✋ No veo NADA en gs://$BUCKET/neaevento."
  echo "     No apago nada: si duermes la máquina ahora y la copia no está,"
  echo "     te quedas sin los datos. Mira primero:"
  echo "        bash deploy/rescate.sh"
  exit 1
fi
echo "     última escritura en el bucket: $ULTIMA  ✔"

echo ""
echo ">> 2/3 Bájate una copia a mano, por si acaso"
echo "     Entra en  /admin → ⚙️ Evento → «Descargar copia»  y guárdala."
echo "     (Es un fichero .db de nada; con eso ya no dependes de la nube.)"
read -r -p "     ¿Hecho? [s/N] " HECHO
case "${HECHO:-n}" in
  s|S|si|SI|sí|Sí) ;;
  *) echo "     Vale, lo dejo como está. Cuando la tengas, repite esto."; exit 0 ;;
esac

echo ""
echo ">> 3/3 Dejando que la máquina se duerma…"
gcloud run services update "$SERVICIO" --project "$PROYECTO" --region "$REGION" \
  --min-instances 0

echo ""
echo "============================================================"
echo "  Listo. A partir de ahora solo se enciende cuando alguien entra."
echo ""
echo "  · La app sigue funcionando y los enlaces siguen valiendo."
echo "  · La primera visita tras un rato parado tarda unos segundos."
echo "  · Si algún día quieres volver a dejarla despierta:"
echo "       gcloud run services update $SERVICIO --region $REGION --min-instances 1"
echo ""
echo "  Y si ya no la quieres para nada, esto la borra del todo:"
echo "       gcloud run services delete $SERVICIO --region $REGION"
echo "       gcloud storage rm -r gs://$BUCKET"
echo "============================================================"
