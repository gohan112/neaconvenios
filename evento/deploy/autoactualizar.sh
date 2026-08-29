#!/usr/bin/env bash
# Trae la última versión del código desde GitHub y reinicia la app, pero solo
# si las pruebas siguen pasando: si algo falla, se queda la versión anterior
# (la app no se cae nunca por una actualización) y no vuelve a intentar esa
# misma versión rota hasta que se suba una nueva.
#
# Lo lanza solo el temporizador neaevento-update.timer cada 5 minutos.
# Para ver qué ha hecho:  journalctl -u neaevento-update -n 50
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"                 # …/evento
REPO="$(git -C "$APP_DIR" rev-parse --show-toplevel)"
RAMA="$(git -C "$REPO" rev-parse --abbrev-ref HEAD)"
FALLIDA="$APP_DIR/.version_fallida"

git -C "$REPO" fetch --quiet origin "$RAMA"
ANTES="$(git -C "$REPO" rev-parse HEAD)"
NUEVO="$(git -C "$REPO" rev-parse "origin/$RAMA")"
if [ "$ANTES" = "$NUEVO" ]; then
  exit 0                                                    # no hay nada nuevo
fi
if [ -f "$FALLIDA" ] && [ "$(cat "$FALLIDA")" = "$NUEVO" ]; then
  exit 0                                        # esa versión ya falló: ni la toco
fi

echo "Versión nueva: ${ANTES:0:7} -> ${NUEVO:0:7}"
git -C "$REPO" merge --ff-only "origin/$RAMA"

# A partir de aquí, si algo sale mal se vuelve a la versión que funcionaba.
# Solo hace falta reiniciar si el fallo llegó al propio reinicio.
FASE="preparando"
trap 'echo "Algo ha fallado (${FASE}): vuelvo a ${ANTES:0:7} sin tocar el evento."; \
      echo "$NUEVO" > "$FALLIDA"; \
      git -C "$REPO" reset --hard "$ANTES"; \
      [ "$FASE" = "reiniciando" ] && sudo systemctl restart neaevento; \
      exit 1' ERR

"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
FASE="pruebas"
# Las pruebas usan una base de datos temporal: NO tocan el evento de verdad
(cd "$APP_DIR" && ./venv/bin/python pruebas.py)
FASE="reiniciando"
sudo systemctl restart neaevento
trap - ERR
rm -f "$FALLIDA"

echo "Actualizado a ${NUEVO:0:7} y reiniciado. Todo en orden."
