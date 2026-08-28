#!/usr/bin/env bash
# Instalación de NeaEvento en un Lightsail (Ubuntu) con UN solo comando.
# Se pega en el terminal del navegador de Lightsail («Connect using SSH»):
#
#   curl -fsSL https://raw.githubusercontent.com/gohan112/neaconvenios/claude/event-app-day-12-e4lcrp/evento/deploy/lightsail.sh | bash
#
# Descarga el código y ejecuta evento/deploy/setup.sh (servicio en el puerto 8502).
set -euo pipefail

RAMA="claude/event-app-day-12-e4lcrp"
DESTINO="$HOME/neaevento"

echo ">> Preparando git…"
sudo apt-get update -y >/dev/null
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git >/dev/null

if [ -d "$DESTINO/.git" ]; then
  echo ">> Actualizando el código en $DESTINO…"
  git -C "$DESTINO" fetch origin "$RAMA"
  git -C "$DESTINO" checkout "$RAMA"
  git -C "$DESTINO" pull origin "$RAMA"
else
  echo ">> Descargando el código en $DESTINO…"
  git clone --branch "$RAMA" --depth 1 https://github.com/gohan112/neaconvenios.git "$DESTINO"
fi

bash "$DESTINO/evento/deploy/setup.sh"
