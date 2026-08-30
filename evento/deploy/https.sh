#!/usr/bin/env bash
# Pone NeaEvento en https con un certificado de verdad y gratis (Let's Encrypt).
#
#   bash deploy/https.sh
#
# ¿Para qué? Con https el móvil deja de avisar de «sitio no seguro» y Android
# ofrece instalar la app de verdad (con su icono y sin barras del navegador).
# Usa un dominio gratis del tipo 13.38.46.216.nip.io, que apunta a esta misma
# máquina: no hay que comprar nada ni tocar DNS.
#
# ANTES de ejecutarlo: en la web de Lightsail, instancia -> «Networking» ->
# «+ Add rule», abre los puertos 80 (HTTP) y 443 (HTTPS). Sin eso, Let's
# Encrypt no puede comprobar el dominio y el certificado no sale.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PUERTO="${PUERTO:-8502}"

# --------------------------------------------------------------- la dirección
ip_publica() {
  local ip token
  ip="$(curl -s -m 3 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)"
  if [ -z "$ip" ]; then
    token="$(curl -s -m 3 -X PUT http://169.254.169.254/latest/api/token \
             -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' 2>/dev/null || true)"
    [ -n "$token" ] && ip="$(curl -s -m 3 -H "X-aws-ec2-metadata-token: $token" \
      http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)"
  fi
  [ -z "$ip" ] && ip="$(curl -4 -s -m 5 ifconfig.me 2>/dev/null || true)"
  printf '%s' "$ip"
}

DOMINIO="${1:-}"
if [ -z "$DOMINIO" ]; then
  IP="$(ip_publica)"
  case "$IP" in
    *[0-9].[0-9]*) DOMINIO="${IP}.nip.io" ;;
    *) echo "No he podido averiguar la IP pública. Pásame el dominio:"
       echo "   bash deploy/https.sh mi-dominio.com"; exit 1 ;;
  esac
fi
echo ">> Dominio: $DOMINIO"

# ------------------------------------------------------------ puertos abiertos
echo ">> Comprobando que el puerto 80 se ve desde fuera…"
if ! curl -s -m 8 "https://api.ipify.org" >/dev/null 2>&1; then
  echo "   (sin internet para comprobar; sigo de todas formas)"
fi

# ------------------------------------------------------------------- Caddy
if ! command -v caddy >/dev/null 2>&1; then
  echo ">> Instalando Caddy (el que pide y renueva el certificado)…"
  sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y caddy
fi

echo ">> Configurando Caddy para $DOMINIO -> localhost:$PUERTO…"
sudo tee /etc/caddy/Caddyfile >/dev/null <<CADDY
$DOMINIO {
	encode gzip
	reverse_proxy localhost:$PUERTO
}
CADDY
sudo systemctl enable caddy >/dev/null 2>&1 || true
sudo systemctl restart caddy
sleep 6

# --------------------------------------------- la app genera los enlaces https
echo ">> Fijando la URL pública en el evento (los enlaces saldrán con https)…"
cd "$APP_DIR"
"$APP_DIR/venv/bin/python" -c "
import sys; sys.path.insert(0, '$APP_DIR')
import db
db.guardar_config({'url_base': 'https://$DOMINIO'})
print('   url_base =', db.leer_config().get('url_base'))
"

echo ""
echo "============================================================"
echo "  Comprueba que responde:"
echo "     https://$DOMINIO/admin"
echo ""
echo "  Si da error de certificado, casi siempre es que faltan los"
echo "  puertos 80 y 443 abiertos en Lightsail («Networking»)."
echo "  Mira qué dice Caddy con:   sudo journalctl -u caddy -n 30"
echo ""
echo "  Los enlaces de los participantes ya salen con https, pero los"
echo "  que repartieras antes (http://IP:$PUERTO/p/...) siguen valiendo:"
echo "  la app sigue escuchando en el puerto $PUERTO."
echo "============================================================"
