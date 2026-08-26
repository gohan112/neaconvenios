# Imagen para desplegar NeaEvento en un servidor (p. ej. AWS Lightsail).
# Construir DESDE esta carpeta:   docker build -t neaevento evento/
# Ejecutar (la base de datos vive en el volumen /data para no perderla):
#   docker run -d -p 8502:8502 -v neaevento_datos:/data \
#     -e EVENTO_ADMIN_PASSWORD=... neaevento
FROM python:3.12-slim

WORKDIR /app

# Dependencias primero (mejor cacheo de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código y logos
COPY *.py ./
COPY assets/ ./assets/

# La base de datos (evento.db) se guarda fuera de la imagen, en /data
ENV EVENTO_DB_PATH=/data/evento.db
VOLUME /data

ENV TZ=Europe/Madrid
EXPOSE 8502

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8502/salud')" || exit 1

CMD ["python", "app.py"]
