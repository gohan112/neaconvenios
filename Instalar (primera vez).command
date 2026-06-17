#!/bin/bash
# Doble clic UNA sola vez para instalar lo que necesita la app.
cd "$(dirname "$0")" || exit 1

echo "Instalando dependencias (puede tardar 1-2 minutos)..."
python3 -m pip install -r requirements.txt

echo ""
echo "Listo. Ya puedes abrir la app con 'Abrir Convenios.command'."
echo "Pulsa Enter para cerrar."
read -r
