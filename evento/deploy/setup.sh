#!/usr/bin/env bash
# Instalador de NeaEvento en un servidor Ubuntu (p. ej. AWS Lightsail).
# Se ejecuta DENTRO de la carpeta evento/ ya descargada. Deja la app corriendo
# como servicio (se reinicia sola) en el puerto 8502.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"
echo ">> Instalando NeaEvento en: $APP_DIR"

echo ">> 1/4 Paquetes del sistema…"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip

echo ">> 2/4 Entorno Python y dependencias…"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo ">> 3/4 Contraseña del panel (vacía de momento; PONLA antes de repartir enlaces)…"
if [ ! -f /etc/neaevento.env ]; then
  printf 'EVENTO_ADMIN_PASSWORD=\n' | sudo tee /etc/neaevento.env >/dev/null
  sudo chmod 600 /etc/neaevento.env
fi

echo ">> 4/4 Servicio del sistema (arranque automático)…"
sudo tee /etc/systemd/system/neaevento.service >/dev/null <<SERVICE
[Unit]
Description=NeaEvento
After=network.target

[Service]
WorkingDirectory=$APP_DIR
EnvironmentFile=/etc/neaevento.env
ExecStart=$APP_DIR/venv/bin/python app.py
Restart=always
User=$(whoami)

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable --now neaevento
sleep 3
sudo systemctl --no-pager status neaevento | head -5 || true

IP="$(curl -s ifconfig.me || echo TU_IP_PUBLICA)"
echo ""
echo "============================================================"
echo "  NeaEvento en marcha."
echo "  Panel de organización:  http://$IP:8502/admin"
echo "  (Falta abrir el puerto 8502 en el firewall de Lightsail)"
echo ""
echo "  IMPORTANTE antes de repartir enlaces:"
echo "   1) Pon la contraseña:  sudo nano /etc/neaevento.env"
echo "      y reinicia:         sudo systemctl restart neaevento"
echo "   2) En el panel ⚙️ Evento, fija la URL pública: http://$IP:8502"
echo "============================================================"
