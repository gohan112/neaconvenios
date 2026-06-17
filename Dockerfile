# Imagen para desplegar la app de convenios en un servidor (p. ej. AWS Lightsail).
# Empaqueta Python + dependencias + la app. La API key NO va aquí: se pasa como
# variable de entorno al arrancar (docker run -e ANTHROPIC_API_KEY=...).
FROM python:3.12-slim

WORKDIR /app

# Dependencias primero (mejor cacheo de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la app (los .py; no se necesitan los PDF/SQL de ejemplo en producción)
COPY *.py ./

EXPOSE 8501

# Healthcheck para que el orquestador sepa si la app está viva
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Arranque. --server.address 0.0.0.0 para que sea accesible desde fuera del contenedor.
CMD ["python", "-m", "streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
