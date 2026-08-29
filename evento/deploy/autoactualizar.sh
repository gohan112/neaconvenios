#!/usr/bin/env bash
# Trae la última versión del código desde GitHub y reinicia la app, pero solo
# si las pruebas siguen pasando: si algo falla, se queda la versión anterior
# (la app no se cae nunca por una actualización).
#
# Lo lanza solo el temporizador neaevento-update.timer cada 5 minutos.
# Para ver qué ha hecho:  journalctl -u neaevento-update -n 50
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"                 # …/evento
REPO="$(git -C "$APP_DIR" rev-parse --show-toplevel)"
RAMA="$(git -C "$REPO" rev-parse --abbrev-ref HEAD)"

git -C "$REPO" fetch --quiet origin "$RAMA"
ANTES="$(git -C "$REPO" rev-parse HEAD)"
NUEVO="$(git -C "$REPO" rev-parse "origin/$RAMA")"
if [ "$ANTES" = "$NUEVO" ]; then
  exit 0                                                    # no hay nada nuevo
fi

echo "Versión nueva: ${ANTES:0:7} -> ${NUEVO:0:7}"
git -C "$REPO" merge --ff-only "origin/$RAMA"

# A partir de aquí, si algo sale mal se vuelve a la versión que funcionaba
trap 'echo "Algo ha fallado: vuelvo a ${ANTES:0:7} sin tocar el evento."; \
      git -C "$REPO" reset --hard "$ANTES"; \
      sudo systemctl restart neaevento || true; exit 1' ERR

"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
# Las pruebas usan una base de datos temporal: NO tocan el evento de verdad
(cd "$APP_DIR" && ./venv/bin/python pruebas.py)
sudo systemctl restart neaevento
trap - ERR

echo "Actualizado a ${NUEVO:0:7} y reiniciado. Todo en orden."
