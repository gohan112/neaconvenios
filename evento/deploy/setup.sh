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

echo ">> 3/4 Contraseña del panel…"
PASS_NUEVA=""
if [ ! -f /etc/neaevento.env ] || ! sudo grep -q '^EVENTO_ADMIN_PASSWORD=..*' /etc/neaevento.env; then
  # Se genera una contraseña aleatoria y se enseña al final (apúntala)
  PASS_NUEVA="$(head -c 256 /dev/urandom | tr -dc 'A-Za-z0-9' | cut -c1-14)"
  printf 'EVENTO_ADMIN_PASSWORD=%s\n' "$PASS_NUEVA" | sudo tee /etc/neaevento.env >/dev/null
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

# IP pública IPv4. Se pregunta primero a los metadatos de la propia instancia
# (dentro de AWS es lo fiable); si no, a un servicio externo forzando IPv4 con
# -4: sin eso, una máquina con IPv6 responde su dirección larga, que no vale
# para repartir enlaces.
ip_publica() {
  local ip token
  ip="$(curl -s -m 3 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)"
  if [ -z "$ip" ]; then
    token="$(curl -s -m 3 -X PUT http://169.254.169.254/latest/api/token \
             -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' 2>/dev/null || true)"
    if [ -n "$token" ]; then
      ip="$(curl -s -m 3 -H "X-aws-ec2-metadata-token: $token" \
            http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)"
    fi
  fi
  [ -z "$ip" ] && ip="$(curl -4 -s -m 5 ifconfig.me 2>/dev/null || true)"
  case "$ip" in
    *[0-9].[0-9]*) printf '%s' "$ip" ;;
    *) printf '%s' "TU_IP_PUBLICA" ;;
  esac
}
IP="$(ip_publica)"
echo ""
echo "============================================================"
echo "  NeaEvento en marcha."
echo ""
echo "  Panel de organización:  http://$IP:8502/admin"
if [ -n "$PASS_NUEVA" ]; then
  echo "  Contraseña del panel:   $PASS_NUEVA   <-- APÚNTALA"
else
  echo "  Contraseña del panel:   la de siempre (está en /etc/neaevento.env)"
fi
echo ""
echo "  Te quedan solo 2 pasos:"
echo "   1) En la web de Lightsail: instancia -> pestaña «Networking» ->"
echo "      «+ Add rule» -> TCP, puerto 8502 -> Save."
echo "   2) En el panel ⚙️ Evento, fija la URL pública: http://$IP:8502"
echo "============================================================"
