#!/usr/bin/env bash
# Instalador de NeaConvenios en un servidor Ubuntu (AWS Lightsail).
# Se ejecuta DENTRO de la carpeta de la app ya descargada. Deja la app corriendo
# como servicio (se reinicia sola) en el puerto 8501.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"
echo ">> Instalando NeaConvenios en: $APP_DIR"

echo ">> 0/4 Memoria de intercambio (evita errores en servidores pequeños)…"
if ! sudo swapon --show | grep -q .; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile \
    && sudo mkswap /swapfile && sudo swapon /swapfile || true
fi

echo ">> 1/4 Paquetes del sistema…"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-pip

echo ">> 2/4 Entorno Python y dependencias…"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo ">> 3/4 Variable de la API key (vacía de momento; se puede añadir luego)…"
if [ ! -f /etc/neaconvenios.env ]; then
  echo 'ANTHROPIC_API_KEY=' | sudo tee /etc/neaconvenios.env >/dev/null
fi

echo ">> 4/4 Servicio del sistema (arranque automático)…"
sudo tee /etc/systemd/system/neaconvenios.service >/dev/null <<SERVICE
[Unit]
Description=NeaConvenios
After=network.target

[Service]
WorkingDirectory=$APP_DIR
EnvironmentFile=/etc/neaconvenios.env
ExecStart=$APP_DIR/venv/bin/python -m streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false
Restart=always
User=$(whoami)

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable --now neaconvenios
sleep 3
sudo systemctl --no-pager status neaconvenios | head -5 || true

IP="$(curl -s ifconfig.me || echo TU_IP_PUBLICA)"
echo ""
echo "============================================================"
echo "  NeaConvenios en marcha."
echo "  Abre en el navegador:  http://$IP:8501"
echo "  (Falta abrir el puerto 8501 en el firewall de Lightsail)"
echo "============================================================"
